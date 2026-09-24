# Export d'inventaire Zabbix

Extrait les hosts Zabbix (propriétés, champs d'inventaire, interfaces, tags)
vers un fichier CSV ou Excel, selon un mapping défini dans `extraction.yaml`.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

- **`config.yaml`** : URL Zabbix, token (support `${VAR_ENV}`), format/chemin
  de sortie, filtres (hostgroups par nom, tags avec logique ET).
- **`extraction.yaml`** : mapping `champ_zabbix: nom_colonne`. Une colonne
  `"excluded"` désactive le champ. Deux champs ne peuvent pas pointer vers
  la même colonne (erreur de validation au démarrage sinon).

Le token n'est jamais à mettre en dur dans un fichier versionné :

```bash
export ZABBIX_TOKEN="votre_token_api"
```

## Exécution

```bash
python main.py
```

## Règles de comportement à connaître

- **Valeurs multiples** (groupes, tags avec plusieurs valeurs pour un même
  nom, interfaces multiples d'un même type) → jointure par virgule dans une
  seule colonne.
- **Inventaire désactivé** sur un host → champs d'inventaire vides, pas
  d'erreur.
- **Interfaces** : adresse = IP si `useip=1`, sinon DNS. Le port n'est
  affiché que s'il diffère du port standard du protocole
  (10050/161/623/12345 pour agent/SNMP/IPMI/JMX). Les credentials SNMP/IPMI
  ne sont jamais extraits.
- **Hostgroups** filtrés par nom, résolus en ID au démarrage (plus fiable
  qu'un filtre par nom direct si un groupe est renommé entre deux runs).
- Pas de pagination (volumétrie < 300 hosts), pas de mode asynchrone, pas
  d'arguments CLI — tout passe par les deux fichiers YAML.

## Structure du projet

```
config.yaml         Connexion, sortie, filtres
extraction.yaml      Mapping des champs à extraire
models.py            Validation pydantic des deux configs
zabbix_client.py      Connexion API + résolution filtres + fetch
transform.py          Transformation host brut -> ligne de sortie
writer.py             Écriture CSV / Excel
main.py               Orchestration
```

.

## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)
