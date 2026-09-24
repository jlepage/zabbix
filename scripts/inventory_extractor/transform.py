"""Transforme les objets host renvoyés par l'API en lignes plates (dict)."""
from __future__ import annotations

from collections import OrderedDict, defaultdict

from models import DEFAULT_PORTS, ExtractionConfig

# type d'interface Zabbix (int, en string dans l'API) -> clé de section
_INTERFACE_TYPE_NAMES = {"1": "agent", "2": "snmp", "3": "ipmi", "4": "jmx"}


def _format_interface_address(interface: dict) -> str:
    """ip si useip=1 sinon dns, suffixé :port si le port n'est pas le défaut."""
    address = interface["ip"] if interface.get("useip") == "1" else interface["dns"]
    iface_type = _INTERFACE_TYPE_NAMES.get(interface.get("type"), "")
    default_port = DEFAULT_PORTS.get(iface_type)
    port = interface.get("port")
    if port and default_port is not None and str(port) != str(default_port):
        return f"{address}:{port}"
    return address


def build_column_order(extraction: ExtractionConfig) -> list[str]:
    """Ordre de sortie = ordre de déclaration dans extraction.yaml, section par section."""
    columns: list[str] = []
    for section in (
        extraction.host_properties,
        extraction.inventory_fields,
        extraction.interfaces,
        extraction.tags,
    ):
        columns.extend(extraction.active(section).values())
    return columns


def build_row(host: dict, extraction: ExtractionConfig) -> OrderedDict:
    row: OrderedDict[str, str] = OrderedDict()

    # -- host_properties --
    for field, column in extraction.active(extraction.host_properties).items():
        if field == "groups":
            row[column] = ", ".join(sorted(g["name"] for g in host.get("groups", [])))
        elif field == "status" and "status" in extraction.value_labels:
            labels = extraction.value_labels["status"]
            raw_status = host.get("status", "0")
            row[column] = labels.enable if raw_status == "0" else labels.disable
        else:
            row[column] = host.get(field, "")

    # -- inventory_fields (vide si inventory désactivé sur le host) --
    inventory = host.get("inventory") or {}
    for field, column in extraction.active(extraction.inventory_fields).items():
        row[column] = inventory.get(field, "")

    # -- interfaces (groupées par type, jointure virgule) --
    active_interfaces = extraction.active(extraction.interfaces)
    if active_interfaces:
        by_type: dict[str, list[str]] = defaultdict(list)
        for iface in host.get("interfaces", []):
            type_name = _INTERFACE_TYPE_NAMES.get(iface.get("type"))
            if type_name in active_interfaces:
                by_type[type_name].append(_format_interface_address(iface))
        for type_name, column in active_interfaces.items():
            row[column] = ", ".join(by_type.get(type_name, []))

    # -- tags (groupés par nom de tag, jointure virgule) --
    active_tags = extraction.active(extraction.tags)
    if active_tags:
        by_tag: dict[str, list[str]] = defaultdict(list)
        for tag in host.get("tags", []):
            if tag["tag"] in active_tags:
                by_tag[tag["tag"]].append(tag.get("value", ""))
        for tag_name, column in active_tags.items():
            row[column] = ", ".join(by_tag.get(tag_name, []))

    return row
