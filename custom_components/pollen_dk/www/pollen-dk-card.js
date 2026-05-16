// Pollen DK Card — custom Lovelace card for the pollen_dk integration

const REGION_NAMES = {
  koebenhavn: "København (Østdanmark)",
  viborg: "Viborg (Vestdanmark)",
};

const POLLEN_TYPE_ORDER = [
  "Birk", "Bynke", "El", "Elm", "Græs", "Hassel", "Alternaria", "Cladosporium",
];

const POLLEN_TYPE_KEYS = {
  Birk: "birk",
  Bynke: "bynke",
  El: "el",
  Elm: "elm",
  Græs: "graes",
  Hassel: "hassel",
  Alternaria: "alternaria",
  Cladosporium: "cladosporium",
};

const SEVERITY_COLORS = {
  none: "#E0E0E0",
  low: "#8BC34A",
  moderate: "#FFD600",
  high: "#FF9800",
  very_high: "#F44336",
  unknown: "#BDBDBD",
};

const TRANSLATIONS = {
  da: {
    default_title: "Pollenprognose",
    today: "I dag",
    weekdays: ["Søn", "Man", "Tir", "Ons", "Tor", "Fre", "Lør"],
    severity: {
      none: "Ingen",
      low: "Lav",
      moderate: "Moderat",
      high: "Høj",
      very_high: "Meget høj",
      unknown: "Ukendt",
    },
    no_data: (region) =>
      `Ingen pollendata fundet for ${region}.<br>Kontroller at integrationen er sat op.`,
    editor: {
      title: "Titel",
      region: "Region",
      days: "Antal dage vist (inkl. i dag)",
      pollen_types: "Pollentyper (tom = alle)",
      regions: {
        koebenhavn: "København (Østdanmark)",
        viborg: "Viborg (Vestdanmark)",
      },
      pollen_names: {
        birk: "Birk",
        bynke: "Bynke",
        el: "El",
        elm: "Elm",
        graes: "Græs",
        hassel: "Hassel",
        alternaria: "Alternaria",
        cladosporium: "Cladosporium",
      },
    },
  },
  en: {
    default_title: "Pollen Forecast",
    today: "Today",
    weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    severity: {
      none: "None",
      low: "Low",
      moderate: "Moderate",
      high: "High",
      very_high: "Very high",
      unknown: "Unknown",
    },
    no_data: (region) =>
      `No pollen data found for ${region}.<br>Check that the integration is configured correctly.`,
    editor: {
      title: "Title",
      region: "Region",
      days: "Days to show (incl. today)",
      pollen_types: "Pollen types (empty = all)",
      regions: {
        koebenhavn: "Copenhagen (East Denmark)",
        viborg: "Viborg (West Denmark)",
      },
      pollen_names: {
        birk: "Birch",
        bynke: "Mugwort",
        el: "Alder",
        elm: "Elm",
        graes: "Grass",
        hassel: "Hazel",
        alternaria: "Alternaria",
        cladosporium: "Cladosporium",
      },
    },
  },
};

const POLLEN_MDI_ICONS = {
  Birk: "mdi:tree",
  Bynke: "mdi:grass",
  El: "mdi:tree-outline",
  Elm: "mdi:tree",
  Græs: "mdi:grass",
  Hassel: "mdi:leaf",
  Alternaria: "mdi:mushroom",
  Cladosporium: "mdi:mushroom-outline",
};

function buildEditorSchema(lang) {
  const tr = (TRANSLATIONS[lang] ?? TRANSLATIONS.en).editor;
  return [
    {
      name: "title",
      label: tr.title,
      selector: { text: {} },
    },
    {
      name: "region",
      label: tr.region,
      required: true,
      selector: {
        select: {
          options: Object.entries(tr.regions).map(([value, label]) => ({ value, label })),
        },
      },
    },
    {
      name: "days",
      label: tr.days,
      selector: { number: { min: 1, max: 5, mode: "slider", step: 1 } },
    },
    {
      name: "pollen_types",
      label: tr.pollen_types,
      selector: {
        select: {
          multiple: true,
          options: Object.entries(tr.pollen_names).map(([value, label]) => ({ value, label })),
        },
      },
    },
  ];
}

