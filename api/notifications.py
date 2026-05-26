from supabase import create_client
import os

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_KEY']
)


def create_notification(user_id, patient_id, severity, title, message):

    supabase.table('notifications').insert({
        'user_id': user_id,
        'patient_id': patient_id,
        'severity': severity,
        'title': title,
        'message': message
    }).execute()