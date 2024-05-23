import hprose, json, time
from utilities import UserInDB, is_ipv6, is_local_network_ip

APPID_MIMEI_KEY = "FmKK37e1T0oGaQJXRMcMjyrmoxa"
USER_ACCOUNT_KEY = "SECRETARI_APP_USER_ACCOUNT_KEY"
GPT_3_Tokens = 1000000      # bonus tokens upon installation
GPT_4_Turbo_Tokens = 10000
# USER_NODE_ID = "1-U-7NvW2hOWmyoiipkzno65so-"      # Mac 8004
USER_NODE_ID = "pM6YSo4Edczo5VYM05hjsGxFtJF"        # Gen8/mimei 8001

class LeitherAPI:
    def __init__(self):
        self.client = hprose.HttpClient('http://localhost:8004/webapi/')
        print(self.client.GetVar("", "ver"))
        ppt = self.client.GetVarByContext("", "context_ppt")
        self.api = self.client.Login(ppt)
        self.sid = self.api.sid
        self.uid = self.api.uid
        self.mid = self.client.MMCreate(self.sid, APPID_MIMEI_KEY, "app", "secretari backend", 2, 0x07276705)

        print("sid  ", self.sid)
        print("uid  ", self.uid)
        print("mid  ", self.mid)

    # The function is called when user create a real account by providing personal information. The username shall be different from identifier.
    # A temporary user account has been created when user installed Secretari app. The username is set with device identifier, for a better user experience. This temp account will be deleted after registration. 
    # Information such as token usage and cost will be stored in the database.
    def register_in_db(self, user: UserInDB):
        mid = self.client.MMCreate(self.sid, APPID_MIMEI_KEY, "mimei file", user.username, 1, 0x07276705)
        mmsid = self.client.MMOpen(self.sid, mid, "last")
        user_in_db = self.client.MFGetObject(mmsid)
        if user_in_db:
            # if the created mid is not empty, the username is taken.
            return False
        
        if not user.mid:
            # a new user who has not even tried. Go to register directly. A good man.
            user.mid = mid
            mmsid_cur = self.client.MMOpen(self.sid, user.mid, "cur")
            self.client.MFSetObject(mmsid_cur, json.dumps(user.model_dump()))
            self.client.MMBackup(self.sid, mmsid_cur, "", "delRef=true")
            self.client.MMAddRef(self.sid, self.mid, user.mid)
        else:
            # if the user already has a mid, it is not a new user.
            mmsid = self.client.MMOpen(self.sid, user.mid, "last")
            user_in_db = UserInDB(**json.loads(self.client.MFGetObject(mmsid)))
            print(user, user_in_db)

            for attr in vars(user):
                setattr(user_in_db, attr, getattr(user, attr))
            user_in_db.mid = mid

            # now theere is changed new username, create a new Mimei for the user.
            mmsid_cur = self.client.MMOpen(self.sid, user_in_db.mid, "cur")
            self.client.HMFSetObject(mmsid_cur, json.dumps(user_in_db.model_dump()))
            self.client.MMBackup(self.sid, mmsid_cur, "", "delRef=true")
            self.client.MMAddRef(self.sid, self.mid, user_in_db.mid)
            self.client.MMDelRef(self.sid, self.mid, user.mid)   # get rid of old mm

    # After registration, username will be different from its identifier.
    def get_user(self, username):
        user_mid = self.client.MMCreate(self.sid, APPID_MIMEI_KEY, "mimei file", username, 1, 0x07276705)
        mmsid = self.client.MMOpen(self.sid, user_mid, "last")
        user = self.client.MFGetObject(mmsid)
        if not user:
            # create an account for the new user. Identifier is required, which is its device ID
            # create an anonymous account, use device id as username until it registers a real account
            mmsid_cur = self.client.MMOpen(self.sid, user_mid, "cur")
            user = UserInDB(username=username, hashed_password="", token_count={"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, token_usage={"gpt-3.5":0, "gpt-4-turbo":0}, subscription=False, mid=user_mid)

            # create a mimei file for the user and ref to it from main mimei
            self.client.MFSetObject(mmsid_cur, user.model_dump())
            self.client.MMBackup(self.sid, mmsid_cur, "", "delRef=true")
            self.client.MMAddRef(self.sid, self.mid, user_mid)
            return user
        else:
            return UserInDB(**json.loads(user))

    def update_user(self, user: UserInDB):
        mmsid = self.client.MMOpen(self.sid, user.mid, "last")
        user_in_db = UserInDB(**json.loads(self.client.Hget(mmsid, USER_ACCOUNT_KEY, user.username)))
        for attr in vars(user):
            setattr(user_in_db, attr, getattr(user, attr))
        mmsid_cur = self.client.MMOpen(self.sid, user.mid, "cur")
        self.client.MFSetObject(mmsid_cur, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")

    def delete_user(self, username: str):
        pass

    def bookkeeping(self, llm, total_cost, total_tokens, mid):
        mmsid = self.client.MMOpen(self.sid, mid, "last")
        user_in_db = UserInDB(**json.loads(self.client.MFGetObject(mmsid)))
        user_in_db.token_usage[llm] += float(total_cost)
        user_in_db.token_count[llm] = max(user_in_db.token_count[llm]-int(total_tokens), 0)

        mmsid_cur = self.client.MMOpen(self.sid, mid, "cur")
        self.client.MFSetObject(mmsid_cur, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, mid, "", "delRef=true")

    # def get_user(username, password, identifier):
    #     # the password is hashed already
    #     user = json.load(self.client.Hget(mmsid, USER_ACCOUNT_KEY, identifier))
    #     if not user:
    #         user = {username:username, password:password, "tokenCount":{"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, "tokenUsage":{"gpt-3.5":0, "gpt-4-turbo":0}, "subscription": False, identifier:identifier}
    #         self.client.Hset(mmsid, USER_ACCOUNT_KEY, identifier, user)
    #     return user
