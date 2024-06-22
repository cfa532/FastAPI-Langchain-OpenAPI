import json
import sys
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union, List

from fastapi import Depends, FastAPI, HTTPException, status, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv, dotenv_values

from apscheduler.schedulers.background import BackgroundScheduler
from openaiCBHandler import get_cost_tracker_callback
from leither_api import LeitherAPI
from utilities import ConnectionManager, UserIn, UserOut, UserInDB
from pet_hash import get_password_hash, verify_password
import apple_notification_sandbox, apple_notification_production

# Load environment variables
load_dotenv()

# Constants
SECRET_KEY = "ebf79dbbdcf6a3c860650661b3ca5dc99b7d44c269316c2bd9fe7c7c5e746274"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 480  # Token expires in 480 weeks
BASE_ROUTE = "/secretari"
MIN_BALANCE = 0.1
MAX_EXPENSE = 15.0
MAX_TOKEN = {
    "gpt-4o": 8192,
    "gpt-4": 4096,
    "gpt-4-turbo": 8192,
    "gpt-3.5-turbo": 4096,
}

# Initialize utilities
connectionManager = ConnectionManager()
lapi = LeitherAPI()

# Load environment-specific configurations
env = dotenv_values(".env")
LLM_MODEL = env["CURRENT_LLM_MODEL"]
OPENAI_KEYS = env["OPENAI_KEYS"].split('|')
SERVER_MAINTENCE = env["SERVER_MAINTENCE"]

# Token splitter configuration
token_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=MAX_TOKEN[LLM_MODEL]/4*3,  # Set your desired chunk size in tokens
    chunk_overlap=50  # Set the overlap between chunks if needed
)

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# FastAPI app initialization
app = FastAPI()

# Background scheduler for periodic tasks
scheduler = BackgroundScheduler()

def periodic_task():
    """Periodic task to update environment variables."""
    env = dotenv_values(".env")
    global LLM_MODEL, OPENAI_KEYS, SERVER_MAINTENCE
    LLM_MODEL = env["CURRENT_LLM_MODEL"]
    OPENAI_KEYS = env["OPENAI_KEYS"].split('|')
    SERVER_MAINTENCE = env["SERVER_MAINTENCE"]

scheduler.add_job(periodic_task, 'interval', seconds=3600)
scheduler.start()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

