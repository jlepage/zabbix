# Wasabi S3

A Zabbix 7.4 template to monitor a Wasabi S3 service: availability, functional test, per-bucket storage, traffic and requests, and account-level totals to check the invoice.

## Who runs the checks?

The **Zabbix server or proxy** that monitors the host runs every check, not the host itself.

The host you link the template to is only a container for the items and triggers. No agent is involved:

```
Zabbix server / proxy  --HTTPS->  Wasabi (S3 endpoint + Stats API)
```

If the host is monitored by a proxy, the script, the AWS CLI and the credentials must be installed on **that proxy**.

## What it monitors

| Level | What | How | Credentials |
|---|---|---|---|
| 1 | Endpoint availability and response time | Simple checks (`net.tcp.service`) | None |
| 2 | Real write / read / delete on a bucket | External script `wasabi_check.sh` | S3 access key |
| 3 | Per-bucket storage, upload / download, requests, account totals | Wasabi Stats API (auto-discovery + calculated items) | Stats API key |

Each level works on its own. Leave the related macros empty to skip a level.

## Wasabi users and permissions

Create **two dedicated sub-users**, one per use, with programmatic (API) access only. Never use root keys.

| User | Used by | Permissions |
|---|---|---|
| `zabbix-stats` | Level 3 (Stats API) | Built-in policy `WasabiBucketStatsAccess` |
| `zabbix-probe` | Level 2 (write/read test) | Custom policy limited to the `zabbix-probe/` prefix |

Two users keep the impact of a leaked key limited to one use, and let you rotate or revoke each key independently.

### `zabbix-stats`

1. In the Wasabi console, go to **Users** and create `zabbix-stats` with programmatic access only.
2. Attach the policy **`WasabiBucketStatsAccess`**. It gives access to the bucket utilization endpoints only, which is all the template needs. Don't use `WasabiAccountStatsAccess`: it gives full access to account and bucket stats.
3. In **Access Keys**, generate a key for this sub-user. Copy the secret right away, it is shown only once.

### `zabbix-probe`

1. In **Policies**, create `zabbix-probe-policy` (replace `MY-BUCKET`):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
         "Resource": "arn:aws:s3:::MY-BUCKET/zabbix-probe/*"
       }
     ]
   }
   ```
   This user cannot list the bucket or touch anything outside `zabbix-probe/`. Even if the key leaks, your data stays out of reach.
2. Create `zabbix-probe` with programmatic access only, attach the policy, and generate a key.

Testing your production bucket is the most representative check, and the prefix restriction keeps it safe. Use a small dedicated bucket if you prefer full isolation.

### Key management

- **Rotation**: Wasabi allows two keys per user. Create the new key, update Zabbix, check, then delete the old one. No monitoring gap.
- **Storage**: keep the Stats API key in a *Secret text* macro, or better, a *Vault secret* macro if you use HashiCorp Vault or CyberArk.

## Setup

### Level 1: endpoint

1. Import `wasabi_s3_template.yaml` and link the template to a host.
2. Set `{$WASABI.ENDPOINT}` to your region's endpoint (e.g. `s3.eu-central-1.wasabisys.com`).

### Level 2: write/read test

On the server or proxy:

1. Install the AWS CLI.
2. Copy `wasabi_check.sh` to the `ExternalScripts` directory (usually `/usr/lib/zabbix/externalscripts/`) and make it executable.
3. Create the credentials files with the `zabbix-probe` key, readable only by the `zabbix` user:
   ```ini
   # /etc/zabbix/wasabi/credentials
   [wasabi-probe]
   aws_access_key_id = XXXX
   aws_secret_access_key = XXXX

   # /etc/zabbix/wasabi/config
   [profile wasabi-probe]
   region = eu-central-1
   ```
   ```bash
   chown -R zabbix: /etc/zabbix/wasabi && chmod 600 /etc/zabbix/wasabi/*
   ```
4. Test it as the `zabbix` user. It should print a duration, not `-1`:
   ```bash
   sudo -u zabbix /usr/lib/zabbix/externalscripts/wasabi_check.sh my-bucket s3.eu-central-1.wasabisys.com wasabi-probe
   ```
5. Check that the key is properly restricted. Listing the bucket must fail with `AccessDenied`:
   ```bash
   sudo -u zabbix env AWS_SHARED_CREDENTIALS_FILE=/etc/zabbix/wasabi/credentials AWS_CONFIG_FILE=/etc/zabbix/wasabi/config \
     aws --profile wasabi-probe --endpoint-url https://s3.eu-central-1.wasabisys.com s3 ls s3://my-bucket/
   ```
6. On the host, set `{$WASABI.PROBE.BUCKET}`.

If the script prints `-1`, run the `aws` commands from the script by hand, without `>/dev/null`, to see the exact error.

The script stores and deletes one tiny object at each run. Wasabi bills deleted objects for a minimum storage duration, so keep the interval reasonable (default 10m).

### Level 3: Stats API

1. Use the `zabbix-stats` key (see [Wasabi users and permissions](#wasabi-users-and-permissions)).
2. Check that both endpoints used by the template answer with HTTP 200:
   ```bash
   # Bucket list (used by the discovery)
   curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: ACCESS:SECRET" \
     "https://stats.wasabisys.com/v1/standalone/utilizations/bucket?pageSize=1"

   # Per-bucket record (used by the items): traffic fields must be filled
   curl -s -H "Authorization: ACCESS:SECRET" \
     "https://stats.wasabisys.com/v1/standalone/utilizations/bucket/<bucket>?latest=true&pageSize=1" \
     | jq '.Records[0] | {RawStorageSizeBytes, UploadBytes, DownloadBytes, NumGETCalls, NumPUTCalls}'
   ```
   If the bucket list returns 403 while the per-bucket call works, `WasabiBucketStatsAccess` does not cover the discovery endpoint: the discovery won't work with this policy.
3. On the host, set `{$WASABI.STATS.AUTH}` to `ACCESS_KEY:SECRET_KEY` (secret macro).
4. Optionally, restrict the discovered buckets with `{$WASABI.STATS.BUCKET.MATCHES}` / `{$WASABI.STATS.BUCKET.NOT_MATCHES}` (e.g. `^test-`).

Buckets are discovered every 6 hours.

### Deleted buckets

Wasabi can keep publishing daily records for a deleted bucket, with no data left in it. To avoid monitoring these buckets:

- the discovery reads the **latest record** of each bucket and **skips buckets with no data left** (0 bytes and 0 objects);
- a bucket that is no longer discovered has its items **disabled immediately**, so it no longer counts in the totals and raises no alert. Its items are deleted after 7 days.

The Stats API cannot tell a deleted bucket from an existing but empty one: both are skipped. Set `{$WASABI.STATS.SKIP_EMPTY}` to `0` to discover them anyway.

Trade-off: data deleted from a skipped bucket can still be billed for the minimum storage duration. With `{$WASABI.STATS.SKIP_EMPTY}` = `1`, the totals don't include it and slightly underestimate the invoice during that period.

## How the Stats API data works

Wasabi publishes **one record per bucket per day**. Traffic and request values are **daily totals**, not cumulative counters.

To store each daily value only once, the bucket data is collected **once a day at 06:00** (server or proxy time, custom interval `0;h6`). Ratios and totals are computed at 07:00, and the 30-day averages at 08:00.

Consequences:

- New buckets get their first values at the next 06:00. Use *Execute now* on the master item to collect them sooner.
- This is trend monitoring, not real time: a traffic spike shows up the next day.
- Don't change the collection to a regular interval (e.g. `1h`): each daily value would be stored 24 times, and the 30-day sums would be wrong.

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$WASABI.ENDPOINT}` | `s3.eu-central-1.wasabisys.com` | Wasabi endpoint (hostname only). |
| `{$WASABI.RESPONSE_TIME.WARN}` | `0.5` | Endpoint response time threshold (s). |
| `{$WASABI.PROBE.BUCKET}` | *(empty)* | Bucket used for the write/read test. |
| `{$WASABI.PROBE.PROFILE}` | `wasabi-probe` | AWS CLI profile used by the script. |
| `{$WASABI.PROBE.INTERVAL}` | `10m` | Write/read test interval. |
| `{$WASABI.PROBE.WARN}` | `10` | Write/read test duration threshold (s). |
| `{$WASABI.STATS.AUTH}` | *(secret)* | Stats API credentials, `AccessKey:SecretKey`. Empty = no discovery. |
| `{$WASABI.STATS.BUCKET.MATCHES}` | `.*` | Regex: buckets to discover. |
| `{$WASABI.STATS.BUCKET.NOT_MATCHES}` | `CHANGE_IF_NEEDED` | Regex: buckets to ignore. |
| `{$WASABI.STATS.SKIP_EMPTY}` | `1` | 1 = skip buckets with no data left (deleted or emptied). 0 = discover them. |
| `{$WASABI.STATS.STALE}` | `2d` | Age after which stats are considered stale. |
| `{$WASABI.BUCKET.SIZE.MAX}` | `0` | Bucket size threshold, 0 = disabled. Use context: `{$WASABI.BUCKET.SIZE.MAX:"backups"}` = `5T`. |
| `{$WASABI.EGRESS.RATIO.WARN}` | `80` | 30-day download / storage ratio threshold (%), per bucket (context allowed) and for the account. |
| `{$WASABI.DELETED.RATIO.WARN}` | `20` | Deleted storage threshold, in % of padded storage. |
| `{$WASABI.GROWTH.WARN}` | `20` | Billable storage growth threshold over 7 days (%). |
| `{$WASABI.PRICE.TB}` | `0` | Price per TB per month. 0 = no cost estimate. |
| `{$WASABI.BUDGET}` | `0` | Monthly budget. 0 = budget trigger disabled. |

## Items per bucket

| Item | Source field | Unit |
|---|---|---|
| Storage size | `RawStorageSizeBytes` | B |
| Padded storage size (billing) | `PaddedStorageSizeBytes` | B |
| Metadata storage size | `MetadataStorageSizeBytes` | B |
| Billable objects | `NumBillableObjects` | — |
| Deleted storage size | `DeletedStorageSizeBytes` | B |
| Uploaded (daily) | `UploadBytes` | B |
| Downloaded (daily) | `DownloadBytes` | B |
| GET / PUT / DELETE / LIST requests (daily) | `NumGETCalls`, `NumPUTCalls`, `NumDELETECalls`, `NumLISTCalls` | — |
| 30d download / storage ratio | Calculated | % |
| Stats record date | `CreateTime` | unixtime |

Two graphs are created per bucket: *traffic* (upload vs download) and *requests*.

## Account totals

Calculated items sum the values of all discovered buckets. They are computed by the Zabbix server (no API call), once a day.

| Item | Calculation |
|---|---|
| Storage size | Sum of bucket storage sizes |
| Padded storage size | Sum of padded sizes (billing basis) |
| Deleted storage size | Sum of deleted data still billed |
| **Billable storage (estimate)** | Padded + deleted |
| Billable objects | Sum of objects |
| Active buckets | Number of discovered buckets |
| Uploaded / downloaded (daily) | Sum of daily traffic |
| Downloaded (30 days) | Sum of downloads over 30 days |
| **30d download / storage ratio** | Account-level egress ratio |
| Billable storage, 30d average | Average of the billable estimate over 30 days |
| Estimated monthly cost | 30d average (decimal TB) × `{$WASABI.PRICE.TB}` |

Two graphs show the totals: *storage* (padded, deleted, billable) and *traffic*.

### Checking the invoice

These figures are **estimates**. Wasabi bills an average over the month, and the exact rules (minimum billed volume, metadata, TB vs TiB, rounding) depend on your contract. Compare one month of Zabbix data with a real invoice before relying on the cost estimate.

## Triggers

| Name | Severity | Fires when |
|---|---|---|
| Wasabi endpoint unavailable | High | The last 3 HTTPS connection attempts failed. |
| Wasabi endpoint high response time | Warning | Average response time over 5 minutes exceeds the threshold. |
| Wasabi write/read test failed | High | The last 2 tests failed. |
| Wasabi write/read test slow | Warning | The last 3 tests were slower than the threshold. |
| Wasabi write/read test: no data | Warning | No result for 30 minutes (missing script, timeout…). |
| Bucket {#BUCKET}: size above threshold | Warning | The bucket is larger than its threshold (if set). |
| Bucket {#BUCKET}: high egress ratio | Warning | 30-day downloads exceed the ratio threshold of the bucket size. |
| Bucket {#BUCKET}: Stats API data is stale | Info | The latest stats record is older than `{$WASABI.STATS.STALE}`. |
| Wasabi total: high egress ratio | Warning | 30-day account downloads exceed the ratio threshold of stored data. |
| Wasabi total: fast storage growth | Warning | Billable storage grew more than `{$WASABI.GROWTH.WARN}`% in 7 days. |
| Wasabi total: high deleted storage | Warning | Deleted storage exceeds `{$WASABI.DELETED.RATIO.WARN}`% of active storage. |
| Wasabi total: estimated cost above budget | Warning | The cost estimate exceeds `{$WASABI.BUDGET}` (if set). |

When the endpoint is unavailable, the performance and write/read triggers are suppressed, so you get a single alert.

## About the egress ratio

Wasabi does not charge for egress, but its fair-use policy expects monthly downloads to stay below the stored volume. Check the exact terms of your contract.

The **account ratio** (`Wasabi total: 30d download / storage ratio`) is the one to follow, since the policy applies to the whole account. The per-bucket ratios help find the bucket that drives the downloads. All ratios need 30 days of data to be accurate.

## References

- Wasabi Stats API: https://docs.wasabi.com/docs/utilizations-stats-api
- Wasabi policies: https://docs.wasabi.com/docs/policies-1
- Wasabi Stats API keys: https://docs.wasabi.com/apidocs/generating-a-wasabi-stats-api-key
- Zabbix aggregate calculations: https://www.zabbix.com/documentation/current/en/manual/config/items/itemtypes/calculated/aggregate
- Zabbix custom intervals: https://www.zabbix.com/documentation/current/en/manual/config/items/item/custom_intervals
- Zabbix external checks: https://www.zabbix.com/documentation/current/en/manual/config/items/itemtypes/external
- Zabbix low-level discovery: https://www.zabbix.com/documentation/current/en/manual/discovery/low_level_discovery

.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)
