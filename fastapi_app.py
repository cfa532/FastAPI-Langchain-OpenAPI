import json, sys, time, random
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union, List
from fastapi import Depends, FastAPI, HTTPException, status, Query, WebSocket, WebSocketDisconnect, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from starlette.websockets import WebSocketState
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv, dotenv_values
load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from openaiCBHandler import get_cost_tracker_callback
from leither_api import LeitherAPI
from utilities import ConnectionManager, UserIn, UserOut, UserInDB
from pet_hash import get_password_hash, verify_password
from apple_notification import decode_notification

# to get a string like this run: openssl rand -hex 32
SECRET_KEY = "ebf79dbbdcf6a3c860650661b3ca5dc99b7d44c269316c2bd9fe7c7c5e746274"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = 480   # expires
BASE_ROUTE = "/secretari"
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
OPENAI_KEYS = env["OPENAI_KEYS"]
print("api keys:", OPENAI_KEYS)

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
    global LLM_MODEL, OPENAI_KEYS
    # export as defualt parameters. Values updated hourly.
    LLM_MODEL = env["CURRENT_LLM_MODEL"]
    OPENAI_KEYS = env["OPENAI_KEYS"]
    print("api keys:", OPENAI_KEYS)

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

def authenticate_user(username: str, password: str):
    user = lapi.get_user(username)
    if user is None:
        return None
    if password != "" and not verify_password(password, user.hashed_password):
        # if password is empty string, this is a temp user. "" not equal to None.
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
    print("token:", token)
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

