#!/usr/bin/env python3
"""
Backfill de l'historique de facturation OVH vers Zabbix (item Trapper).

Rejoue, mois par mois, la même logique que ovh_billing_data.js (le script
de collecte "live"), et pousse chaque mois vers Zabbix via l'API
`history.push`, avec un `clock` correspondant à la fin du mois concerné.

Ce script est PONCTUEL : il suppose que l'item Zabbix ciblé a été basculé
en type Trapper avant l'exécution, et devra être rebasculé en Script juste
après (voir la checklist affichée en fin d'exécution).

Prérequis Zabbix, À VÉRIFIER AVANT DE LANCER :
  1. L'item `ovh.billing.data` est bien de type Trapper (le script le
     vérifie et refuse de continuer sinon).
  2. Son "History storage period" (et celui de ses items dépendants /
     prototypes : ovh.billing.total, ovh.billing.cost[*],
     ovh.billing.category.total[*]) couvre au moins --months mois.
     Sinon le housekeeper purgera silencieusement les données injectées
     au prochain cycle de nettoyage.
  3. L'IP de ce script (ou du serveur qui l'exécute) figure dans le champ
     "Allowed hosts" de l'item Trapper.
  4. Le jeton API Zabbix utilisé a la permission d'appeler `history.push`
     (Administration -> Rôles utilisateurs -> onglet API).

Usage :
  python3 ovh_billing_backfill.py \
      --ovh-endpoint ovh-eu \
      --ovh-app-key XXX --ovh-app-secret YYY --ovh-consumer-key ZZZ \
      --zabbix-url https://zabbix.example.com/api_jsonrpc.php \
      --zabbix-token <jeton API Zabbix> \
      --zabbix-host "OVH Billing" \
      --months 24 \
      --dry-run          # aperçu sans rien écrire dans Zabbix

  Puis, une fois vérifié, relancer SANS --dry-run et avec --yes pour
  confirmer l'exécution réelle.
"""

import argparse
import json
import sys
import time
from calendar import monthrange
from datetime import datetime, timezone

import ovh
from zabbix_utils import ZabbixAPI, APIRequestError

ITEM_KEY = 'ovh.billing.data'
TRAPPER_ITEM_TYPE = 2  # type Zabbix pour "Trapper"


def make_ovh_client(endpoint, app_key, app_secret, consumer_key):
    """Le SDK officiel OVH gère nativement la signature, la synchronisation
    d'horloge (paresseuse, mise en cache après le premier appel) et les
    alias d'endpoint 'ovh-eu'/'ovh-ca'/'ovh-us' — pas besoin de les
    redéfinir nous-mêmes."""
    return ovh.Client(
        endpoint=endpoint,
        application_key=app_key,
        application_secret=app_secret,
        consumer_key=consumer_key,
    )


# --------------------------------------------------------------------------
# Client Zabbix — API JSON-RPC, authentification par jeton (Bearer).
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Zabbix — via zabbix_utils.ZabbixAPI, qui gère nativement l'authentification
# par jeton et le passage à la méthode JSON-RPC demandée (zapi.history.push
# devient l'appel "history.push", zapi.item.get devient "item.get", etc.).
# --------------------------------------------------------------------------
class ZabbixClient:

    def __init__(self, url, token):
        # skip_version_check : évite un appel apiinfo.version superflu au
        # démarrage, et fonctionne même si le compte n'a pas accès à cette
        # méthode (restreinte par certains rôles).
        self.api = ZabbixAPI(url=url, token=token, skip_version_check=True)

    def get_item(self, host, key):
        try:
            result = self.api.item.get(
                output=['itemid', 'type', 'history'],
                host=host,
                filter={'key_': key},
            )
        except APIRequestError as error:
            raise RuntimeError('Zabbix API error on item.get: %s' % error) from error

        if not result:
            raise RuntimeError('Item "%s" not found on host "%s".' % (key, host))
        return result[0]

    def history_push(self, host, key, value, clock):
        try:
            result = self.api.history.push(host=host, key=key, value=value, clock=clock)
        except APIRequestError as error:
            raise RuntimeError('Zabbix API error on history.push: %s' % error) from error
 
        # ATTENTION : un succès JSON-RPC global (pas d'exception) ne veut PAS
        # dire que la valeur a été acceptée. Chaque entrée de result['data']
        # peut porter sa propre erreur (item désactivé, permission refusée,
        # item introuvable pour ce host...) sans que l'appel API échoue.
        entries = result.get('data', []) if isinstance(result, dict) else []
        errors = [e['error'] for e in entries if isinstance(e, dict) and 'error' in e]
        if errors:
            raise RuntimeError('history.push a répondu "success" mais a rejeté la valeur '
                                'pour %s : %s' % (key, '; '.join(errors)))
 
        return result


