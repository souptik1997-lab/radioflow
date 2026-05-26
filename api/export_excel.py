from openpyxl import Workbook
from fastapi.responses import FileResponse


def build_excel(patients):

    workbook = Workbook()
    sheet = workbook.active

    headers = [
        'Patient Name',
        'File Number',
        'Diagnosis',
        'Consultants',
        'Primary Consultant',
        'Simulation Date',
        'Treatment Started',
        'Treatment Start Date',
        'Machine'
    ]

    sheet.append(headers)

    for patient in patients:

        sheet.append([
            patient.get('name'),
            patient.get('patient_number'),
            patient.get('diagnosis'),
            patient.get('consultants'),
            patient.get('primary_consultant'),
            patient.get('simulation_date'),
            patient.get('treatment_started'),
            patient.get('treatment_start_date'),
            patient.get('machine')
        ])

    file_name = '/tmp/patients.xlsx'

    workbook.save(file_name)

    return FileResponse(
        file_name,
        filename='patients.xlsx'
    )
