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

For AWS RDS, you can avoid URL-encoding password characters by using separate
environment variables instead of `DATABASE_URL`:

```text
REQUIRE_POSTGRES=true
RDS_HOST=aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=aramunj
RDS_USERNAME=postgres
RDS_PASSWORD=your_raw_aws_database_password
RDS_SSL_MODE=verify-full
```

When `RDS_HOST`, `RDS_DATABASE`, and `RDS_PASSWORD` are set, the app uses those
values before `DATABASE_URL`.

## Inquiry Dashboard

The private inquiry dashboard is available at:

```text
https://aramunj.com/inquiries.html
```

Add an admin token in Render:

```text
ADMIN_TOKEN=generate_a_long_random_value
```

The dashboard reads from the same `aramunj_leads` Postgres table used by the
contact form. Keep `ADMIN_TOKEN` private and do not commit it.

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

For Google Workspace / Gmail, use an app password instead of your normal Gmail
password:

```text
INQUIRY_RECIPIENT=ranga@aramunj.com, info@aramunj.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=info@aramunj.com
SMTP_PASSWORD=your_16_character_google_app_password
SMTP_FROM=info@aramunj.com
SMTP_SSL=false
```

The Gmail account must have 2-Step Verification enabled before Google lets you
create an app password. If Gmail returns `535 BadCredentials`, replace
`SMTP_PASSWORD` in Render with a fresh app password, then choose
`Save, rebuild, and deploy`.

## AWS RDS + DBeaver

For AWS PostgreSQL and DBeaver setup, use:

```text
docs/aws-dbeaver-setup.md
```

The same `DATABASE_URL` format works for Render, local development, AWS RDS, and
DBeaver. Keep real passwords out of Git; `.env` is ignored.
