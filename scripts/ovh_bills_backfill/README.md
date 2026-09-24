# OVH Cost Explorer - Historical backfill script

.

This script reconstructs past months of OVH billing history into Zabbix, for the items created by the "OVH Cost Explorer" part of the template.

Zabbix items can only be dated at collection time, so getting past invoices into history requires switching the target items to Trapper for the duration of the import, pushing each month with its own timestamp through the Zabbix API, then switching them back. The script handles this end to end, including the `Calculated` items used for per-category totals, which cannot be backfilled any other way since they only ever read the current state of the items they sum.

.

## Requirements

.

1. Python 3.9 or later
2. Install dependencies
```
pip install -r requirements.txt --break-system-packages
```
This installs the official `ovh` and `zabbix_utils` SDKs.

.

## Configuration

.

1. Copy `config.example.json` to `config.json`
2. Fill in your OVH API credentials (same ones used by the template) and your Zabbix connection details
```json
{
  "ovh_endpoint": "ovh-eu",
  "ovh_app_key": "",
  "ovh_app_secret": "",
  "ovh_consumer_key": "",
  "zabbix_url": "https://<your-zabbix>/api_jsonrpc.php",
  "zabbix_token": "",
  "zabbix_host": "",
  "item_key": "ovh.billing.data",
  "sleep": 0.2
}
```
3. Restrict `config.json` permissions, it contains secrets
```
chmod 600 config.json
```

.

## Zabbix prerequisites, check before running

.

1. The billing master item (`ovh.billing.data` by default) must be switched to type Trapper before the script runs, and back to Script once done
2. History and Trends storage period on the master item and on its dependent/prototype items (`ovh.billing.total`, `ovh.billing.cost[*]`, `ovh.billing.category.total[*]`) must cover the number of months you intend to backfill, otherwise Zabbix housekeeping will silently delete the injected data on its next cleanup cycle
3. `Allowed hosts` on the trapper items must not block the request. Leave it empty unless you have a specific reason to restrict it, and note that `0.0.0.0` is treated as a literal IP, not a wildcard
4. The API token needs permission to call `history.push` and `item.update` (Administration > User roles > API tab)
5. The Zabbix host running this script must be monitored directly by the Zabbix server, not through a proxy - `history.push` does not support proxy-monitored hosts

.

## Usage

.

1. Preview what would be sent, nothing is written to Zabbix
```
python3 ovh_billing_backfill.py --config config.json --months 24 --dry-run
```
2. Check the totals and currency printed for each month against your OVH billing space
3. Run it for real
```
python3 ovh_billing_backfill.py --config config.json --months 24 --yes
```
4. Check "Latest data" on the host, widen the time range on the graphs since the injected points are dated in the past, not "now"
5. Switch the master item back to type Script. Category items are restored automatically by the script, including on error

.

## Options

.

```
--months N          number of complete months to backfill, excluding the current one (default: 24)
--dry-run            print what would happen, write nothing
--yes                required to confirm a real run
--skip-categories    do not touch the Calculated category items, only backfill the master and the per-service items
--config PATH        path to the config file (default: config.json)
```
Any config.json field can be overridden on the command line with the matching `--ovh-*` / `--zabbix-*` flag, except `--months`, `--dry-run` and `--yes`, which only exist as CLI flags.

.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)
