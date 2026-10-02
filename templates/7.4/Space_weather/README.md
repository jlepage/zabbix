# NOAA Space Weather Kp by HTTP

## Overview

This template monitors geomagnetic activity using the **planetary Kp index** published by the NOAA Space Weather Prediction Center (SWPC). It raises alerts when the storm level on the NOAA **G-scale** (G1 to G5) goes above configurable thresholds.

It uses a single HTTP agent item. No Zabbix agent, external script or interface is required.

Data source: https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json

Typical use cases:

- Correlating GNSS/GPS degradation, HF radio outages or satellite link issues with geomagnetic storms.
- Early warning for teams operating power grids, long pipelines, aviation or satellite services.
- Aurora alerts for the curious.

## Requirements

- Zabbix **7.4** or newer. The template uses the 7.4 export format. It can be adapted to 7.0 by changing the `version` field, since no 7.4-specific feature is used.
- Outbound HTTPS access from the Zabbix server or proxy to `services.swpc.noaa.gov`.

## Setup

1. Import `Noaa_Space_Weather.yaml` via **Data collection → Templates → Import**.
2. Create a host, for example `NOAA SWPC`. No interface is needed.
3. Link the template **NOAA Space Weather Kp by HTTP** to this host.
4. Optionally, override the macros at host level (see below).
5. Check **Monitoring → Latest data**. Values should appear within one polling interval.

If the master item becomes *Not supported*, the error message from the preprocessing script explains the reason (empty response, invalid Kp value, invalid timestamp, etc.).

## How it works

The template follows the **master item → dependent items** pattern.

