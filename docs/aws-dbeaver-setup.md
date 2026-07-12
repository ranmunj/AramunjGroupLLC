# AWS RDS PostgreSQL + DBeaver Setup

Use this setup when Aramunj Group LLC should store website inquiries in an AWS
PostgreSQL database and let you inspect the same database from DBeaver.

## Current Status

- The Aramunj website already supports PostgreSQL through `DATABASE_URL`.
- AWS CLI is installed on this workstation.
- The provided AWS RDS Proxy ARN is:

```text
arn:aws:rds:us-east-2:574031549478:db-proxy:prx-0ce7c62eb4dd954c1
```

- The current AWS IAM user can authenticate, but it cannot list RDS instances,
  RDS proxies, or RDS proxy endpoints yet.
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

Use one AWS RDS PostgreSQL database for Aramunj inquiries. If you connect
through RDS Proxy, Render and DBeaver need the proxy endpoint hostname, database
name, username, and password.

Important: an RDS Proxy ARN is not a database host. You still need the proxy
endpoint hostname, which usually looks like this:

```text
proxy-name.proxy-xxxxxxxxxxxx.us-east-2.rds.amazonaws.com
```

## Information You Need From AWS

Collect these values from AWS:

```text
RDS or RDS Proxy endpoint: your-endpoint.xxxxxx.us-east-2.rds.amazonaws.com
Port: 5432
Database name: aramunj
Username: aramunj_app
Password: stored securely, never committed
SSL mode: verify-full
SSL root certificate: global-bundle.pem
```

The app connection string format is:

```text
postgresql://USERNAME:PASSWORD@RDS_OR_PROXY_ENDPOINT:5432/DATABASE_NAME?sslmode=verify-full
```

Example placeholder:

```text
postgresql://aramunj_app:CHANGE_ME@proxy-name.proxy-xxxxxxxxxxxx.us-east-2.rds.amazonaws.com:5432/aramunj?sslmode=verify-full
```

## Resolve The RDS Proxy Endpoint

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

Use the returned `Endpoint` value as the hostname in DBeaver and in
`DATABASE_URL`.

## RDS Proxy Network Reality Check

RDS Proxy endpoints are normally private inside an AWS VPC. That means:

- DBeaver on your laptop can connect only if you are on the VPC network path,
  such as VPN, Direct Connect, bastion host, or SSM port forwarding.
- Render usually cannot connect directly to a private RDS Proxy endpoint.
- If the website must stay on Render, the simpler connection is often the public
  RDS database endpoint with a locked-down security group and SSL.
- If you want to use RDS Proxy cleanly, the app should usually run inside AWS,
  for example on App Runner with VPC connector, ECS/Fargate, EC2, Elastic
  Beanstalk, or Lambda in the same VPC.

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
Host: RDS_OR_PROXY_ENDPOINT
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
databases, proxies, proxy endpoints, and network settings, attach a policy with
at least:

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
