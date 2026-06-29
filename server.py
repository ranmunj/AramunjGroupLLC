from __future__ import annotations

import json
import os
import pathlib
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOCAL_JSONL = DATA_DIR / "leads.jsonl"


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def validate_lead(payload: dict) -> dict:
    required = ("name", "email", "interest", "message")
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if "@" not in payload["email"]:
        raise ValueError("Please provide a valid email address.")
    return {
        "name": payload["name"].strip(),
        "email": payload["email"].strip(),
        "organization": str(payload.get("organization", "")).strip(),
        "interest": payload["interest"].strip(),
        "message": payload["message"].strip(),
        "source": "website",
    }


def save_to_postgres(lead: dict) -> bool:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
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
                  (name, email, organization, interest, message, source)
                VALUES
                  (%(name)s, %(email)s, %(organization)s, %(interest)s, %(message)s, %(source)s)
                """,
                lead,
            )
        conn.commit()
    return True


def save_locally(lead: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with LOCAL_JSONL.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(lead) + "\n")


class AramunjHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            json_response(
                self,
                HTTPStatus.OK,
                {
                    "ok": True,
                    "postgresConfigured": bool(os.environ.get("DATABASE_URL")),
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
            stored_in_postgres = save_to_postgres(lead)
            if not stored_in_postgres:
                save_locally(lead)
            json_response(
                self,
                HTTPStatus.CREATED,
                {"ok": True, "storage": "postgres" if stored_in_postgres else "local"},
            )
        except ValueError as error:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(error)})
        except Exception as error:
            json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(error)})


def main() -> None:
    port = int(os.environ.get("PORT", "5179"))
    host = os.environ.get("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), AramunjHandler)
    print(f"Aramunj Group LLC site running at http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
