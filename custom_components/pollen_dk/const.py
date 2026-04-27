"""Constants for the Pollen DK integration."""

DOMAIN = "pollen_dk"
CONF_REGION = "region"
DEFAULT_SCAN_INTERVAL = 3600  # 1 hour — data updates once daily around 16:00 CET

ATTRIBUTION = "Data leveret af Astma-Allergi Danmark (astma-allergi.dk)"

REGION_KOEBENHAVN = "koebenhavn"
REGION_VIBORG = "viborg"
REGION_BOTH = "begge"

REGIONS = {
    REGION_KOEBENHAVN: "København (Østdanmark)",
    REGION_VIBORG: "Viborg (Vestdanmark)",
    REGION_BOTH: "Begge regioner",
}

POLLEN_TYPES = {
    "birk": "Birk",
    "bynke": "Bynke",
    "el": "El",
    "elm": "Elm",
    "graes": "Græs",
    "hassel": "Hassel",
    "alternaria": "Alternaria",
    "cladosporium": "Cladosporium",
}

POLLEN_ICONS = {
    "birk": "mdi:tree",
    "bynke": "mdi:grass",
    "el": "mdi:tree-outline",
    "elm": "mdi:tree",
    "graes": "mdi:grass",
    "hassel": "mdi:leaf",
    "alternaria": "mdi:mushroom",
    "cladosporium": "mdi:mushroom-outline",
}

SEVERITY_ICONS = {
    "ingen": "mdi:flower-pollen-outline",
    "lav": "mdi:flower-pollen",
    "moderat": "mdi:flower-pollen",
    "høj": "mdi:alert",
    "meget høj": "mdi:alert-circle",
    "ukendt": "mdi:help-circle-outline",
}
