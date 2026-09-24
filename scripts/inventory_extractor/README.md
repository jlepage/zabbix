# Zabbix Host Inventory Extractor

A standalone Python script that exports a Zabbix host inventory to CSV or Excel.
It pulls host properties, inventory fields, interfaces and tags in a single API call and lets you map each one to a column name of your choice, so the output file matches whatever format the rest of your team expects.

This is not a Zabbix template, it runs outside Zabbix and only needs read access to the API.

.

## What it exports

- Host properties (name, status, groups, proxy, and so on)
- Inventory fields (the ones filled in the host's Inventory tab)
- Interfaces (Agent, SNMP, IPMI, JMX), resolved to IP or DNS depending on how the interface is configured, with the port shown only when it differs from the protocol default
- Tags, including hosts with several values on the same tag name

Groups, tags and interfaces of the same type are joined with a comma when a host has more than one.

.

## Install

1. Clone or copy the project folder
2. Install the dependencies
```
pip install -r requirements.txt
```
3. Set your Zabbix API token as an environment variable
```
export ZABBIX_TOKEN="your_api_token"
```

.

## Create the Zabbix API token

1. Go to "Users" > "API tokens" on your Zabbix instance
2. Create a token for a user with read access to the hosts you want to export
3. Copy the token value, it will only be shown once

.

## Configure

Two files, no other configuration source.

### config.yaml

Connection to the Zabbix API, output format and path, and filters.

```yaml
zabbix:
  url: "https://zabbix.example.com"
  token: "${ZABBIX_TOKEN}"
  validate_certs: true

output:
  format: csv        # csv or xlsx
  path: "export_hosts.csv"

filters:
  hostgroups:
    - OVH
  tags:
    - tag: location
      value: france
      operator: equals   # equals or contains
```

Leave `filters:` empty (or remove its children) to export every host the token can see.

### extraction.yaml

Field mapping, one entry per line: the Zabbix field on the left, the column name you want in the output on the right. Set a value to `excluded` to leave a field out.

```yaml
host_properties:
  host: "Technical name"
  status: excluded
  groups: "Groups"

inventory_fields:
  location: "Country"

interfaces:
  agent: "Agent"
  snmp: excluded

tags:
  project: "Project"
```

The file shipped with the project already lists every host property and inventory field Zabbix exposes, all set to `excluded` by default. Turn on what you need and rename the columns as you like.

Two fields can't share the same output column, the script checks this at startup and stops with a clear error if it happens.

### Status labels

`host.status` is `0` for a monitored host and `1` for an unmonitored one, which reads backwards at a glance. If you want readable labels instead of the raw value, add this to `extraction.yaml`:

```yaml
value_labels:
  status:
    enable: "Enabled"
    disable: "Disabled"
```

This only applies if `host_properties.status` is active.

.

## Run

```
python main.py
```

The script prints the number of hosts exported and the output path. If no host matches the filters, it exits without writing a file.

.

## Notes

- No pagination, no async, no command line arguments. Everything comes from the two YAML files, on purpose, to keep the script easy to read end to end
- SNMP community strings, SNMPv3 credentials and IPMI passwords are never read or exported
- Hostgroups are resolved to IDs at startup so a rename between two runs doesn't silently change the result
- The CSV is written in UTF-8 with BOM so accented characters display correctly when opened directly in Excel
- The Excel output has frozen headers and an autofilter, sorting and filtering is left to the user in Excel rather than baked into the script

.

## Project structure

```
config.yaml         connection, output, filters
extraction.yaml      field mapping
models.py            config validation
zabbix_client.py      API connection, filter resolution, host fetch
transform.py          raw host to output row
writer.py             CSV / Excel writing
main.py               entry point
```
