"""Extraction d'un inventaire Zabbix vers CSV/Excel.

Usage :
    python main.py

Toute la configuration passe par config.yaml (connexion/filtres/sortie) et
extraction.yaml (mapping des champs) — pas d'arguments en ligne de commande
(choix acté : simplicité, un seul point de configuration par fichier).
"""
from __future__ import annotations

import sys

import yaml
from pydantic import ValidationError

from models import AppConfig, ExtractionConfig
from transform import build_column_order, build_row
from writer import write_csv, write_xlsx
from zabbix_client import build_tags_filter, connect, fetch_hosts, resolve_hostgroup_ids

CONFIG_PATH = "config.yaml"
EXTRACTION_PATH = "extraction.yaml"


def load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    try:
        config = AppConfig.model_validate(load_yaml(CONFIG_PATH))
        extraction = ExtractionConfig.model_validate(load_yaml(EXTRACTION_PATH))
    except ValidationError as exc:
        print(f"Erreur de configuration :\n{exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Fichier de configuration introuvable : {exc}", file=sys.stderr)
        return 1

    try:
        api = connect(config)
        groupids = resolve_hostgroup_ids(api, config.filters.hostgroups)
        tags_filter = build_tags_filter(config)
        hosts = fetch_hosts(api, groupids, tags_filter, extraction)
    except RuntimeError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    if not hosts:
        print("Aucun host ne correspond aux filtres définis dans config.yaml.")
        return 0

    columns = build_column_order(extraction)
    rows = [build_row(host, extraction) for host in hosts]

    if config.output.format == "csv":
        write_csv(rows, columns, config.output.path)
    else:
        write_xlsx(rows, columns, config.output.path)

    print(f"{len(rows)} host(s) exporté(s) vers {config.output.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
