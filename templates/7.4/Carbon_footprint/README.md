# Simplified Carbon Footprint - Zabbix Template

.

This Zabbix 7.4 template provides an estimation of the carbon footprint of cloud virtual machines using standard metrics collected by the Zabbix agent.

The template estimates CPU and RAM power consumption from the VM resources and CPU utilization. It then calculates operational emissions using the carbon intensity of the electricity in the VM location, as well as embodied emissions allocated from a generic server model.

The methodology and several reference values are inspired by the Boavizta project. However, the calculations implemented in this template are simplified and independent. This template is not produced, maintained, validated or endorsed by Boavizta, and its results should not be considered equivalent to BoaviztAPI results.

The values are intended for monitoring, comparison and trend analysis rather than precise carbon accounting.

**Metrics per virtual machine**

- Number of vCPUs
- Total RAM
- CPU utilization
- Estimated CPU power
- Estimated RAM power
- Estimated total power
- Operational CO2 emissions
- Embodied CO2 emissions
- Total CO2 emissions

A reference template also provides global aggregated metrics using Zabbix calculated items and tag-based `last_foreach()` queries.

**Global metrics**

- Total vCPUs
- Total RAM
- Total estimated power
- Total operational emissions
- Total embodied emissions
- Total emissions

.

## Requirements

.

The monitored virtual machines must already use a standard Zabbix agent template such as "Linux by Zabbix agent" or "Windows by Zabbix agent".

The following item keys are required:

```
system.cpu.num
system.cpu.util[,idle]
vm.memory.size[total]
```

.

## Import the templates

.

1. Download the template file
2. Go to "Data collection" > "Templates" on your Zabbix instance
3. Click on "Import"
4. Select the template file and click on the "Import" button

.

## Create the reference host

.

1. Go to "Data collection" > "Hosts" on your Zabbix instance
2. Create an empty host with the exact host name:

```
Simplified Carbon Footprint Reference
```

3. No agent interface is required
4. Link the template "Simplified Carbon Footprint - Reference" to this host

The reference host stores the coefficients used by the model and calculates the global values for all monitored virtual machines.

.

## Link the template to virtual machines

.

1. Go to "Data collection" > "Hosts" on your Zabbix instance
2. Select a cloud virtual machine
3. Link the template "Simplified Carbon Footprint - Cloud VM"
4. Make sure the required Zabbix agent items are available on the host

The carbon footprint items are tagged with:

```
component: carbon-footprint
```

This tag is used by the reference template to aggregate values across the monitored virtual machines.

.

## Configure the carbon intensity

.

The electricity carbon intensity must be configured on each virtual machine using the host macro:

```
{$CARBON.INTENSITY}
```

The value is expressed in `gCO2e/kWh` and should represent the electricity carbon intensity of the VM location.

Example values:

```
France       41.44
Canada      190.72
Ireland     256.54
Germany     329.65
Singapore   402
Hong Kong   500
```

Carbon intensity values may vary depending on the year, electricity provider and methodology. They should be reviewed and adapted to the environment being monitored.

.

## Scope and limitations

.

The model uses VM-visible resources because the underlying physical infrastructure of cloud providers is generally unknown.

CPU power is estimated from CPU utilization and the VM vCPU allocation. RAM power is estimated using a per-GiB coefficient. Embodied emissions are estimated from a generic server model and allocated proportionally to the number of vCPUs.

The current model does not include:

- Datacenter PUE and cooling
- Network infrastructure
- Physical storage infrastructure
- Exact physical server characteristics
- Cloud provider specific hardware

The resulting values should therefore be considered estimates and orders of magnitude.

.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring)