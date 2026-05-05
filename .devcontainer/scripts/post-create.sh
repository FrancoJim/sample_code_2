#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Python dependencies"
pip install --quiet --no-cache-dir -r /workspace/requirements.txt

echo "==> Configuring AWS CLI for LocalStack"
# Write a named profile so both 'aws' CLI and boto3 (via AWS_ENDPOINT_URL)
# work out of the box against LocalStack without real credentials.
mkdir -p /root/.aws

cat > /root/.aws/config <<'CONFIG'
[default]
region = us-east-1
output = json

[profile localstack]
region = us-east-1
output = json
endpoint_url = http://localstack:4566
CONFIG

cat > /root/.aws/credentials <<'CREDS'
[default]
aws_access_key_id = test
aws_secret_access_key = test

[localstack]
aws_access_key_id = test
aws_secret_access_key = test
CREDS

echo "==> Waiting for LocalStack S3 to be ready"
for i in $(seq 1 20); do
    if curl -sf http://localstack:4566/_localstack/health | grep -q '"s3"'; then
        echo "    LocalStack S3 ready."
        break
    fi
    echo "    Attempt ${i}/20 — waiting..."
    sleep 3
done

echo "==> Creating default local S3 bucket"
aws --endpoint-url http://localstack:4566 s3 mb s3://sample-sized-bucket-local --region us-east-1 2>/dev/null || true

echo ""
echo "==> Dev environment ready."
echo "    LocalStack S3 : http://localstack:4566  (forwarded → http://localhost:4566 on host)"
echo "    List buckets  : aws --endpoint-url http://localstack:4566 s3 ls"
echo "    Run pipeline  : python -m sample_2.main --bucket sample-sized-bucket-local --dataset gdp"
echo ""
