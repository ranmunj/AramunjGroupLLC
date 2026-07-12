# AWS RDS PostgreSQL + DBeaver Setup

Use this setup when Aramunj Group LLC should store website inquiries in an AWS
PostgreSQL database and let you inspect the same database from DBeaver.

## Current Status

- The Aramunj website already supports PostgreSQL through `DATABASE_URL`.
- AWS CLI is installed on this workstation and is configured for `us-west-2`.
- The current AWS IAM user can authenticate, but it cannot list RDS instances yet.
- DBeaver is not available on the command-line PATH, so open it from the Windows
  Start menu if it is already installed.

## Recommended Architecture

```text
aramunj.com / Render web service
        |
        | DATABASE_URL
        v
AWS RDS PostgreSQL database
        ^
        |
DBeaver desktop connection
```

Use one AWS RDS PostgreSQL database for Aramunj inquiries. Render and DBeaver
should connect to the same endpoint, database name, username, and password.

## Information You Need From AWS

Collect these values from the AWS RDS database page:

```text
RDS endpoint: your-db-name.xxxxxx.us-west-2.rds.amazonaws.com
Port: 5432
Database name: aramunj
Username: aramunj_app
Password: stored securely, never committed
SSL mode: verify-full
SSL root certificate: global-bundle.pem
```

The app connection string format is:

```text
postgresql://USERNAME:PASSWORD@RDS_ENDPOINT:5432/DATABASE_NAME?sslmode=verify-full
```

Example placeholder:

```text
postgresql://aramunj_app:CHANGE_ME@aramunj-db.xxxxxx.us-west-2.rds.amazonaws.com:5432/aramunj?sslmode=verify-full
```

## Connect Render To AWS RDS

In Render, open the `AramunjGroupLLC` web service. The repo includes the public
AWS RDS CA bundle at `global-bundle.pem`, and the app automatically sets
`PGSSLROOTCERT` to that file when it exists.

1. Go to `Environment`.
2. Set `DATABASE_URL` to the AWS RDS PostgreSQL connection string.
3. Set `REQUIRE_POSTGRES=true`.
4. Save, rebuild, and deploy.
5. Verify:

```powershell
(Invoke-WebRequest -UseBasicParsing https://aramunj.com/api/health).Content
```

Expected:

```json
{
  "postgresConfigured": true,
  "postgresRequired": true,
  "postgresEnvKey": "DATABASE_URL"
}
```

## Connect Local Development To AWS RDS

From the project folder:

```powershell
$env:REQUIRE_POSTGRES="true"
$env:DATABASE_URL="postgresql://USERNAME:PASSWORD@RDS_ENDPOINT:5432/DATABASE_NAME?sslmode=verify-full"
python server.py
```

Then open:

```text
http://127.0.0.1:5179/api/health
```

## Connect DBeaver

In DBeaver:

1. New Database Connection.
2. Choose `PostgreSQL`.
3. Enter:

```text
Host: RDS_ENDPOINT
Port: 5432
Database: DATABASE_NAME
Username: USERNAME
Password: PASSWORD
```

4. Open the `SSL` tab.
5. Set SSL mode to `verify-full`.
6. Set Root Certificate / CA Certificate to this file:

```text
C:\Users\ranmu\Documents\Codex\2026-06-28\i-need-a-website-desigened-for\work\AramunjGroupLLC\global-bundle.pem
```

If DBeaver asks for separate client certificate or private key files, leave
those blank. RDS only needs the CA/root certificate for server verification.
7. Click `Test Connection`.
8. Save.

Useful DBeaver SQL checks:

```sql
SELECT now();

SELECT *
FROM aramunj_leads
ORDER BY created_at DESC
LIMIT 25;
```

## AWS Security Group

For DBeaver to connect from your laptop, the RDS security group needs inbound
PostgreSQL access:

```text
Type: PostgreSQL
Port: 5432
Source: your public IP address /32
```

For Render to connect, the RDS database must also allow Render outbound traffic
to reach the database. The simplest approach is a publicly accessible RDS
instance with a strong password, SSL required, and very limited security group
sources. A more locked-down production setup uses a private network/VPN or a
controlled bastion/SSM tunnel.

## AWS IAM Permissions Needed For Automation

The current AWS CLI user cannot inspect RDS. To let Codex discover existing RDS
databases and help finish the setup automatically, attach a policy with at least:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusters",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets"
      ],
      "Resource": "*"
    }
  ]
}
```

If you want Codex to create or modify AWS resources, approve that separately
because RDS can create monthly AWS costs.

## Do Not Commit Secrets

Never commit real database passwords, AWS keys, or Render secrets. Keep real
values in Render environment variables, AWS Secrets Manager, DBeaver's encrypted
local profile, or a local `.env` file that stays ignored by Git.
