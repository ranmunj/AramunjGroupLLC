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
$env:DATABASE_URL="postgresql://user:password@host:5432/database"
python server.py
```

When `DATABASE_URL` or `psycopg` is not available, submissions are stored in `data/leads.jsonl` so inquiries are not lost during local development.

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
DATABASE_URL=postgresql://...
```