1. The master item `noaa.kp.summary` fetches the full JSON (about 60 records, one per 3-hour interval).
2. A JavaScript preprocessing step:
   - normalizes the payload (see [Format compatibility](#format-compatibility));
   - keeps the latest record;
   - computes the maximum Kp over the last 24 hours (last 8 intervals);
   - converts Kp to the NOAA G-scale;
   - computes the age of the latest measurement.
3. It outputs a compact JSON document, for example:

```json
{
  "time_tag": "2026-09-29T00:00:00",
  "time_ts": 1790640000,
  "data_age": 5400,
  "kp": 2,
  "kp_max_24h": 4.67,
  "g_scale": 0,
  "g_scale_max_24h": 1,
  "a_running": 7,
  "station_count": 8
}
```

4. Dependent items extract each field with a simple JSONPath.

This design makes one HTTP request per interval, keeps all items consistent with each other, and keeps the business logic in a single place.

### Kp to G-scale conversion

The G-scale is computed as `round(Kp) - 4`, bounded to the range 0 to 5. This follows the NOAA convention, where a Kp integer bin includes its minus and plus values. For example, 5- (4.67), 5o (5.00) and 5+ (5.33) all map to G1.

| Kp | G-scale | NOAA level |
|---|---|---|
| < 5 | G0 | Quiet to active |
| 5 | G1 | Minor |
| 6 | G2 | Moderate |
| 7 | G3 | Strong |
| 8 | G4 | Severe |
| 9 | G5 | Extreme |

### Format compatibility

NOAA has changed this product's format in the past. The script supports both known formats:

- **Current format**: an array of objects with numeric values.
- **Legacy format**: an array of arrays whose first row is a header, with values as strings.

## Macros

| Macro | Default | Description |
|---|---|---|
| `{$NOAA.KP.URL}` | `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json` | URL of the NOAA Kp JSON product. |
| `{$NOAA.INTERVAL}` | `15m` | Polling interval. |
| `{$NOAA.NODATA}` | `1h` | Time without data before the availability trigger fires. |
| `{$NOAA.DATA.MAXAGE}` | `21600` | Maximum age of the latest measurement, in seconds (6 hours). |
| `{$NOAA.G.WARN}` | `1` | G-scale threshold for the Warning trigger (G1, Kp 5). |
| `{$NOAA.G.HIGH}` | `3` | G-scale threshold for the High trigger (G3, Kp 7). |
| `{$NOAA.G.DISASTER}` | `4` | G-scale threshold for the Disaster trigger (G4, Kp 8). |

## Items

| Name | Key | Type | Units | Description |
|---|---|---|---|---|
| NOAA: Kp - données brutes (résumé) | `noaa.kp.summary` | HTTP agent (text) | | Master item. Normalized summary of the NOAA feed. |
| NOAA: Indice Kp | `noaa.kp.current` | Dependent (float) | | Latest planetary Kp index (0 to 9, in steps of 1/3). |
| NOAA: Indice Kp max 24h | `noaa.kp.max24h` | Dependent (float) | | Highest Kp over the last 24 hours. |
| NOAA: Échelle G (tempête géomagnétique) | `noaa.kp.gscale` | Dependent (integer) | | Current NOAA G-scale level, with value mapping. |
| NOAA: Échelle G max 24h | `noaa.kp.gscale.max24h` | Dependent (integer) | | Highest G-scale level over the last 24 hours. |
| NOAA: Indice A (running) | `noaa.kp.a_running` | Dependent (integer) | | Planetary a-index, the linear equivalent of Kp. |
| NOAA: Nombre de stations | `noaa.kp.station_count` | Dependent (integer) | | Number of magnetometers used (8 means a complete measurement). |
| NOAA: Horodatage de la dernière mesure | `noaa.kp.timestamp` | Dependent (integer) | unixtime | Start of the 3-hour UTC interval of the latest value. |
| NOAA: Âge des données | `noaa.kp.data_age` | Dependent (integer) | s | Time elapsed since the start of the latest interval. |

Item and trigger names are in French in the template. Keys, macros and tags are in English.

## Triggers

| Name | Expression (simplified) | Severity | Depends on |
|---|---|---|---|
| NOAA: Tempête géomagnétique en cours | `last(noaa.kp.gscale) >= {$NOAA.G.WARN}` | Warning | Strong storm |
| NOAA: Tempête géomagnétique forte | `last(noaa.kp.gscale) >= {$NOAA.G.HIGH}` | High | Severe/extreme storm |
| NOAA: Tempête géomagnétique sévère/extrême | `last(noaa.kp.gscale) >= {$NOAA.G.DISASTER}` | Disaster | |
| NOAA: Données Kp périmées | `last(noaa.kp.data_age) > {$NOAA.DATA.MAXAGE}` | Warning | No data from API |
| NOAA: Aucune donnée reçue de l'API | `nodata(noaa.kp.summary, {$NOAA.NODATA}) = 1` | Average | |

The storm triggers are chained with dependencies, so only the highest active level raises a problem. The current Kp value is shown as operational data on each storm trigger.

## Value mapping

**NOAA G-scale**: `0` → G0 (calme), `1` → G1 (mineure), `2` → G2 (modérée), `3` → G3 (forte), `4` → G4 (sévère), `5` → G5 (extrême).

## Graphs

- **NOAA: Indice Kp**: current Kp and 24-hour maximum, on a fixed 0 to 9 scale.
- **NOAA: Indice A**: running a-index.

## Tags

- Template level: `class: service`, `target: noaa-swpc`.
- Item level: `component: raw`, `geomagnetic` or `quality`.
- Trigger level: `scope: notice` (storms) or `scope: availability` (data source).

## Notes and tuning

- **Polling interval.** Kp is published every 3 hours, with provisional values updated in between. Polling more often than every 15 minutes adds load without adding information.
- **Data age.** `time_tag` marks the *start* of a 3-hour UTC interval, so an age of 2 to 3 hours is normal. This is why the default threshold is 6 hours.
- **Alert noise.** G1 storms are fairly common, especially near solar maximum. Set `{$NOAA.G.WARN}` to `2` if Warning alerts are too frequent.
- **Provisional values.** The latest Kp value can be revised when NOAA publishes the final value for an interval. A storm trigger may therefore occasionally fire and then resolve shortly after.

## Possible extensions

- **Kp forecast**: add a second master item on `noaa-planetary-k-index-forecast.json` to anticipate storms.
- **Real-time solar wind**: the `solar-wind/plasma-*.json` and `solar-wind/mag-*.json` products provide density, speed and Bz. A sustained negative Bz is a good early indicator of a geomagnetic storm.

## References

- NOAA Space Weather Scales: https://www.swpc.noaa.gov/noaa-scales-explanation
- Planetary K-index: https://www.swpc.noaa.gov/products/planetary-k-index
- NOAA SWPC data products: https://services.swpc.noaa.gov/
- Zabbix dependent items: https://www.zabbix.com/documentation/current/en/manual/config/items/itemtypes/dependent_items
- Zabbix JavaScript preprocessing: https://www.zabbix.com/documentation/current/en/manual/config/items/preprocessing/javascript


## Copyrights

.

Copyrights [jLepage - Zabbix Certified Trainer](https://formation.jlepage.fr/formation/zabbix/formations-zabbix-l-outil-opensource-de-monitoring) / [jLepage blog](https://www.jlepage.blog)
