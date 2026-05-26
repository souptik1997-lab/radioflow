from supabase import create_client
from cryptography.fernet import Fernet
import os

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_KEY']
)

cipher = Fernet(os.environ['ENCRYPTION_KEY'])


def save_setting(key, value, user_id):

    encrypted = cipher.encrypt(
        value.encode()
    ).decode()

    supabase.table('system_settings').upsert({
        'key': key,
        'encrypted_value': encrypted,
        'updated_by': user_id
    }).execute()


def get_setting(key):

    response = (
        supabase
        .table('system_settings')
        .select('*')
        .eq('key', key)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    encrypted = response.data[0]['encrypted_value']

    return cipher.decrypt(
        encrypted.encode()
    ).decode()
