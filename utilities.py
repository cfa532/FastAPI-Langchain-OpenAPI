from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import sys, ipaddress, re
from typing import Union
from pydantic import BaseModel
from enum import Enum

MAX_TOKEN = {
    "gpt-4": 4096,
    "gpt-4-turbo": 8192
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

class UserOut(BaseModel):
    username: str
    subscription: bool = False
    identifier: str                   # device id of this user
    email: Union[str, None] = None          # if present, useful for reset password
    family_name: Union[str, None] = None
    given_name: Union[str, None] = None
    template: Union[dict, None] = None      # parameters for LLM

    # bookkeeping information is based on server records. User keep a copy on its device as FYI
    token_count: Union[dict, None] = None   # how many takens left in user account
    token_usage: Union[dict, None] = None   # accumulated tokens usage in dollar amount
    current_usage: Union[dict, None] = None # token cost for the month

class UserIn(BaseModel):
    password: str                           # the password is hashed in DB
    username: str
    subscription: bool = False
    identifier: str                   # device id of this user
    email: Union[str, None] = None          # if present, useful for reset password
    family_name: Union[str, None] = None
    given_name: Union[str, None] = None

class UserInDB(UserOut):
    hashed_password: str

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
