from __future__ import annotations

import json
import os
import pathlib
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOCAL_JSONL = DATA_DIR / "leads.jsonl"
DATABASE_ENV_KEYS = (
    "DATABASE_URL",
    "RENDER_DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRESQL_URL",
    "POSTGRESQL",
    "postgresql",
)


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def validate_lead(payload: dict) -> dict:
    required = ("name", "email", "message")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    project_type = str(payload.get("project_type") or payload.get("interest") or "").strip()
    if not project_type:
        missing.append("project_type")
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if "@" not in payload["email"]:
        raise ValueError("Please provide a valid email address.")
    return {
        "name": payload["name"].strip(),
        "company": str(payload.get("company", "")).strip(),
        "email": payload["email"].strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "organization": str(payload.get("organization", "")).strip(),
        "country": str(payload.get("country", "")).strip(),
        "project_type": project_type,
        "interest": project_type,
        "budget": str(payload.get("budget", "")).strip(),
        "message": payload["message"].strip(),
        "source": "website",
        "submitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ip_address": "",
    }


def get_database_config() -> tuple[str, str]:
    for key in DATABASE_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value, key
    return "", ""


def get_database_url() -> str:
    return get_database_config()[0]


def get_database_env_key() -> str:
    return get_database_config()[1]


def postgres_required() -> bool:
    return truthy(os.environ.get("REQUIRE_POSTGRES")) or truthy(os.environ.get("RENDER"))


def postgres_configured() -> bool:
    database_url = get_database_url()
    if not database_url:
        return False
    placeholder_parts = ("user:password@host", "your_render_postgres_url", "postgresql://...")
    return not any(part in database_url for part in placeholder_parts)


def save_to_postgres(lead: dict) -> bool:
    database_url = get_database_url()
    if not postgres_configured():
        return False

    try:
        import psycopg
    except ImportError:
        return False

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / "schema.sql").read_text(encoding="utf-8"))
            cur.execute(
                """
                INSERT INTO aramunj_leads
                  (
                    name, company, email, phone, organization, country,
                    project_type, budget, interest, message, source, ip_address
                  )
                VALUES
                  (
                    %(name)s, %(company)s, %(email)s, %(phone)s, %(organization)s, %(country)s,
                    %(project_type)s, %(budget)s, %(interest)s, %(message)s, %(source)s,
                    %(ip_address)s
                  )
                """,
                lead,
            )
        conn.commit()
    return True


def save_locally(lead: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with LOCAL_JSONL.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(lead) + "\n")


def smtp_configured() -> bool:
    return all(
        os.environ.get(name)
        for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM")
    )


def deliver_email(
    message: EmailMessage,
    host: str,
    port: int,
    username: str,
    password: str,
    use_ssl: bool,
    timeout: int,
) -> None:
    if use_ssl:
        with smtplib.SMTP_SSL(
            host, port, context=ssl.create_default_context(), timeout=timeout
        ) as server:
            server.login(username, password)
            server.send_message(message)
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)


def send_inquiry_email(lead: dict) -> str:
    if not smtp_configured():
        return "not_configured"

    recipient = os.environ.get("INQUIRY_RECIPIENT", "ranga@aramunj.com, info@aramunj.com")
    subject = f"New Aramunj inquiry: {lead['interest']}"
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = recipient
    message["Reply-To"] = lead["email"]
    message.set_content(
        "\n".join(
            [
                "A new inquiry was submitted through aramunj.com.",
                "",
                f"Name: {lead['name']}",
                f"Company: {lead['company'] or 'Not provided'}",
                f"Email: {lead['email']}",
                f"Phone: {lead['phone'] or 'Not provided'}",
                f"Organization: {lead['organization'] or 'Not provided'}",
                f"Country: {lead['country'] or 'Not provided'}",
                f"Project Type: {lead['project_type']}",
                f"Budget: {lead['budget'] or 'Not provided'}",
                f"Date Submitted: {lead['submitted_at']}",
                f"IP Address: {lead['ip_address'] or 'Not available'}",
                "",
                "Message:",
                lead["message"],
            ]
        )
    )

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    timeout = int(os.environ.get("SMTP_TIMEOUT", "10"))
    requested_ssl = os.environ.get("SMTP_SSL", "").lower() in ("1", "true", "yes")
    use_ssl = requested_ssl and port == 465

    try:
        deliver_email(message, host, port, username, password, use_ssl, timeout)
    except ssl.SSLError:
        if not use_ssl:
            raise
        deliver_email(message, host, port, username, password, False, timeout)

    return "sent"


class AramunjHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        request_path = urlsplit(self.path).path
        if request_path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        elif request_path in ("/", "/index.html") or request_path.endswith(".html"):
            self.send_header("Cache-Control", "no-cache, max-age=0, must-revalidate")
        elif request_path.endswith((".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".webp")):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path == "/api/health":
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "ok": True,
                    "postgresConfigured": postgres_configured(),
                    "postgresRequired": postgres_required(),
                    "postgresEnvKey": get_database_env_key() or None,
                    "emailConfigured": smtp_configured(),
                    "service": "aramunj-group-llc",
                },
            )
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/leads":
            json_response(self, HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            lead = validate_lead(payload)
            lead["ip_address"] = self.get_client_ip()
            stored_in_postgres = save_to_postgres(lead)
            if not stored_in_postgres:
                if postgres_required():
                    json_response(
                        self,
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        {
                            "error": "Postgres is required but no valid Postgres connection URL is configured.",
                            "storage": "none",
                        },
                    )
                    return
                save_locally(lead)
            try:
                email_status = send_inquiry_email(lead)
            except Exception as error:
                email_status = f"failed: {error}"
            json_response(
                self,
                HTTPStatus.CREATED,
                {
                    "ok": True,
                    "storage": "postgres" if stored_in_postgres else "local",
                    "email": email_status,
                },
            )
        except ValueError as error:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})

    def get_client_ip(self) -> str:
        forwarded_for = self.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return self.client_address[0] if self.client_address else ""


def main() -> None:
    port = int(os.environ.get("PORT", "5179"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), AramunjHandler)
    print(f"Aramunj Group LLC site running at http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
