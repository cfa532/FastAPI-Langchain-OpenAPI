from fastapi import WebSocket
import sys, ipaddress, re, time
from typing import Union
from pydantic import BaseModel
from enum import Enum

MAX_TOKEN = {
    "gpt-4": 4096,
    "gpt-4-turbo": 8192,
    "gpt-3.5-turbo": 4096,
}

# Function to check if an IP is a local network IP
def is_local_network_ip(ip):
    addr = re.findall(r'\[(.+)\]', ip[:ip.rfind(':')])
    if len(addr) == 0:
        #IPv4, remove :PORT
        return ipaddress.ip_address(ip[:ip.rfind(':')]).is_private
    else:
        # IPv6
        return ipaddress.ip_address(addr[0]).is_private

def is_ipv6(ip):
    addr = re.findall(r'\[(.+)\]', ip[:ip.rfind(':')])
    if len(addr) == 0:
        return False
    else:
        return True
        # return ipaddress.ip_address(addr).version == 6

class RoleName(str, Enum):
    user = "user"
    admin = "admin"

class UserGroup(BaseModel):
    id: int
    name: str
    description: str
    users: set[str]        # list of usernames

class User(BaseModel):
    username: str
    subscription: bool = False
    mid: Union[str, None] = None            # the user's mid, which is a mimei file
    email: Union[str, None] = None          # if present, useful for reset password
    family_name: Union[str, None] = None
    given_name: Union[str, None] = None
    template: Union[dict, None] = None      # parameters for LLM

    # def model_dump(self, exclude: list = []):
    #     if "password" in exclude:
    #         exclude.remove("password")
    #     return {k: v for k, v in self.dict().items() if k not in exclude}
    
class UserOut(User):
    # bookkeeping information is based on server records. User keep a copy on its device as FYI
    dollar_balance: Union[dict, None] = None        # account balance in dollar amount. Aware of model. {model: balance}
    monthly_usage: Union[dict, None] = None         # dollar cost per month. Ignorant of LLM model. {month: cost}
    token_count: Union[dict, None] = None          # token count per model. {model: count}

class UserIn(User):
    password: str                                   # the password is hashed in DB

class UserInDB(UserOut):
    hashed_password: str
    timestamp: float = time.time()                  # last time service is used
    dollar_usage: Union[float, None] = None          # accumulated dollar usage. Ignorant of LLM model
    subscription_type: Union[str, None] = None      # monthly, yearly
    subscription_start: Union[int, None] = None     # start time
    subscription_end: Union[int, None] = None       # end time

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)
