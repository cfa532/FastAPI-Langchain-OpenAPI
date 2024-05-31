import hprose, json, time
from datetime import datetime
from utilities import UserInDB, UserOut

APPID_MIMEI_KEY = "FmKK37e1T0oGaQJXRMcMjyrmoxa"
USER_ACCOUNT_KEY = "SECRETARI_APP_USER_ACCOUNT_KEY"
GPT_3_Tokens = 1000000      # bonus tokens upon installation
GPT_4_Turbo_Tokens = 10000
MIMEI_EXT = "mimei file"
# USER_NODE_ID = "1-U-7NvW2hOWmyoiipkzno65so-"      # Mac 8004
USER_NODE_ID = "pM6YSo4Edczo5VYM05hjsGxFtJF"        # Gen8/mimei 8001

class LeitherAPI:
    def __init__(self):
        self.client = hprose.HttpClient('http://localhost:8081/webapi/')
        print(self.client.GetVar("", "ver"))
        self.ppt = self.client.GetVarByContext("", "context_ppt")
        self.api = self.client.Login(self.ppt)
        self.sid = self.api.sid
        self.uid = self.api.uid
        self.mid = self.client.MMCreate(self.sid, APPID_MIMEI_KEY, "app", "secretari backend", 2, 0x07276705)
        self.sid_time = time.time()

        print("sid  ", self.sid)
        print("uid  ", self.uid)
        print("mid  ", self.mid)

    def get_sid(self):
        if time.time() - self.sid_time > 3600:
            self.api = self.client.Login(self.ppt)
            self.sid = self.api.sid
            self.sid_time = time.time()
        return self.sid

    def create_user_mm(self, username) -> str:
        return self.client.MMCreate(self.get_sid(), APPID_MIMEI_KEY, MIMEI_EXT, username, 1, 0x07276705)
    
    def register_temp_user(self, user: UserInDB) -> UserOut:
        user.mid = self.create_user_mm(user.username)
        mmsid = self.client.MMOpen(self.get_sid(), user.mid, "cur")
        user_in_db = self.client.MFGetObject(mmsid)
        if user_in_db:
            # the created mid is not empty, the username is taken.
            print("Temp user exists. Reuse it.")
            mmsid = self.client.MMOpen(self.sid, user.mid, "last")
            return UserOut(**json.loads(self.client.MFGetObject(mmsid)))

        user.token_count = {"gpt-3.5": GPT_3_Tokens, "gpt-4-turbo": GPT_4_Turbo_Tokens}
        user.token_usage = {"gpt-3.5": 0, "gpt-4-turbo": 0}
        user.current_usage = user.token_usage
        self.client.MFSetObject(mmsid, json.dumps(user.model_dump()))
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")
        self.client.MMAddRef(self.sid, self.mid, user.mid)
        return UserOut(**user.model_dump())

    # The function is called when user create a real account by providing personal information. The username shall be different from identifier, used as username in temproral account.
    # A temporary user account has been created when user installed Secretari app. The username is set with device identifier, for a better user experience. This temp account will be deleted after registration. 
    # Information such as token usage and cost will be stored in the database.
    def register_in_db(self, user_in: UserInDB) -> UserOut:
        mid = self.create_user_mm(user_in.username)
        mmsid = self.client.MMOpen(self.get_sid(), mid, "cur")
        user_in_db = self.client.MFGetObject(mmsid)
        if user_in_db:
            # the created mid is not empty, the username is taken.
            print("username is taken", user_in_db)
            return None
        
        if not user_in.mid or not self.client.MFGetObject(self.client.MMOpen(self.sid, user_in.mid, "cur")):
            # a new user who has not even tried before registrating. A good man.
            # or the old mimei is deleted for testing purpose
            user_in.mid = mid
            user_in.token_count = {"gpt-3.5": GPT_3_Tokens, "gpt-4-turbo": GPT_4_Turbo_Tokens}
            user_in.token_usage = {"gpt-3.5": 0, "gpt-4-turbo": 0}
            user_in.current_usage = user_in.token_usage
            self.client.MFSetObject(mmsid, json.dumps(user_in.model_dump()))
            self.client.MMBackup(self.sid, user_in.mid, "", "delRef=true")
            self.client.MMAddRef(self.sid, self.mid, user_in.mid)
            return UserOut(**user_in.model_dump())
        else:
            # if the user already has a mid, open the old mid and copy it content to the new mimei.
            mmsid_in_db = self.client.MMOpen(self.sid, user_in.mid, "last")
            user_in_db = UserInDB(**json.loads(self.client.MFGetObject(mmsid_in_db)))
            print("Before copy. user in db:", user_in_db)
            # Update existing mimei data with incoming data
            user_in_db.username = user_in.username
            user_in_db.hashed_password = user_in.hashed_password
            user_in_db.family_name = user_in.family_name
            user_in_db.given_name = user_in.given_name
            user_in_db.email = user_in.email
            user_in_db.mid = mid    # get a new Mimei id that is genereated with real username
            user_in_db.timestamp = time.time()
    
            print("After copy. user in db:", user_in_db)
            # return UserOut(**user_in_db.model_dump())

            # Open a new mimei for the new user.
            self.client.MFSetObject(mmsid, json.dumps(user_in_db.model_dump()))
            self.client.MMBackup(self.sid, user_in_db.mid, "", "delRef=true")
            self.client.MMAddRef(self.sid, self.mid, user_in_db.mid)
            self.client.MMDelRef(self.sid, self.mid, user_in.mid)      # get rid of old mm
            return UserOut(**user_in_db.model_dump())

    # After registration, username will be different from its identifier.
    def get_user(self, username) -> UserInDB:
        user_mid = self.create_user_mm(username)
        mmsid = self.client.MMOpen(self.get_sid(), user_mid, "cur")
        user = self.client.MFGetObject(mmsid)
        if user:
            print("get_user() found: ", user_mid)
            return UserInDB(**json.loads(user))
        else:
            print("In get_user() user not found", username)
            return None
            # # create an account for the new user. Identifier is required, which is its device ID
            # # create an anonymous account, use device id as username until it registers a real account
            # user = UserInDB(username=username, hashed_password="", token_count={"gpt-3.5":GPT_3_Tokens, "gpt-4-turbo":GPT_4_Turbo_Tokens}, token_usage={"gpt-3.5":0, "gpt-4-turbo":0}, subscription=False, mid=user_mid, current_usage={"gpt-3.5":0, "gpt-4-turbo":0})
            # self.client.MFSetObject(mmsid, json.dumps(user.model_dump()))

            # # create a mimei file for the user and ref to it from main mimei
            # self.client.MMBackup(self.sid, user_mid, "", "delRef=true")
            # self.client.MMAddRef(self.sid, self.mid, user_mid)
            # return user

    def update_user(self, user: UserInDB):
        mmsid = self.client.MMOpen(self.get_sid(), user.mid, "cur")
        user_in_db = UserInDB(**json.loads(self.client.MFGetObject(mmsid)))
        for attr in vars(user):
            setattr(user_in_db, attr, getattr(user, attr))
        self.client.MFSetObject(mmsid, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")

    def delete_user(self, username: str):
        pass

    def bookkeeping(self, llm, total_tokens, total_cost, user_in_db: UserInDB):
        # update monthly expense.
        user_in_db.token_usage[llm] += float(total_cost)    # total usage in dollar amount
        user_in_db.token_count[llm] = max(user_in_db.token_count[llm]-int(total_tokens), 0)
        last_month = datetime.fromtimestamp(user_in_db.timestamp).month
        current_month = datetime.now().month
        if last_month != current_month:
            user_in_db.current_usage[llm] = float(total_cost)       # a new month
        else:
            user_in_db.current_usage[llm] += float(total_cost)      # usage of the month
        user_in_db.timestamp = time.time()
        print("In bookkeeper, user in db:", user_in_db)

        mmsid_cur = self.client.MMOpen(self.get_sid(), user_in_db.mid, "cur")
        self.client.MFSetObject(mmsid_cur, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, user_in_db.mid, "", "delRef=true")
