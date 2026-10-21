# Jira ticket statistics per project - Zabbix Template

.

This integration pulls per-project Jira ticket statistics into Zabbix, without manual per-project setup.
Two scripts (jira_projects_discovery.js, jira_metrics_data.js) query the Jira Cloud REST API (/rest/api/3/search/jql) using a service account and a classic (non-scoped) API token.
Project discovery feeds a Zabbix LLD rule, filterable by regex on project key, name and type via host macros, so items are created automatically for each project without touching the template when a new project shows up in Jira.

Per-project metrics cover volume (open tickets, new/resolved in the last 7 days), warning signals (overdue, unassigned, high priority) and backlog health (age distribution across 4 buckets, average age using the "uptime" unit for readable formatting).
Calculated items using sum_foreach() aggregate these metrics across all projects for global graphs and reports, including a properly volume-weighted average age. Requirements: a classic Jira Cloud API token and "Browse Projects" permission on the relevant projects.


**Mon article de blog (en français)**:
(Suivre les projets Jira dans Zabbix)[https://www.jlepage.blog/blog/zabbix-3/suivre-les-projets-jira-dans-zabbix-8]


**Per project and global metrics**

- 0 to 3 months old tickets
- 3 to 6 months old tickets
- 6 to 12 months old tickets
- 12 months and older tickets
- Average age of tickets
- Bugs open
- High priority tickets
- Open tickets
- Overdue tickets
- Unassigned tickets
- New tickets (7 days)
- Resolved tickets (7 days)

.

## Import the template

1. Download the template
2. Go to "Data collection" > "Templates" on your Zabbix instance
3. Click on "Import"
4. Select the template file and click on "Import" button.

.

## Create OVH API token

.

1. Go to [Jira API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create a API token (simple)

.

## Link the template to an Host

.

1. Go to "Data collection" > "Host" on your Zabbix instance
2. Create an empty Host like "Jira's projects" or "Jira overview"
3. Link the template "Jira cloud projects overview" to your host
4. Fill User macros in your host
```
{$JIRA.API_TOKEN} xxxxxyyyyzzzzz
{$JIRA.EMAIL} - name@corporate.com
{$JIRA.BASE_URL} - https://<workspace>.atlassian.net
```

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