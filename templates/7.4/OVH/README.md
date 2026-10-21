# OVH by HTTP (French Provider) - Zabbix template
.

**OVH Cost Explorer**

This template adds OVH billing visibility to Zabbix, separate from the existing host discovery.
A dedicated discovery script lists billable services (cloud projects, VPS, dedicated servers, domains, NAS-HA) at the granularity OVH actually bills at, while a second script pulls monthly costs from the OVH billing API.
Dependent items expose the cost per service, tagged by category, and Zabbix aggregate items sum those tags into per-category totals, so the data model stays live and doesn't need any custom caching or state.
Per-service budget alerting is available through the `{$OVH.BUDGET}` macro, overridable per service with `{$OVH.BUDGET:"<service or project name>"}`.

**OVH Hosts discovery**

A single discovery script queries Public Cloud instances and dedicated (bare metal) servers and creates Zabbix hosts from them, tagged with location, provider and project/product context.
It is disabled by default: enable it once your credentials macros are filled in.
Public Cloud host prototypes are also created disabled, so you can review them before turning monitoring on.
No monitoring template is linked to the discovered hosts by default — link one (e.g. ICMP Ping) on the host prototypes if you want items/triggers out of the box.
VPS are collected by the same script and counted in the Cost Explorer, but don't have a discovery rule yet.

.

## Import the template

.

1. Download the template
2. Go to "Data collection" > "Templates" on your Zabbix instance
3. Click on "Import"
4. Select the template file and click on "Import" button.

.

## Create OVH API token

1. Go to [OVH API Token creation page](https://auth.eu.ovhcloud.com/api/createToken)
2. Set the correct rights
```
   GET /me/bill*
   GET /dedicated/server*
   GET /dedicated/nasha*
   GET /cloud/project*
   GET /vps*
   GET /domain*
```
3. fill the validity and restricted IPs

.

## Link the template to an Host

.

1. Go to "Data collection" > "Host" on your Zabbix instance
2. Create an empty Host like "OVH Endpoint" or "OVH Overview"
3. Link the template "OVH by HTTP" to your host
4. Fill User macros in your host
```
    {$OVH.APP_ID}
    {$OVH.APP_SECRET}
    {$OVH.CONSUMER_KEY}
    {$OVH.ENDPOINT} - ovh-eu, ovh-ca or ovh-us
    {$OVH.PROXY}
    {$OVH.BUDGET}
```
5. Once credentials are validated (check "Latest data" on the raw items, `errors` should stay empty), enable the "OVH servers discovery" item if you want host discovery.

.

## Copyrights

.

Formations certifiées Zabbix:
[ZCS v7](https://formation.jlepage.fr/formation/zabbix/zcs-zabbix-certified-specialist-formation-specialiste-zabbix),
[ZCP v7](https://formation.jlepage.fr/formation/zabbix/zcp-zabbix-certified-professional-formation-professionnel-zabbix),
[ZCE v7](https://formation.jlepage.fr/formation/zabbix/zce-zabbix-certified-expert-formation-expert-zabbix),
[ZCS / ZCP Upgrade v8](https://formation.jlepage.fr/formation/zabbix/zcsu-zabbix-certified-specialist-upgrade-v8-formation-specialiste-zabbix),
[ZCS v8](https://formation.jlepage.fr/formation/zabbix/zcs-v8-zabbix-certified-specialist-formation-specialiste-zabbix),
[ZCP v8](https://formation.jlepage.fr/formation/zabbix/zcp-v8-zabbix-certified-professional-formation-professionnel-zabbix),
[ZCE v8](https://formation.jlepage.fr/formation/zabbix/zce-v8-zabbix-certified-expert-v8-formation-expert-zabbix)

**Copyrights 2026 [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)**
