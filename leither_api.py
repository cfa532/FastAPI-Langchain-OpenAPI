import hprose, json, time
from datetime import datetime
from utilities import UserInDB, UserOut
from dotenv import load_dotenv, dotenv_values

APPID_MIMEI_KEY = "FmKK37e1T0oGaQJXRMcMjyrmoxa"
USER_ACCOUNT_KEY = "SECRETARI_APP_USER_ACCOUNT_KEY"
MIMEI_EXT = "mimei file"
MIMEI_COUPON_KEY="SECRETARI_USER_COUPON_KEY"
PRODUCTS={}     # in-app purchase products defined in Appconnect

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

        # user .env to update important parameters. To update app settings without reboot.
        self.load_env()

        print("sid  ", self.sid)
        print("uid  ", self.uid)
        print("mid  ", self.mid)

    def load_env(self):
        global PRODUCTS
        env = dotenv_values(".env")
        self.init_balance = float(env["SIGNUP_BONUS"])
        self.cost_efficiency = float(env["COST_EFFICIENCY"])
        PRODUCTS = json.loads(env["SECRETARI_PRODUCT_ID_IOS"])["ver0"]["productIDs"]     #{"890842":8.99,"Yearly.bunny0":89.99,"monthly.bunny0":8.99}
        
    def get_sid(self):
        if time.time() - self.sid_time > 3600:
            self.api = self.client.Login(self.ppt)
            self.sid = self.api.sid
            self.sid_time = time.time()

            # reload some parameters. Every hour with the sid update
            self.load_env()
        return self.sid

    def create_user_mm(self, username) -> str:
        # given username, get its corresponding mimei
        return self.client.MMCreate(self.get_sid(), APPID_MIMEI_KEY, MIMEI_EXT, username, 1, 0x07276705)
    
    def register_temp_user(self, user: UserInDB) -> UserOut:
        user.mid = self.create_user_mm(user.username)
        mmsid = self.client.MMOpen(self.get_sid(), user.mid, "cur")     # exception if "last" and user does not exist
        if self.client.MFGetObject(mmsid):
            # the created mid is not empty, the username is taken.
            print("Temp user exists. Reuse it.")
            mmsid = self.client.MMOpen(self.sid, user.mid, "last")
            return UserOut(**json.loads(self.client.MFGetObject(mmsid)))

        user.id = user.username         # user's device identifier is used as username for now.
        user.dollar_balance = self.init_balance
        user.token_count = 0
        user.monthly_usage = {datetime.now().month: 0}
        user.dollar_usage = 0
        user.creation_date = time.time()    # required by Apple
        user.timestamp = user.creation_date

        user_str = json.dumps(user.model_dump())
        self.client.MFSetObject(mmsid, user_str)
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")
        self.client.MMAddRef(self.sid, self.mid, user.mid)

        # add new user to index database in Main Mimei
        mmsid = self.client.MMOpen(self.sid, self.mid, "cur")
        self.client.Hset(mmsid, USER_ACCOUNT_KEY, user.mid, user_str)
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
        return UserOut(**user.model_dump())

    # The function is called when user create a real account by providing personal information.
    # The username shall be different from identifier, used as username in temproral account.
    # A temporary user account has been created when user installed Secretari app. 
    # The username is set with device identifier, for a better user experience.
    # This temp account will be deleted after registration. 
    def register_in_db(self, user_in: UserInDB) -> UserOut:
        mid = self.create_user_mm(user_in.username)
        mmsid = self.client.MMOpen(self.get_sid(), mid, "cur")
        user_in_db = self.client.MFGetObject(mmsid)

        if user_in_db:
            # the created mid is not empty, the username is taken.
            print("username is taken", user_in_db)
            return None
        else:
            # the user already has a mid, open the old mid and copy its content to the new mimei.
            mmsid_in_db = self.client.MMOpen(self.sid, user_in.mid, "last")
            user_in_db = UserInDB(**json.loads(self.client.MFGetObject(mmsid_in_db)))
                        # Update existing mimei data with incoming data
            user_in_db.username = user_in.username
            user_in_db.hashed_password = user_in.hashed_password
            user_in_db.family_name = user_in.family_name
            user_in_db.given_name = user_in.given_name
            user_in_db.email = user_in.email
            user_in_db.mid = mid        # new Mimei id that is genereated with real username
            print("After copy. user in db:", user_in_db)

            user_str = json.dumps(user_in_db.model_dump())
            self.client.MFSetObject(mmsid, user_str)
            self.client.MMBackup(self.sid, mid, "", "delRef=true")
            self.client.MMAddRef(self.sid, self.mid, mid)
            self.client.MMDelRef(self.sid, self.mid, user_in.mid)      # get rid of old mm

            # update index Mimei db
            mmsid = self.client.MMOpen(self.sid, self.mid, "cur")
            self.client.Hset(mmsid, USER_ACCOUNT_KEY, mid, user_str)
            self.client.Hdel(mmsid, USER_ACCOUNT_KEY, user_in.mid)
            self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
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

    def update_user(self, user_in: UserInDB):
        mmsid = self.client.MMOpen(self.get_sid(), user_in.mid, "cur")
        user_in_db = UserInDB(**json.loads(self.client.MFGetObject(mmsid)))
        if user_in.hashed_password == "":
            del user_in.hashed_password

        for attr in vars(user_in):
            setattr(user_in_db, attr, getattr(user_in, attr))
        self.client.MFSetObject(mmsid, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, user_in.mid, "", "delRef=true")

    def cash_coupon(self, user_in: UserInDB, coupon: str):
        mmsid = self.client.MMOpen(self.get_sid(), self.mid, "cur")
        coupon_in_db = self.client.Hget(mmsid, MIMEI_COUPON_KEY, coupon)
        # coupon_in_db = {model:"gpt-4-turbo", redeemed: false, amount: 1001000, expiration_date: 1672588674}
        if not coupon_in_db and not coupon_in_db.used and time.time() < coupon_in_db.expiration_date:
            return False
        # redeem the coupon
        mmsid = self.client.MMOpen(self.sid, user_in.mid, "cur")
        user_in.dollar_balance += coupon_in_db.amount
        self.client.MFSetObject(mmsid, json.dumps(user_in.model_dump()))
        self.client.MMBackup(self.sid, user_in.mid, "", "delRef=true")

        coupon_in_db.redeemed = True
        coupon_in_db.expiration_date = time.time()
        self.client.Hset(mmsid, MIMEI_COUPON_KEY, coupon, (coupon_in_db))
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
        return True

    def delete_user(self, username: str):
        pass

    def bookkeeping(self, llm, total_cost: float, token_cost: int, user_in_db: UserInDB):
        # update monthly expense. Times the cost efficiency to include profit.
        user_in_db.dollar_usage += total_cost * self.cost_efficiency    # total usage in dollar amount
        user_in_db.dollar_balance -= total_cost * self.cost_efficiency
        user_in_db.token_count += int(token_cost * self.cost_efficiency)

        last_month = datetime.fromtimestamp(user_in_db.timestamp).month
        current_month = datetime.now().month
        if last_month != current_month:
            user_in_db.monthly_usage[str(current_month)] = total_cost * self.cost_efficiency       # a new month
        else:
            user_in_db.monthly_usage[str(current_month)] += total_cost * self.cost_efficiency     # usage of the month
        user_in_db.timestamp = time.time()
        print("In bookkeeper, user in db:", user_in_db)

        mmsid_cur = self.client.MMOpen(self.get_sid(), user_in_db.mid, "cur")
        self.client.MFSetObject(mmsid_cur, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, user_in_db.mid, "", "delRef=true")

    # keep a record of all the purchase and subscriptions a customer made.
    def upload_recharge(self, current_user: UserInDB, purchase) -> UserOut:
        # ["originalTransactionID": 2000000622918330, "product_id": "890842", "currency": "TWD", "transactionDate": 1717914627.067, "amount": 290]
        purchase["balance"] = current_user.dollar_balance       # remember the dollar balance at the time of recharge,
                                                                # in case of a refund, need to know how much to refund.
        # Apple uses localized currency, so need to convert to dollar.
        dollar_amount = float(PRODUCTS[purchase["product_id"]])
        current_user.dollar_balance += dollar_amount
        current_user.accured_total += dollar_amount        # revenue from the user.

        if current_user.purchase_history is None:
            current_user.purchase_history = [purchase]
        else:
            current_user.purchase_history.append(purchase)

        mmsid = self.client.MMOpen(self.get_sid(), current_user.mid, "cur")
        self.client.MFSetObject(mmsid, json.dumps(current_user.model_dump()))
        self.client.MMBackup(self.sid, current_user.mid, "", "delRef=true")

        print("After recharge:", current_user)
        return current_user

    def subscribe_user(self, current_user, subscription) -> UserOut:
        if current_user.purchase_history is None:
            current_user.purchase_history = [subscription]
        else:
            current_user.purchase_history.append(subscription)

        mmsid = self.client.MMOpen(self.get_sid(), current_user.mid, "cur")
        self.client.MFSetObject(mmsid, json.dumps(current_user.model_dump()))
        self.client.MMBackup(self.sid, current_user.mid, "", "delRef=true")

        print("After subscription:", current_user)
        return current_user