@app.post(BASE_ROUTE+"/token")
async def login_for_access_token( form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    print("form data", form_data.username, form_data.client_id)
    start_time = time.time()
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
    user_out = user.model_dump(exclude=["hashed_password"])
    print("--- %s seconds ---" % (time.time() - start_time))
    return {"token": token, "user": user_out}

@app.post(BASE_ROUTE+"/users/register")
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

@app.post(BASE_ROUTE+"/users/update")
async def update_user(user: UserIn, user_in_db: Annotated[UserInDB, Depends(get_current_user)]) -> UserOut:
    user_in_db.family_name = user.family_name
    user_in_db.given_name = user.given_name
    user_in_db.email = user.email
    # if User password is null, do not update it.
    if user.password:
        user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB

    user = lapi.update_user(user_in_db)
    print("User out", user)
    return user

@app.post(BASE_ROUTE+"/users/temp")
async def register_temp_user(user: UserIn):
    # A temp user has assigned username, usuall the device identifier. It does not login, so no taken is needed.
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB
    user = lapi.register_temp_user(UserInDB(**user_in_db))
    print("temp user created. ", user)
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create temp User.")
    
    access_token_expires = timedelta(weeks=ACCESS_TOKEN_EXPIRE)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    token = Token(access_token=access_token, token_type="Bearer")

    # create a token for temp user too, so they can buy product and access premium service without login.
    return {"token": token, "user": user}

# upload purchase to server
@app.post(BASE_ROUTE+"/users/recharge")
async def upload_purchase(purchase: dict, current_user: Annotated[UserInDB, Depends(get_current_user)]) -> UserOut:
    print("purchase:", purchase)
    try:
        return lapi.upload_recharge(current_user, purchase)
    except:
        raise HTTPException(status_code=400, detail="Failed to upload purchase history.")

    # there are two piece of data in dict. Purchase receipt and other data. Confrim with Apple first.
    # payload = {
    #     'receipt-data': purchase["receipt"],
    #     # 'password': '04df7f4eb0f04034a25081673d464e6d',  # Only needed for auto-renewable subscriptions
    # }
    # headers = {'Content-Type': 'application/json'}
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(VERIFICATION_URL_SANDBOX, json=payload, headers=headers)
    # if response.status_code == 200:
    #     result = response.json()
    #     print(result)
    #     if result.get("status") != 0:
    #         raise HTTPException(status_code=400, detail="Failed to verify receipt with Apple")
    #     purchase["validation"] = result
    #     return lapi.upload_purchase_history(current_user, purchase)
    # else:
    #     if response.status_code == 21007:
    #             async with httpx.AsyncClient() as client:
    #                 response = await client.post(VERIFICATION_URL_PRODUCTION, json=payload, headers=headers)
    #             if response.status_code == 200:
    #                 result = response.json()
    #                 print(result)
    #                 if result.get("status") != 0:
    #                     raise HTTPException(status_code=400, detail="Failed to verify receipt with Apple")
    #                 purchase["validation"] = result
    #                 return lapi.upload_purchase_history(current_user, purchase)
    #     else:
    #         raise HTTPException(status_code=response.status_code, detail="Failed to verify receipt with Apple")

@app.post(BASE_ROUTE + "/users/subscribe")
async def subscribe_user(subscription: dict, current_user: Annotated[UserInDB, Depends(get_current_user)]) -> UserOut:
    return lapi.subscribe_user(current_user, subscription)

# redeem coupons
@app.post(BASE_ROUTE+"/users/redeem")
async def cash_coupon(coupon: str, current_user: Annotated[UserInDB, Depends(get_current_user)]) -> bool:
    return lapi.cash_coupon(current_user, coupon)

@app.get(BASE_ROUTE+"/users", response_model=UserOut)
async def get_user_by_id(id: str, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != id:
        raise HTTPException(status_code=400, detail="Not admin")
    return lapi.get_user(id)
    # return current_user

@app.get(BASE_ROUTE+"/users/all", response_model=List[UserOut])
async def get_all_users(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.role != "admin":
        return [UserOut(**current_user.model_dump())] 
    return lapi.get_users()

@app.delete(BASE_ROUTE+"/users/{username}")
async def delete_user_by_id(username: str, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(status_code=400, detail="Not admin")
    return lapi.delete_user(username)

#update user infor
@app.put(BASE_ROUTE+"/users")
async def update_user_by_obj(user: UserIn, current_user: Annotated[UserInDB, Depends(get_current_user)]):
    if current_user.role != "admin" and current_user.username != user.username:
        raise HTTPException(status_code=400, detail="Not admin")
    user_in_db = user.model_dump(exclude=["password"])

    # if no password, do not update it
    if not user.password:
        user_in_db["hashed_password"] = ""
    else:
        user_in_db["hashed_password"] = get_password_hash(user.password)
    return lapi.update_user(UserInDB(**user_in_db))

# get current product IDs
@app.get(BASE_ROUTE+"/productids")
async def get_productIDs():
    product_ids = dotenv_values(".env")["SECRETARI_PRODUCT_ID_IOS"]
    # return HTMLResponse("Hello world.")
    return json.loads(product_ids)

@app.post(BASE_ROUTE+"/app_server_notifications")
async def apple_notifications(request: Request):
    try:
        body = await request.json()
        await decode_notification(body["signedPayload"])
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=400, detail="Invalid notification data")

@app.get(BASE_ROUTE+"/")
async def get():
    return HTMLResponse("Hello world.")

@app.websocket(BASE_ROUTE+"/ws/")
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
        print(user)
        if not user:
            raise WebSocketDisconnect
        
        while True:
            message = await websocket.receive_text()
            event = json.loads(message)
            print("Incoming event: ", event)
            
            # create the right Chat LLM
            params = event["parameters"]
            if params["llm"] == "openai":
                # randomly select OpenAI key from a list
                print(OPENAI_KEYS)
                CHAT_LLM = ChatOpenAI(
                    api_key = random.choice(OPENAI_KEYS),   # pick a random OpenAI key from a list
                    temperature = float(params["temperature"]),
                    model = params["model"],
                    streaming = True,
                    verbose = True
                )     # ChatOpenAI cannot have max_token=-1
            elif params["llm"] == "qianfan":
                pass

            # check user account balance. If current model has not balance, use the cheaper default one.
            user = lapi.get_user(event["user"])
            llm_model = LLM_MODEL
            lapi.bookkeeping(llm_model, 0.015, 123, user)
            await websocket.send_text(json.dumps({
                "type": "result",
                "answer": event["input"]["rawtext"], 
                "tokens": 111,
                "cost": 0.015,
                "user": UserOut(**user.model_dump()).model_dump()}))

            continue
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
                    if hlen > MAX_TOKEN[llm_model]/2:
                        break
                    else:
                        query += "Human: "+c["Q"]+"\nAI: "+c["A"]+"\n"
            query += "Human: "+event["input"]["rawtext"]+"\nAI:"
            print(query)
            start_time = time.time()
            with get_cost_tracker_callback(llm_model) as cb:
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
                
                lapi.bookkeeping(llm_model, cb.total_cost, cb.total_tokens, user)

    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)
    except JWTError:
        print("JWTError", e)
        sys.stdout.flush()
        await websocket.send_text(json.dumps({"type": "error", "error": "Invalid token"}))
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
