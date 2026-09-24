# Linux OS version - Zabbix template

This template collects Linux operating system information from `/etc/os-release`.

It uses a single master item to retrieve the file content and dependent items to extract the operating system name, version and human-readable distribution name.

The template does not require any external script or additional package.

## Collected data

The following information is collected:

| Item                     | Key                                    | Description                                                       |
| ------------------------ | -------------------------------------- | ----------------------------------------------------------------- |
| Os Release - raw         | `vfs.file.contents["/etc/os-release"]` | Raw content of `/etc/os-release`                                  |
| Os Release - Name        | `os.release.name`                      | Operating system name extracted from `NAME`                       |
| Os Release - Pretty name | `os.release.pretty-name`               | Human-readable operating system name extracted from `PRETTY_NAME` |
| Os Release - Version     | `os.release.version`                   | Operating system version extracted from `VERSION`                 |

The `/etc/os-release` file is collected every 12 hours. Dependent items are updated from the master item without additional requests to the monitored host.

## Distribution normalization

The `PRETTY_NAME` value is normalized for Debian and Ubuntu systems to provide more consistent values in Zabbix.

For Debian, `GNU/Linux` is removed while the version and codename are preserved.

Example:

```text
Debian GNU/Linux 12 (bookworm)
```

becomes:

```text
Debian 12 (bookworm)
```

For Ubuntu, only the major and minor release version is kept.

Example:

```text
Ubuntu 24.04.3 LTS
```

becomes:

```text
Ubuntu 24.04
```

Other distributions are returned without modification.

## Requirements

The monitored system must:

1. Use a Linux distribution providing `/etc/os-release`
2. Allow the Zabbix agent to read `/etc/os-release`
3. Support the `vfs.file.contents` item key

No additional user macros are required.

## Import the template

1. Download the template
2. Go to "Data collection" > "Templates" on your Zabbix instance
3. Click on "Import"
4. Select the template file and click on "Import"

## Link the template to a host

1. Go to "Data collection" > "Hosts" on your Zabbix instance
2. Select the Linux host you want to monitor
3. Open the "Templates" section
4. Link the template "Linux OS version"
5. Save the host configuration

The operating system information will be available in "Monitoring" > "Latest data" after the master item has been collected.

## Update interval

The raw `/etc/os-release` file is checked every 12 hours.

The master item uses "Discard unchanged" preprocessing, so dependent items are only processed when the content changes.

## Tags

The template uses the following item tags:

```text
os-scope: name
os-scope: pretty-name
os-scope: version
component: raw
```

The template itself is tagged with:

```text
component: system
```

## Compatibility

The template is exported for Zabbix 7.4.

## Copyrights

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring)
