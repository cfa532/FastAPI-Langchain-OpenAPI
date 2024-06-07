# pip install app-store-server-library

import jwt
import time
from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.SendTestNotificationResponse import SendTestNotificationResponse

key_id = "2PMR9NKLU7"
issuer_id = "b806e892-de29-49c9-b54e-8d79584f6c68"
# private_key = open('./SubscriptionKey_2PMR9NKLU7.p8').read()
bundle_id = "secretari.leither.uk"               # in app settings
environment = Environment.SANDBOX
with open("./SubscriptionKey_2PMR9NKLU7.p8", 'rb') as f:        # read to bytes-like object
    private_key = f.read()

# print(private_key)
client = AppStoreServerAPIClient(private_key, key_id, issuer_id, bundle_id, environment)

try:    
    response = client.request_test_notification()
    print(response)
except APIException as e:
    print(e)
