# Pollen DK - Home Assistant Integration

Home Assistant custom integration that fetches **live pollen data** for Denmark from **Astma-Allergi Danmarks** official JSON feed.

> **Data source:** `https://www.astma-allergi.dk/umbraco/Api/PollenApi/GetPollenFeed`
> This is the same backend used by Astma-Allergi Danmarks own app and website — not a scraper.

> **Disclaimer:** This integration is an independent community project and is not affiliated with, endorsed by, or in any way connected to Astma-Allergi Danmark.

---

## Features

- **No scraping** — uses the official JSON API endpoint
- **Two measurement stations**: København (Østdanmark) and Viborg (Vestdanmark)
- **8 pollen/spore types**: Birk, Bynke, El, Elm, Græs, Hassel, Alternaria, Cladosporium
- **Raw count sensors** (pollen/m³) with severity attribute for each type
- **Overall severity sensor** per region (worst level across all types)
- **5-day forecast** — per-allergen daily counts and worst-severity summary per day
- UI config flow — no YAML required
- Updates every hour (data itself refreshes once daily ~16:00 CET)

---

## Sensors created

For each configured region you get:

| Entity | Description |
|---|---|
| `sensor.pollen_dk_birk_REGION` | Birch pollen count (pollen/m³) |
| `sensor.pollen_dk_bynke_REGION` | Mugwort pollen count |
| `sensor.pollen_dk_el_REGION` | Alder pollen count |
| `sensor.pollen_dk_elm_REGION` | Elm pollen count |
| `sensor.pollen_dk_graes_REGION` | Grass pollen count |
| `sensor.pollen_dk_hassel_REGION` | Hazel pollen count |
| `sensor.pollen_dk_alternaria_REGION` | Alternaria mold spore count |
| `sensor.pollen_dk_cladosporium_REGION` | Cladosporium mold spore count |
| `sensor.pollen_dk_pollenvarsel_REGION` | Overall worst severity level |

Each count sensor includes the following **attributes**:
- `severity` — `none` / `low` / `moderate` / `high` / `very_high` / `unknown`
- `pollen_type_da` — Danish name
- `pollen_type_en` — English name
- `last_update` — Date of last measurement
- `region` — Station name
- `forecast` — dict of upcoming dates → predicted pollen count (e.g. `{"28-04-2026": 2, "29-04-2026": 5, ...}`). Out-of-season types have an empty dict.

The **overall severity sensor** includes:
- `pollen_levels` — dict of all in-season types with count + severity
- `forecast` — dict of upcoming dates → worst severity across all allergens (e.g. `{"28-04-2026": "low", "29-04-2026": "moderate", ...}`)
- `last_update`

---

## Installation

### Via HACS (recommended)

1. In HACS → Integrations → ⋮ menu → **Custom repositories**
2. Add `https://github.com/briis/pollen_dk` as type **Integration**
3. Install **Pollen DK**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/pollen_dk` folder to your HA `custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. **Settings → Devices & Services → Add Integration**
2. Search for **Pollen DK**
3. Choose region: `København`, `Viborg`, or **Begge** (creates sensors for both)
4. Done — sensors appear immediately

---

## Notes

- **Outside pollen season** sensors show `0` instead of unknown, and their `forecast` attribute is an empty dict.
- Data is published once daily around **16:00 CET**. The integration polls hourly so you'll see the new values within an hour of publication.
- Astma-Allergi Danmark is a non-profit organisation. Please consider supporting them at [astma-allergi.dk](https://www.astma-allergi.dk/).

---

## Attribution

All pollen data is © **Astma-Allergi Danmark**. This integration is for personal, non-commercial use only, in accordance with Astma-Allergi Danmarks terms.
