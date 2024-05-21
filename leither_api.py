import hprose, json
from utilities import UserInDB, is_ipv6, is_local_network_ip

client = hprose.HttpClient('http://localhost:8004/webapi/')
print(client.GetVar("", "ver"))
ppt = client.GetVarByContext("", "context_ppt")
api = client.Login(ppt)
print("reply", api)
print("sid  ", api.sid)
print("uid  ", api.uid)

USER_ACCOUNT_KEY = "AICHAT_APP_USER_ACCOUNT_KEY"
GPT_3_Tokens = 1000000      # bonus tokens upon installation
GPT_4_Turbo_Tokens = 10000
# USER_NODE_ID = "1-U-7NvW2hOWmyoiipkzno65so-"
USER_NODE_ID = "pM6YSo4Edczo5VYM05hjsGxFtJF"

mid = client.MMCreate(api.sid, api.uid, "", "ajchat app db", 2, 0x07276705)
print("mid  ", mid)

# so = subprocess.check_output("../darwin/Leither dht findpeer "+USER_NODE_ID, shell=True).decode('utf-8')
# print(so)
def get_user_session():
    # given a node id, find valid IPs
    ips = list(filter(lambda x: len(x)>6, client.GetVar(api.sid, "ips", USER_NODE_ID).split(",")))

    public_ips = [ip for ip in ips if not is_local_network_ip(ip)]      # remove local network IP
    ip = public_ips[0]

    v4_ips = [ip for ip in public_ips if not is_ipv6(ip)]      # get ipv4 list
    if len(v4_ips) > 0:
        ip = v4_ips[0]      # v4 IP takes priority

    user_client, session_id = get_user_client(ip)
    return {"node_ip": ip, "sid": session_id}

def get_user_client(user_node_ip):
    user_client = hprose.HttpClient("http://"+ user_node_ip +"/webapi/")
    result = user_client.Login("aj", "123456", "byname")
    ppt = user_client.SignPPT(result.sid, {
        "CertFor": "Self",
        "Userid": result.uid,
        "RequestService": "mimei"
    }, 1)
    user_client.RequestService(ppt)
    return user_client, result.sid

def register_in_db(user: UserInDB):
    print(user)
    u = get_user(user.username)
    if not u:
        user_client, client_sid = get_user_client(get_user_session()["node_ip"])

        # create a mimei for the user at its mimei server
        user.mid = user_client.MMCreate(client_sid, '5KF-zeJy-KUQVFukKla8vKWuSoT', 'USER_MM', USER_ACCOUNT_KEY+'_'+user.username, 2, 0x07276704);
        mmsid_cur = client.MMOpen(api.sid, mid, "cur")
        client.Hset(mmsid_cur, USER_ACCOUNT_KEY, user.username, json.dumps(user.model_dump()))
        client.MMBackup(api.sid, mid, "", "delRef=true")
        return True
    else:
        return False
    
def get_user(username):
    mmsid = client.MMOpen(api.sid, mid, "last")
    user = client.Hget(mmsid, USER_ACCOUNT_KEY, username)
    if not user:
        return None
    return UserInDB(**json.loads(user))

def get_users():
    mmsid = client.MMOpen(api.sid, mid, "last")
    return [UserInDB(**json.loads(user.value)) for user in client.Hgetall(mmsid, USER_ACCOUNT_KEY)]

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

# def get_user(username, password, identifier):
#     # the password is hashed already
#     user = json.load(client.Hget(mmsid, USER_ACCOUNT_KEY, identifier))
#     if not user:
#         user = {username:username, password:password, "tokenCount":{"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, "tokenUsage":{"gpt-3.5":0, "gpt-4-turbo":0}, "subscription": False, identifier:identifier}
#         client.Hset(mmsid, USER_ACCOUNT_KEY, identifier, user)
#     return user