// ============================================================
// EDITOR
// ============================================================

class PollenDkCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._form = null;
  }

  set hass(hass) {
    const langChanged = hass?.language !== this._hass?.language;
    this._hass = hass;
    if (langChanged) {
      this._render();
    } else if (this._form) {
      this._form.hass = hass;
    }
  }

  setConfig(config) {
    this._config = {
      title: "",
      days: 5,
      pollen_types: [],
      ...config,
    };
    this._render();
  }

  _render() {
    const form = document.createElement("ha-form");
    form.hass = this._hass;
    form.data = this._config;
    form.schema = buildEditorSchema(this._hass?.language || "en");
    form.computeLabel = (schema) => schema.label || schema.name;
    form.addEventListener("value-changed", (e) => {
      this._config = e.detail.value;
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        })
      );
    });
    this._form = form;
    this.shadowRoot.innerHTML = "";
    this.shadowRoot.appendChild(form);
  }
}

// ============================================================
// CARD
// ============================================================

const DOT_COL_W = 48; // px per day column

class PollenDkCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = null;
    this._visibleDays = 5;
    this._resizeObserver = null;
  }

  static getConfigElement() {
    return document.createElement("pollen-dk-card-editor");
  }

  static getStubConfig() {
    return { region: "koebenhavn", title: "", days: 5 };
  }

  setConfig(config) {
    if (!config.region) throw new Error("'region' er påkrævet i kortets konfiguration");
    this._config = { title: "", days: 5, pollen_types: [], ...config };
    this._updateVisibleDays();
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 3 + this._getSensors().length;
  }

  getLayoutOptions() {
    const n = this._getSensors().length;
    return {
      grid_rows: 2 + Math.max(n, 1),
      grid_columns: 4,
      grid_min_rows: 3,
      grid_min_columns: 2,
    };
  }

  connectedCallback() {
    this._resizeObserver = new ResizeObserver(() => {
      const prev = this._visibleDays;
      this._updateVisibleDays();
      if (this._visibleDays !== prev) this._render();
    });
    this._resizeObserver.observe(this);
  }

  disconnectedCallback() {
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
  }

  _updateVisibleDays() {
    const max = this._config?.days ?? 5;
    const w = this.offsetWidth || 500;
    let days = max;
    if (w < 274) days = Math.min(max, 1);
    else if (w < 322) days = Math.min(max, 2);
    else if (w < 370) days = Math.min(max, 3);
    else if (w < 420) days = Math.min(max, 4);
    this._visibleDays = days;
  }

  _getSensors() {
    if (!this._hass || !this._config) return [];
    const regionName = REGION_NAMES[this._config.region];
    if (!regionName) return [];

    const filterKeys = this._config.pollen_types;
    const hasFilter = Array.isArray(filterKeys) && filterKeys.length > 0;

    return Object.values(this._hass.states)
      .filter((s) => {
        if (!s.attributes.pollen_type_da) return false;
        if (s.attributes.region !== regionName) return false;
        const sev = s.attributes.severity;
        if (!sev || sev === "none" || sev === "unknown") return false;
        if (hasFilter) {
          const key = POLLEN_TYPE_KEYS[s.attributes.pollen_type_da];
          if (!filterKeys.includes(key)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const ai = POLLEN_TYPE_ORDER.indexOf(a.attributes.pollen_type_da);
        const bi = POLLEN_TYPE_ORDER.indexOf(b.attributes.pollen_type_da);
        return ai - bi;
      });
  }

  _t() {
    const lang = this._hass?.language || "en";
    return TRANSLATIONS[lang] ?? TRANSLATIONS.en;
  }

  _getForecastDates(sensors) {
    const todayStr = new Date().toISOString().split("T")[0];
    const all = new Set();
    for (const s of sensors) {
      for (const d of Object.keys(s.attributes.forecast || {})) {
        if (d > todayStr) all.add(d);
      }
    }
    return Array.from(all)
      .sort()
      .slice(0, this._visibleDays - 1);
  }

  _getDayLabel(dateStr) {
    return this._t().weekdays[new Date(dateStr + "T12:00:00").getDay()];
  }

  _dot(severity, tooltip) {
    const color = SEVERITY_COLORS[severity] || SEVERITY_COLORS.unknown;
    const label = this._t().severity[severity] || severity;
    return `<span class="dot" style="background:${color}" title="${tooltip}: ${label}"></span>`;
  }

  _render() {
    if (!this._config) return;

    const sensors = this._getSensors();
    const forecastDates = sensors.length ? this._getForecastDates(sensors) : [];
    const dayCount = Math.min(this._visibleDays, 1 + forecastDates.length);

    const css = `
      :host { display: block; }
      ha-card { padding: 16px; box-sizing: border-box; }
      .card-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--primary-text-color);
        margin-bottom: 14px;
      }
      .header-row {
        display: flex;
        align-items: flex-end;
        padding: 0 14px 6px;
      }
      .header-label { flex: 1; }
      .header-days { display: flex; }
      .header-day {
        width: ${DOT_COL_W}px;
        text-align: center;
        font-size: 0.82rem;
        font-weight: 500;
        color: var(--secondary-text-color);
      }
      .rows { display: flex; flex-direction: column; gap: 6px; }
      .pollen-row {
        display: flex;
        align-items: center;
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.04);
        border-radius: 12px;
        padding: 10px 14px;
        min-height: 48px;
      }
      .pollen-label {
        flex: 1;
        min-width: 0;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.95rem;
        font-weight: 500;
        color: var(--primary-text-color);
      }
      .pollen-label ha-icon {
        --mdc-icon-size: 22px;
        color: var(--secondary-text-color);
        flex-shrink: 0;
      }
      .pollen-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .dot-cells { display: flex; }
      .dot-cell {
        width: ${DOT_COL_W}px;
        display: flex;
        justify-content: center;
        align-items: center;
      }
      .dot {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
        cursor: default;
      }
      .no-data {
        text-align: center;
        color: var(--secondary-text-color);
        font-size: 0.9rem;
        padding: 12px 2px;
      }
    `;

    const t = this._t();
    const dayLabels = [
      t.today,
      ...forecastDates.map((d) => this._getDayLabel(d)),
    ].slice(0, dayCount);

    const headerHtml = dayLabels
      .map((l) => `<div class="header-day">${l}</div>`)
      .join("");

    let rowsHtml;
    if (!sensors.length) {
      const regionLabel = REGION_NAMES[this._config.region] || this._config.region;
      rowsHtml = `<div class="no-data">${t.no_data(regionLabel)}</div>`;
    } else {
      rowsHtml = sensors
        .map((s) => {
          const nameDa = s.attributes.pollen_type_da;
          const name =
            t === TRANSLATIONS.da
              ? nameDa
              : s.attributes.pollen_type_en || nameDa;
          const icon = POLLEN_MDI_ICONS[nameDa] || "mdi:flower-pollen";
          const forecast = s.attributes.forecast || {};
          const dots = [
            this._dot(s.attributes.severity || "unknown", "I dag"),
            ...forecastDates.map((d) =>
              this._dot(forecast[d] || "unknown", this._getDayLabel(d))
            ),
          ]
            .slice(0, dayCount)
            .map((d) => `<div class="dot-cell">${d}</div>`)
            .join("");

          return `
            <div class="pollen-row">
              <div class="pollen-label">
                <ha-icon icon="${icon}"></ha-icon>
                <span class="pollen-name">${name}</span>
              </div>
              <div class="dot-cells">${dots}</div>
            </div>`;
        })
        .join("");
    }

    this.shadowRoot.innerHTML = `
      <style>${css}</style>
      <ha-card>
        <div class="card-title">${this._config.title || t.default_title}</div>
        <div class="header-row">
          <div class="header-label"></div>
          <div class="header-days">${headerHtml}</div>
        </div>
        <div class="rows">${rowsHtml}</div>
      </ha-card>`;
  }
}

customElements.define("pollen-dk-card-editor", PollenDkCardEditor);
customElements.define("pollen-dk-card", PollenDkCard);

window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "pollen-dk-card")) {
  window.customCards.push({
    type: "pollen-dk-card",
    name: "Pollen DK",
    description: "Viser pollenprognose fra Astma-Allergi Danmark",
    preview: true,
    documentationURL: "https://github.com/briis/pollen_dk",
  });
}
