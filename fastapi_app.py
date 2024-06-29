import json, sys, random
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union
from fastapi import Depends, FastAPI, HTTPException, status, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv, dotenv_values
load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from openaiCBHandler import get_cost_tracker_callback
from leither_api import LeitherAPI
from utilities import ConnectionManager, UserIn, UserOut, UserInDB
from pet_hash import get_password_hash, verify_password
import apple_notification_sandbox, apple_notification_production

# to get a string like this run: openssl rand -hex 32
SECRET_KEY = "ebf79dbbdcf6a3c860650661b3ca5dc99b7d44c269316c2bd9fe7c7c5e746274"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 480   # expires in 480 weeks
BASE_ROUTE = "/secretari"
MIN_BALANCE = 0.1
MAX_EXPENSE = 15.0
MAX_TOKEN = {
    "gpt-4o": 8192,
    "gpt-4": 4096,
    "gpt-4-turbo": 8192,
    "gpt-3.5-turbo": 4096,
}
connectionManager = ConnectionManager()
lapi = LeitherAPI()

env = dotenv_values(".env")
LLM_MODEL = env["CURRENT_LLM_MODEL"]
OPENAI_KEYS = env["OPENAI_KEYS"].split('|')
SERVER_MAINTENCE = env["SERVER_MAINTENCE"]

token_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name = "cl100k_base",
    chunk_size = MAX_TOKEN[LLM_MODEL]/4*3,  # Set your desired chunk size in tokens
    chunk_overlap = 50  # Set the overlap between chunks if needed
)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()
scheduler = BackgroundScheduler()

def periodic_task():
    env = dotenv_values(".env")
    global LLM_MODEL, OPENAI_KEYS, SERVER_MAINTENCE
    # export as defualt parameters. Values updated hourly.
    LLM_MODEL = env["CURRENT_LLM_MODEL"]
    OPENAI_KEYS = env["OPENAI_KEYS"].split('|')
    SERVER_MAINTENCE=env["SERVER_MAINTENCE"]

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
    user = lapi.get_user(username)    # check index db
    if user is None:
        return None
    if password != "" and not verify_password(password, user.hashed_password):
        # if password is empty string, this is a temp user. "" not equal to None.
        return None
    # check if index db record exists. If not, the user has been deleted.
    user_in_db = lapi.get_user_in_db(user)
    if user_in_db is None:
        return None
    return UserOut(**user.model_dump())

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
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
async def login_for_access_token( form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    print("form data", form_data.username, form_data.client_id)
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
    # If user has tried service, there is valid mid attribute. Otherwise, it is None
    print("User in for register:", user)
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB
    user = lapi.register_in_db(UserInDB(**user_in_db))
    if not user:
        raise HTTPException(status_code=400, detail="Username already taken")
    print("User out", user)
    return user

@app.post(BASE_ROUTE + "/users/temp")
async def register_temp_user(user: UserIn):
    # A temp user has assigned username, usuall the device identifier.
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB
    user = lapi.register_temp_user(UserInDB(**user_in_db))
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create temp User.")
    
    access_token_expires = timedelta(weeks=ACCESS_TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    token = Token(access_token=access_token, token_type="Bearer")

    # create a token for temp user too, so they can buy product and access premium service without login.
    return {"token": token, "user": user}

# redeem coupons
@app.post(BASE_ROUTE + "/users/redeem")
async def cash_coupon(coupon: str, current_user: Annotated[UserInDB, Depends(get_current_user)]) -> bool:
    return lapi.cash_coupon(current_user, coupon)

#update user infor
@app.put(BASE_ROUTE + "/users")
async def update_user_by_obj(user: UserIn, user_in_db: Annotated[UserInDB, Depends(get_current_user)]):
    user_in_db.family_name = user.family_name
    user_in_db.given_name = user.given_name
    user_in_db.email = user.email
    # if User password is null, do not update it.
    if user.password:
        user_in_db.hashed_password = get_password_hash(user.password)  # save hashed password in DB
    return lapi.update_user(user_in_db).model_dump()

# delete current user, return {id: user_id}
@app.delete(BASE_ROUTE + "/users")
async def delete_user(user_in_db: Annotated[UserInDB, Depends(get_current_user)]):
    ret = lapi.delete_user(user_in_db)
    print("delete=", ret)
    return ret

# get current product IDs
@app.get(BASE_ROUTE + "/productids")
async def get_productIDs():
    product_ids = dotenv_values(".env")["SECRETARI_PRODUCT_ID_IOS"]
    # return HTMLResponse("Hello world.")
    return json.loads(product_ids)

@app.post(BASE_ROUTE + "/app_server_notifications_production")
async def apple_notifications_production(request: Request):
    try:
        body = await request.json()
        await apple_notification_production.decode_notification(lapi, body["signedPayload"])
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=400, detail="Invalid notification data")

@app.post(BASE_ROUTE + "/app_server_notifications_sandbox")
async def apple_notifications_sandbox(request: Request):
    try:
        body = await request.json()
        await apple_notification_sandbox.decode_notification(lapi, body["signedPayload"])
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=400, detail="Invalid notification data")

