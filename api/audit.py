from supabase import create_client
import os

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_KEY']
)


def log_action(user_id, patient_id, action, old_value, new_value, ip):

    supabase.table('audit_logs').insert({
        'user_id': user_id,
        'patient_id': patient_id,
        'action': action,
        'old_value': old_value,
        'new_value': new_value,
        'ip_address': ip
    }).execute()