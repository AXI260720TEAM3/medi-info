from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

# 믹서기: bcrypt 방식으로 갈아요
password_hash = PasswordHash((BcryptHasher(),))


def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)