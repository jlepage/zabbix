"""Modèles de validation pour config.yaml et extraction.yaml.

La validation est volontairement stricte : on préfère un échec net et
explicite au chargement plutôt qu'un KeyError/AttributeError en pleine
extraction sur le host n°4000.
"""
from __future__ import annotations

import os
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

EXCLUDED_SENTINEL = "excluded"

# Types d'interfaces supportés par Zabbix et leur port par défaut respectif.
# Valeurs figées : ce sont des standards de protocole, pas une config propre
# à un environnement Zabbix donné.
DEFAULT_PORTS: dict[str, int] = {
    "agent": 10050,
    "snmp": 161,
    "ipmi": 623,
    "jmx": 12345,
}

_ENV_VAR_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def _resolve_env(value: str) -> str:
    """Résout une valeur de la forme ${MA_VARIABLE} depuis l'environnement.

    Si la valeur ne suit pas ce format, elle est retournée telle quelle
    (permet aussi bien un token en dur qu'une variable d'environnement).
    """
    match = _ENV_VAR_PATTERN.match(value.strip())
    if not match:
        return value
    env_name = match.group(1)
    resolved = os.environ.get(env_name)
    if resolved is None:
        raise ValueError(
            f"La variable d'environnement '{env_name}' référencée dans le "
            f"config n'est pas définie."
        )
    return resolved


# --------------------------------------------------------------------------
# config.yaml — connexion / sortie / filtres
# --------------------------------------------------------------------------

class ZabbixAuthConfig(BaseModel):
    url: str
    token: str
    validate_certs: bool = True

    @field_validator("token")
    @classmethod
    def resolve_token(cls, v: str) -> str:
        return _resolve_env(v)


class OutputConfig(BaseModel):
    format: Literal["csv", "xlsx"]
    path: str


class TagFilter(BaseModel):
    tag: str
    value: str
    operator: Literal["equals", "contains"] = "equals"


class FiltersConfig(BaseModel):
    hostgroups: list[str] = Field(default_factory=list)
    tags: list[TagFilter] = Field(default_factory=list)


class AppConfig(BaseModel):
    zabbix: ZabbixAuthConfig
    output: OutputConfig
    filters: FiltersConfig = Field(default_factory=FiltersConfig)

    @field_validator("filters", mode="before")
    @classmethod
    def none_filters_to_empty(cls, v):
        # Cas où la clé "filters:" est présente dans le YAML mais vide
        # (tous les enfants commentés) -> yaml.safe_load renvoie None
        # pour cette clé, distinct du cas où la clé est absente.
        return {} if v is None else v


# --------------------------------------------------------------------------
# extraction.yaml — mapping des champs
# --------------------------------------------------------------------------

class StatusLabels(BaseModel):
    """Libellés d'affichage pour le champ host.status (binaire : 0 ou 1).

    Valeurs par défaut = les codes bruts, pour un comportement identique
    à avant si value_labels.status n'est pas renseigné dans extraction.yaml.
    """
    enable: str = "0"   # host.status == "0" (monitored)
    disable: str = "1"  # host.status == "1" (unmonitored)


class ExtractionConfig(BaseModel):
    host_properties: dict[str, str] = Field(default_factory=dict)
    inventory_fields: dict[str, str] = Field(default_factory=dict)
    interfaces: dict[str, str] = Field(default_factory=dict)
    tags: dict[str, str] = Field(default_factory=dict)
    value_labels: dict[str, StatusLabels] = Field(default_factory=dict)

    @field_validator(
        "host_properties", "inventory_fields", "interfaces", "tags", "value_labels",
        mode="before",
    )
    @classmethod
    def none_section_to_empty(cls, v):
        return {} if v is None else v

    @field_validator("value_labels")
    @classmethod
    def check_supported_value_labels(cls, v: dict[str, "StatusLabels"]) -> dict[str, "StatusLabels"]:
        # Un seul champ supporté pour l'instant : "status" est binaire
        # (0/1), contrairement à d'autres champs enum Zabbix (ex:
        # inventory_mode a 3 états) qui demanderaient un mécanisme différent.
        unsupported = set(v) - {"status"}
        if unsupported:
            raise ValueError(
                f"value_labels ne supporte actuellement que 'status'. "
                f"Champ(s) non supporté(s): {sorted(unsupported)}."
            )
        return v

    @field_validator("interfaces")
    @classmethod
    def check_interface_types(cls, v: dict[str, str]) -> dict[str, str]:
        unknown = set(v) - set(DEFAULT_PORTS)
        if unknown:
            raise ValueError(
                f"Type(s) d'interface inconnu(s) dans extraction.yaml: "
                f"{sorted(unknown)}. Attendus: {sorted(DEFAULT_PORTS)}."
            )
        return v

    def active(self, section: dict[str, str]) -> dict[str, str]:
        """Ne garde que les champs dont la colonne n'est pas 'excluded'."""
        return {
            field: column
            for field, column in section.items()
            if column.strip().lower() != EXCLUDED_SENTINEL
        }

    @model_validator(mode="after")
    def check_status_labels_require_active_status_field(self) -> "ExtractionConfig":
        if "status" in self.value_labels and "status" not in self.active(self.host_properties):
            raise ValueError(
                "value_labels.status est défini mais host_properties.status "
                "vaut 'excluded'. Activez le champ pour que le libellé "
                "s'applique, ou retirez value_labels.status."
            )
        return self

    @model_validator(mode="after")
    def check_no_duplicate_columns(self) -> "ExtractionConfig":
        seen: dict[str, str] = {}  # nom_colonne -> "section.champ" d'origine
        for section_name in ("host_properties", "inventory_fields", "interfaces", "tags"):
            section = getattr(self, section_name)
            for field, column in self.active(section).items():
                origin = f"{section_name}.{field}"
                if column in seen:
                    raise ValueError(
                        f"Collision de colonne de sortie '{column}' entre "
                        f"'{seen[column]}' et '{origin}'. Chaque champ actif "
                        f"doit avoir un nom de colonne unique."
                    )
                seen[column] = origin
        if not seen:
            raise ValueError(
                "extraction.yaml ne contient aucun champ actif (tout est à "
                "'excluded'). Activez au moins un champ."
            )
        return self
