from __future__ import annotations

import base64
import hmac
import json
import os
import pathlib
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen
from urllib.parse import parse_qs, quote, unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOCAL_JSONL = DATA_DIR / "leads.jsonl"
RDS_CA_BUNDLE = ROOT / "global-bundle.pem"
ARAMUNJ_RDS_HOST = "aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com"
ARAMUNJ_RDS_DATABASE = "aramunj"
DATABASE_ENV_KEYS = (
    "DATABASE_URL",
    "RENDER_DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRESQL_URL",
    "POSTGRESQL",
    "postgresql",
)
SECRET_DATABASE_URL_CACHE: str | None = None
SECRET_DATABASE_ERROR: str | None = None


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


def get_admin_token() -> str:
    return (
        os.environ.get("ADMIN_TOKEN", "").strip()
        or os.environ.get("INQUIRY_ADMIN_TOKEN", "").strip()
    )


def admin_authorized(handler: SimpleHTTPRequestHandler) -> bool:
    expected = get_admin_token()
    if not expected:
        return False

    supplied = ""
    authorization = handler.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not supplied:
        query = parse_qs(urlsplit(handler.path).query)
        supplied = str(query.get("token", [""])[0]).strip()
    return hmac.compare_digest(supplied, expected)


def parse_limit(handler: SimpleHTTPRequestHandler) -> int:
    query = parse_qs(urlsplit(handler.path).query)
    try:
        limit = int(str(query.get("limit", ["100"])[0]))
    except ValueError:
        limit = 100
    return max(1, min(limit, 500))


def get_database_config() -> tuple[str, str]:
    structured_url = get_structured_database_url()
    if structured_url:
        return structured_url, "RDS_ENV"

    for key in DATABASE_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return normalize_database_url(value), key

    secret_url = get_secret_database_url()
    if secret_url:
        return secret_url, "RDS_SECRET_ARN"
    return "", ""


def get_database_url() -> str:
    return get_database_config()[0]


def get_database_env_key() -> str:
    return get_database_config()[1]


def get_aws_region() -> str:
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-2"
    )


