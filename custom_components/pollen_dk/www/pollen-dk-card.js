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
  high: "#F44336",
  very_high: "#9C27B0",
  unknown: "#BDBDBD",
};

// Upper bounds (inclusive) for low / moderate / high per pollen type
const POLLEN_THRESHOLDS = {
  birk: [30, 100, 200],
  bynke: [10, 50, 100],
  el: [10, 50, 100],
  elm: [10, 50, 100],
  graes: [10, 50, 100],
  hassel: [5, 15, 30],
  alternaria: [20, 100, 500],
  cladosporium: [2000, 6000, 10000],
};

const GAUGE_PCT = { none: 0, low: 0.2, moderate: 0.5, high: 0.75, very_high: 1.0, unknown: 0 };

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
    popup: {
      low: "Lavt",
      moderate: "Moderat",
      high: "Højt",
      under: "Under",
      between: "Mellem",
      over: "Over",
      pollen: "pollen",
      measured: (date, region) => `Målt d. ${date} — ${region}`,
    },
    descriptions: {
      birk: "Mængden af birkepollen i luften topper typisk i slut april.",
      bynke: "Bynkepollen er i sæson fra juli til september.",
      el: "Elpollen spredes tidligt på foråret, typisk i marts–april.",
      elm: "Elmpollen spredes om foråret, typisk i april–maj.",
      graes: "Græspollen er i sæson fra maj til august.",
      hassel: "Hasselpollen spredes tidligt, typisk fra januar til marts.",
      alternaria: "Alternaria er en skimmelsvamp med sporer i luften fra juli til oktober.",
      cladosporium: "Cladosporium er den mest udbredte skimmelsvamp og findes i luften fra april til november.",
    },
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
    popup: {
      low: "Low",
      moderate: "Moderate",
      high: "High",
      under: "Under",
      between: "Between",
      over: "Over",
      pollen: "pollen",
      measured: (date, region) => `Measured on ${date} — ${region}`,
    },
    descriptions: {
      birk: "Birch pollen levels typically peak in late April.",
      bynke: "Mugwort pollen is in season from July to September.",
      el: "Alder pollen spreads early in spring, typically March–April.",
      elm: "Elm pollen spreads in spring, typically April–May.",
      graes: "Grass pollen is in season from May to August.",
      hassel: "Hazel pollen spreads early, typically from January to March.",
      alternaria: "Alternaria is a mold with spores in the air from July to October.",
      cladosporium: "Cladosporium is the most widespread mold and is found in the air from April to November.",
    },
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
    this._closePopup();
  }

  _buildGauge(severity) {
    const pct = GAUGE_PCT[severity] ?? 0;
    const color = SEVERITY_COLORS[severity] || SEVERITY_COLORS.unknown;
    const r = 80, cx = 100, cy = 100;
    const bg = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
    let fill = "";
    if (pct > 0) {
      const a = Math.PI * (1 - pct);
      const ex = (cx + r * Math.cos(a)).toFixed(2);
      const ey = (cy - r * Math.sin(a)).toFixed(2);
      fill = `<path d="M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${ex} ${ey}"
        fill="none" stroke="${color}" stroke-width="14" stroke-linecap="round"/>`;
    }
    return `<svg viewBox="0 0 200 108" xmlns="http://www.w3.org/2000/svg">
      <path d="${bg}" fill="none" stroke="rgba(0,0,0,0.1)" stroke-width="14" stroke-linecap="round"/>
      ${fill}
    </svg>`;
  }

  _formatDate(lastUpdate) {
    if (!lastUpdate || !/^\d{2}-\d{2}-\d{4}$/.test(lastUpdate)) return lastUpdate;
    const [d, m, y] = lastUpdate.split("-").map(Number);
    return new Date(y, m - 1, d).toLocaleDateString(
      this._hass?.language === "da" ? "da-DK" : "en-US",
      { day: "numeric", month: "long" }
    );
  }

  _showPopup(sensor) {
    if (!sensor) return;
    this._closePopup();

    const t = this._t();
    const nameDa = sensor.attributes.pollen_type_da;
    const pollenKey = POLLEN_TYPE_KEYS[nameDa];
    const name = t === TRANSLATIONS.da ? nameDa : (sensor.attributes.pollen_type_en || nameDa);
    const icon = POLLEN_MDI_ICONS[nameDa] || "mdi:flower-pollen";
    const severity = sensor.attributes.severity || "unknown";
    const count = sensor.state;
    const region = sensor.attributes.region || "";
    const date = this._formatDate(sensor.attributes.last_update || "");

    const severityLabel = t.severity[severity] || severity;
    const description = t.descriptions?.[pollenKey] || "";
    const [tLow, tMod] = POLLEN_THRESHOLDS[pollenKey] || [10, 50];
    const p = t.popup;

    const thresholdsHtml = `
      <div class="pd-trow"><b>${p.low}:</b> ${p.under} ${tLow} ${p.pollen}</div>
      <div class="pd-trow"><b>${p.moderate}:</b> ${p.between} ${tLow}–${tMod} ${p.pollen}</div>
      <div class="pd-trow"><b>${p.high}:</b> ${p.over} ${tMod} ${p.pollen}</div>`;

    const el = document.createElement("div");
    el.style.cssText =
      "position:fixed;inset:0;z-index:9999;display:flex;align-items:center;" +
      "justify-content:center;background:rgba(0,0,0,0.45);padding:12px;box-sizing:border-box";

    el.innerHTML = `
      <style>
        .pd-card {
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #212121);
          border-radius: 24px;
          width: 100%; max-width: 480px;
          padding: 24px 24px 28px;
          box-shadow: 0 8px 40px rgba(0,0,0,0.25);
          max-height: 92vh; overflow-y: auto; box-sizing: border-box;
          position: relative;
        }
        .pd-head { display:flex; align-items:center; gap:12px; margin-bottom:20px; }
        .pd-head ha-icon { --mdc-icon-size:26px; color:var(--secondary-text-color,#757575); }
        .pd-head-name { font-size:1.05rem; font-weight:600; }
        .pd-close {
          position:absolute; top:18px; right:18px;
          width:30px; height:30px; border-radius:50%;
          border:none; cursor:pointer; font-size:16px;
          display:flex; align-items:center; justify-content:center;
          background:rgba(var(--rgb-primary-text-color,0,0,0),0.08);
          color:var(--secondary-text-color,#757575);
        }
        .pd-gauge { display:flex; flex-direction:column; align-items:center; }
        .pd-gauge svg { width:180px; }
        .pd-count { font-size:2.4rem; font-weight:700; margin-top:-16px; line-height:1; }
        .pd-sev { color:var(--secondary-text-color,#757575); font-size:0.95rem; margin:4px 0 18px; }
        .pd-desc { font-size:0.88rem; color:var(--secondary-text-color,#757575); line-height:1.55; margin-bottom:14px; }
        .pd-trow { font-size:0.9rem; margin-bottom:5px; }
        .pd-divider { border:none; border-top:1px solid var(--divider-color,rgba(0,0,0,0.12)); margin:14px 0; }
        .pd-footer { font-size:0.8rem; color:var(--disabled-text-color,#9e9e9e); }
      </style>
      <div class="pd-card">
        <div class="pd-head">
          <ha-icon icon="${icon}"></ha-icon>
          <span class="pd-head-name">${name}</span>
        </div>
        <button class="pd-close">✕</button>
        <div class="pd-gauge">
          ${this._buildGauge(severity)}
          <div class="pd-count">${count}</div>
        </div>
        <div class="pd-sev">${severityLabel}</div>
        ${description ? `<div class="pd-desc">${description}</div>` : ""}
        <div>${thresholdsHtml}</div>
        <hr class="pd-divider">
        <div class="pd-footer">${p.measured(date, region)}</div>
      </div>`;

    el.addEventListener("click", (e) => { if (e.target === el) this._closePopup(); });
    el.querySelector(".pd-close").addEventListener("click", () => this._closePopup());
    this._escHandler = (e) => { if (e.key === "Escape") this._closePopup(); };
    document.addEventListener("keydown", this._escHandler);

    document.body.appendChild(el);
    this._popupEl = el;
  }

  _closePopup() {
    this._popupEl?.remove();
    this._popupEl = null;
    if (this._escHandler) {
      document.removeEventListener("keydown", this._escHandler);
      this._escHandler = null;
    }
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
        cursor: pointer;
      }
      .pollen-row:hover {
        background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.08);
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
            this._dot(s.attributes.severity || "unknown", t.today),
            ...forecastDates.map((d) =>
              this._dot(forecast[d] || "unknown", this._getDayLabel(d))
            ),
          ]
            .slice(0, dayCount)
            .map((d) => `<div class="dot-cell">${d}</div>`)
            .join("");

          return `
            <div class="pollen-row" data-entity-id="${s.entity_id}">
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

    this.shadowRoot.querySelector(".rows")?.addEventListener("click", (e) => {
      const row = e.target.closest("[data-entity-id]");
      if (row) this._showPopup(this._hass.states[row.dataset.entityId]);
    });
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
