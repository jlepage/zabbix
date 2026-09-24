# Overview by tags - Zabbix Template

.

This Zabbix template provides a centralized overview of infrastructure resources grouped by host tags, such as cloud provider or other custom dimensions. It uses Low-Level Discovery (LLD) to dynamically generate aggregated metrics for each discovered tag/value pair.

The template calculates the number of hosts, total and used CPU, memory, and disk resources, along with their usage percentages.
Metrics are aggregated across matching hosts using Zabbix calculated items and tag-based last_foreach() queries, making the overview automatically adapt as hosts and tags change.

**Metrics per tags (key/value)**

- Number of CPU
- Usage of CPUs
- Usage % of CPUs
- Total memory
- Memory usage
- Memory usage in %
- Total disk
- Disk usage
- Disk usage in %

.

## Import the template

.

1. Download the template
2. Go to "Data collection" > "Templates" on your Zabbix instance
3. Click on "Import"
4. Select the template file and click on "Import" button.

.

## Link the template to an Host

1. Go to "Data collection" > "Host" on your Zabbix instance
2. Create an empty Host like "Overview by countries" or "Overview by providers"
3. Link the template "Overview_by_tags" to your host

.

## Configure the host

1. Go to your host's items : "Data collection" > "Host" > "Items" (of your host)
2. Open the item "Raw Json Data"
3. Edit the formula of the calculated item to generate a valid json with the structure
```
[
    {
        "{#TAG.KEY}": "<your tag key>",
        "{#TAG.VALUE}": "<your tag value>",
    },
    {
        "{#TAG.KEY}": "<your tag key>",
        "{#TAG.VALUE}": "<your tag value>",
    },
]
```

Formula should be like this :
```
concat("[", "{\"{#TAG.KEY}\": \"provider\",\"{#TAG.VALUE}\": \"OVH\"},{\"{#TAG.KEY}\": \"provider\",\"{#TAG.VALUE}\": \"AWS\"}", "]")
```
or
```
concat("[", "{\"{#TAG.KEY}\": \"country\",\"{#TAG.VALUE}\": \"france\"},{\"{#TAG.KEY}\": \"country\",\"{#TAG.VALUE}\": \"canada\"}", "]")
```

4. Execute the item by clicking on "Execute now" button.

.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)