def first_value(source: dict, *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def normalize_database_url(database_url: str) -> str:
    if ARAMUNJ_RDS_HOST not in database_url:
        return database_url

    scheme = ""
    for candidate in ("postgresql://", "postgres://"):
        if database_url.startswith(candidate):
            scheme = candidate
            break
    if not scheme:
        return database_url

    delimiter = f"@{ARAMUNJ_RDS_HOST}"
    delimiter_index = database_url.rfind(delimiter)
    credentials = database_url[len(scheme) : delimiter_index]
    if delimiter_index <= len(scheme) or ":" not in credentials:
        return database_url

    username, password = credentials.split(":", 1)
    username = unquote(username)
    password = unquote(password)
    remainder = database_url[delimiter_index + 1 :]
    host_and_path = remainder
    query = ""
    if "?" in host_and_path:
        host_and_path, query = host_and_path.split("?", 1)

    host_port, _, path = host_and_path.partition("/")
    if ":" not in host_port:
        host_port = f"{ARAMUNJ_RDS_HOST}:5432"
    database = unquote(path.strip("/")) or ARAMUNJ_RDS_DATABASE
    query = query or "sslmode=verify-full"

    return (
        "postgresql://"
        f"{quote(username, safe='')}:{quote(password, safe='')}"
        f"@{host_port}/{quote(database, safe='')}"
        f"?{query}"
    )


def build_postgres_url_from_secret(secret: dict) -> str:
    username = (
        os.environ.get("RDS_USERNAME")
        or os.environ.get("RDS_USER")
        or first_value(secret, "username", "user")
        or "postgres"
    )
    password = os.environ.get("RDS_PASSWORD") or first_value(secret, "password")
    host = (
        os.environ.get("RDS_HOST")
        or os.environ.get("RDS_PROXY_ENDPOINT")
        or first_value(secret, "host", "hostname")
        or ARAMUNJ_RDS_HOST
    )
    port = os.environ.get("RDS_PORT") or first_value(secret, "port") or "5432"
    database = (
        os.environ.get("RDS_DATABASE")
        or os.environ.get("RDS_DB_NAME")
        or first_value(secret, "dbname", "database", "dbName")
        or ARAMUNJ_RDS_DATABASE
    )
    ssl_mode = os.environ.get("RDS_SSL_MODE") or "verify-full"

    missing = [
        name
        for name, value in (
            ("username", username),
            ("password", password),
            ("host", host),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"RDS secret is missing required fields: {', '.join(missing)}")

    return (
        "postgresql://"
        f"{quote(str(username), safe='')}:{quote(str(password), safe='')}"
        f"@{host}:{port}/{quote(str(database), safe='')}"
        f"?sslmode={quote(str(ssl_mode), safe='')}"
    )


def get_structured_database_url() -> str:
    if not os.environ.get("RDS_PASSWORD"):
        return ""
    return build_postgres_url_from_secret({})


def get_secret_database_url() -> str:
    global SECRET_DATABASE_URL_CACHE, SECRET_DATABASE_ERROR

    if SECRET_DATABASE_URL_CACHE is not None:
        return SECRET_DATABASE_URL_CACHE

    secret_arn = os.environ.get("RDS_SECRET_ARN", "").strip()
    if not secret_arn:
        return ""

    try:
        import boto3

        client = boto3.client("secretsmanager", region_name=get_aws_region())
        response = client.get_secret_value(SecretId=secret_arn)
        secret_payload = response.get("SecretString")
        if not secret_payload and response.get("SecretBinary"):
            secret_payload = base64.b64decode(response["SecretBinary"]).decode("utf-8")
        if not secret_payload:
            raise ValueError("RDS secret did not include SecretString or SecretBinary.")
        SECRET_DATABASE_URL_CACHE = build_postgres_url_from_secret(json.loads(secret_payload))
        SECRET_DATABASE_ERROR = None
        return SECRET_DATABASE_URL_CACHE
    except Exception as error:
        SECRET_DATABASE_URL_CACHE = ""
        SECRET_DATABASE_ERROR = error.__class__.__name__
        print(f"Unable to load RDS secret from AWS Secrets Manager: {error}", flush=True)
        return ""


def postgres_required() -> bool:
    return truthy(os.environ.get("REQUIRE_POSTGRES")) or truthy(os.environ.get("RENDER"))


def postgres_configured() -> bool:
    database_url = get_database_url()
    if not database_url:
        return False
    placeholder_parts = ("user:password@host", "your_render_postgres_url", "postgresql://...")
    return not any(part in database_url for part in placeholder_parts)


def get_database_target() -> dict:
    database_url = get_database_url()
    if not database_url:
        return {"host": None, "database": None}

    parsed = urlsplit(database_url)
    return {
        "host": parsed.hostname,
        "database": parsed.path.strip("/") or None,
    }


def sanitize_error(error: Exception) -> str:
    message = str(error)
    database_url = get_database_url()
    if database_url:
        message = message.replace(database_url, "[redacted-database-url]")
    return message[:260]


def get_outbound_ip() -> str | None:
    try:
        with urlopen("https://api.ipify.org", timeout=5) as response:
            return response.read().decode("utf-8").strip()
    except Exception as error:
        print(f"Unable to resolve outbound IP: {error}", flush=True)
        return None


def check_postgres_connection() -> dict:
    if not postgres_configured():
        return {"ok": False, "errorType": "NotConfigured"}

    configure_postgres_ssl()

    try:
        import psycopg

        with psycopg.connect(get_database_url(), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user")
                database, user = cur.fetchone()
        return {"ok": True, "database": database, "user": user}
    except Exception as error:
        return {
            "ok": False,
            "errorType": error.__class__.__name__,
            "error": sanitize_error(error),
        }


def configure_postgres_ssl() -> None:
    if RDS_CA_BUNDLE.exists() and not os.environ.get("PGSSLROOTCERT"):
        os.environ["PGSSLROOTCERT"] = str(RDS_CA_BUNDLE)


def save_to_postgres(lead: dict) -> bool:
    database_url = get_database_url()
    if not postgres_configured():
        return False

    configure_postgres_ssl()

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


def list_leads_from_postgres(limit: int) -> list[dict]:
    database_url = get_database_url()
    if not postgres_configured():
        return []

    configure_postgres_ssl()

    try:
        import psycopg
    except ImportError:
        return []

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / "schema.sql").read_text(encoding="utf-8"))
            cur.execute(
                """
                SELECT
                  id, name, company, email, phone, organization, country,
                  project_type, budget, interest, message, source, ip_address, created_at
                FROM aramunj_leads
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
        conn.commit()

    leads = []
    for row in rows:
        created_at = row[13].isoformat() if hasattr(row[13], "isoformat") else str(row[13])
        leads.append(
            {
                "id": row[0],
                "name": row[1] or "",
                "company": row[2] or "",
                "email": row[3] or "",
                "phone": row[4] or "",
                "organization": row[5] or "",
                "country": row[6] or "",
                "project_type": row[7] or row[9] or "",
                "budget": row[8] or "",
                "interest": row[9] or "",
                "message": row[10] or "",
                "source": row[11] or "",
                "ip_address": row[12] or "",
                "created_at": created_at,
            }
        )
    return leads


def list_leads_locally(limit: int) -> list[dict]:
    if not LOCAL_JSONL.exists():
        return []

    leads = []
    lines = LOCAL_JSONL.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(reversed(lines[-limit:]), start=1):
        try:
            lead = json.loads(line)
        except json.JSONDecodeError:
            continue
        lead.setdefault("id", f"local-{index}")
        lead.setdefault("created_at", lead.get("submitted_at", ""))
        leads.append(lead)
    return leads


def list_leads(limit: int) -> tuple[list[dict], str]:
    if postgres_configured():
        return list_leads_from_postgres(limit), "postgres"
    if postgres_required():
        raise RuntimeError("Postgres is required but no valid Postgres connection URL is configured.")
    return list_leads_locally(limit), "local"


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
        request_path = urlsplit(self.path).path
        if request_path == "/api/health":
            query = parse_qs(urlsplit(self.path).query)
            include_db_check = str(query.get("check", [""])[0]).lower() == "db"
            payload = {
                "ok": True,
                "postgresConfigured": postgres_configured(),
                "postgresRequired": postgres_required(),
                "postgresEnvKey": get_database_env_key() or None,
                "postgresTarget": get_database_target(),
                "emailConfigured": smtp_configured(),
                "service": "aramunj-group-llc",
            }
            if include_db_check:
                payload["outboundIp"] = get_outbound_ip()
                payload["postgresCheck"] = check_postgres_connection()
            json_response(
                self,
                HTTPStatus.OK,
                payload,
            )
            return
        if request_path == "/api/leads":
            if not get_admin_token():
                json_response(
                    self,
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "Inquiry dashboard is not configured."},
                )
                return
            if not admin_authorized(self):
                json_response(self, HTTPStatus.UNAUTHORIZED, {"error": "Unauthorized"})
                return
            try:
                leads, storage = list_leads(parse_limit(self))
                json_response(
                    self,
                    HTTPStatus.OK,
                    {"ok": True, "storage": storage, "count": len(leads), "leads": leads},
                )
            except Exception as error:
                json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})
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
                print(f"Inquiry email delivery failed: {error}", flush=True)
                email_status = "failed"
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
            print(f"Inquiry submission failed: {error}", flush=True)
            json_response(
                self,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "We could not submit your inquiry. Please try again shortly."},
            )

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
