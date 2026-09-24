

#  Zabbix Summit 2025 (Riga, Latvia) - 10 tips to please your IT Manager and keep him away from real stuff

### Abstract

.

Your manager wants KPIs. You want to sleep on weekends.
Good news: Zabbix can help with both. In this session, we'll explore 10 practical Zabbix tips that go far beyond server monitoring.
Through humor and live demos, you'll discover features like calculated items, RBAC, HTTP Agent, Geomap, forecasting, and more-each tied to a real-world use case.
Whether you're new to Zabbix or an experienced administrator, you'll leave with actionable ideas to improve visibility, impress your manager, and make your work a little easier.

.

## Tips #2: Let him be commander in chief

#### GEOMAP

1. Fill "longitude" and "latitude" in the host's inventory.
2. Add a widget geomap in your dashboard.
3. Set the coordinates and zoom levels for the initial view.

.

#### Map with host groups

1. Use building plans as background. - A visual representation of your workflow or infrastructure
2. Use a Host group as map elements
3. Place it on your map, set the status icons (OK, Problem, In maintenance, Disabled)
4. Add labels and links - Use Macro expression for display metrics on a link's label.

.

## Tips #3: Let him see inoffensive data

Example of calculated items

**Number of vCPU**
`sum(last_foreach(/*/system.cpu.num?[tag=“u_key:u_value"]))`

**Amount of memory**
`sum(last_foreach(/*/vm.memory.size[total]?[tag=“u_key:u_value"]))`

**Disk usage**
```
sum(last_foreach(/*/vfs.fs.dependent.size[*,used]?[tag="u_key:u_value"]))
+
sum(last_foreach(/*/vfs.fs.size[*,used]?[tag="u_key:u_value"]))
```

**String concatenation**
```
concat(
    last(//system.cpu.num), " vCPU - ",
    round(last(//vm.memory.size[total]) / 1G, 2), " Go RAM - ",
    round(sum(last_foreach(//vfs.fs.size[/,total])) + sum(last_foreach(//vfs.fs.dependant.size[/,total])) / 1G, 2), " Go Hdd"
)
```

You can also use my "ready to use" template : [Overview by tags template](https://github.com/jlepage/zabbix/tree/main/templates/7.4/Overview_by_tags)

.

## Tips #5: Let him think you worked hard

1. Use Template [Linux OS Version](https://github.com/jlepage/zabbix/tree/main/templates/7.4/Linux_os_version) to get your linux distribution

.

## Tips #6: Let him save the planet

Use Template [Carbon footprint](https://github.com/jlepage/zabbix/tree/main/templates/7.4/Carbon_footprint) to get your carbon footprint

.

## Tips #7: Let him be distracted

Use Template [Jira projects overview](https://github.com/jlepage/zabbix/tree/main/templates/7.4/Jira) to get data from Jira

.

## Tips #8: Let him predict the future


- Use Template [OVH by HTTP](https://github.com/jlepage/zabbix/tree/main/templates/7.4/OVH) to get financial data from provider
- Use official Zabbix Template 'AWS Cost explorer'

**Forecast example** :
```
forecast(//ovh.billing.service.cost["{#SERVICE.ID}"], 180d, 90d, "linear", "value")

forecast(
    /<host>/<item>,
    <data samples>,
    <forecast period>,
	<fit>,
    <mode>
)

```

**Timeleft example** :
```
timeleft(//ovh.billing.service.cost["{#SERVICE.ID}"], 180d, {$OVH.BUDGET:"{#SERVICE.NAME}"}, "linear")

timeleft(
    /<host>/<item>,
    <data sample>,
    <goal>,
    <fit>
)
```


See [Zabbix documentation for details](https://www.zabbix.com/documentation/7.4/en/manual/appendix/functions/prediction?hl=Predictive%2Cfunctions%2Cpredictive%2Ctrigger)





.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)