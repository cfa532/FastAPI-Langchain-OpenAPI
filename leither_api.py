import hprose, json
from utilities import UserInDB, is_ipv6, is_local_network_ip

client = hprose.HttpClient('http://localhost:8004/webapi/')
print(client.GetVar("", "ver"))
ppt = client.GetVarByContext("", "context_ppt")
api = client.Login(ppt)
print("reply", api)
print("sid  ", api.sid)
print("uid  ", api.uid)

USER_ACCOUNT_KEY = "SECRETARI_APP_USER_ACCOUNT_KEY"
GPT_3_Tokens = 1000000      # bonus tokens upon installation
GPT_4_Turbo_Tokens = 10000
# USER_NODE_ID = "1-U-7NvW2hOWmyoiipkzno65so-"
USER_NODE_ID = "pM6YSo4Edczo5VYM05hjsGxFtJF"

mid = client.MMCreate(api.sid, api.uid, "", "ajchat app db", 2, 0x07276705)
print("mid  ", mid)

# registrate a real user account.
def register_in_db(user: UserInDB):
    print(user)
    if not get_user(user.username):
        mmsid_cur = client.MMOpen(api.sid, mid, "cur")
        client.Hset(mmsid_cur, USER_ACCOUNT_KEY, user.username, json.dumps(user.model_dump()))
        client.MMBackup(api.sid, mid, "", "delRef=true")
        return True
    else:
        return False

# Create an account for all trial users. Set username with device identifier.
# After registration, username will be different from its identifier.
def get_user(username, identifier):
    mmsid = client.MMOpen(api.sid, mid, "last")
    if username == identifier:
        user = client.Hget(mmsid, USER_ACCOUNT_KEY, username)
        if not user:
            # create an account for the new user
            user = UserInDB(username=username, hashed_password="", token_count={"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, token_usage={"gpt-3.5":0, "gpt-4-turbo":0}, subscription=False, deviceIdentifier=identifier)
            mmsid_cur = client.MMOpen(api.sid, mid, "cur")
            client.Hset(mmsid_cur, USER_ACCOUNT_KEY, username, json.dumps(user.model_dump()))
            client.MMBackup(api.sid, mid, "", "delRef=true")
        else:
            # this is a anonymous user, no registered yet.
            return UserInDB(**json.loads(user))
    else:
        # this is a registered user
        user = client.Hget(mmsid, USER_ACCOUNT_KEY, identifier)
        return UserInDB(**json.loads(user))

def update_user(user: UserInDB):
    mmsid = client.MMOpen(api.sid, mid, "last")
    user_in_db = UserInDB(**json.loads(client.Hget(mmsid, USER_ACCOUNT_KEY, user.username)))
    for attr in vars(user):
        setattr(user_in_db, attr, getattr(user, attr))
    mmsid_cur = client.MMOpen(api.sid, mid, "cur")
    client.Hset(mmsid_cur, USER_ACCOUNT_KEY, user.username, json.dumps(user_in_db.model_dump()))
    client.MMBackup(api.sid, mid, "", "delRef=true")

def delete_user(username: str):
    mmsid_cur = client.MMOpen(api.sid, mid, "cur")
    client.Hdel(mmsid_cur, USER_ACCOUNT_KEY, username)
    client.MMBackup(api.sid, mid, "", "delRef=true")


def bookkeeping(llm, total_cost, total_tokens, username):
    mmsid = client.MMOpen(api.sid, mid, "last")
    user_in_db = UserInDB(**json.loads(client.Hget(mmsid, USER_ACCOUNT_KEY, username)))
    user_in_db.token_usage[llm] += float(total_cost)
    user_in_db.token_count[llm] = max(user_in_db.token_count[llm]-int(total_tokens), 0)

    mmsid_cur = client.MMOpen(api.sid, mid, "cur")
    client.Hset(mmsid_cur, USER_ACCOUNT_KEY, username, json.dumps(user_in_db.model_dump()))
    client.MMBackup(api.sid, mid, "", "delRef=true")

# def get_user(username, password, identifier):
#     # the password is hashed already
#     user = json.load(client.Hget(mmsid, USER_ACCOUNT_KEY, identifier))
#     if not user:
#         user = {username:username, password:password, "tokenCount":{"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, "tokenUsage":{"gpt-3.5":0, "gpt-4-turbo":0}, "subscription": False, identifier:identifier}
#         client.Hset(mmsid, USER_ACCOUNT_KEY, identifier, user)
#     return user
