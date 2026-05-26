from datetime import datetime, timedelta
from jose import jwt
import os

JWT_SECRET = os.environ['JWT_SECRET']
ALGORITHM = 'HS256'


def create_token(user):

    payload = {
        'sub': str(user['id']),
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(hours=12)
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=ALGORITHM
    )
