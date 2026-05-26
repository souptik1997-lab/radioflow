from datetime import datetime, timedelta


def evaluate_patient(patient):

    alerts = []

    if patient['simulation_date']:

        simulation_date = datetime.fromisoformat(
            patient['simulation_date']
        )

        if not patient['treatment_started']:

            if datetime.utcnow() - simulation_date > timedelta(days=4):
                alerts.append({
                    'severity': 'critical',
                    'message': 'Treatment not started within 4 days'
                })

    if patient['contouring_done'] and not patient['planning_done']:

        alerts.append({
            'severity': 'warning',
            'message': 'Planning pending'
        })

    return alerts