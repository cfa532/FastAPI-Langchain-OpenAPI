from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import jwt
import hprose
import datetime, os
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()
SECRET_KEY = os.environ["FASTAPI_SECRET_KEY"]

@app.post("/api/token")
async def get_token(request: Request):
    data = await request.json()
    username = data.get('username')
    password = data.get('password')

    # Here you should validate the username and password, e.g., check against a database
    if username == 'admin' and password == 'secret':  # This is just an example
        # Generate token
        payload = {
            'exp': datetime.now(datetime.UTC) + datetime.timedelta(hours=1),  # Expiration time
            'iat': datetime.now(datetime.UTC),  # Issued at time
            'sub': username  # Subject (whom the token refers to)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return JSONResponse({'token': token})
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
