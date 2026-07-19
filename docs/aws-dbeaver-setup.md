# AWS RDS PostgreSQL + DBeaver Setup

Use this setup when Aramunj Group LLC should store website inquiries in an AWS
PostgreSQL database and let you inspect the same database from DBeaver.

## Current Status

- The Aramunj website already supports PostgreSQL through `DATABASE_URL`.
- AWS CLI is installed on this workstation.
- The target AWS RDS DB instance for Aramunj inquiries is:

```text
aramunj-postgres
```

- The provided AWS RDS Proxy ARN is:

```text
arn:aws:rds:us-east-2:574031549478:db-proxy:prx-0ce7c62eb4dd954c1
```

- The provided AWS Secrets Manager ARN is:

```text
arn:aws:secretsmanager:us-east-2:574031549478:secret:rds!db-5e19b321-3b66-4c48-8164-a316849b2677-gzHB2S
```

- The `Ranganai` AWS profile can inspect `aramunj-postgres`, the `aramunj` RDS
  Proxy, and the database secret metadata.
- `aramunj-postgres` is publicly accessible and reachable on PostgreSQL port
  `5432` when the client IP/range is allowed by the security group:

```text
PubliclyAccessible: true
Endpoint: aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
```

- The `aramunj` database exists on `aramunj-postgres`.
- The `public.aramunj_leads` table exists and has been verified with an
  app-level test insert.
- The `aramunj` RDS Proxy target for `aramunj-postgres` is available after
  adding the security group self-reference rule on PostgreSQL port `5432`.
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

Use the AWS RDS PostgreSQL instance `aramunj-postgres` for Aramunj inquiries.
Render and DBeaver need the database endpoint hostname, database name, username,
and password.

RDS Proxy is optional. Important: an RDS Proxy ARN is not a database host. If
you connect through the proxy, you still need the proxy endpoint hostname, which
usually looks like this:

```text
proxy-name.proxy-xxxxxxxxxxxx.us-east-2.rds.amazonaws.com
```

## Information You Need From AWS

Collect these values from AWS:

```text
RDS endpoint: aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
RDS Proxy endpoint: aramunj.proxy-c9aewamuqc3f.us-east-2.rds.amazonaws.com
Port: 5432
Database name: aramunj
Username: postgres
Password: stored securely, never committed
SSL mode: verify-full
SSL root certificate: global-bundle.pem
```

The Secrets Manager secret should contain the database username and password.
DBeaver cannot connect with a secret ARN directly; it needs the resolved
username/password and a host endpoint.

The app connection string format is:

```text
postgresql://USERNAME:PASSWORD@RDS_OR_PROXY_ENDPOINT:5432/DATABASE_NAME?sslmode=verify-full
```

Example placeholder:

```text
postgresql://postgres:CHANGE_ME@aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com:5432/aramunj?sslmode=verify-full
```

## Resolve The aramunj-postgres Endpoint

Once the AWS IAM user has read permissions, use:

```powershell
aws rds describe-db-instances `
  --region us-east-2 `
  --db-instance-identifier aramunj-postgres `
  --query "DBInstances[0].{DBInstanceIdentifier:DBInstanceIdentifier,Endpoint:Endpoint.Address,Port:Endpoint.Port,DBName:DBName,Engine:Engine,Status:DBInstanceStatus,PubliclyAccessible:PubliclyAccessible,VpcSecurityGroups:VpcSecurityGroups[*].VpcSecurityGroupId}" `
  --output table
```

The current endpoint is:

```text
aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
```

Use the returned `Endpoint` value as the hostname in Render, DBeaver, and local
development.

## Optional: Resolve The RDS Proxy Endpoint

The proxy ARN you provided is:

```text
arn:aws:rds:us-east-2:574031549478:db-proxy:prx-0ce7c62eb4dd954c1
```

Once the AWS IAM user has read permissions, use:

```powershell
aws rds describe-db-proxies `
  --region us-east-2 `
  --query "DBProxies[?DBProxyArn=='arn:aws:rds:us-east-2:574031549478:db-proxy:prx-0ce7c62eb4dd954c1'].{Name:DBProxyName,Endpoint:Endpoint,Status:Status,RequireTLS:RequireTLS,EngineFamily:EngineFamily}" `
  --output table

aws rds describe-db-proxy-endpoints `
  --region us-east-2 `
  --query "DBProxyEndpoints[].{Name:DBProxyEndpointName,Endpoint:Endpoint,Status:Status,TargetRole:TargetRole,VpcId:VpcId}" `
  --output table
```

Use the returned proxy `Endpoint` value as the hostname only if you intentionally
want Render and DBeaver to connect through RDS Proxy instead of directly to
`aramunj-postgres`.

The current proxy endpoint is:

```text
aramunj.proxy-c9aewamuqc3f.us-east-2.rds.amazonaws.com
```

The proxy target is registered to `aramunj-postgres`. A security group
self-reference rule on PostgreSQL port `5432` is required so the proxy can reach
the database.

## Resolve The Database Secret

The secret ARN you provided is:

```text
arn:aws:secretsmanager:us-east-2:574031549478:secret:rds!db-5e19b321-3b66-4c48-8164-a316849b2677-gzHB2S
```

