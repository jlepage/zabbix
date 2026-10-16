#!/bin/bash
# Zabbix external check for Wasabi S3: put / get / delete a small test object.
# Usage: wasabi_check.sh <bucket> <endpoint_host> <aws_profile>
# Output: duration of the full cycle in seconds, or -1 on failure.

BUCKET="$1"
ENDPOINT="https://$2"
PROFILE="$3"

export AWS_SHARED_CREDENTIALS_FILE=/etc/zabbix/wasabi/credentials
export AWS_CONFIG_FILE=/etc/zabbix/wasabi/config

KEY="zabbix-probe/$(hostname -s).txt"
AWS="aws --profile $PROFILE --endpoint-url $ENDPOINT --only-show-errors"

START=$(date +%s%N)
if echo "zabbix probe $(date -u +%FT%TZ)" | $AWS s3 cp - "s3://$BUCKET/$KEY" >/dev/null 2>&1 \
   && $AWS s3 cp "s3://$BUCKET/$KEY" - >/dev/null 2>&1 \
   && $AWS s3 rm "s3://$BUCKET/$KEY" >/dev/null 2>&1; then
  END=$(date +%s%N)
  awk -v d=$((END - START)) 'BEGIN { printf "%.3f\n", d / 1e9 }'
else
  echo -1
fi
