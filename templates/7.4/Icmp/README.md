# ICMP target ping

A fork of the official Zabbix **ICMP Ping** template (Zabbix 7.4).

The official template pings the host's own interface. This fork pings a **target** defined in the user macro `{$ICMP_TARGET}` instead, which can be any IP address or hostname.

## Who sends the ping?

The **Zabbix server or proxy** that monitors the host sends the ping, not the host itself.

The host you link the template to is only a container for the items and triggers. No agent is involved, and nothing runs on that host. The ICMP packets always go from the server or proxy to `{$ICMP_TARGET}`:

```
Zabbix server / proxy  ──ICMP──►  {$ICMP_TARGET}
```

If the host is monitored by a proxy, that proxy sends the ping. Choosing the proxy therefore lets you test reachability from a specific network location.

## Requirements

`fping` must be installed on the server and on every proxy that may monitor the host, and `FpingLocation` must be set in `zabbix_server.conf` / `zabbix_proxy.conf`.

## Setup

1. Import `Icmp_ping_target.yaml`.
2. Link the template to a host.
3. On the host, set `{$ICMP_TARGET}` to the address you want to ping. Don't rely on the template default (`<change_me>`).

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$ICMP_TARGET}` | `<change_me>` | IP address or hostname to ping. Set it on each host. |
| `{$ICMP_LOSS_WARN}` | `20` | Packet loss warning threshold (%). |
| `{$ICMP_RESPONSE_TIME_WARN}` | `0.15` | Response time warning threshold (seconds). |

## Items

| Name | Key | Description |
|---|---|---|
| ICMP ping | `icmpping[{$ICMP_TARGET}]` | 1 = Up, 0 = Down |
| ICMP loss | `icmppingloss[{$ICMP_TARGET}]` | Packet loss in % |
| ICMP response time | `icmppingsec[{$ICMP_TARGET}]` | Response time in seconds |

## Triggers

| Name | Severity | Fires when |
|---|---|---|
| Unavailable by ICMP ping | High | The last 3 checks failed. |
| High ICMP ping loss | Warning | Loss stays above `{$ICMP_LOSS_WARN}` for 5 minutes (excluding 100%). |
| High ICMP ping response time | Warning | Average response time over 5 minutes exceeds `{$ICMP_RESPONSE_TIME_WARN}`. |

The triggers depend on each other (Unavailable → Loss → Response time), so a down target raises a single alert.

## Limitation

You can only link a template to a host once, so each host can watch only one target. To monitor several targets, create one host per target.

.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)
