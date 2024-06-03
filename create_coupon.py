import hprose, json, time, sys
from datetime import datetime
from utilities import UserInDB, UserOut
from dotenv import load_dotenv, dotenv_values
import secrets

APPID_MIMEI_KEY = "FmKK37e1T0oGaQJXRMcMjyrmoxa"
USER_ACCOUNT_KEY = "SECRETARI_APP_USER_ACCOUNT_KEY"
MIMEI_EXT = "mimei file"
MIMEI_COUPON_KEY="SECRETARI_USER_COUPON_KEY"

def generate_random_key():
    # Generate a random key with 32 bytes of data, then convert it to a hexadecimal string
    random_key = secrets.token_hex(32)
    return random_key

client = hprose.HttpClient('http://localhost:8080/webapi/')
ppt = client.GetVarByContext("", "context_ppt")
api = client.Login(ppt)
sid = api.sid
uid = api.uid
mid = client.MMCreate(sid, APPID_MIMEI_KEY, "app", "secretari backend", 2, 0x07276705)

coupon_amount = sys.argv[1]     # dollar amount of the coupon
# coupon_key = generate_random_key()
coupon_key = int(time.time())
mmsid = client.MMOpen(sid, mid, "cur")
coupon = {"model":"gpt-4-turbo", "redeemed": False, "amount": coupon_amount, "expiration_date": time.time()}
client.Hset(mmsid, MIMEI_COUPON_KEY, coupon_key, coupon)
client.MMBackup(sid, mid, "", "delRef=true")
print(coupon_key)