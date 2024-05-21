import json, sys, bcrypt, time
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from typing import Annotated, Union, List
from fastapi import Depends, FastAPI, HTTPException, status, Request, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from openaiCBHandler import get_cost_tracker_callback
from dotenv import load_dotenv
load_dotenv()

from leither_api import get_user, register_in_db, delete_user, update_user, get_users, get_user_session
from utilities import ConnectionManager, MAX_TOKEN, UserIn, UserOut, UserInDB
import time

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "ebf79dbbdcf6a3c860650661b3ca5dc99b7d44c269316c2bd9fe7c7c5e746274"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480   # expire in 8 hrs
BASE_ROUTE = "/aichat"
connectionManager = ConnectionManager()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

class User(UserInDB):
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    get_user_session()
    yield
    # Clean up the ML models and release the resources
    # ml_models.clear()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(password = plain_password.encode('utf-8') , hashed_password = hashed_password.encode('utf-8'))

def get_password_hash(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)
    return hashed_password
    # return pwd_context.hash(password)

def authenticate_user(username: str, password: str, identtifer: str):
    user = get_user(username, identtifer)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
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


@app.post(BASE_ROUTE+"/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    print("form data", form_data.username, form_data.client_id)
    start_time = time.time()
    user = authenticate_user(form_data.username, form_data.password, form_data.client_id)
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
    user_out = user.model_dump(exclude=["hashed_password"])
    print("--- %s seconds ---" % (time.time() - start_time))
    return {"token": token, "user": user_out, "session": get_user_session()}

@app.post(BASE_ROUTE+"/users/register")
async def register_user(user: UserIn):
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB
    return register_in_db(UserInDB(**user_in_db))
    # return False

@app.get(BASE_ROUTE+"/users", response_model=UserOut)
async def get_user_by_id(id: str, current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != id:
        raise HTTPException(status_code=400, detail="Not admin")
    return get_user(id)
    # return current_user

@app.get(BASE_ROUTE+"/users/all", response_model=List[UserOut])
async def get_all_users(current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin":
        return [UserOut(**current_user.model_dump())] 
    return get_users()

@app.delete(BASE_ROUTE+"/users/{username}")
async def delete_user_by_id(username: str, current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(status_code=400, detail="Not admin")
    return delete_user(username)

#update user infor
@app.put(BASE_ROUTE+"/users")
async def update_user_by_obj(user: UserIn, current_user: Annotated[UserOut, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != user.username:
        raise HTTPException(status_code=400, detail="Not admin")
    user_in_db = user.model_dump(exclude=["password"])

    # if no password, do not update it
    if user.password != "":
        user_in_db["hashed_password"] = get_password_hash(user.password)
    return update_user(UserInDB(**user_in_db))

@app.get(BASE_ROUTE+"/")
async def get():
    return HTMLResponse("Hello world.")

@app.websocket(BASE_ROUTE+"/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await connectionManager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            event = json.loads(message)
            # print(event)
            # await websocket.send_text(json.dumps({
            #         "type": "result",
            #         "answer": "Message received fine", 
            #         "tokens": "111",
            #         "cost": "0.01"}))
            # continue
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
            query = "The following is a friendly conversation between a human and an AI. The AI is talkative and provides lots of specific details from its context. If the AI does not know the answer to a question, it truthfully says it does not know.\nCurrent conversation:\n"
            if event["input"].get("history"):
                # user server history if history key is not present in user request
                # memory.clear()  # do not use memory on serverside. Add chat history kept by client.
                hlen = 0
                for c in event["input"]["history"]:
                    hlen += len(c["Q"]) + len(c["A"])
                    if hlen > MAX_TOKEN[params["model"]]/2:
                        break
                    else:
                        query += "Human: "+c["Q"]+"\nAI: "+c["A"]+"\n"
            query += "Human: "+event["input"]["query"]+"\nAI:"
            print(query)
            start_time = time.time()
            with get_cost_tracker_callback(params["model"]) as cb:
                # chain = ConversationChain(llm=CHAT_LLM, memory=memory, output_parser=StrOutputParser())
                chain =CHAT_LLM
                resp = ""
                async for chunk in chain.astream(query):
                    print(chunk.content, end="|", flush=True)    # chunk size can be big
                    resp += chunk.content
                    await websocket.send_text(json.dumps({"type": "stream", "data": chunk.content}))
                print('\n', cb)
                print("time diff=", (time.time() - start_time))
                sys.stdout.flush()
                await websocket.send_text(json.dumps({
                    "type": "result",
                    "answer": resp, 
                    "tokens": cb.total_tokens,
                    "cost": cb.total_cost}))

    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8506)
