import json, sys, random
from datetime import datetime, timedelta, timezone
from typing import Annotated, Union
from fastapi import Depends, FastAPI, HTTPException, status, Query, WebSocket, WebSocketDisconnect, Request
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from pydantic import BaseModel
import litellm
import tiktoken
from dotenv import load_dotenv, dotenv_values
load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from leither_api import LeitherAPI
from utilities import ConnectionManager, UserIn, UserOut, UserInDB
from pet_hash import get_password_hash, verify_password
import apple_notification_sandbox, apple_notification_production
from leither_detector import leither_port_detector

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
lapi = None  # Will be initialized after port detection

# Global state for Leither port
LEITHER_PORT = None

env = dotenv_values(".env")
LLM_MODEL = env["CURRENT_LLM_MODEL"]
OPENAI_KEYS = env["OPENAI_KEYS"].split('|')
SERVER_MAINTENCE = env["SERVER_MAINTENCE"]

def split_text(text: str, model: str, max_tokens: int, overlap: int = 50) -> list[str]:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return [text]
    chunks, i = [], 0
    while i < len(tokens):
        chunks.append(enc.decode(tokens[i:i + max_tokens]))
        i += max_tokens - overlap
    return chunks

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Leither port detection on startup"""
    global LEITHER_PORT, lapi
    print("=" * 50, flush=True)
    print("LIFESPAN STARTUP TRIGGERED", flush=True)
    print("=" * 50, flush=True)
    try:
        print("Starting FastAPI application...", flush=True)
        print("Detecting Leither service port...", flush=True)
        
        # Detect and store the Leither port
        LEITHER_PORT = await leither_port_detector.get_leither_port()
        print(f"Leither service detected on port: {LEITHER_PORT}", flush=True)
        print(f"LEITHER_PORT = {LEITHER_PORT}", flush=True)
        print(f"LEITHER_PORT type: {type(LEITHER_PORT)}", flush=True)
        
        # Initialize the LeitherAPI with the detected port
        lapi = LeitherAPI(LEITHER_PORT)
        print("LeitherAPI initialized successfully", flush=True)
        print("=" * 50, flush=True)
        
    except RuntimeError as e:
        print(f"CRITICAL ERROR: {e}", flush=True)
        print("FastAPI startup aborted - Leither service is required", flush=True)
        raise e  # Re-raise to prevent FastAPI from starting without Leither
    except Exception as e:
        print(f"Unexpected error during startup: {e}", flush=True)
        raise e  # Re-raise unexpected errors
    
    yield  # This is where the app runs
    
    # Cleanup code goes here (shutdown)
    print("Shutting down...", flush=True)

app = FastAPI(lifespan=lifespan)
scheduler = BackgroundScheduler()

def periodic_task():
    env = dotenv_values(".env")
    global LLM_MODEL, OPENAI_KEYS, SERVER_MAINTENCE, LEITHER_PORT, lapi
    # export as defualt parameters. Values updated hourly.
    LLM_MODEL = env["CURRENT_LLM_MODEL"]
    OPENAI_KEYS = env["OPENAI_KEYS"].split('|')
    SERVER_MAINTENCE=env["SERVER_MAINTENCE"]
    
    # Check if Leither port is still working (only if lapi is initialized)
    if lapi is not None and LEITHER_PORT is not None:
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            is_working = loop.run_until_complete(leither_port_detector._test_port_connection(LEITHER_PORT))
            if not is_working:
                print(f"Leither port {LEITHER_PORT} is not responding, attempting to redetect...")
                try:
                    new_port = loop.run_until_complete(leither_port_detector.get_leither_port())
                    if new_port != LEITHER_PORT:
                        LEITHER_PORT = new_port
                        lapi.update_port(LEITHER_PORT)
                        print(f"Leither port updated to: {LEITHER_PORT}")
                except RuntimeError as e:
                    print(f"CRITICAL: Leither service no longer available: {e}")
                    # Could implement service restart logic here if needed
            loop.close()
        except Exception as e:
            print(f"Error checking Leither port health: {e}")

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

def authenticate_user(username: str, password: str, lapi_instance) -> UserOut:
    user = lapi_instance.get_user(username)    # check index db
    if user is None:
        return None
    if password != "" and not verify_password(password, user.hashed_password):
        # if password is empty string, this is a temp user. "" not equal to None.
        return None
    # check if index db record exists. If not, the user has been deleted.
    user_in_db = lapi_instance.get_user_in_db(user)
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

async def get_lapi():
    """Dependency to ensure LeitherAPI is initialized"""
    if lapi is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Leither service not available"
        )
    return lapi

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
    if lapi is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Leither service not available"
        )
    user = lapi.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

@app.post(BASE_ROUTE + "/token")
async def login_for_access_token( form_data: Annotated[OAuth2PasswordRequestForm, Depends()], lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]):
    print("form data", form_data.username, form_data.client_id)
    user = authenticate_user(form_data.username, form_data.password, lapi_instance)
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
async def register_user(user: UserIn, lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]) -> UserOut:
    # If user has tried service, there is valid mid attribute. Otherwise, it is None
    print("User in for register:", user)
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB
    user = lapi_instance.register_in_db(UserInDB(**user_in_db))
    if not user:
        raise HTTPException(status_code=400, detail="Username already taken")
    print("User out", user)
    return user

@app.post(BASE_ROUTE + "/users/temp")
async def register_temp_user(user: UserIn, lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]):
    # A temp user has been assigned a username, usually the device identifier.
    user_in_db = user.model_dump(exclude=["password"])
    user_in_db.update({"hashed_password": get_password_hash(user.password)})  # save hashed password in DB
    user = lapi_instance.register_temp_user(UserInDB(**user_in_db))
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
async def cash_coupon(coupon: str, current_user: Annotated[UserInDB, Depends(get_current_user)], lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]) -> bool:
    return lapi_instance.cash_coupon(current_user, coupon)

#update user infor
@app.put(BASE_ROUTE + "/users")
async def update_user_by_obj(user: UserIn, user_in_db: Annotated[UserInDB, Depends(get_current_user)], lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]):
    user_in_db.family_name = user.family_name
    user_in_db.given_name = user.given_name
    user_in_db.email = user.email
    # if User password is null, do not update it.
    if user.password:
        user_in_db.hashed_password = get_password_hash(user.password)  # save hashed password in DB
    return lapi_instance.update_user(user_in_db).model_dump()

# delete current user, return {id: user_id}
@app.delete(BASE_ROUTE + "/users")
async def delete_user(user_in_db: Annotated[UserInDB, Depends(get_current_user)], lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]):
    ret = lapi_instance.delete_user(user_in_db)
    print("delete=", ret)
    return ret

# get current product IDs
@app.get(BASE_ROUTE + "/productids")
async def get_productIDs():
    product_ids = dotenv_values(".env")["SECRETARI_PRODUCT_ID_IOS"]
    # return HTMLResponse("Hello world.")
    return json.loads(product_ids)

@app.get(BASE_ROUTE + "/server/status")
async def get_server_status():
    """Get server status including Leither port information"""
    global LEITHER_PORT
    try:
        # Test current Leither port connectivity
        is_leither_working = await leither_port_detector._test_port_connection(LEITHER_PORT) if LEITHER_PORT else False
        
        return {
            "server_time": datetime.now().isoformat(),
            "leither_port": LEITHER_PORT,
            "leither_connected": is_leither_working,
            "active_connections": len(connectionManager.active_connections),
            "llm_model": LLM_MODEL,
            "server_maintenance": SERVER_MAINTENCE,
            "max_token_limits": MAX_TOKEN
        }
    except Exception as e:
        return {
            "error": str(e),
            "server_time": datetime.now().isoformat(),
            "leither_port": LEITHER_PORT,
            "leither_connected": False
        }

@app.post(BASE_ROUTE + "/app_server_notifications_production")
async def apple_notifications_production(request: Request, lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]):
    try:
        body = await request.json()
        await apple_notification_production.decode_notification(lapi_instance, body["signedPayload"])
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=400, detail="Invalid notification data")

@app.post(BASE_ROUTE + "/app_server_notifications_sandbox")
async def apple_notifications_sandbox(request: Request, lapi_instance: Annotated[LeitherAPI, Depends(get_lapi)]):
    try:
        body = await request.json()
        await apple_notification_sandbox.decode_notification(lapi_instance, body["signedPayload"])
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
    client_host = websocket.client.host if websocket.client else "unknown"
    server_host = websocket.url.hostname
    print(f"[WS] New connection — client: {client_host}, server: {server_host}, url: {websocket.url}", flush=True)
    await connectionManager.connect(websocket)
    try:
        # token = websocket.query_params.get("token")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise WebSocketDisconnect
        token_data = TokenData(username=username)
        if lapi is None:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Leither service not available",
            }))
            await websocket.close()
            return
        
        user = lapi.get_user(username=token_data.username)
        if not user:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "User not found. Please re-login.",
            }))
            await websocket.close()
            return
        
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
            else:
                # a subscriber. Check monthly usage
                current_month = str(datetime.now().month)
                if user.monthly_usage.get(current_month) and user.monthly_usage.get(current_month) >= MAX_EXPENSE:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Monthly max expense exceeded. Purchase consumable product if necessary.", 
                        }))
                    continue

            # Map provider to litellm model string and kwargs
            if params["llm"] == "openai":
                model_str = llm_model                           # e.g. "gpt-4o"
                extra_kwargs = {"api_key": random.choice(OPENAI_KEYS)}
            elif params["llm"] == "gemini":
                model_str = f"gemini/{llm_model}"               # e.g. "gemini/gemini-2.0-flash"
                extra_kwargs = {}
            elif params["llm"] == "anthropic":
                model_str = f"anthropic/{llm_model}"            # e.g. "anthropic/claude-sonnet-4-6"
                extra_kwargs = {}
            else:
                continue

            chunk_size = int(MAX_TOKEN.get(llm_model, 4096) * 3 / 4)
            resp = ""
            text_chunks = split_text(query["rawtext"], llm_model, chunk_size)
            print(f"[WS] model={model_str}, chunks={len(text_chunks)}, chunk_size={chunk_size}", flush=True)
            for index, ci in enumerate(text_chunks):
                collected_chunks = []
                print(f"[WS] calling litellm for chunk {index}", flush=True)
                stream = await litellm.acompletion(
                    model=model_str,
                    messages=[{"role": "user", "content": query["prompt"] + "\n\n" + ci}],
                    temperature=float(params["temperature"]),
                    stream=True,
                    **extra_kwargs,
                )
                async for chunk in stream:
                    collected_chunks.append(chunk)
                    content = chunk.choices[0].delta.content or ""
                    if content:
                        print(content, end="|", flush=True)
                        resp += content
                        await websocket.send_text(json.dumps({"type": "stream", "data": content}))

                full_response = litellm.stream_chunk_builder(collected_chunks)
                total_cost = litellm.completion_cost(completion_response=full_response)
                total_tokens = full_response.usage.total_tokens if full_response.usage else 0
                print(f"\nLLMModel: {llm_model}, chunk {index}/{len(text_chunks)}, tokens: {total_tokens}, cost: ${total_cost:.6f}")
                sys.stdout.flush()

                await websocket.send_text(json.dumps({
                    "type": "result",
                    "answer": resp,
                    "tokens": int(total_tokens * lapi.cost_efficiency),
                    "cost": total_cost * lapi.cost_efficiency,
                    "eof": index == (len(text_chunks) - 1),
                    }))
                lapi.bookkeeping(total_cost, total_tokens, user)

    except WebSocketDisconnect:
        connectionManager.disconnect(websocket)
    except JWTError as e:
        print(f"[WS] JWTError: {e}", flush=True)
        await websocket.send_text(json.dumps({"type": "error", "message": "Invalid token. Try to re-login."}))
    except HTTPException as e:
        print(f"[WS] HTTPException: {e}", flush=True)
    except Exception as e:
        import traceback
        print(f"[WS] Unhandled exception: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8506)