# --------------------------------------------------------------------------
# Reprise de la logique de ovh_billing_data.js pour un mois donné.
# --------------------------------------------------------------------------
def fetch_billing_for_month(ovh_client, year, month):
    period_start = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = monthrange(year, month)[1]
    period_end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    from_str = period_start.strftime('%Y-%m-%d')
    to_str = period_end.strftime('%Y-%m-%d')

    data = {
        'errors': '',
        'meta': {
            'period': '%04d-%02d' % (year, month),
            'period_start': from_str,
            'period_end': to_str,
            'currency': '',
        },
        'total': 0.0,
        'services': [],
    }

    errors = {}
    amounts_by_service = {}

    try:
        bill_ids = ovh_client.get('/me/bill', **{'date.from': from_str, 'date.to': to_str})
    except ovh.exceptions.Forbidden as error:
        data['errors'] = ('Failed to list bills: Forbidden (403). Check that the consumer_key access '
                           'rules include BOTH "/me/bill" AND "/me/bill/*". Raw error: %s' % error)
        return data, period_end
    except Exception as error:
        data['errors'] = 'Failed to list bills: %s' % error
        return data, period_end

    for bill_id in bill_ids:
        try:
            if data['meta']['currency'] == '':
                bill = ovh_client.get('/me/bill/%s' % bill_id)
                data['meta']['currency'] = bill['priceWithTax']['currencyCode']

            detail_ids = ovh_client.get('/me/bill/%s/details' % bill_id)

            for detail_id in detail_ids:
                line = ovh_client.get('/me/bill/%s/details/%s' % (bill_id, detail_id))
                amount = line['totalPrice']['value']
                service_id = line.get('domain') or 'unknown'
                amounts_by_service[service_id] = amounts_by_service.get(service_id, 0.0) + amount

        except Exception as error:
            errors['bill_' + bill_id] = str(error)

    for service_id, amount in amounts_by_service.items():
        amount = round(amount, 2)
        if amount != 0:
            data['services'].append({'id': service_id, 'amount': amount})
            data['total'] += amount

    data['total'] = round(data['total'], 2)

    if errors:
        data['errors'] = 'Failed to receive data:\n' + '\n'.join(
            '%s : %s' % (k, v) for k, v in errors.items()
        )

    return data, period_end


def months_back(count):
    """Liste (year, month) du plus ancien au plus récent, en excluant le
    mois en cours (laissé au script live une fois rebasculé en Script)."""
    today = datetime.now(timezone.utc)
    year, month = today.year, today.month

    results = []
    for _ in range(count):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        results.append((year, month))

    results.reverse()  # du plus ancien au plus récent
    return results


CONFIG_FIELDS = [
    'ovh_endpoint', 'ovh_app_key', 'ovh_app_secret', 'ovh_consumer_key',
    'zabbix_url', 'zabbix_token', 'zabbix_host', 'item_key', 'sleep',
]


def load_config(path):
    """Charge config.json. Toutes les clés sont optionnelles dans le fichier
    (des valeurs peuvent aussi venir des arguments CLI correspondants, qui
    sont prioritaires si fournis) — sauf months/dry-run/yes, volontairement
    exclus du fichier et disponibles uniquement en CLI."""
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    unknown = set(config) - set(CONFIG_FIELDS)
    if unknown:
        print('ATTENTION : clés inconnues dans %s, ignorées : %s' % (path, ', '.join(sorted(unknown))))

    return {k: v for k, v in config.items() if k in CONFIG_FIELDS}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', default='config.json',
                         help='Fichier JSON contenant les paramètres OVH/Zabbix (défaut : config.json)')
    parser.add_argument('--ovh-endpoint', choices=['ovh-eu', 'ovh-ca', 'ovh-us'],
                         help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--ovh-app-key', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--ovh-app-secret', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--ovh-consumer-key', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--zabbix-url', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--zabbix-token', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--zabbix-host', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--item-key', help='Surcharge la valeur de config.json si fourni')
    parser.add_argument('--sleep', type=float, help='Surcharge la valeur de config.json si fourni')
    # Volontairement absents de config.json, CLI uniquement :
    parser.add_argument('--months', type=int, default=24, help='Nombre de mois complets à reconstituer (défaut : 24)')
    parser.add_argument('--dry-run', action='store_true', help="Affiche ce qui serait poussé, n'écrit rien dans Zabbix")
    parser.add_argument('--yes', action='store_true', help='Confirme une exécution réelle (ignoré en --dry-run)')
    args = parser.parse_args()

    # --- Fusion config.json + arguments CLI (la CLI est prioritaire) -------
    config = {}
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        if any(getattr(args, f) is None for f in CONFIG_FIELDS if f != 'sleep'):
            print('Fichier de config "%s" introuvable, et certains paramètres ne sont pas fournis en CLI.' % args.config)
            print('Créez un config.json (voir config.example.json) ou passez tous les paramètres en ligne de commande.')
            sys.exit(1)
    except json.JSONDecodeError as error:
        print('Fichier de config "%s" invalide (JSON mal formé) : %s' % (args.config, error))
        sys.exit(1)

    settings = {}
    for field in CONFIG_FIELDS:
        cli_value = getattr(args, field, None)
        settings[field] = cli_value if cli_value is not None else config.get(field)

    settings.setdefault('item_key', ITEM_KEY)
    if settings.get('sleep') is None:
        settings['sleep'] = 0.2

    missing = [f for f in CONFIG_FIELDS if f != 'sleep' and not settings.get(f)]
    if missing:
        print('Paramètres manquants (ni dans %s, ni en CLI) : %s' % (args.config, ', '.join(missing)))
        sys.exit(1)

    args.ovh_endpoint = settings['ovh_endpoint']
    args.ovh_app_key = settings['ovh_app_key']
    args.ovh_app_secret = settings['ovh_app_secret']
    args.ovh_consumer_key = settings['ovh_consumer_key']
    args.zabbix_url = settings['zabbix_url']
    args.zabbix_token = settings['zabbix_token']
    args.zabbix_host = settings['zabbix_host']
    args.item_key = settings['item_key']
    args.sleep = settings['sleep']

    print('== Backfill facturation OVH -> Zabbix ==')
    print('Server Zabbix : %s' % args.zabbix_url)
    print('Host Zabbix : %s' % args.zabbix_host)
    print('Item        : %s' % args.item_key)
    print('Période     : %d derniers mois complets (hors mois en cours)' % args.months)
    print()

    zbx = ZabbixClient(args.zabbix_url, args.zabbix_token)

    # --- Garde-fou : refuse de continuer si l'item n'est pas en Trapper ----
    item = zbx.get_item(args.zabbix_host, args.item_key)
    if int(item['type']) != TRAPPER_ITEM_TYPE:
        print('ERREUR : l\'item "%s" sur "%s" n\'est pas de type Trapper (type actuel = %s).' %
              (args.item_key, args.zabbix_host, item['type']))
        print('Basculez-le en Trapper dans Zabbix avant de relancer ce script.')
        sys.exit(1)

    history_period = item.get('history', '')
    print('Item trouvé (itemid=%s), History storage period = %r' % (item['itemid'], history_period))
    print('-> Vérifiez manuellement que cette rétention couvre bien %d mois avant de continuer.' % args.months)
    print()

    if not args.dry_run and not args.yes:
        print('Ajoutez --yes pour confirmer une exécution réelle (ou --dry-run pour un aperçu).')
        sys.exit(1)

    ovh_client = make_ovh_client(args.ovh_endpoint, args.ovh_app_key, args.ovh_app_secret, args.ovh_consumer_key)

    periods = months_back(args.months)
    print('Mois à traiter (du plus ancien au plus récent) : %s' %
          ', '.join('%04d-%02d' % p for p in periods))
    print()

    for year, month in periods:
        data, period_end = fetch_billing_for_month(ovh_client, year, month)
        clock = int(period_end.timestamp())
        value = json.dumps(data, ensure_ascii=False)

        status = 'OK' if data['errors'] == '' else 'ERREURS PARTIELLES'
        print('[%04d-%02d] total=%.2f %s | %d service(s) | clock=%s | %s' % (
            year, month, data['total'], data['meta']['currency'],
            len(data['services']), clock, status
        ))
        if data['errors']:
            print('    ' + data['errors'].replace('\n', '\n    '))

        if args.dry_run:
            print('    [dry-run] valeur non envoyée.')
        else:
            result = zbx.history_push(args.zabbix_host, args.item_key, value, clock)
            print('    -> history.push : %s' % result)

        time.sleep(args.sleep)

    print()
    print('Terminé.' if not args.dry_run else 'Terminé (dry-run, rien n\'a été écrit).')
    print()
    print('Prochaine étape : vérifiez Monitoring -> Latest data (graphique sur 24 mois),')
    print('puis rebasculez l\'item "%s" de Trapper vers Script.' % args.item_key)


if __name__ == '__main__':
    main()
