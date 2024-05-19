import json, sys
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union, List
from fastapi import Depends, FastAPI, HTTPException, status, Request, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel
from passlib.apps import custom_app_context as pwd_context
from passlib.context import CryptContext
from langchain_openai import ChatOpenAI
from openaiCBHandler import get_cost_tracker_callback
from dotenv import load_dotenv
load_dotenv()

from leither_api import get_user, register, delete_user, update_user, get_users
from utilities import ConnectionManager, MAX_TOKEN, UserIn, UserOut, UserInDB

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "ebf79dbbdcf6a3c860650661b3ca5dc99b7d44c269316c2bd9fe7c7c5e746274"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
connectionManager = ConnectionManager()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

class User(UserInDB):
    pass

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
router = APIRouter(prefix="/ajchat")
app = FastAPI()
app.include_router(router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

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
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    print("form data", form_data)
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    token = Token(access_token=access_token, token_type="Bearer")
    return {"token": token, "user": user}

# @app.post("/authenticate")
# async def authenticate_user(formd_data: Annotated[OAuth2PasswordRequestForm, Depends()], token: Annotated[str, Depends(oauth2_scheme)]):
#     print(formd_data)
#     return get_user(formd_data.username)

@app.post("/ajchat/users/register")
async def register_user(user: UserIn):
    print(user)
    return register(user)

@app.get("/users", response_model=UserOut)
async def get_user_by_id(current_user: Annotated[UserOut, Depends(get_current_user)]):
    return current_user

@app.get("/users/all", response_model=List[UserOut])
async def get_all_users(current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin":
        raise HTTPException(status_code=400, detail="Not admin")
    return get_users()

@app.delete("/users")
async def delete_user_by_id(username: str, current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin":
        raise HTTPException(status_code=400, detail="Not admin")
    return delete_user(username)

@app.put("/users")
async def update_user_by_id(user: Annotated[UserIn, Depends()], current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != user.username:
        raise HTTPException(status_code=400, detail="Not admin")
    return update_user(user)

@app.get("/")
async def get():
    return HTMLResponse("Hello world.")

@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await connectionManager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            event = json.loads(message)
            print(event)
            await websocket.send_text(json.dumps({
                    "type": "result",
                    "answer": "Message received fine", 
                    "tokens": "111",
                    "cost": "0.01"}))
            continue
            params = event["parameters"]
            if params["llm"] == "openai":
                CHAT_LLM = ChatOpenAI(
                    temperature=float(params["temperature"]),
                    model=params["model"],
                    streaming=True,
                    verbose=True
                    )     # ChatOpenAI cannot have max_token=-1
            elif params["llm"] == "qianfan":
                pass

            # CHAT_LLM.callbacks=[MyStreamingHandler()]
            # query = event["input"]["query"]
            # memory = ConversationBufferMemory(return_messages=False)
            if event["input"].get("history"):
                # user server history if history key is not present in user request
                # memory.clear()  # do not use memory on serverside. Add chat history kept by client.
                query = "The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\nCurrent conversation:\n"
                hlen = 0
                for c in event["input"]["history"]:
                    hlen += len(c["Q"]) + len(c["A"])
                    if hlen > MAX_TOKEN[params["model"]]/2:
                        break
                    else:
                        query += "Human: "+c["Q"]+"\nAI:\n"+c["A"]+"\n"
                query += "Human: "+event["input"]["query"]+"\nAI:"

            with get_cost_tracker_callback(params["model"]) as cb:
                # chain = ConversationChain(llm=CHAT_LLM, memory=memory, output_parser=StrOutputParser())
                chain =CHAT_LLM
                resp = ""
                async for chunk in chain.astream(query):
                    print(chunk, end="|", flush=True)    # chunk size can be big
                    resp += chunk.content
                    await websocket.send(json.dumps({"type": "stream", "data": chunk.content}))
                print('\n', cb)
                sys.stdout.flush()
                await websocket.send(json.dumps({
                    "type": "result",
                    "answer": chunk["response"], 
                    "tokens": cb.total_tokens,
                    "cost": cb.total_cost}))

    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8506)
