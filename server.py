from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "rt_patient_flow.sqlite3"
SESSION_DAYS = 7
ROLES = ("Admin", "Doctor", "Physicist", "RTT")

ADMIN_FIELDS = {
    "id", "name", "phone", "diagnosis", "firstVisit", "consultantId", "simulationDate",
    "simulationDone", "machine", "paymentMode", "contouringDone", "planningDone",
    "tentativeStart", "treatmentStarted", "pendingIssue", "cancelled", "cancellationNote",
}
ROLE_FIELDS = {
    "Admin": ADMIN_FIELDS,
    "Doctor": {
        "diagnosis", "consultantId", "machine", "paymentMode", "contouringDone",
        "planningDone", "tentativeStart", "pendingIssue", "cancelled", "cancellationNote",
    },
    "Physicist": {"planningDone", "machine"},
    "RTT": {"simulationDone", "simulationDate", "treatmentStarted", "consultantId", "machine"},
}


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 160_000)
    return f"{salt}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt).split("$", 1)[1], expected)


def bool_int(value):
    return 1 if value in (True, 1, "1", "true", "True", "yes", "Yes") else 0


def row_to_patient(row):
    data = dict(row)
    for key in ("simulationDone", "contouringDone", "planningDone", "treatmentStarted", "cancelled"):
        data[key] = bool(data[key])
    return data


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS consultants (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              is_primary INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS payment_modes (
              name TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              login_id TEXT NOT NULL UNIQUE,
              name TEXT NOT NULL,
              email TEXT NOT NULL UNIQUE,
              role TEXT NOT NULL CHECK(role IN ('Admin','Doctor','Physicist','RTT')),
              password_hash TEXT NOT NULL,
              must_change_password INTEGER NOT NULL DEFAULT 1,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recovery_tokens (
              token TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              expires_at TEXT NOT NULL,
              used INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS patients (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              phone TEXT DEFAULT '',
              diagnosis TEXT DEFAULT '',
              firstVisit TEXT DEFAULT '',
              consultantId TEXT NOT NULL,
              simulationDate TEXT DEFAULT '',
              simulationDone INTEGER NOT NULL DEFAULT 0,
              machine TEXT DEFAULT 'Elekta',
              paymentMode TEXT DEFAULT 'Cash',
              contouringDone INTEGER NOT NULL DEFAULT 0,
              planningDone INTEGER NOT NULL DEFAULT 0,
              tentativeStart TEXT DEFAULT '',
              treatmentStarted INTEGER NOT NULL DEFAULT 0,
              pendingIssue TEXT DEFAULT '',
              cancelled INTEGER NOT NULL DEFAULT 0,
              cancellationNote TEXT DEFAULT ''
            );
            """
        )
        if not conn.execute("SELECT 1 FROM consultants").fetchone():
            conn.execute(
                "INSERT INTO consultants (id, name, is_primary) VALUES (?, ?, 1)",
                ("dr-abhijit-das", "Dr. Abhijit Das"),
            )
        for mode in ("Cash", "Swasthya Sathi", "Ayushman", "WBUHS", "Railway", "ESI", "ECL"):
            conn.execute("INSERT OR IGNORE INTO payment_modes (name) VALUES (?)", (mode,))
        if not conn.execute("SELECT 1 FROM users").fetchone():
            conn.execute(
                """
                INSERT INTO users (login_id, name, email, role, password_hash, must_change_password, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    "admin",
                    "Department Admin",
                    "admin@example.com",
                    "Admin",
                    hash_password("ChangeMe123!"),
                    now(),
                ),
            )
        if not conn.execute("SELECT 1 FROM patients").fetchone():
            seed = [
                ("RT2026000123", "Ananya Sen", "9830011122", "Carcinoma cervix", "2026-05-18", "2026-05-21", 1, "Tomo", "Swasthya Sathi", 1, 0, "2026-05-28", 0, "Awaiting recent creatinine report.", 0, ""),
                ("RT2026000456", "Rahul Ghosh", "9903123456", "Head and neck cancer", "2026-05-10", "2026-05-14", 1, "Elekta", "Cash", 1, 1, "2026-05-20", 1, "", 0, ""),
                ("RT2026000789", "Mina Paul", "9007001122", "Left breast cancer", "2026-05-20", "2026-05-24", 1, "Tomo", "WBUHS", 0, 0, "2026-06-02", 0, "", 0, ""),
                ("RT2026000911", "Subhash Roy", "9433321099", "Ca prostate", "2026-05-09", "", 0, "Elekta", "Railway", 0, 0, "", 0, "", 1, "Patient opted for treatment nearer home."),
            ]
            conn.executemany(
                """
                INSERT INTO patients VALUES (?, ?, ?, ?, ?, 'dr-abhijit-das', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                seed,
            )


def now():
    return datetime.now(timezone.utc).isoformat()


def expires(days=SESSION_DAYS):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        clean = urlparse(path).path.lstrip("/") or "index.html"
        return str(ROOT / clean)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.route_api("GET")
            return
        super().do_GET()

    def do_POST(self):
        self.route_api("POST")

    def do_PATCH(self):
        self.route_api("PATCH")

    def do_DELETE(self):
        self.route_api("DELETE")

    def route_api(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/login" and method == "POST":
                self.login()
            elif path == "/api/logout" and method == "POST":
                self.logout()
            elif path == "/api/recover" and method == "POST":
                self.recover()
            elif path == "/api/reset-password" and method == "POST":
                self.reset_password()
            elif path == "/api/me":
                self.send_json({"user": None})
            elif path == "/api/state":
                self.state()
            elif path == "/api/patients" and method == "POST":
                self.create_patient()
            elif path.startswith("/api/patients/") and method == "PATCH":
                self.update_patient(path.rsplit("/", 1)[1])
            elif path == "/api/consultants" and method == "POST":
                self.create_consultant()
            elif path.startswith("/api/consultants/") and method == "PATCH":
                self.set_primary_consultant(path.rsplit("/", 1)[1])
            elif path.startswith("/api/consultants/") and method == "DELETE":
                self.delete_consultant(path.rsplit("/", 1)[1])
            elif path == "/api/payment-modes" and method == "POST":
                self.create_payment_mode()
            elif path.startswith("/api/payment-modes/") and method == "DELETE":
                self.delete_payment_mode(path.rsplit("/", 1)[1])
            elif path == "/api/users" and method == "POST":
                self.create_user()
            elif path.startswith("/api/users/") and method == "PATCH":
                self.update_user(path.rsplit("/", 1)[1])
            elif path == "/api/change-password" and method == "POST":
                self.require_user()
                self.change_password()
            else:
                self.send_error_json(HTTPStatus.NOT_FOUND, "Endpoint not found")
        except PermissionError as exc:
            self.send_error_json(HTTPStatus.FORBIDDEN, str(exc) or "Not allowed")
        except ValueError as exc:
            self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception as exc:
            self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"Server error: {exc}")

    def body(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode() if length else "{}"
        return json.loads(raw or "{}")

    def send_json(self, data, status=HTTPStatus.OK, cookies=None):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        if cookies:
            for cookie in cookies:
                self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(payload)

    def send_error_json(self, status, message):
        self.send_json({"error": message}, status)

    def session_token(self):
        cookie = SimpleCookie(self.headers.get("Cookie"))
        return cookie.get("rt_session").value if cookie.get("rt_session") else None

    def require_user(self, roles=None):
        token = self.session_token()
        if not token:
            raise PermissionError("Login required")
        with db() as conn:
            row = conn.execute(
                """
                SELECT users.* FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ? AND sessions.expires_at > ? AND users.active = 1
                """,
                (token, now()),
            ).fetchone()
        if not row:
            raise PermissionError("Login required")
        self.user = {key: row[key] for key in ("id", "login_id", "name", "email", "role", "must_change_password")}
        if roles and self.user["role"] not in roles:
            raise PermissionError("Your role cannot perform this operation")

    def login(self):
        data = self.body()
        with db() as conn:
            row = conn.execute("SELECT * FROM users WHERE login_id = ? AND active = 1", (data.get("loginId", ""),)).fetchone()
            if not row or not verify_password(data.get("password", ""), row["password_hash"]):
                raise PermissionError("Invalid login ID or password")
            token = secrets.token_urlsafe(32)
            conn.execute("INSERT INTO sessions VALUES (?, ?, ?)", (token, row["id"], expires()))
        cookie = f"rt_session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={SESSION_DAYS * 86400}"
        self.send_json({"ok": True}, cookies=[cookie])

    def logout(self):
        token = self.session_token()
        with db() as conn:
            if token:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.send_json({"ok": True}, cookies=["rt_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"])

    def state(self):
        with db() as conn:
            patients = [row_to_patient(row) for row in conn.execute("SELECT * FROM patients ORDER BY name")]
            consultants = []
            for row in conn.execute("SELECT id, name, is_primary FROM consultants ORDER BY name"):
                consultants.append({"id": row["id"], "name": row["name"], "primary": bool(row["is_primary"])})
            modes = [row["name"] for row in conn.execute("SELECT name FROM payment_modes ORDER BY name")]
            users = [dict(row) for row in conn.execute("SELECT id, login_id, name, email, role, active, must_change_password FROM users ORDER BY name")]
        self.send_json({"patients": patients, "consultants": consultants, "paymentModes": modes, "machines": ["Elekta", "Tomo"], "users": users, "me": None})

    def create_patient(self):
        data = self.body()
        patient_id = data.get("id", "").strip()
        name = data.get("name", "").strip()
        if not patient_id or not name:
            raise ValueError("Patient ID and name are required")
        primary = primary_consultant_id()
        with db() as conn:
            conn.execute(
                """
                INSERT INTO patients (id, name, phone, diagnosis, firstVisit, consultantId, machine, paymentMode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (patient_id, name, data.get("phone", ""), data.get("diagnosis", ""), data.get("firstVisit", ""), data.get("consultantId") or primary, data.get("machine", "Elekta"), data.get("paymentMode", "Cash")),
            )
        self.send_json({"ok": True})

    def update_patient(self, patient_id):
        data = self.body()
        updates = {key: value for key, value in data.items() if key in ADMIN_FIELDS}
        if not updates:
            raise ValueError("No patient fields to update")
        bool_fields = {"simulationDone", "contouringDone", "planningDone", "treatmentStarted", "cancelled"}
        assignments = []
        values = []
        for key, value in updates.items():
            assignments.append(f"{key} = ?")
            values.append(bool_int(value) if key in bool_fields else value)
        values.append(patient_id)
        with db() as conn:
            conn.execute(f"UPDATE patients SET {', '.join(assignments)} WHERE id = ?", values)
        self.send_json({"ok": True})

    def create_consultant(self):
        name = self.body().get("name", "").strip()
        if not name:
            raise ValueError("Consultant name is required")
        with db() as conn:
            conn.execute("INSERT INTO consultants VALUES (?, ?, 0)", (slug(name), name))
        self.send_json({"ok": True})

    def set_primary_consultant(self, consultant_id):
        with db() as conn:
            conn.execute("UPDATE consultants SET is_primary = 0")
            conn.execute("UPDATE consultants SET is_primary = 1 WHERE id = ?", (consultant_id,))
        self.send_json({"ok": True})

    def delete_consultant(self, consultant_id):
        with db() as conn:
            count = conn.execute("SELECT COUNT(*) AS count FROM consultants").fetchone()["count"]
            if count <= 1:
                raise ValueError("At least one consultant is required")
            replacement = primary_consultant_id(conn, exclude=consultant_id)
            conn.execute("UPDATE patients SET consultantId = ? WHERE consultantId = ?", (replacement, consultant_id))
            conn.execute("DELETE FROM consultants WHERE id = ?", (consultant_id,))
        self.send_json({"ok": True})

    def create_payment_mode(self):
        name = self.body().get("name", "").strip()
        if not name:
            raise ValueError("Payment mode is required")
        with db() as conn:
            conn.execute("INSERT OR IGNORE INTO payment_modes VALUES (?)", (name,))
        self.send_json({"ok": True})

    def delete_payment_mode(self, mode):
        mode = parse_qs(f"x={mode}")["x"][0]
        with db() as conn:
            modes = [row["name"] for row in conn.execute("SELECT name FROM payment_modes WHERE name != ? ORDER BY name", (mode,))]
            if not modes:
                raise ValueError("At least one payment mode is required")
            conn.execute("UPDATE patients SET paymentMode = ? WHERE paymentMode = ?", (modes[0], mode))
            conn.execute("DELETE FROM payment_modes WHERE name = ?", (mode,))
        self.send_json({"ok": True})

    def create_user(self):
        data = self.body()
        role = data.get("role")
        if role not in ROLES:
            raise ValueError("Invalid role")
        password = secrets.token_urlsafe(9)
        login_id = data.get("loginId", "").strip() or make_login(data.get("name", "user"))
        with db() as conn:
            conn.execute(
                """
                INSERT INTO users (login_id, name, email, role, password_hash, must_change_password, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (login_id, data.get("name", "").strip(), data.get("email", "").strip(), role, hash_password(password), now()),
            )
        self.send_json({"ok": True, "loginId": login_id, "temporaryPassword": password})

    def update_user(self, user_id):
        data = self.body()
        allowed = {key: data[key] for key in ("name", "email", "role", "active") if key in data}
        if "role" in allowed and allowed["role"] not in ROLES:
            raise ValueError("Invalid role")
        if not allowed:
            raise ValueError("No user fields to update")
        assignments = [f"{key} = ?" for key in allowed]
        values = [bool_int(v) if k == "active" else v for k, v in allowed.items()]
        values.append(user_id)
        with db() as conn:
            conn.execute(f"UPDATE users SET {', '.join(assignments)} WHERE id = ?", values)
        self.send_json({"ok": True})

    def change_password(self):
        data = self.body()
        if len(data.get("newPassword", "")) < 8:
            raise ValueError("New password must be at least 8 characters")
        with db() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (self.user["id"],)).fetchone()
            if not verify_password(data.get("currentPassword", ""), row["password_hash"]):
                raise PermissionError("Current password is incorrect")
            conn.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?", (hash_password(data["newPassword"]), self.user["id"]))
        self.send_json({"ok": True})

    def recover(self):
        email = self.body().get("email", "").strip()
        with db() as conn:
            row = conn.execute("SELECT id, email FROM users WHERE email = ? AND active = 1", (email,)).fetchone()
            if row:
                token = secrets.token_urlsafe(24)
                conn.execute("INSERT INTO recovery_tokens VALUES (?, ?, ?, 0)", (token, row["id"], expires(days=1)))
                send_recovery_email(row["email"], token)
        self.send_json({"ok": True, "message": "If the email exists, a recovery link has been sent."})

    def reset_password(self):
        data = self.body()
        if len(data.get("newPassword", "")) < 8:
            raise ValueError("New password must be at least 8 characters")
        with db() as conn:
            row = conn.execute(
                "SELECT * FROM recovery_tokens WHERE token = ? AND used = 0 AND expires_at > ?",
                (data.get("token", ""), now()),
            ).fetchone()
            if not row:
                raise ValueError("Invalid or expired recovery token")
            conn.execute("UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?", (hash_password(data["newPassword"]), row["user_id"]))
            conn.execute("UPDATE recovery_tokens SET used = 1 WHERE token = ?", (data["token"],))
        self.send_json({"ok": True})


def primary_consultant_id(conn=None, exclude=None):
    owns = conn is not None
    conn = conn or db()
    try:
        row = conn.execute("SELECT id FROM consultants WHERE is_primary = 1 AND id != ? LIMIT 1", (exclude or "",)).fetchone()
        if row:
            return row["id"]
        row = conn.execute("SELECT id FROM consultants WHERE id != ? LIMIT 1", (exclude or "",)).fetchone()
        if not row:
            raise ValueError("No replacement consultant available")
        return row["id"]
    finally:
        if not owns:
            conn.close()


def slug(value):
    base = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return f"{base}-{secrets.token_hex(3)}"


def make_login(name):
    base = "".join(char.lower() for char in name if char.isalnum())[:12] or "user"
    return f"{base}{secrets.randbelow(900) + 100}"


def send_recovery_email(email, token):
    link = f"{os.environ.get('APP_BASE_URL', 'http://localhost:8000')}?reset={token}"
    if not os.environ.get("SMTP_HOST"):
        print(f"Password recovery link for {email}: {link}")
        return
    msg = EmailMessage()
    msg["Subject"] = "RT Patient Flow password recovery"
    msg["From"] = os.environ.get("SMTP_FROM", "noreply@example.com")
    msg["To"] = email
    msg.set_content(f"Use this link to reset your password: {link}")
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        if os.environ.get("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    print(f"RT Patient Flow running at http://127.0.0.1:{port}")
    print("Seed admin login: admin / ChangeMe123!")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