@app.get(BASE_ROUTE + "/notice")
async def get_notice():
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
    await connectionManager.connect(websocket)
    try:
        # token = websocket.query_params.get("token")
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
            print("Incoming event: ", event)    # request from client, with parameters
            query = event["input"]
            params = event["parameters"]
            llm_model = LLM_MODEL

            # Turbo seems to have just the right content for memo. 4o does better in summarizing.
            # if query["prompt_type"] == "memo":
            #     llm_model = "gpt-4-turbo"

            # when dollar balance is lower than $0.1, user gpt-3.5-turbo
            if not query["subscription"]:
                if user.dollar_balance <= MIN_BALANCE:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Low balance. Please purchase consumable product or subscribe.", 
                        }))
                    continue
                elif user.dollar_balance <= MIN_BALANCE:
                    llm_model = "gpt-3.5-turbo"
                    token_splitter._chunk_size = MAX_TOKEN["gpt-3.5-turbo"]
            else:
                # a subscriber. Check monthly usage
                current_month = str(datetime.now().month)
                if user.monthly_usage.get(current_month) and user.monthly_usage.get(current_month) >= MAX_EXPENSE:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Monthly max expense exceeded. Purchase consumable product if necessary.", 
                        }))
                    continue

            # create the right Chat LLM
            if params["llm"] == "openai":
                # randomly select OpenAI key from a list
                CHAT_LLM = ChatOpenAI(
                    api_key = random.choice(OPENAI_KEYS),       # pick a random OpenAI key from a list
                    temperature = float(params["temperature"]),
                    model = llm_model,
                    streaming = True,
                    verbose = True
                )
            elif params["llm"] == "qianfan":
                continue

            # lapi.bookkeeping(0.015, 123, user)
            # await websocket.send_text(json.dumps({
            #     "type": "result",
            #     "answer": event["input"]["rawtext"], 
            #     "tokens": int(111 * lapi.cost_efficiency),
            #     "cost": 0.015 * lapi.cost_efficiency,
            #     }))
            # continue

            chain = CHAT_LLM
            resp = ""
            chunks = token_splitter.split_text(query["rawtext"])
            for index, ci in enumerate(chunks):
                with get_cost_tracker_callback(llm_model) as cb:
                    # chain = ConversationChain(llm=CHAT_LLM, memory=memory, output_parser=StrOutputParser())
                    print(ci)
                    async for chunk in chain.astream(query["prompt"] + "\n\n" + ci):
                        print(chunk.content, end="|", flush=True)    # chunk size can be big
                        resp += chunk.content
                        await websocket.send_text(json.dumps({"type": "stream", "data": chunk.content}))
                    print('\n', cb, '\nLLMModel:', llm_model, index, len(chunks))
                    sys.stdout.flush()

                    await websocket.send_text(json.dumps({
                        "type": "result",
                        "answer": resp,
                        "tokens": int(cb.total_tokens * lapi.cost_efficiency),  # sum of prompt tokens and comletion tokens. Prices are different.
                        "cost": cb.total_cost * lapi.cost_efficiency,           # total cost in USD
                        "eof": index == (len(chunks) - 1),                      # end of content
                        }))
                    lapi.bookkeeping(cb.total_cost, cb.total_tokens, user)

    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)
    except JWTError:
        print("JWTError", e)
        sys.stdout.flush()
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid token. Try to re-login."}))
    except HTTPException as e:
        print("HTTPException", e)
        sys.stdout.flush()
        # connectionManager.disconnect(websocket)
    # finally:
    #     if websocket.client_state == WebSocketState.CONNECTED:
    #         await websocket.close()

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8506)