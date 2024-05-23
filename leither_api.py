import hprose, json, time
from utilities import UserInDB, is_ipv6, is_local_network_ip

USER_ACCOUNT_KEY = "AICHAT_APP_USER_ACCOUNT_KEY"
GPT_3_Tokens = 1000000      # bonus tokens upon installation
GPT_4_Turbo_Tokens = 10000
# USER_NODE_ID = "1-U-7NvW2hOWmyoiipkzno65so-"
USER_NODE_ID = "pM6YSo4Edczo5VYM05hjsGxFtJF"

class LeitherAPI:
    def __init__(self):
        self.client = hprose.HttpClient('http://localhost:8004/webapi/')
        print(self.client.GetVar("", "ver"))
        ppt = self.client.GetVarByContext("", "context_ppt")
        self.api = self.client.Login(ppt)
        self.sid = self.api.sid
        self.uid = self.api.uid
        self.mid = self.client.MMCreate(self.sid, "FmKK37e1T0oGaQJXRMcMjyrmoxa", "app", "aichat index db", 2, 0x07276705)
        print("sid  ", self.api.sid)
        print("uid  ", self.api.uid)
        print("mid  ", self.mid)

    def get_user_session(self):
        # given a node id, find valid IPs
        ips = list(filter(lambda x: len(x)>6, self.client.GetVar(self.sid, "ips", USER_NODE_ID).split(",")))

        public_ips = [ip for ip in ips if not is_local_network_ip(ip)]      # remove local network IP
        ip = public_ips[0]

        v4_ips = [ip for ip in public_ips if not is_ipv6(ip)]      # get ipv4 list
        if len(v4_ips) > 0:
            ip = v4_ips[0]      # v4 IP takes priority

        # problem: IPv4 might be polutted by IPFS. Hprose cannot handle IPv6
        
        print("user node ip: ", ip)
        user_client, session_id = self.get_user_client(ip)
        return {"node_ip": ip, "sid": session_id}

    def get_user_client(self, user_node_ip):
        user_client = hprose.HttpClient("http://"+ user_node_ip +"/webapi/")
        result = user_client.Login("aj", "123456", "byname")
        ppt = user_client.SignPPT(result.sid, {
            "CertFor": "Self",
            "Userid": result.uid,
            "RequestService": "mimei"
        }, 1)
        user_client.RequestService(ppt)
        return user_client, result.sid

    def register_in_db(self, user: UserInDB):
        print(user)
        u = self.get_user(user.username)
        if not u:
            user_client, client_sid = self.get_user_client(self.get_user_session()["node_ip"])

            # create a mimei for the user at its mimei server
            user.mid = user_client.MMCreate(client_sid, '5KF-zeJy-KUQVFukKla8vKWuSoT', 'USER_MM', USER_ACCOUNT_KEY+'_'+user.username, 2, 0x07276704);
            mmsid_cur = self.client.MMOpen(self.sid, self.mid, "cur")
            self.client.Hset(mmsid_cur, USER_ACCOUNT_KEY, user.username, json.dumps(user.model_dump()))
            self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
            return True
        else:
            return False
        
    def get_user(self, username):
        mmsid = self.client.MMOpen(self.sid, self.mid, "last")
        user = self.client.Hget(mmsid, USER_ACCOUNT_KEY, username)
        if not user:
            return None
        return UserInDB(**json.loads(user))

    def get_users(self):
        mmsid = self.client.MMOpen(self.sid, self.mid, "last")
        return [UserInDB(**json.loads(user.value)) for user in self.client.Hgetall(mmsid, USER_ACCOUNT_KEY)]

    def update_user(self, user: UserInDB):
        mmsid = self.client.MMOpen(self.sid, self.mid, "last")
        user_in_db = UserInDB(**json.loads(self.client.Hget(mmsid, USER_ACCOUNT_KEY, user.username)))
        for attr in vars(user):
            setattr(user_in_db, attr, getattr(user, attr))
        mmsid_cur = self.client.MMOpen(self.sid, self.mid, "cur")
        self.client.Hset(mmsid_cur, USER_ACCOUNT_KEY, user.username, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")

    def delete_user(self, username: str):
        mmsid_cur = self.client.MMOpen(self.sid, self.mid, "cur")
        self.client.Hdel(mmsid_cur, USER_ACCOUNT_KEY, username)
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")

    def bookkeeping(self, llm, total_cost, total_tokens, username):
        mmsid = self.client.MMOpen(self.sid, self.mid, "last")
        user_in_db = UserInDB(**json.loads(self.client.Hget(mmsid, USER_ACCOUNT_KEY, username)))
        user_in_db.token_usage[llm] += float(total_cost)
        user_in_db.token_count[llm] = max(user_in_db.token_count[llm]-int(total_tokens), 0)

        mmsid_cur = self.client.MMOpen(self.sid, self.mid, "cur")
        self.client.Hset(mmsid_cur, USER_ACCOUNT_KEY, username, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")

    # def get_user(username, password, identifier):
    #     # the password is hashed already
    #     user = json.load(client.Hget(mmsid, USER_ACCOUNT_KEY, identifier))
    #     if not user:
    #         user = {username:username, password:password, "tokenCount":{"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, "tokenUsage":{"gpt-3.5":0, "gpt-4-turbo":0}, "subscription": False, identifier:identifier}
    #         client.Hset(mmsid, USER_ACCOUNT_KEY, identifier, user)
    #     return user
