# RT Patient Flow

A hosted radiation department patient-flow tracker with a Python/SQLite backend, login, role-based access, and a responsive browser UI for Windows, macOS, Android, and intranet/server use.

## Run

Start the backend server:

```powershell
python server.py
```

Then visit:

```text
http://127.0.0.1:8000
```

Seed admin login:

```text
Login ID: admin
Password: ChangeMe123!
```

Change the admin password after first login.

## Notes

- Data is stored in `rt_patient_flow.sqlite3`.
- Seed consultant: Dr. Abhijit Das as primary consultant.
- Seed payment modes: Cash, Swasthya Sathi, Ayushman, WBUHS, Railway, ESI, ECL.
- Machine options: Elekta, Tomo.
- Deleting a consultant transfers their patients to the current primary consultant.
- Deleting a payment mode transfers affected patients to the first remaining mode.
- Admin can onboard users and generate login IDs plus temporary passwords.
- Password recovery emails use SMTP environment variables. Without SMTP, the recovery link is printed in the server console.

## SMTP recovery variables

```text
APP_BASE_URL=https://your-server.example
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_FROM=noreply@example.com
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
```
