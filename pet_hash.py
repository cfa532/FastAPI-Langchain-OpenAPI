import hashlib
import os
import base64
ROUNDS = 1000

def get_password_hash(password):
    salt = os.urandom(16)  # Smaller salt for demonstration; 32 bytes is more secure
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ROUNDS)  # Reduced iterations

    # Storing the salt along with the hash is crucial
    storage = base64.b64encode(salt + hashed).decode('utf-8')
    return storage

def verify_password(plain_password, hashed_password):
    storage_bytes = base64.b64decode(hashed_password.encode('utf-8'))
    salt_from_storage = storage_bytes[:16]
    hashed_from_storage = storage_bytes[16:]

    # Ensure the password is encoded before hashing
    password_to_verify = plain_password.encode('utf-8')
    new_hashed = hashlib.pbkdf2_hmac('sha256', password_to_verify, salt_from_storage, ROUNDS)

    if new_hashed == hashed_from_storage:
        return True
    else:
        return False