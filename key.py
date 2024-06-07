import jwt
import time
from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.SendTestNotificationResponse import SendTestNotificationResponse
from asyncssh import read_private_key

key_id = "2PMR9NKLU7"
issuer_id = "b806e892-de29-49c9-b54e-8d79584f6c68"
# private_key = open('./SubscriptionKey_2PMR9NKLU7.p8').read()
bundle_id = "com.example"
environment = Environment.SANDBOX
private_key = read_private_key("./SubscriptionKey_2PMR9NKLU7.p8") # Implementation will vary

client = AppStoreServerAPIClient(private_key, key_id, issuer_id, bundle_id, environment)

# headers = {
#        'alg': 'ES256',
#        'kid': key_id
# }
# payload = {
#        'iss': issuer_id,
#        'iat': int(time.time()),
#        'exp': int(time.time()) + 20 * 60,  # Token valid for 20 minutes
#        'aud': 'appstoreconnect-v1'
# }
# token = jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
# print(token)

try:    
    response = client.request_test_notification()
    print(response)
except APIException as e:
    print(e)