import hprose, json
from utilities import UserIn, UserOut, UserInDB
from passlib.apps import custom_app_context as pwd_context

client = hprose.HttpClient('http://localhost:8004/webapi/')
print(client.GetVar("", "ver"))
ppt = client.GetVarByContext("", "context_ppt")
api = client.Login(ppt)
print("reply", api)
print("sid  ", api.sid)
print("uid  ", api.uid)

userAccountKey = "AJCHAT_APP_USER_ACCOUNT_KEY"
GPT_3_Tokens = 1000000      # bonus tokens upon installation
GPT_4_Turbo_Tokens = 10000

mid = client.MMCreate(api.sid, api.uid, "", "ajchat app db", 2, 0x07276705)
print("mid  ", mid)
mmsid = client.MMOpen(api.sid, mid, "last")

def register(user: UserIn):
    u = get_user(user.username)
    if not u:
        user_in_db = user.model_dump(exclude=["password"])
        user_in_db["hashed_password"] = pwd_context.hash(user.password)  # save hashed password in DB
        print("register action", user_in_db)
        mmsid_cur = client.MMOpen(api.sid, mid, "cur")
        client.Hset(mmsid_cur, userAccountKey, user.username, json.dumps(user_in_db))
        client.MMBackup(api.sid, mid, "", "delRef=true")
        mmsid = client.MMOpen(api.sid, mid, "last")
        return True
    else:
        return False
    
def get_user(username):
    user = client.Hget(mmsid, userAccountKey, username)
    print("null user", user)
    if not user:
        return None
    return UserInDB(user)

def get_users():
    return [UserOut(user) for user in client.Hgetall(mmsid, userAccountKey)]

def update_user(user: UserIn):
    user_in_db = UserInDB(client.Hget(mmsid, userAccountKey, user.username))
    if user.password:
        user.hashed_password = pwd_context.hash(user.password)  # save hashed password in DB
        del user.password
    for attr in vars(user):
        setattr(user_in_db, attr, getattr(user, attr))
    mmsid_cur = client.MMOpen(api.sid, mid, "cur")
    client.Hset(mmsid_cur, userAccountKey, user.username, user_in_db)
    client.MMBackup(api.sid, mid, "", "delRef=true")
    mmsid = client.MMOpen(api.sid, mid, "last")

def delete_user(username: str):
    mmsid_cur = client.MMOpen(api.sid, mid, "cur")
    client.Hdel(mmsid_cur, userAccountKey, username)
    client.MMBackup(api.sid, mid, "", "delRef=true")
    mmsid = client.MMOpen(api.sid, mid, "last")

# def get_user(username, password, identifier):
#     # the password is hashed already
#     user = json.load(client.Hget(mmsid, userAccountKey, identifier))
#     if not user:
#         user = {username:username, password:password, "tokenCount":{"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, "tokenUsage":{"gpt-3.5":0, "gpt-4-turbo":0}, "subscription": False, identifier:identifier}
#         client.Hset(mmsid, userAccountKey, identifier, user)
#     return user
