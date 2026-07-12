# Aramunj Group LLC Website

A polished consultancy website for Aramunj Group LLC with a Postgres-ready lead capture API.

## Run Locally

```powershell
python server.py
```

Open `http://127.0.0.1:5179`.

## Postgres Setup

Set `DATABASE_URL` before starting the server. The API creates the `aramunj_leads` table from `schema.sql` and stores contact form submissions in Postgres.

```powershell
$env:DATABASE_URL="postgresql://user:password@host:5432/database?sslmode=verify-full"
python server.py
```

When `DATABASE_URL` or `psycopg` is not available, submissions are stored in `data/leads.jsonl` so inquiries are not lost during local development.

To force local development to use Postgres instead of the local JSONL fallback:

```powershell
$env:REQUIRE_POSTGRES="true"
$env:DATABASE_URL="postgresql://user:password@host:5432/database?sslmode=verify-full"
python server.py
```

## Render Deployment

Use these settings when creating the Render web service:

```text
Root Directory: leave blank
Build Command: pip install -r requirements.txt
Start Command: python server.py
Branch: AramunjgroupLLc
```

Add the Render Postgres connection string as an environment variable:

```text
DATABASE_URL=postgresql://...?sslmode=verify-full
REQUIRE_POSTGRES=true
```

Use the real Postgres URL, not placeholder text. For AWS RDS PostgreSQL, the
repo includes `global-bundle.pem` and the app automatically uses it as the RDS
root certificate.

To route contact inquiries to email while still saving them to Postgres, add SMTP
settings in Render:

```text
INQUIRY_RECIPIENT=ranga@aramunj.com, info@aramunj.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=no-reply@aramunj.com
```

Use `SMTP_SSL=true` only if your provider requires SSL on port `465`.

## AWS RDS + DBeaver

For AWS PostgreSQL and DBeaver setup, use:

```text
docs/aws-dbeaver-setup.md
```

The same `DATABASE_URL` format works for Render, local development, AWS RDS, and
DBeaver. Keep real passwords out of Git; `.env` is ignored.
