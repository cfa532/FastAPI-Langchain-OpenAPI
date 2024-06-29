import hprose, json, time, sys
from datetime import datetime
from utilities import UserInDB, UserOut, Purchase
from dotenv import load_dotenv, dotenv_values

APPID_MIMEI_KEY: str = "FmKK37e1T0oGaQJXRMcMjyrmoxa"
USER_ACCOUNT_KEY: str = "SECRETARI_APP_USER_ACCOUNT_KEY"
MIMEI_EXT: str = "mimei file"
MIMEI_COUPON_KEY: str = "SECRETARI_USER_COUPON_KEY"
PRODUCTS={}     # in-app purchase products defined in Appconnect

class LeitherAPI:
 
    def __init__(self):
        self.client = hprose.HttpClient('http://localhost:8081/webapi/')
        print(self.client.GetVar("", "ver"))
        self.ppt = self.client.GetVarByContext("", "context_ppt")
        self.api = self.client.Login(self.ppt)
        self.sid = self.api.sid
        self.uid = self.api.uid
        self.mid = self.client.MMCreate(self.sid, APPID_MIMEI_KEY, "App", "secretari backend", 2, 0x07276705)
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
        print("Products of the hour:", PRODUCTS)

    # keep a record of all the purchase and subscriptions a customer made.
    # process message from Apple notification server. UserId is the only identifier of the user.
    def recharge_user(self, userId: str, transaction: Purchase):
        mmsid = self.client.MMOpen("", self.mid, "last")
        user = UserInDB(**json.loads(self.client.Hget(mmsid, USER_ACCOUNT_KEY, userId)))

        # user.id is assigned to transaction.appAccountToken before purchase, so that we know who paid for the productId.
        # Now get the mimei file where all user data is stored, and append new purchase data to it.
        mmsid = self.client.MMOpen(self.sid, user.mid, "cur")
        user = UserInDB(**json.loads(self.client.MFGetObject(mmsid)))

        # transaction from Apple use local currency for price. Get USD price.
        dollar_amount = float(PRODUCTS[transaction.productId])
        
        # remember the dollar balance at the time of recharge, in case of a refund, need to know how much left to refund
        transaction.currentBalance = user.dollar_balance
        user.dollar_balance += dollar_amount * transaction.quantity
        user.accured_total += dollar_amount * transaction.quantity       # revenue from the user.
        if user.purchase_history is None:
            user.purchase_history = [transaction.model_dump()]
        else:
            user.purchase_history.append(transaction.model_dump())

        self.client.MFSetObject(mmsid, json.dumps(user.model_dump()))
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")
        print("After recharge:", user)
        return user

    def subscribed(self, userId: str, transaction: Purchase):
        mmsid = self.client.MMOpen("", self.mid, "last")
        user = UserInDB(**json.loads(self.client.Hget(mmsid, USER_ACCOUNT_KEY, userId)))

        mmsid = self.client.MMOpen(self.sid, user.mid, "cur")
        user = UserInDB(**json.loads(self.client.MFGetObject(mmsid)))

        # transaction from Apple use local currency for price. Get USD price.
        # record total income from the user
        user.accured_total += float(PRODUCTS[transaction.productId])
        if user.purchase_history is None:
            user.purchase_history = [transaction.model_dump()]
        else:
            user.purchase_history.append(transaction.model_dump())

        self.client.MFSetObject(mmsid, json.dumps(user.model_dump()))
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")
        print("After subscription:", user)

    def get_sid(self) -> str:
        if time.time() - self.sid_time > 3600:
            self.ppt = self.client.GetVarByContext("", "context_ppt")   # get new ppt everytime
            self.api = self.client.Login(self.ppt)
            self.sid = self.api.sid
            self.sid_time = time.time()

            # reload some parameters. Every hour with the sid update
            self.load_env()

            # publish data changes every hour
            self.client.MiMeiPublish(self.sid, "", self.mid)
        return self.sid

    def create_user_mm(self, username) -> str:
        # given username, get its corresponding mimei
        return self.client.MMCreate(self.get_sid(), APPID_MIMEI_KEY, MIMEI_EXT, username, 1, 0x07276705)
    
    def get_user_name(self, id):
        # given user id, find username from the index db
        mmsid = self.client.MMOpen(self.get_sid(), self.mid, "last")
        user_str = self.client.Hget(mmsid, USER_ACCOUNT_KEY, id)
        if not user_str:
            return None
        return json.loads(user_str).get("username")

    def register_temp_user(self, user: UserInDB) -> UserOut:
        user.mid = self.create_user_mm(user.username)

        # If the mm does not exist, open its "last" version will result in an exception. User "cur" instead.
        mmsid = self.client.MMOpen(self.get_sid(), user.mid, "cur")
        if self.client.MFGetObject(mmsid):
            # the created mid is not empty, the username is taken.
            mmsid = self.client.MMOpen(self.sid, user.mid, "last")
            user = json.loads(self.client.MFGetObject(mmsid))
            print("Temp user exists. Reuse it.", user)
            return UserOut(**user)

        # user's device identifier is used as username for temp account. After user regisetered with a username,
        # user.id will still be used as index in the main user db, and appAccountToken in Transaction.
        # so when server receives notification from Apple Server, it is easier to find which user it belongs.
        user.id = user.username
        user.dollar_balance = self.init_balance     # singup bonus offered for free trial.
        user.token_count = 0
        user.monthly_usage = {datetime.now().month: 0}      # to enforce the spending cap of an user.
        user.dollar_usage = 0
        user.creation_date = time.time()    # required by Apple to know how long the user has been.
        user.timestamp = user.creation_date     # updated each time the user used service.

        user_str = json.dumps(user.model_dump())
        self.client.MFSetObject(mmsid, user_str)
        self.client.MMBackup(self.sid, user.mid, "", "delRef=true")
        self.client.MMAddRef(self.sid, self.mid, user.mid)      # when main DB published, user MM publish with it.

        # add new user to index database in Main Mimei
        mmsid = self.client.MMOpen(self.sid, self.mid, "cur")
        self.client.Hset(mmsid, USER_ACCOUNT_KEY, user.id.upper(), user_str)    # user.id always as index to user object in main DB.
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
        self.client.MiMeiPublish(self.sid, "", self.mid)
        print("temp user created:", user)
        return UserOut(**user.model_dump())

    # The function is called when user create a real account by providing personal information.
    # Before it, a device identifier is used as username in temporary account, which will be deleted after registration. 
    def register_in_db(self, user_in: UserInDB) -> UserOut:
        mid = self.create_user_mm(user_in.username)
        mmsid = self.client.MMOpen(self.get_sid(), mid, "cur")
        user_in_mm = self.client.MFGetObject(mmsid)

        if user_in_mm:
            # the mimei file is not empty, the username is taken.
            print("username is taken", user_in_mm)
            return None
        else:
            # the mimei file is empty, let's check index mimei db, which is indexed by user.id
            user_in_db = self.client.Hget(self.client.MMOpen(self.sid, self.mid, "last"), USER_ACCOUNT_KEY, user_in.id)
            print("user in db", user_in_db)
            if not user_in_db:
                # no record of user_in.id in index db too and no mimei file exists, create one.
                user_in.dollar_balance = self.init_balance     # singup bonus offered for free trial.
                user_in.token_count = 0
                user_in.monthly_usage = {datetime.now().month: 0}      # to enforce the spending cap of an user.
                user_in.dollar_usage = 0
                user_in.creation_date = time.time()    # required by Apple to know how long the user has been.
                user_in.timestamp = user_in.creation_date     # updated each time the user used service.
                user_in.mid = mid
                self.client.MFSetObject(mmsid, json.dumps(user_in.model_dump()))
                self.client.MMBackup(self.sid, mid, "", "delRef=true")

                mmsid_db = self.client.MMOpen(self.sid, self.mid, "cur")
                self.client.Hset(mmsid_db, USER_ACCOUNT_KEY, user_in.id, json.dumps(user_in.model_dump()))
                self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
                self.client.MMAddRef(self.sid, self.mid, mid)
                self.client.MiMeiPublish(self.sid, "", self.mid)
                return UserOut(**user_in.model_dump())

            else:
                # Mimei create from given username not exists, but there is record in index db.
                # Happens when user registered with a new username. Overwrite the previous one in index db.
                user_in_db = UserInDB(**json.loads(user_in_db))
                
                # open incumbent account to get user mid, which might points to temp mm or previous mimei
                mmsid_in_db = self.client.MMOpen(self.sid, user_in_db.mid, "last")
                user_in_mm = UserInDB(**json.loads(self.client.MFGetObject(mmsid_in_db)))
                
                # Update existing mimei data with registration information provided by user.
                user_in_mm.username = user_in.username
                user_in_mm.hashed_password = user_in.hashed_password
                user_in_mm.family_name = user_in.family_name
                user_in_mm.given_name = user_in.given_name
                user_in_mm.email = user_in.email

                # new Mimei id that is genereated with real username, so the mimei can be found with username quickly.
                user_in_mm.mid = mid
                print("After copy. user in db:", user_in_mm)

                # create new mimei for the incoming user object
                user_str = json.dumps(user_in_mm.model_dump())
                self.client.MFSetObject(mmsid, user_str)
                self.client.MMBackup(self.sid, mid, "", "delRef=true")
                self.client.MMAddRef(self.sid, self.mid, mid)

                # remove reference to temp account mimei.
                self.client.MMDelRef(self.sid, self.mid, user_in_db.mid)

                # update index Mimei db
                mmsid_db = self.client.MMOpen(self.sid, self.mid, "cur")
                self.client.Hset(mmsid_db, USER_ACCOUNT_KEY, user_in_db.id, user_str)     # update temp user account with registered one.
                self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
                self.client.MiMeiPublish(self.sid, "", self.mid)
                self.client.MMDelVers(self.sid, user_in_db.mid)     # delete old mm created with user id

                return UserOut(**user_in_mm.model_dump())
        
    def update_user(self, user_in: UserInDB) -> UserOut:
        mmsid = self.client.MMOpen(self.get_sid(), user_in.mid, "cur")
        self.client.MFSetObject(mmsid, json.dumps(user_in.model_dump()))
        self.client.MMBackup(self.sid, user_in.mid, "", "delRef=true")

        mmsid = self.client.MMOpen(self.sid, self.mid, "cur")
        self.client.Hset(mmsid, USER_ACCOUNT_KEY, user_in.id, json.dumps(user_in.model_dump()))     # update temp user account with registered one.
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
        self.client.MiMeiPublish(self.sid, "", self.mid)

        return UserOut(**user_in.model_dump())
    
    def delete_user(self, user_in: UserInDB) -> dict:
        mmsid = self.client.MMOpen(self.get_sid(), self.mid, "last")
        user_in = UserInDB(**json.loads(self.client.Hget(mmsid, USER_ACCOUNT_KEY, user_in.id)))
        user_in.disabled = True
        mmsid = self.client.MMOpen(self.get_sid(), self.mid, "cur")
        self.client.Hset(mmsid, USER_ACCOUNT_KEY, user_in.id, json.dumps(user_in.model_dump()))     # remove user from index db
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
        self.client.MiMeiPublish(self.sid, "", self.mid)
        # self.client.MMDelRef(self.sid, self.mid, user_in.mid)     # remove reference to mimei

        #keep the mimei created from username, in case use re-register with the same username.
        return {"id": user_in.id}

    # After registration, username will be different from its identifier.
    def get_user(self, username) -> UserInDB:
        user_mid = self.create_user_mm(username)
        mmsid = self.client.MMOpen(self.get_sid(), user_mid, "cur")
        user = self.client.MFGetObject(mmsid)
        if user:
            # print("get_user() found: ", user_mid)
            return UserInDB(**json.loads(user))
        else:
            print("get_user() cannot found", username)
            return None

    # check user record in index db
    def get_user_in_db(self, user: UserInDB) -> UserInDB:
        mmsid = self.client.MMOpen(self.get_sid(), self.mid, "last")
        r = self.client.Hget(mmsid, USER_ACCOUNT_KEY, user.id)
        if not r:
            return None
        else:
            user_in_db = UserInDB(**json.loads(r))
            if user_in_db.disabled:
                return None
            return user_in_db
        
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
        self.client.Hset(mmsid, MIMEI_COUPON_KEY, coupon, json.dumps(coupon_in_db))
        self.client.MMBackup(self.sid, self.mid, "", "delRef=true")
        self.client.MiMeiPublish(self.sid, "", self.mid)
        return True

    def bookkeeping(self, total_cost: float, token_cost: int, user_in_db: UserInDB):
        # update monthly expense. Times the cost efficiency to include profit.
        dollar_cost = total_cost * self.cost_efficiency
        user_in_db.dollar_usage += dollar_cost    # total usage in dollar amount. Full history
        user_in_db.dollar_balance -= dollar_cost  # keep sync with device
        user_in_db.token_count += int(token_cost * self.cost_efficiency)

        last_month = datetime.fromtimestamp(user_in_db.timestamp).month
        current_month = datetime.now().month
        if last_month != current_month:
            user_in_db.monthly_usage[str(current_month)] = dollar_cost       # a new month
        else:
            user_in_db.monthly_usage[str(current_month)] += dollar_cost     # usage of the month
        user_in_db.timestamp = time.time()
        print("In bookkeeper, user in db:", UserOut(**user_in_db.model_dump()))
        sys.stdout.flush()
        
        mmsid_cur = self.client.MMOpen(self.get_sid(), user_in_db.mid, "cur")
        self.client.MFSetObject(mmsid_cur, json.dumps(user_in_db.model_dump()))
        self.client.MMBackup(self.sid, user_in_db.mid, "", "delRef=true")
