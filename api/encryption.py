from cryptography.fernet import Fernet
import os

cipher = Fernet(os.environ['ENCRYPTION_KEY'])


def encrypt(value):

    if not value:
        return ''

    return cipher.encrypt(
        value.encode()
    ).decode()


def decrypt(value):

    if not value:
        return ''

    return cipher.decrypt(
        value.encode()
    ).decode()
