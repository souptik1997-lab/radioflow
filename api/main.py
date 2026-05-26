from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client
from encryption import encrypt
from encryption import decrypt
from export_excel import build_excel
from settings_manager import save_setting
from settings_manager import get_setting
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

supabase = create_client(
    os.environ['SUPABASE_URL'],
    os.environ['SUPABASE_KEY']
)


@app.get('/api/patients')
def get_patients():

    response = (
        supabase
        .table('patients')
        .select('*')
        .execute()
    )

    patients = []

    for patient in response.data:

        patient['name'] = decrypt(
            patient['encrypted_name']
        )

        patient['diagnosis'] = decrypt(
            patient['encrypted_diagnosis']
        )

        patients.append(patient)

    return patients


@app.post('/api/patients')
def create_patient(payload: dict):

    supabase.table('patients').insert({
        'patient_number': payload['patient_number'],
        'encrypted_name': encrypt(payload['name']),
        'encrypted_diagnosis': encrypt(payload['diagnosis']),
        'simulation_date': payload.get('simulation_date'),
        'treatment_started': payload.get('treatment_started', False),
        'machine_id': payload.get('machine_id')
    }).execute()

    return {
        'success': True
    }


@app.get('/api/export')
def export_excel():

    response = (
        supabase
        .table('patients')
        .select('*')
        .execute()
    )

    return build_excel(response.data)


@app.post('/api/settings')
def update_settings(payload: dict):

    for key, value in payload.items():

        save_setting(
            key,
            value,
            'system'
        )

    return {
        'success': True
    }


@app.get('/api/settings')
def fetch_settings():

    return {
        'smtp_host': bool(get_setting('SMTP_HOST')),
        'smtp_user': bool(get_setting('SMTP_USER')),
        'google_drive': bool(get_setting('GOOGLE_DRIVE_CLIENT_ID'))
    }

@app.get("/")
def root():
    return {"status": "ok"}