def authenticate_user(username: str, password: str) -> UserOut:
    """Authenticate user by username and password."""
    user = lapi.get_user(username)
    if user is None:
        return None
    if password != "" and not verify_password(password, user.hashed_password):
        return None
    return UserOut(**user.model_dump())

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """Get the current user from the token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = lapi.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.post(BASE_ROUTE + "/token")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Login endpoint to get an access token."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(weeks=ACCESS_TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    token = Token(access_token=access_token, token_type="Bearer")
    return {"token": token, "user": user.model_dump()}

@app.post(BASE_ROUTE + "/users/register")
async def register_user(user: UserIn) -> UserOut:
    """Register a new user."""
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # Save hashed password in DB
    user = lapi.register_in_db(UserInDB(**user_in_db))
    if not user:
        raise HTTPException(status_code=400, detail="Username already taken")
    return user

@app.post(BASE_ROUTE + "/users/temp")
async def register_temp_user(user: UserIn):
    """Register a temporary user."""
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # Save hashed password in DB
    user = lapi.register_temp_user(UserInDB(**user_in_db))
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create temp User.")
    
    access_token_expires = timedelta(weeks=ACCESS_TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    token = Token(access_token=access_token, token_type="Bearer")

    return {"token": token, "user": user}

@app.post(BASE_ROUTE + "/users/redeem")
async def cash_coupon(coupon: str, current_user: Annotated[UserInDB, Depends(get_current_user)]) -> bool:
    """Redeem a coupon."""
    return lapi.cash_coupon(current_user, coupon)

@app.put(BASE_ROUTE + "/users")
async def update_user_by_obj(user: UserIn, user_in_db: Annotated[UserInDB, Depends(get_current_user)]):
    """Update user information."""
    user_in_db.family_name = user.family_name
    user_in_db.given_name = user.given_name
    user_in_db.email = user.email
    if user.password:
        user_in_db.hashed_password = get_password_hash(user.password)  # Save hashed password in DB
    return lapi.update_user(user_in_db).model_dump()

@app.get(BASE_ROUTE + "/productids")
async def get_productIDs():
    """Get current product IDs."""
    product_ids = dotenv_values(".env")["SECRETARI_PRODUCT_ID_IOS"]
    return json.loads(product_ids)

@app.post(BASE_ROUTE + "/app_server_notifications_production")
async def apple_notifications_production(request: Request):
    """Handle Apple production notifications."""
    try:
        body = await request.json()
        await apple_notification_production.decode_notification(lapi, body["signedPayload"])
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=400, detail="Invalid notification data")

@app.post(BASE_ROUTE + "/app_server_notifications_sandbox")
async def apple_notifications_sandbox(request: Request):
    """Handle Apple sandbox notifications."""
    try:
        body = await request.json()
        await apple_notification_sandbox.decode_notification(lapi, body["signedPayload"])
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=400, detail="Invalid notification data")

@app.get(BASE_ROUTE + "/notice")
async def get_notice():
    """Get the current notice."""
    env = dotenv_values(".env")
    return HTMLResponse(env["NOTICE"])

@app.get(BASE_ROUTE + "/public/{page}", response_class=HTMLResponse)
async def get_files(page: str):
    """Serve the index.html file."""
    if page == "privacy":
        filepath = "./public/privacy.html"
    else:
        filepath = "./public/index.html"
    with open(filepath, "r") as file:
        content = file.read()
    return HTMLResponse(content=content)

@app.websocket(BASE_ROUTE + "/ws/")
async def websocket_endpoint(websocket: WebSocket, token: str = Query()):
    """WebSocket endpoint for real-time communication."""
    await connectionManager.connect(websocket)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise WebSocketDisconnect
        token_data = TokenData(username=username)
        user = lapi.get_user(username=token_data.username)
        if not user:
            raise WebSocketDisconnect
        
        if SERVER_MAINTENCE == "true":
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Server is under maintenance. Please try again later.",
            }))
            await websocket.close()
            return
        
        while True:
            message = await websocket.receive_text()
            event = json.loads(message)
            query = event["input"]
            params = event["parameters"]
            llm_model = LLM_MODEL

            if query["prompt_type"] == "memo":
                llm_model = "gpt-4-turbo"

            if not query["subscription"]:
                if user.dollar_balance <= MIN_BALANCE:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Low balance. Please purchase consumable product or subscribe.", 
                    }))
                    continue
                elif user.dollar_balance < MIN_BALANCE:
                    llm_model = "gpt-3.5-turbo"
                    token_splitter._chunk_size = MAX_TOKEN["gpt-3.5-turbo"]
            else:
                current_month = str(datetime.now().month)
                if user.monthly_usage.get(current_month) and user.monthly_usage.get(current_month) >= MAX_EXPENSE:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Monthly max expense exceeded. Purchase consumable product if necessary.", 
                    }))
                    continue

            if params["llm"] == "openai":
                CHAT_LLM = ChatOpenAI(
                    api_key=random.choice(OPENAI_KEYS),
                    temperature=float(params["temperature"]),
                    model=llm_model,
                    streaming=True,
                    verbose=True
                )
            elif params["llm"] == "qianfan":
                continue

            chain = CHAT_LLM
            resp = ""
            chunks = token_splitter.split_text(query["rawtext"])
            for index, ci in enumerate(chunks):
                with get_cost_tracker_callback(llm_model) as cb:
                    async for chunk in chain.astream(query["prompt"] + "\n\n" + ci):
                        resp += chunk.content
                        await websocket.send_text(json.dumps({"type": "stream", "data": chunk.content}))

                    await websocket.send_text(json.dumps({
                        "type": "result",
                        "answer": resp,
                        "tokens": int(cb.total_tokens * lapi.cost_efficiency),
                        "cost": cb.total_cost * lapi.cost_efficiency,
                        "eof": index == (len(chunks) - 1),
                    }))
                    lapi.bookkeeping(cb.total_cost, cb.total_tokens, user)

    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)
    except JWTError:
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid token. Try to re-login."}))
    except HTTPException as e:
        pass

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8506)