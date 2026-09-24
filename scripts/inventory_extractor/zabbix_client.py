"""Connexion à l'API Zabbix et récupération des hosts via zabbix_utils."""
from __future__ import annotations

from zabbix_utils import APIRequestError, ZabbixAPI

from models import AppConfig, ExtractionConfig

# Mapping operator texte (config) -> code operator API Zabbix pour les tags.
# 0 = contains (LIKE), 1 = equals.
_TAG_OPERATOR_CODES = {"contains": 0, "equals": 1}


def connect(config: AppConfig) -> ZabbixAPI:
    """Ouvre une session à l'API Zabbix via token (pas de login/logout requis)."""
    try:
        api = ZabbixAPI(
            url=config.zabbix.url,
            skip_version_check=True if not config.zabbix.validate_certs else False,
        )
        if not config.zabbix.validate_certs:
            api.session.verify = False
        api.login(token=config.zabbix.token)
    except APIRequestError as exc:
        raise RuntimeError(f"Échec d'authentification à l'API Zabbix : {exc}") from exc
    return api


def resolve_hostgroup_ids(api: ZabbixAPI, names: list[str]) -> list[str]:
    """Résout des noms de hostgroups en IDs (plus fiable que filter par nom)."""
    if not names:
        return []
    try:
        groups = api.hostgroup.get(filter={"name": names}, output=["groupid", "name"])
    except APIRequestError as exc:
        raise RuntimeError(f"Échec de résolution des hostgroups : {exc}") from exc

    found_names = {g["name"] for g in groups}
    missing = set(names) - found_names
    if missing:
        raise RuntimeError(
            f"Hostgroup(s) introuvable(s) dans Zabbix : {sorted(missing)}. "
            f"Vérifiez l'orthographe dans config.yaml."
        )
    return [g["groupid"] for g in groups]


def build_tags_filter(config: AppConfig) -> list[dict] | None:
    """Construit le paramètre 'tags' pour host.get (logique ET, actée en discussion)."""
    if not config.filters.tags:
        return None
    return [
        {
            "tag": t.tag,
            "value": t.value,
            "operator": _TAG_OPERATOR_CODES[t.operator],
        }
        for t in config.filters.tags
    ]


def fetch_hosts(
    api: ZabbixAPI,
    groupids: list[str],
    tags_filter: list[dict] | None,
    extraction: ExtractionConfig,
) -> list[dict]:
    """Récupère les hosts en un seul appel, avec uniquement les sous-objets requis."""
    host_fields = list(extraction.active(extraction.host_properties).keys())
    # hostid est toujours nécessaire en interne même si pas exporté
    # (ne coûte rien, utile pour les messages d'erreur/logs).
    output_fields_set = set(host_fields) | {"hostid", "host"}
    output_fields_set.discard("groups")  # 'groups' se récupère via selectGroups, pas output
    output_fields = sorted(output_fields_set)

    inventory_fields = list(extraction.active(extraction.inventory_fields).keys())
    want_groups = "groups" in extraction.active(extraction.host_properties)
    want_interfaces = bool(extraction.active(extraction.interfaces))
    want_tags = bool(extraction.active(extraction.tags))

    params: dict = {
        "output": output_fields,
        "filter": {},
    }
    if groupids:
        params["groupids"] = groupids
    if tags_filter:
        params["tags"] = tags_filter
        # evaltype=0 (défaut Zabbix) = "And/Or" : ET entre tags de noms
        # différents, OU entre plusieurs valeurs d'un même tag. C'est le
        # comportement "logique ET" demandé pour des tags de noms distincts.

    if inventory_fields:
        params["selectInventory"] = inventory_fields
    if want_groups:
        params["selectGroups"] = ["name"]
    if want_interfaces:
        params["selectInterfaces"] = ["type", "useip", "ip", "dns", "port", "main"]
    if want_tags:
        params["selectTags"] = "extend"

    try:
        return api.host.get(**params)
    except APIRequestError as exc:
        raise RuntimeError(f"Échec de récupération des hosts : {exc}") from exc
