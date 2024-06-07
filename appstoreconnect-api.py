import requests, time, json
from authlib.jose import jwt
# import jwt

KEY_ID = "58MT2N3H4G"
ISSUER_ID = "b806e892-de29-49c9-b54e-8d79584f6c68"
EXPIRATION_TIME = int(round(time.time() + (20.0 * 60.0))) # 20 minutes timestamp
PATH_TO_KEY = './AuthKey_58MT2N3H4G.p8'
with open(PATH_TO_KEY, 'r') as f:
    PRIVATE_KEY = f.read()

header = {
    "alg": "ES256",
    "kid": KEY_ID,
    "typ": "JWT"
}

payload = {
    "iss": ISSUER_ID,
    "iat": int(time.time()),
    "exp": EXPIRATION_TIME,
    "aud": "appstoreconnect-v1",
    # "scope": [
    #     "GET /v1/apps?filter[platform]=IOS"
    # ],
}

# Create the JWT
token = jwt.encode(header, payload, PRIVATE_KEY)

# API Request
JWT = 'Bearer ' + token.decode()
URL = 'https://api.appstoreconnect.apple.com/v1/users'
HEAD = {'Authorization': JWT}

r = requests.get(URL, params={'limit': 200}, headers=HEAD)

# Write the response in a pretty printed JSON file
with open('output.json', 'w') as out:
    out.write(json.dumps(r.json(), indent=4))
