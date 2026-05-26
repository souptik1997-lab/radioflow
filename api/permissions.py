ROLE_PERMISSIONS = {
    'Coordinator': ['*'],

    'Doctor': [
        'diagnosis',
        'consultants',
        'machine',
        'payment_mode',
        'contouring_done',
        'planning_done',
        'tentative_start',
        'pending_issue',
        'cancelled'
    ],

    'Physicist': [
        'planning_done',
        'machine'
    ],

    'RTT': [
        'simulation_done',
        'treatment_started',
        'consultants',
        'machine'
    ]
}


def can_edit(role, field):

    permissions = ROLE_PERMISSIONS.get(role, [])

    return (
        '*' in permissions or
        field in permissions
    )
