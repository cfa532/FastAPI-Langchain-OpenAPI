from fastapi import WebSocket
import sys, ipaddress, re, time
from typing import Union
from pydantic import BaseModel
from enum import Enum

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

class Purchase(BaseModel):
    notificationType: str
    productId: str
    transactionId: str
    originalTransactionId: str
    originalPurchaseDate: float
    purchaseDate: float                   # datetime the purchase happened.
    quantity: int = 1
    currentBalance: float = 0.0         # the account balance at the time of this purchase.

class User(BaseModel):
    id: Union[str, None] = None             # use device identifier as appAccountToken.
    username: str
    email: Union[str, None] = None          # if present, useful for reset password
    family_name: Union[str, None] = None
    given_name: Union[str, None] = None
    
class UserOut(User):
    # bookkeeping information is based on server records. User keep a copy on its device as FYI
    dollar_balance: float = 0.0                     # account balance in dollar amount. ignorant of model. 
                                                    # revert to gpt-3.5 when balance < 0.1, signup bonus 0.2
    monthly_usage: Union[dict, None] = None         # dollar cost per month. Ignorant of LLM model. {month: cost}
    token_count: int = 0                            # token count

class UserIn(User):
    password: str                                   # the password is hashed in DB

class UserInDB(UserOut):
    mid: Union[str, None] = None            # the user's mid, which is a mimei file
    hashed_password: str
    creation_date: float = time.time()              # when user is created
    timestamp: float = time.time()                  # last time service is used
    dollar_usage: float = 0.0                       # accumulated dollar usage. Ignorant of LLM model
    accured_total: float = 0.0                      # accumulated revenue, consumables and subscriptions.
    purchase_history: Union[list, None] = None      # purchase history. {productID, purchase date, amount, balance} 
                                                    # or {start date, end date, monthly/yearly, price}
    disabled: Union[bool, None] = False             # disabled by admin

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