Once the AWS IAM user has read permission, use this to confirm the secret keys
without printing the password:

```powershell
$secretJson = aws secretsmanager get-secret-value `
  --region us-east-2 `
  --secret-id "arn:aws:secretsmanager:us-east-2:574031549478:secret:rds!db-5e19b321-3b66-4c48-8164-a316849b2677-gzHB2S" `
  --query SecretString `
  --output text

$secret = $secretJson | ConvertFrom-Json
$secret | Select-Object username, engine, host, port, dbname
```

Do not print or commit `$secret.password`.

## RDS Proxy Network Reality Check

RDS Proxy endpoints are normally private inside an AWS VPC. That means:

- DBeaver and Render should connect to the public RDS endpoint
  `aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com` when using the
  current Render-hosted website.
- The RDS Proxy endpoint remains optional and is best used by apps running
  inside the AWS VPC.
- If you want to use RDS Proxy cleanly, the app should usually run inside AWS,
  for example on App Runner with VPC connector, ECS/Fargate, EC2, Elastic
  Beanstalk, or Lambda in the same VPC.
- Render Private Link is also possible on a Pro workspace or higher, but it
  requires an AWS VPC endpoint service/NLB setup and the Render service must be
  in the same region as the private link.

## Connect Render To AWS RDS

In Render, open the `AramunjGroupLLC` web service. The repo includes the public
AWS RDS CA bundle at `global-bundle.pem`, and the app automatically sets
`PGSSLROOTCERT` to that file when it exists.

### Option A: Direct Database URL

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

### Option A2: Separate RDS Variables

Use this option if the database password contains characters like `@`, `#`,
`/`, `?`, `&`, or `=` and you do not want to URL-encode the password.

1. Go to `Environment`.
2. Add:

```text
REQUIRE_POSTGRES=true
RDS_HOST=aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=aramunj
RDS_USERNAME=postgres
RDS_PASSWORD=YOUR_RAW_AWS_DATABASE_PASSWORD
RDS_SSL_MODE=verify-full
```

3. Leave `DATABASE_URL` unset, or keep it only if you know it is correct.
4. Save, rebuild, and deploy.
5. Verify `/api/health` shows:

```json
{
  "postgresConfigured": true,
  "postgresRequired": true,
  "postgresEnvKey": "RDS_ENV"
}
```

### Option B: AWS Secrets Manager

Use this when you do not want to paste the database password into Render.

1. Go to `Environment`.
2. Add:

```text
REQUIRE_POSTGRES=true
AWS_REGION=us-east-2
RDS_SECRET_ARN=arn:aws:secretsmanager:us-east-2:574031549478:secret:rds!db-5e19b321-3b66-4c48-8164-a316849b2677-gzHB2S
RDS_HOST=aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
RDS_DATABASE=aramunj
RDS_SSL_MODE=verify-full
AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_ACCESS_KEY
```

3. Give that AWS key permission to read the secret and describe
   `aramunj-postgres`.
4. Save, rebuild, and deploy.
5. Verify `/api/health` shows:

```json
{
  "postgresConfigured": true,
  "postgresRequired": true,
  "postgresEnvKey": "RDS_SECRET_ARN"
}
```

If you set `DATABASE_URL`, the app uses it first. If `DATABASE_URL` is empty,
the app tries `RDS_SECRET_ARN`.

## Connect Local Development To AWS RDS

From the project folder:

```powershell
$env:REQUIRE_POSTGRES="true"
$env:DATABASE_URL="postgresql://USERNAME:PASSWORD@RDS_OR_PROXY_ENDPOINT:5432/DATABASE_NAME?sslmode=verify-full"
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
Host: aramunj-postgres.c9aewamuqc3f.us-east-2.rds.amazonaws.com
Port: 5432
Database: aramunj
Username: postgres
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
to reach the database. The current security group allows:

```text
24.253.94.200/32
74.220.48.0/24
sg-0e1469b6395ed4033 self-reference on port 5432
```

Before relying on Render in production, compare `74.220.48.0/24` with the
outbound IP ranges shown in your Render service's `Connect` menu. Add any
missing Render outbound ranges and keep `0.0.0.0/0` out of the database security
group.

## AWS IAM Permissions Needed For Automation

The current AWS CLI user cannot inspect `aramunj-postgres`. To let Codex
discover the Aramunj RDS endpoint, secret, and network settings, attach a policy
with at least:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBClusters",
        "rds:DescribeDBProxies",
        "rds:DescribeDBProxyEndpoints",
        "rds:DescribeDBProxyTargets",
        "secretsmanager:DescribeSecret",
        "secretsmanager:GetSecretValue",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets"
      ],
      "Resource": "*"
    }
  ]
}
```

The repo includes the ready-to-attach policy template:

```text
docs/aws-iam-rds-secret-read-policy.json
```

If the secret uses a customer-managed KMS key, the IAM user may also need
`kms:Decrypt` for that key.

If you want Codex to create or modify AWS resources, approve that separately
because RDS can create monthly AWS costs.

## Do Not Commit Secrets

Never commit real database passwords, AWS keys, or Render secrets. Keep real
values in Render environment variables, AWS Secrets Manager, DBeaver's encrypted
local profile, or a local `.env` file that stays ignored by Git.
