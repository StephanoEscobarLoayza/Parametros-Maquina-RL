"""
═══════════════════════════════════════════════════════════════════════════
  MOTOR INDUSTRIAL · PLATAFORMA DE MONITOREO DE RIESGO OPERACIONAL
  ───────────────────────────────────────────────────────────────────────
  Streamlit + Supabase + Plotly
  4 variables de control · clasificación de riesgo en 4 niveles
═══════════════════════════════════════════════════════════════════════════

  EJECUTAR
  --------
  1) pip install streamlit supabase pandas plotly
  2) Crear  .streamlit/secrets.toml :
         SUPABASE_URL   = "https://TU-PROYECTO.supabase.co"
         SUPABASE_KEY   = "TU_ANON_KEY"
         SUPABASE_TABLE = "motor_sensor_data"
  3) streamlit run main.py

  Si Supabase no está configurado, usa el CSV local como respaldo
  (coloca 'industrial_motor_sensor_data_8000csv.csv' junto a main.py).
═══════════════════════════════════════════════════════════════════════════
"""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ═════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Motor Industrial · Monitoreo de Riesgo",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

C = {
    "bg": "#0e1117", "bg2": "#161b26", "bg3": "#1e2535",
    "border": "#2a3347", "border2": "#374162",
    "text": "#e8ecf4", "text2": "#8b96b0", "text3": "#5a6480",
    "green": "#22d3a0", "yellow": "#f5c842", "orange": "#f07c3a", "red": "#f04f55",
    "blue": "#5b8def",
}

LEVELS = {
    "normal":   {"label": "Normal",         "color": C["green"]},
    "low":      {"label": "Riesgo bajo",     "color": C["yellow"]},
    "moderate": {"label": "Riesgo moderado", "color": C["orange"]},
    "high":     {"label": "Riesgo alto",     "color": C["red"]},
}
ORDER = ["normal", "low", "moderate", "high"]
RANK = {"normal": 0, "low": 1, "moderate": 2, "high": 3}

# Umbrales operacionales (idénticos a la tabla de referencia)
THRESHOLDS = {
    "temperature": {"icon": "🌡️", "name": "Temperatura", "unit": "°C",
                    "normal": (30, 60), "scale": (0, 130), "step": 0.5},
    "vibration":   {"icon": "📳", "name": "Vibración", "unit": "mm/s",
                    "normal": (0, 5), "scale": (0, 35), "step": 0.1},
    "voltage":     {"icon": "⚡", "name": "Voltaje", "unit": "V",
                    "normal": (380, 420), "scale": (200, 480), "step": 1.0},
    "current":     {"icon": "🔌", "name": "Corriente", "unit": "A",
                    "normal": (10, 20), "scale": (0, 50), "step": 0.1},
}

# Nombre de la empresa / marca
BRAND = "INDUSTRIAL MOTOR"
BRAND_SUB = "MONITOREO DE RIESGO"


def emblem(px):
    """Emblema vectorial (analizador de motores) · nítido a cualquier tamaño."""
    g, nn = C["green"], C["text3"]
    return (
        f"<svg viewBox='0 0 40 40' style='width:{px}px;height:{px}px' aria-hidden='true'>"
        f"<rect x='9' y='8' width='22' height='16' rx='2.5' fill='none' stroke='{g}' stroke-width='2'/>"
        f"<path d='M12 17 L14 17 L14 13 L16 13 L16 20 L18 20 L18 15 L20 15 L20 18 L22 18 L22 12 "
        f"L24 12 L24 19 L26 19 L26 16 L28 16' fill='none' stroke='{g}' stroke-width='1.6' "
        f"stroke-linejoin='round' stroke-linecap='round'/>"
        f"<line x1='15' y1='28' x2='25' y2='28' stroke='{g}' stroke-width='2' stroke-linecap='round'/>"
        f"<line x1='20' y1='24' x2='20' y2='28' stroke='{g}' stroke-width='2'/>"
        f"<line x1='13' y1='32' x2='27' y2='32' stroke='{nn}' stroke-width='2' stroke-linecap='round'/>"
        f"</svg>"
    )


# ═════════════════════════════════════════════════════════════════════════
#  MOTOR DE CLASIFICACIÓN
# ═════════════════════════════════════════════════════════════════════════
def classify(param, value):
    if param == "temperature":
        if 30 <= value <= 60: return "normal"
        if 60 < value <= 70:  return "low"
        if 70 < value <= 90:  return "moderate"
        return "high"
    if param == "vibration":
        if 0 <= value <= 5:  return "normal"
        if 5 < value <= 10:  return "low"
        if 10 < value <= 20: return "moderate"
        return "high"
    if param == "voltage":
        if 380 <= value <= 420: return "normal"
        if 360 <= value < 380:  return "low"
        if 340 <= value < 360:  return "moderate"
        return "high"
    if param == "current":
        if 10 <= value <= 20: return "normal"
        if 5 <= value < 10:   return "low"
        if 20 < value <= 35:  return "moderate"
        return "high"
    return "normal"


def diagnose(values: dict):
    """Devuelve (veredicto, acción, detalle_por_parámetro)."""
    detail = {p: classify(p, v) for p, v in values.items()}
    levels = list(detail.values())
    n_bad = sum(1 for l in levels if RANK[l] >= 2)
    worst = max(levels, key=lambda x: RANK[x])
    if n_bad >= 2:
        verdict, action = "high", "DETENER EQUIPO PARA INSPECCIÓN"
    else:
        verdict = worst
        action = {
            "normal": "OPERACIÓN SEGURA · sin acción requerida",
            "low": "VIGILAR · monitorear con mayor frecuencia",
            "moderate": "INSPECCIONAR · programar mantenimiento",
            "high": "DETENER EQUIPO · intervención inmediata",
        }[worst]
    return verdict, action, detail


def make_gauge(param, value, level):
    """Gauge tipo tablero para un parámetro (reutilizado por diagnóstico e inspector)."""
    cfg = THRESHOLDS[param]
    lo, hi = cfg["scale"]
    n_lo, n_hi = cfg["normal"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(font=dict(family="Space Mono", size=22, color=C["text"]),
                    suffix=f" {cfg['unit']}"),
        gauge=dict(
            axis=dict(range=[lo, hi], tickfont=dict(size=8, color=C["text3"]), tickcolor=C["border"]),
            bar=dict(color=LEVELS[level]["color"], thickness=0.28),
            bordercolor=C["border"], borderwidth=1, bgcolor=C["bg3"],
            steps=[
                dict(range=[lo, n_lo], color="rgba(240,79,85,0.12)"),
                dict(range=[n_lo, n_hi], color="rgba(34,211,160,0.15)"),
                dict(range=[n_hi, hi], color="rgba(240,124,58,0.12)"),
            ],
            threshold=dict(line=dict(color=LEVELS[level]["color"], width=3),
                           thickness=0.85, value=value),
        ),
    ))
    fig.update_layout(height=170, paper_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=15, r=15, t=10, b=5),
                      font=dict(family="DM Sans", color=C["text2"]))
    return fig


@st.cache_data(ttl=300, show_spinner=False)
def enrich(df):
    """Añade la clasificación del sistema por parámetro y el veredicto global de cada registro."""
    out = df.copy()
    params = [p for p in THRESHOLDS if p in out.columns]
    for p in params:
        out[f"lvl_{p}"] = out[p].apply(lambda v: classify(p, v))

    def row_verdict(r):
        levels = [r[f"lvl_{p}"] for p in params]
        n_bad = sum(1 for l in levels if RANK[l] >= 2)
        worst = max(levels, key=lambda x: RANK[x])
        return "high" if n_bad >= 2 else worst

    out["sys_verdict"] = out.apply(row_verdict, axis=1)
    return out


# ═════════════════════════════════════════════════════════════════════════
#  DATOS
# ═════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    loaded_at = datetime.now()
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        table = st.secrets.get("SUPABASE_TABLE", "motor_sensor_data")
        from supabase import create_client
        client = create_client(url, key)
        rows, start, page = [], 0, 1000
        while True:
            resp = client.table(table).select("*").range(start, start + page - 1).execute()
            batch = resp.data or []
            rows.extend(batch)
            if len(batch) < page:
                break
            start += page
        df = pd.DataFrame(rows)
        if not df.empty:
            return normalize(df), "supabase", loaded_at
    except Exception:
        pass
    try:
        return normalize(pd.read_csv("industrial_motor_sensor_data_8000csv.csv")), "csv", loaded_at
    except Exception:
        return pd.DataFrame(), "none", loaded_at


def normalize(df):
    rename = {}
    for col in df.columns:
        low = col.strip().lower()
        if "volt" in low: rename[col] = "voltage"
        elif "curr" in low or "amp" in low: rename[col] = "current"
        elif "temp" in low: rename[col] = "temperature"
        elif "vibr" in low: rename[col] = "vibration"
        elif "label" in low or "nivel" in low or "risk" in low: rename[col] = "label"
    df = df.rename(columns=rename)
    for c in ["voltage", "current", "temperature", "vibration"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "label" in df.columns:
        df["label"] = df["label"].astype(str).str.strip().str.lower()
    keep = [c for c in ["voltage", "current", "temperature", "vibration"] if c in df.columns]
    return df.dropna(subset=keep)


# ═════════════════════════════════════════════════════════════════════════
#  CSS
# ═════════════════════════════════════════════════════════════════════════
def inject_css():
    st.markdown(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');
      .stApp {{ background:{C['bg']}; }}
      [data-testid="stHeader"] {{ background:transparent; }}
      .block-container {{ padding:1.2rem 2.5rem 3rem; max-width:1280px; }}
      #MainMenu, footer {{ visibility:hidden; }}
      html, body, [class*="css"], p, span, div {{ font-family:'DM Sans',sans-serif; color:{C['text']}; }}

      /* Sidebar */
      [data-testid="stSidebar"] {{ background:{C['bg2']}; border-right:1px solid {C['border']};
        width:285px !important; min-width:285px !important; max-width:285px !important; }}
      [data-testid="stSidebar"] * {{ color:{C['text']}; }}
      /* impedir que el usuario arrastre/redimensione la barra */
      [data-testid="stSidebarResizeHandle"],
      [data-testid="stSidebarResizer"] {{ display:none !important; pointer-events:none !important; }}

      /* Topbar */
      .topbar {{
        display:flex;align-items:center;gap:16px;
        border-bottom:1px solid {C['border']};padding:4px 0 20px;margin-bottom:24px;
      }}
      .tb-icon {{ width:46px;height:46px;border-radius:11px;flex-shrink:0;
        background:rgba(34,211,160,0.08);border:1px solid rgba(34,211,160,0.25);
        display:flex;align-items:center;justify-content:center;font-size:23px; }}
      .tb-title {{ font-family:'Space Mono',monospace;font-size:20px;font-weight:700;letter-spacing:-.3px; }}
      .tb-sub {{ font-size:12px;color:{C['text2']};margin-top:3px;font-family:'Space Mono',monospace;letter-spacing:.3px; }}
      .tb-right {{ margin-left:auto;text-align:right;font-family:'Space Mono',monospace;font-size:11px;color:{C['text3']}; }}
      .live-dot {{ display:inline-block;width:8px;height:8px;border-radius:50%;background:{C['green']};
        margin-right:6px;box-shadow:0 0 0 0 rgba(34,211,160,.6);animation:pulse 2s infinite; }}
      @keyframes pulse {{ 0%{{box-shadow:0 0 0 0 rgba(34,211,160,.5)}} 70%{{box-shadow:0 0 0 7px rgba(34,211,160,0)}} 100%{{box-shadow:0 0 0 0 rgba(34,211,160,0)}} }}

      .seclabel {{ font-size:11px;font-family:'Space Mono',monospace;color:{C['text3']};
        letter-spacing:1.5px;text-transform:uppercase;margin:30px 0 16px;
        display:flex;align-items:center;gap:12px; }}
      .seclabel::after {{ content:'';flex:1;height:1px;background:{C['border']}; }}

      /* KPI / cards */
      .kpi {{ background:{C['bg2']};border:1px solid {C['border']};border-radius:12px;
        padding:16px 18px;position:relative;overflow:hidden;height:100%; }}
      .kpi::before {{ content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--ac,{C['green']}); }}
      .kpi-lbl {{ font-size:10.5px;color:{C['text2']};font-family:'Space Mono',monospace;
        letter-spacing:.5px;text-transform:uppercase;margin-bottom:8px; }}
      .kpi-val {{ font-size:27px;font-weight:600;font-family:'Space Mono',monospace;line-height:1; }}
      .kpi-unit {{ font-size:13px;color:{C['text2']};font-weight:400;margin-left:3px; }}
      .kpi-sub {{ font-size:11px;color:{C['text3']};font-family:'Space Mono',monospace;margin-top:8px; }}

      .stat-card {{ background:{C['bg2']};border:1px solid {C['border']};border-radius:12px;
        padding:18px 20px;position:relative;overflow:hidden;height:100%;transition:border-color .2s; }}
      .stat-card:hover {{ border-color:{C['border2']}; }}
      .stat-card::before {{ content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--ac); }}
      .sc-icon {{ font-size:20px;margin-bottom:10px; }}
      .sc-label {{ font-size:11px;color:{C['text2']};font-family:'Space Mono',monospace;
        letter-spacing:.5px;text-transform:uppercase;margin-bottom:6px; }}
      .sc-value {{ font-size:26px;font-weight:600;font-family:'Space Mono',monospace; }}
      .sc-unit {{ font-size:13px;color:{C['text2']};font-weight:400;margin-left:3px; }}
      .sc-badge {{ display:inline-block;margin-top:10px;font-size:10px;font-family:'Space Mono',monospace;
        padding:2px 8px;border-radius:4px;letter-spacing:.5px;
        background:rgba(34,211,160,0.08);color:{C['green']};border:1px solid rgba(34,211,160,0.25); }}

      .chip {{ display:inline-block;padding:3px 10px;border-radius:5px;font-size:11px;
        font-family:'Space Mono',monospace;font-weight:700;white-space:nowrap; }}
      .lp-normal{{background:rgba(34,211,160,0.08);color:{C['green']};border:1px solid rgba(34,211,160,0.25);}}
      .lp-low{{background:rgba(245,200,66,0.08);color:{C['yellow']};border:1px solid rgba(245,200,66,0.25);}}
      .lp-moderate{{background:rgba(240,124,58,0.08);color:{C['orange']};border:1px solid rgba(240,124,58,0.25);}}
      .lp-high{{background:rgba(240,79,85,0.08);color:{C['red']};border:1px solid rgba(240,79,85,0.3);}}

      .reftable {{ width:100%;border-collapse:collapse;background:{C['bg2']};
        border:1px solid {C['border']};border-radius:12px;overflow:hidden; }}
      .reftable th {{ padding:11px 16px;font-size:11px;font-family:'Space Mono',monospace;
        text-transform:uppercase;letter-spacing:.8px;color:{C['text3']};
        border-bottom:1px solid {C['border']};background:{C['bg3']};text-align:left; }}
      .reftable td {{ padding:12px 16px;border-bottom:1px solid {C['border']};font-size:13px;vertical-align:middle; }}
      .reftable tr:last-child td {{ border-bottom:none; }}
      .reftable tr:hover td {{ background:rgba(255,255,255,0.02); }}
      .pname {{ font-weight:600;font-family:'Space Mono',monospace;font-size:12px; }}
      .punit {{ font-size:10px;color:{C['text3']};margin-top:2px; }}
      .reftable code {{ background:{C['bg3']};padding:2px 7px;border-radius:4px;font-size:12px;color:{C['text']}; }}

      .alert-card {{ border:1px solid rgba(240,79,85,0.3);border-radius:12px;
        background:rgba(240,79,85,0.08);padding:16px 18px;position:relative;overflow:hidden;height:100%; }}
      .alert-card::before {{ content:'';position:absolute;left:0;top:0;bottom:0;width:3px;background:{C['red']}; }}
      .alert-icon {{ font-size:18px;margin-bottom:8px; }}
      .alert-title {{ font-size:12px;font-weight:600;color:{C['red']};font-family:'Space Mono',monospace;margin-bottom:6px; }}
      .alert-value {{ font-size:18px;font-family:'Space Mono',monospace;font-weight:700;color:{C['red']};margin:8px 0; }}
      .alert-desc {{ font-size:12px;color:{C['text2']};line-height:1.5; }}

      .success-box {{ border:1px solid rgba(34,211,160,0.25);border-radius:12px;
        background:rgba(34,211,160,0.08);padding:20px 24px;display:flex;gap:16px;align-items:flex-start; }}
      .success-icon {{ font-size:24px;flex-shrink:0;margin-top:2px; }}
      .success-title {{ font-size:13px;font-weight:600;color:{C['green']};font-family:'Space Mono',monospace;margin-bottom:6px; }}
      .success-text {{ font-size:13px;color:#a0c4b4;line-height:1.6; }}
      .success-text strong {{ color:{C['green']}; }}

      /* Veredicto del diagnóstico */
      .verdict {{ border-radius:14px;padding:24px 28px;border:1px solid var(--vc);
        background:var(--vbg);display:flex;align-items:center;gap:22px;margin-bottom:26px; }}
      .verdict-big {{ font-size:30px;flex-shrink:0; }}
      .verdict-title {{ font-family:'Space Mono',monospace;font-size:20px;font-weight:700;color:var(--vc);letter-spacing:-.3px;line-height:1.2; }}
      .verdict-action {{ font-size:13px;color:{C['text2']};margin-top:6px;font-family:'Space Mono',monospace;line-height:1.5; }}

      .param-status {{ display:flex;justify-content:space-between;align-items:center;
        background:{C['bg2']};border:1px solid {C['border']};border-radius:10px;
        padding:12px 16px;margin-bottom:8px; }}
      .ps-name {{ font-family:'Space Mono',monospace;font-size:13px; }}
      .ps-val {{ font-family:'Space Mono',monospace;font-size:13px;color:{C['text2']}; }}

      .legend {{ display:flex;flex-wrap:wrap;gap:18px;margin-bottom:6px; }}
      .leg {{ display:flex;align-items:center;gap:6px;font-size:11px;font-family:'Space Mono',monospace;color:{C['text2']}; }}
      .leg-dot {{ width:10px;height:10px;border-radius:3px;flex-shrink:0; }}

      .stTabs [data-baseweb="tab-list"] {{ gap:4px;border-bottom:1px solid {C['border']}; }}
      .stTabs [data-baseweb="tab"] {{ font-family:'Space Mono',monospace;font-size:12px;
        letter-spacing:.5px;color:{C['text2']};background:transparent;padding:8px 16px; }}
      .stTabs [aria-selected="true"] {{ color:{C['green']}; }}

      /* ── SIDEBAR · navegación tipo menú ── */
      /* ocultar el botón de colapsar/ocultar la barra */
      [data-testid="stSidebarCollapseButton"],
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="collapsedControl"] {{ display:none !important; }}

      [data-testid="stSidebar"] [role="radiogroup"] {{ gap:5px; }}
      [data-testid="stSidebar"] [role="radiogroup"] > label {{
        padding:10px 13px;border-radius:8px;margin:0;cursor:pointer;width:100%;
        background:transparent;border:1px solid {C['border']};
        transition:background .15s,border-color .15s; min-height:unset;
      }}
      [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{
        background:rgba(34,211,160,0.05);border-color:{C['border2']};
      }}
      /* oculta el círculo del radio */
      [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display:none !important; }}
      [data-testid="stSidebar"] [role="radiogroup"] > label p {{
        font-family:'Space Mono',monospace !important;font-size:12px !important;
        font-weight:400;color:{C['text2']} !important;line-height:1.4 !important;
      }}
      /* opción seleccionada (navegadores con :has → Chrome/Edge modernos) */
      [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{
        background:rgba(34,211,160,0.10);border-color:rgba(34,211,160,0.45);
      }}
      [data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {{
        color:{C['green']} !important;font-weight:700;
      }}

      /* ── SELECTORES / MULTISELECT / INPUTS (refuerzo del tema) ── */
      [data-baseweb="select"] > div {{
        background:{C['bg3']} !important;border:1px solid {C['border']} !important;
        border-radius:9px !important;color:{C['text']} !important;
      }}
      [data-baseweb="select"] svg {{ color:{C['text2']} !important; }}
      /* ── DROPDOWN ABIERTO · forzar fondo oscuro en todo el menú ── */
      [data-baseweb="popover"], [data-baseweb="popover"] > div,
      [data-baseweb="menu"], [data-baseweb="menu"] ul,
      [data-baseweb="popover"] [role="listbox"] {{
        background-color:{C['bg2']} !important; border-color:{C['border2']} !important;
      }}
      [data-baseweb="popover"] [role="option"],
      [data-baseweb="menu"] li {{
        background-color:{C['bg2']} !important; color:{C['text']} !important;
        font-family:'DM Sans',sans-serif !important;
      }}
      [data-baseweb="popover"] [role="option"]:hover,
      [data-baseweb="menu"] li:hover,
      [data-baseweb="popover"] [role="option"][aria-selected="true"],
      [data-baseweb="menu"] li[aria-selected="true"] {{
        background-color:{C['bg3']} !important; color:{C['green']} !important;
      }}
      /* chips del multiselect */
      [data-baseweb="tag"] {{
        background:rgba(34,211,160,0.12) !important;border:1px solid rgba(34,211,160,0.3) !important;
        color:{C['green']} !important;font-family:'Space Mono',monospace !important;
      }}
      [data-baseweb="tag"] svg {{ fill:{C['green']} !important; }}
      .stTextInput input, .stNumberInput input {{
        background:{C['bg3']} !important;color:{C['text']} !important;
        border:1px solid {C['border']} !important;
      }}
      label, .stSelectbox label, .stMultiSelect label, .stSlider label {{
        color:{C['text2']} !important;font-family:'Space Mono',monospace !important;
        font-size:12px !important;letter-spacing:.3px;
      }}

      /* ── DATAFRAME en oscuro ── */
      [data-testid="stDataFrame"] {{ border:1px solid {C['border']};border-radius:10px;overflow:hidden; }}

      /* ── BOTÓN actualizar / descargar ── */
      .stButton button, .stDownloadButton button {{
        background:{C['bg3']} !important;color:{C['text']} !important;
        border:1px solid {C['border2']} !important;border-radius:9px !important;
        font-family:'Space Mono',monospace !important;font-size:12px !important;
      }}
      .stButton button:hover, .stDownloadButton button:hover {{
        border-color:{C['green']} !important;color:{C['green']} !important;
      }}
    </style>
    """, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
#  PLOTLY · TEMA
# ═════════════════════════════════════════════════════════════════════════
def style_fig(fig, height=340, legend=True):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans, sans-serif", color=C["text2"], size=12),
        margin=dict(l=10, r=10, t=46, b=10),
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12, color=C["text"], family="Space Mono"),
                    orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                    itemsizing="constant"),
        hoverlabel=dict(bgcolor=C["bg3"], font_size=12, font_family="Space Mono"),
    )
    fig.update_xaxes(gridcolor=C["border"], zerolinecolor=C["border"],
                     linecolor=C["border"], tickfont=dict(size=10, color=C["text2"]),
                     title_font=dict(size=11, color=C["text2"], family="Space Mono"))
    fig.update_yaxes(gridcolor=C["border"], zerolinecolor=C["border"],
                     linecolor=C["border"], tickfont=dict(size=10, color=C["text2"]),
                     title_font=dict(size=11, color=C["text2"], family="Space Mono"))
    return fig


def mean_by_level(df, col, lvl):
    sub = df[df["label"] == lvl][col] if "label" in df else pd.Series(dtype=float)
    return sub.mean() if len(sub) else float("nan")


def section(num, title):
    st.markdown(f'<div class="seclabel">{num} · {title}</div>', unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
#  VISTAS
# ═════════════════════════════════════════════════════════════════════════
def view_overview(df):
    n = len(df)
    has_label = "label" in df.columns

    # ── KPIs ──
    section("", "Indicadores generales")
    pct_norm = (df["label"] == "normal").mean() * 100 if has_label else float("nan")
    pct_crit = (df["label"] == "high").mean() * 100 if has_label else float("nan")
    avg_temp = df["temperature"].mean() if "temperature" in df else float("nan")

    kpis = [
        ("Registros totales", f"{n:,}", "", "muestras analizadas", C["blue"]),
        ("Operación normal", f"{pct_norm:.0f}", "%", "dentro de zona segura", C["green"]),
        ("Riesgo alto", f"{pct_crit:.0f}", "%", "requieren intervención", C["red"]),
        ("Temp. promedio", f"{avg_temp:.1f}", "°C", "todas las muestras", C["orange"]),
    ]
    cols = st.columns(4)
    for col, (lbl, val, unit, sub, ac) in zip(cols, kpis):
        col.markdown(f"""<div class="kpi" style="--ac:{ac}">
          <div class="kpi-lbl">{lbl}</div>
          <div class="kpi-val">{val}<span class="kpi-unit">{unit}</span></div>
          <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

    # ── Zona segura ──
    section("01", "Rango de operación segura (zona normal)")
    safe = [("🌡️", "Temperatura", "30–60", "°C", C["green"]),
            ("📳", "Vibración", "0–5", "mm/s", C["yellow"]),
            ("⚡", "Voltaje", "380–420", "V", C["orange"]),
            ("🔌", "Corriente", "10–20", "A", C["red"])]
    cols = st.columns(4)
    for col, (ic, lbl, val, unit, ac) in zip(cols, safe):
        col.markdown(f"""<div class="stat-card" style="--ac:{ac}">
          <div class="sc-icon">{ic}</div><div class="sc-label">{lbl}</div>
          <div class="sc-value">{val}<span class="sc-unit">{unit}</span></div>
          <span class="sc-badge">✓ ZONA SEGURA</span></div>""", unsafe_allow_html=True)

    # ── Distribución (donut) + barras estado ──
    section("02", "Distribución de la flota por nivel de riesgo")
    c1, c2 = st.columns([1, 1.3])
    if has_label:
        counts = df["label"].value_counts().reindex(ORDER).fillna(0)
        fig = go.Figure(go.Pie(
            labels=[LEVELS[l]["label"] for l in ORDER],
            values=[counts[l] for l in ORDER],
            hole=.62,
            marker=dict(colors=[LEVELS[l]["color"] for l in ORDER],
                        line=dict(color=C["bg"], width=2)),
            textinfo="percent", textfont=dict(family="Space Mono", size=12, color=C["bg"]),
            sort=False,
        ))
        fig.add_annotation(text=f"<b>{n:,}</b><br>registros", showarrow=False,
                           font=dict(family="Space Mono", size=15, color=C["text"]))
        c1.plotly_chart(style_fig(fig, 320), use_container_width=True)

    # Conteo por nivel como barras horizontales
    if has_label:
        counts = df["label"].value_counts().reindex(ORDER).fillna(0)
        fig2 = go.Figure(go.Bar(
            y=[LEVELS[l]["label"] for l in ORDER][::-1],
            x=[counts[l] for l in ORDER][::-1],
            orientation="h",
            marker=dict(color=[LEVELS[l]["color"] for l in ORDER][::-1]),
            text=[f"{int(counts[l]):,}" for l in ORDER][::-1],
            textposition="outside",
            textfont=dict(family="Space Mono", size=11),
        ))
        c2.plotly_chart(style_fig(fig2, 320, legend=False), use_container_width=True)


def view_live_diagnostic(df):
    section("", "Diagnóstico en vivo · clasificación de riesgo")
    st.markdown(f"<p style='color:{C['text2']};font-size:13px;margin-top:-8px'>"
                "Ingresa la lectura actual de los 4 sensores. El sistema clasifica cada parámetro "
                "y emite un veredicto operacional según las reglas establecidas.</p>",
                unsafe_allow_html=True)

    # Inputs
    cols = st.columns(4)
    values = {}
    defaults = {"temperature": 45.0, "vibration": 2.5, "voltage": 400.0, "current": 15.0}
    for col, (param, cfg) in zip(cols, THRESHOLDS.items()):
        lo, hi = cfg["scale"]
        values[param] = col.slider(
            f"{cfg['icon']} {cfg['name']} ({cfg['unit']})",
            min_value=float(lo), max_value=float(hi),
            value=float(defaults[param]), step=float(cfg["step"]),
        )

    verdict, action, detail = diagnose(values)
    vcolor = LEVELS[verdict]["color"]
    vrgba = {"normal": "rgba(34,211,160,0.08)", "low": "rgba(245,200,66,0.08)",
             "moderate": "rgba(240,124,58,0.08)", "high": "rgba(240,79,85,0.08)"}[verdict]
    vicon = {"normal": "✅", "low": "👁️", "moderate": "🔧", "high": "🛑"}[verdict]

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(f"""<div class="verdict" style="--vc:{vcolor};--vbg:{vrgba}">
      <div class="verdict-big">{vicon}</div>
      <div><div class="verdict-title">{LEVELS[verdict]['label'].upper()}</div>
      <div class="verdict-action">{action}</div></div></div>""", unsafe_allow_html=True)

    # Gauges
    section("", "Lecturas por parámetro")
    gcols = st.columns(4)
    for col, (param, cfg) in zip(gcols, THRESHOLDS.items()):
        lvl = detail[param]
        col.markdown(f"<div style='text-align:center;font-family:Space Mono;font-size:11px;"
                     f"color:{C['text2']};text-transform:uppercase;letter-spacing:.5px'>"
                     f"{cfg['icon']} {cfg['name']}</div>", unsafe_allow_html=True)
        col.plotly_chart(make_gauge(param, values[param], lvl), use_container_width=True)
        col.markdown(f"<div style='text-align:center;margin-top:-6px'>"
                     f"<span class='chip lp-{lvl}'>{LEVELS[lvl]['label']}</span></div>",
                     unsafe_allow_html=True)


def view_analytics(df):
    if "label" not in df.columns:
        st.info("No hay columna de nivel ('label') para el análisis comparativo.")
        return

    # ── Distribución por nivel (box) ──
    section("", "Distribución de cada variable por nivel de riesgo")
    param = st.selectbox(
        "Variable a analizar",
        list(THRESHOLDS.keys()),
        format_func=lambda p: f"{THRESHOLDS[p]['icon']} {THRESHOLDS[p]['name']} ({THRESHOLDS[p]['unit']})",
    )
    unit = THRESHOLDS[param]["unit"]
    fig = go.Figure()
    for lvl in ORDER:
        sub = df[df["label"] == lvl][param]
        # Resumen limpio en una sola línea (en vez del tooltip verboso por defecto)
        summary = (f"<b>{LEVELS[lvl]['label']}</b><br>"
                   f"Mediana: {sub.median():.1f} {unit}<br>"
                   f"Rango: {sub.min():.1f} – {sub.max():.1f} {unit}<br>"
                   f"Promedio: {sub.mean():.1f} {unit}")
        fig.add_trace(go.Box(
            y=sub, name=LEVELS[lvl]["label"],
            marker_color=LEVELS[lvl]["color"], line=dict(width=1.5),
            boxpoints=False, hoveron="boxes",
            hovertemplate=summary + "<extra></extra>",
        ))
    fig.update_yaxes(title=f"{THRESHOLDS[param]['name']} ({unit})")
    st.plotly_chart(style_fig(fig, 380), use_container_width=True)
    st.markdown(
        f"<p style='font-family:Space Mono,monospace;font-size:11px;color:{C['text3']};margin-top:-8px'>"
        "Lectura: la línea central es la mediana · la caja abarca el 50% central de los datos · "
        "los bigotes marcan mínimo y máximo.</p>", unsafe_allow_html=True)

    # ── Medias por nivel (barras) ──
    section("", "Valores promedio por nivel")
    c1, c2 = st.columns(2)
    for i, (param, cfg) in enumerate(THRESHOLDS.items()):
        means = [mean_by_level(df, param, l) for l in ORDER]
        fig = go.Figure(go.Bar(
            x=[LEVELS[l]["label"] for l in ORDER], y=means,
            marker=dict(color=[LEVELS[l]["color"] for l in ORDER]),
            text=[f"{m:.1f}" for m in means], textposition="outside",
            textfont=dict(family="Space Mono", size=11),
        ))
        fig.update_layout(title=dict(text=f"{cfg['icon']} {cfg['name']} ({cfg['unit']})",
                                     font=dict(family="Space Mono", size=12, color=C["text2"]), x=0.02))
        (c1 if i % 2 == 0 else c2).plotly_chart(style_fig(fig, 300, legend=False),
                                                use_container_width=True)

    # ── Dispersión bivariada ──
    section("", "Correlación entre variables")
    c1, c2 = st.columns(2)
    xparam = c1.selectbox("Eje X", list(THRESHOLDS.keys()), index=0,
                          format_func=lambda p: THRESHOLDS[p]["name"], key="xp")
    yparam = c2.selectbox("Eje Y", list(THRESHOLDS.keys()), index=2,
                          format_func=lambda p: THRESHOLDS[p]["name"], key="yp")
    fig = go.Figure()
    sample = df.sample(min(2000, len(df)), random_state=1)
    for lvl in ORDER:
        sub = sample[sample["label"] == lvl]
        fig.add_trace(go.Scatter(
            x=sub[xparam], y=sub[yparam], mode="markers",
            name=LEVELS[lvl]["label"],
            marker=dict(color=LEVELS[lvl]["color"], size=5, opacity=0.55,
                        line=dict(width=0)),
        ))
    fig.update_xaxes(title=THRESHOLDS[xparam]["name"])
    fig.update_yaxes(title=THRESHOLDS[yparam]["name"])
    st.plotly_chart(style_fig(fig, 420), use_container_width=True)


def view_reference(df):
    t_norm = mean_by_level(df, "temperature", "normal")
    t_high = mean_by_level(df, "temperature", "high")
    v_norm = mean_by_level(df, "vibration", "normal")
    v_high = mean_by_level(df, "vibration", "high")
    c_norm = mean_by_level(df, "current", "normal")
    volt_norm = mean_by_level(df, "voltage", "normal")

    section("03", "Tabla de referencia operacional")
    st.markdown(f"""
    <table class="reftable"><thead><tr>
      <th>Parámetro</th><th><span class="chip lp-normal">Normal</span></th>
      <th><span class="chip lp-low">Riesgo bajo</span></th>
      <th><span class="chip lp-moderate">Riesgo moderado</span></th>
      <th><span class="chip lp-high">Riesgo alto</span></th>
    </tr></thead><tbody>
      <tr><td><div class="pname">🌡️ Temperatura</div><div class="punit">°C · Media normal: {t_norm:.1f}°C</div></td>
        <td><code>30 – 60</code></td><td><code>60 – 70</code></td><td><code>70 – 90</code></td>
        <td><code>&gt; 90</code> <span style="color:{C['red']};font-size:10px">(media: {t_high:.1f}°C)</span></td></tr>
      <tr><td><div class="pname">📳 Vibración</div><div class="punit">mm/s · Media normal: {v_norm:.1f} mm/s</div></td>
        <td><code>0 – 5</code></td><td><code>5 – 10</code></td><td><code>10 – 20</code></td>
        <td><code>&gt; 20</code> <span style="color:{C['red']};font-size:10px">(media: {v_high:.0f} mm/s)</span></td></tr>
      <tr><td><div class="pname">⚡ Voltaje</div><div class="punit">V · Media normal: {volt_norm:.0f} V</div></td>
        <td><code>380 – 420</code></td><td><code>360 – 380</code></td><td><code>340 – 360</code></td>
        <td><code>&lt; 340 o &gt; 420</code></td></tr>
      <tr><td><div class="pname">🔌 Corriente</div><div class="punit">A · Media normal: {c_norm:.1f} A</div></td>
        <td><code>10 – 20</code></td><td><code>5 – 10</code></td><td><code>20 – 35</code></td>
        <td><code>&lt; 5 o &gt; 35</code></td></tr>
    </tbody></table>""", unsafe_allow_html=True)

    section("04", "Alertas críticas — actuar de inmediato")
    alerts = [
        ("🌡️", "TEMPERATURA CRÍTICA", "&gt; 90 °C",
         f"El 100% de los registros de falla alta supera los 90°C. Media en falla: <strong>{t_high:.1f}°C</strong>. Detener y enfriar el equipo de inmediato."),
        ("📳", "VIBRACIÓN SEVERA", "&gt; 20 mm/s",
         f"Todos los casos de riesgo alto presentan vibración elevada. Media: <strong>{v_high:.0f} mm/s</strong>. Indica desgaste mecánico o desbalance severo."),
        ("⚡", "VOLTAJE FUERA DE RANGO", "&lt; 340 V o &gt; 420 V",
         "En falla alta el voltaje puede caer hasta 200 V o superar 460 V. Las fluctuaciones extremas dañan el aislamiento del bobinado."),
        ("🔌", "CORRIENTE ANORMAL", "&lt; 5 A o &gt; 35 A",
         "Corriente alta: sobrecarga o cortocircuito. Corriente baja (&lt;5A): pérdida de fase o conexión defectuosa. Requiere inspección inmediata."),
    ]
    cc = st.columns(2)
    for i, (ic, t, v, d) in enumerate(alerts):
        cc[i % 2].markdown(f"""<div class="alert-card" style="margin-bottom:12px">
          <div class="alert-icon">{ic}</div><div class="alert-title">{t}</div>
          <div class="alert-value">{v}</div><div class="alert-desc">{d}</div></div>""",
                           unsafe_allow_html=True)

    section("05", "Regla operacional")
    st.markdown(f"""<div class="success-box"><div class="success-icon">✅</div><div>
      <div class="success-title">CONDICIÓN DE OPERACIÓN SEGURA</div>
      <div class="success-text">El equipo opera con <strong>riesgo mínimo</strong> únicamente cuando
      <strong>los 4 parámetros</strong> están simultáneamente dentro de la zona normal:<br><br>
      <strong>Temperatura 30–60°C &nbsp;·&nbsp; Vibración 0–5 mm/s &nbsp;·&nbsp; Voltaje 380–420 V &nbsp;·&nbsp; Corriente 10–20 A</strong><br><br>
      Si <em>cualquiera</em> de los parámetros supera su límite normal, escalar al nivel correspondiente y registrar
      el evento. Si dos o más parámetros están en riesgo moderado o alto, detener el equipo para inspección.</div>
      </div></div>""", unsafe_allow_html=True)


def view_explorer(df):
    has_label = "label" in df.columns
    rich = enrich(df)
    params = [p for p in THRESHOLDS if p in df.columns]

    # ── FILTROS CON SENTIDO ──
    section("", "Búsqueda y diagnóstico de registros")
    st.markdown(f"<p style='color:{C['text2']};font-size:13px;margin-top:-8px'>"
                "Filtra por una condición operacional concreta, revisa los hallazgos automáticos "
                "y abre cualquier registro para ver <strong>por qué</strong> el sistema lo clasificó así.</p>",
                unsafe_allow_html=True)

    focus_options = {
        "Todos los registros": None,
        "🛑 Solo registros críticos (riesgo alto)": ("verdict_high", None),
        "🌡️ Temperatura fuera de zona segura": ("oob", "temperature"),
        "📳 Vibración fuera de zona segura": ("oob", "vibration"),
        "⚡ Voltaje fuera de zona segura": ("oob", "voltage"),
        "🔌 Corriente fuera de zona segura": ("oob", "current"),
    }
    c1, c2 = st.columns([1.4, 1])
    focus = c1.selectbox("Enfocar la búsqueda en", list(focus_options.keys()))
    sel = ORDER
    if has_label:
        sel = c2.multiselect("Nivel etiquetado", ORDER, default=ORDER,
                             format_func=lambda x: LEVELS[x]["label"])

    view = rich.copy()
    if has_label and sel:
        view = view[view["label"].isin(sel)]
    rule = focus_options[focus]
    if rule and rule[0] == "verdict_high":
        view = view[view["sys_verdict"] == "high"]
    elif rule and rule[0] == "oob":
        p = rule[1]
        view = view[view[f"lvl_{p}"] != "normal"]

    # ── HALLAZGOS AUTOMÁTICOS DE LA SELECCIÓN ──
    if len(view):
        # variable que más empuja el riesgo en la selección
        oob_counts = {p: int((view[f"lvl_{p}"] != "normal").sum()) for p in params}
        driver = max(oob_counts, key=oob_counts.get)
        driver_pct = oob_counts[driver] / len(view) * 100
        crit = int((view["sys_verdict"] == "high").sum())
        dom_level = view["sys_verdict"].mode()[0] if len(view) else "normal"

        cards = [
            ("Registros en la selección", f"{len(view):,}", f"de {len(df):,} totales", C["blue"]),
            ("Veredicto dominante", LEVELS[dom_level]["label"], "según reglas del sistema", LEVELS[dom_level]["color"]),
            ("Variable que más empuja el riesgo", THRESHOLDS[driver]["name"],
             f"fuera de zona en {driver_pct:.0f}% de los casos", THRESHOLDS[driver].get("acc", C["orange"])),
            ("Requieren detención", f"{crit:,}", "veredicto = riesgo alto", C["red"]),
        ]
        cc = st.columns(4)
        for col, (lbl, val, sub, ac) in zip(cc, cards):
            col.markdown(f"""<div class="kpi" style="--ac:{ac}">
              <div class="kpi-lbl">{lbl}</div>
              <div class="kpi-val" style="font-size:20px">{val}</div>
              <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)
    else:
        st.warning("Ningún registro cumple esa combinación de filtros.")
        return

    # ── INSPECTOR DE REGISTRO ──
    section("", "Inspector de registro")
    id_col = "id" if "id" in view.columns else None
    options = view[id_col].tolist() if id_col else list(view.index)
    pick = st.selectbox(
        f"Selecciona un registro ({len(options):,} disponibles)",
        options,
        format_func=lambda x: f"Registro #{x}",
    )
    row = view[view[id_col] == pick].iloc[0] if id_col else view.loc[pick]
    values = {p: float(row[p]) for p in params}
    verdict, action, detail = diagnose(values)

    vcolor = LEVELS[verdict]["color"]
    vrgba = {"normal": "rgba(34,211,160,0.08)", "low": "rgba(245,200,66,0.08)",
             "moderate": "rgba(240,124,58,0.08)", "high": "rgba(240,79,85,0.08)"}[verdict]
    vicon = {"normal": "✅", "low": "👁️", "moderate": "🔧", "high": "🛑"}[verdict]
    label_txt = f" · etiqueta original: {LEVELS.get(row['label'],{}).get('label', row['label'])}" if has_label else ""
    st.markdown(f"""<div class="verdict" style="--vc:{vcolor};--vbg:{vrgba}">
      <div class="verdict-big">{vicon}</div>
      <div><div class="verdict-title">{LEVELS[verdict]['label'].upper()}</div>
      <div class="verdict-action">{action}{label_txt}</div></div></div>""", unsafe_allow_html=True)

    gcols = st.columns(len(params))
    for col, p in zip(gcols, params):
        lvl = detail[p]
        col.markdown(f"<div style='text-align:center;font-family:Space Mono;font-size:11px;"
                     f"color:{C['text2']};text-transform:uppercase;letter-spacing:.5px'>"
                     f"{THRESHOLDS[p]['icon']} {THRESHOLDS[p]['name']}</div>", unsafe_allow_html=True)
        col.plotly_chart(make_gauge(p, values[p], lvl), use_container_width=True)
        col.markdown(f"<div style='text-align:center;margin-top:-6px'>"
                     f"<span class='chip lp-{lvl}'>{LEVELS[lvl]['label']}</span></div>",
                     unsafe_allow_html=True)

    # Explicación textual: qué disparó el riesgo
    out_of_zone = [p for p in params if detail[p] != "normal"]
    if out_of_zone:
        items = " · ".join(f"{THRESHOLDS[p]['name']} ({values[p]:.1f} {THRESHOLDS[p]['unit']} → {LEVELS[detail[p]]['label']})"
                           for p in out_of_zone)
        st.markdown(f"<p style='font-family:Space Mono,monospace;font-size:12px;color:{C['text2']};"
                    f"margin-top:10px'><strong style='color:{vcolor}'>Motivo:</strong> {items}</p>",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='font-family:Space Mono,monospace;font-size:12px;color:{C['green']};"
                    f"margin-top:10px'>Los 4 parámetros están dentro de la zona segura.</p>",
                    unsafe_allow_html=True)

    # ── TABLA DE APOYO + DESCARGA ──
    section("", "Detalle de la selección")
    show_cols = ([id_col] if id_col else []) + params + (["label"] if has_label else []) + ["sys_verdict"]
    table = view[show_cols].rename(columns={
        "voltage": "Voltaje (V)", "current": "Corriente (A)",
        "temperature": "Temp (°C)", "vibration": "Vibración (mm/s)",
        "label": "Etiqueta", "sys_verdict": "Veredicto sistema", "id": "ID",
    })
    st.markdown(f"<p style='font-family:Space Mono,monospace;color:{C['text3']};font-size:11px'>"
                f"Mostrando {len(view):,} registros · la columna «Veredicto sistema» es la clasificación "
                "calculada en vivo por las reglas operacionales.</p>", unsafe_allow_html=True)
    st.dataframe(table, use_container_width=True, height=360, hide_index=True)
    st.download_button("⬇ Descargar selección (CSV)",
                       view[show_cols].to_csv(index=False).encode("utf-8"),
                       "motor_seleccion.csv", "text/csv")


# ═════════════════════════════════════════════════════════════════════════
#  MACHINE LEARNING · Regresión Lineal (Temperatura → Vibración)
# ═════════════════════════════════════════════════════════════════════════
def _sklearn_ok():
    try:
        import sklearn  # noqa: F401
        return True
    except ImportError:
        return False


@st.cache_data(show_spinner=False)
def train_model(df):
    """Regresión Lineal pura: Temperatura (X) → Vibración (Y), sin usar etiquetas."""
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
    import numpy as np

    X = df[["temperature"]].values
    y = df["vibration"].values

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_tr, y_tr)

    pred_tr = model.predict(X_tr)
    pred_te = model.predict(X_te)

    metrics = {
        "r2_train":   r2_score(y_tr, pred_tr),
        "r2_test":    r2_score(y_te, pred_te),
        "mae_train":  mean_absolute_error(y_tr, pred_tr),
        "mae_test":   mean_absolute_error(y_te, pred_te),
        "rmse_train": np.sqrt(mean_squared_error(y_tr, pred_tr)),
        "rmse_test":  np.sqrt(mean_squared_error(y_te, pred_te)),
    }
    residuals = y_te - pred_te
    return model, metrics, residuals, pred_te, y_te, X_te.flatten(), len(X_tr), len(X_te)


def view_ml(df):
    import numpy as np

    section("", "Modelo de Machine Learning · Regresión Lineal")
    if not _sklearn_ok():
        st.warning("Esta sección necesita scikit-learn. Instálalo con:  "
                   "`pip install scikit-learn`  y vuelve a ejecutar la app.")
        return
    if "temperature" not in df.columns or "vibration" not in df.columns:
        st.info("Se necesitan las columnas de temperatura y vibración.")
        return

    st.markdown(
        f"<p style='color:{C['text2']};font-size:13px;margin-top:-8px'>"
        "El modelo usa <strong>Regresión Lineal Simple</strong> entre las dos variables "
        "más correlacionadas del dataset (r = 0.775): "
        "<strong>Temperatura</strong> como variable independiente (X) y "
        "<strong>Vibración</strong> como variable dependiente (Y). "
        "No se usa la etiqueta de riesgo — el modelo aprende solo de los datos numéricos. "
        "Se entrena con el 80% y se evalúa con el 20% restante.</p>",
        unsafe_allow_html=True,
    )

    model, metrics, residuals, pred_te, y_te, X_te, ntr, nte = train_model(df)
    b0   = model.intercept_
    b1   = model.coef_[0]
    sign = "+" if b1 >= 0 else "−"

    # ── Ecuación del modelo ──
    eq_html = (
        f"<div style='background:{C['bg3']};border:1px solid {C['border2']};border-radius:12px;"
        f"padding:20px 28px;margin-bottom:24px;text-align:center'>"
        f"<div style='font-family:Space Mono,monospace;font-size:11px;color:{C['text3']};"
        f"letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px'>Ecuación del modelo</div>"
        f"<div style='font-family:Space Mono,monospace;font-size:22px;font-weight:700;"
        f"color:{C['text']};letter-spacing:.5px'>"
        f"Vibración&nbsp;=&nbsp;"
        f"<span style='color:{C['blue']}'>{b0:.4f}</span>"
        f"&nbsp;{sign}&nbsp;"
        f"<span style='color:{C['orange']}'>{abs(b1):.4f}</span>"
        f"&nbsp;·&nbsp;Temperatura</div>"
        f"<div style='font-family:Space Mono,monospace;font-size:11px;color:{C['text3']};margin-top:12px'>"
        f"β₀ = {b0:.4f} &nbsp;·&nbsp; β₁ = {b1:.4f} &nbsp;·&nbsp; "
        f"Unidades: Vibración en mm/s · Temperatura en °C</div>"
        f"</div>"
    )
    st.markdown(eq_html, unsafe_allow_html=True)

    # ── Métricas train vs test ──
    section("", "Métricas de validación · detección de sobreentrenamiento")
    kpi_data = [
        ("R² Entrenamiento",   f"{metrics['r2_train']:.4f}",   "",     "varianza explicada · train",    C["green"]),
        ("R² Prueba",          f"{metrics['r2_test']:.4f}",    "",     "varianza explicada · test",     C["blue"]),
        ("MAE Entrenamiento",  f"{metrics['mae_train']:.4f}",  "mm/s", "error absoluto medio · train",  C["orange"]),
        ("MAE Prueba",         f"{metrics['mae_test']:.4f}",   "mm/s", "error absoluto medio · test",   C["yellow"]),
        ("RMSE Entrenamiento", f"{metrics['rmse_train']:.4f}", "mm/s", "raíz error cuadrático · train", C["orange"]),
        ("RMSE Prueba",        f"{metrics['rmse_test']:.4f}",  "mm/s", "raíz error cuadrático · test",  C["yellow"]),
    ]
    cc = st.columns(3)
    for i, (lbl, val, unit, sub, ac) in enumerate(kpi_data):
        cc[i % 3].markdown(f"""<div class="kpi" style="--ac:{ac};margin-bottom:14px">
          <div class="kpi-lbl">{lbl}</div>
          <div class="kpi-val">{val}<span class="kpi-unit">{unit}</span></div>
          <div class="kpi-sub">{sub}</div></div>""", unsafe_allow_html=True)

    # ── Sobreentrenamiento ──
    r2_diff = abs(metrics["r2_train"] - metrics["r2_test"])
    if r2_diff < 0.05:
        ovf_color, ovf_icon, ovf_msg = C["green"],  "✅", f"Sin sobreentrenamiento · ΔR² = {r2_diff:.4f} (< 0.05)"
    elif r2_diff < 0.10:
        ovf_color, ovf_icon, ovf_msg = C["yellow"], "⚠️", f"Sobreentrenamiento leve · ΔR² = {r2_diff:.4f} (0.05 – 0.10)"
    else:
        ovf_color, ovf_icon, ovf_msg = C["red"],    "🛑", f"Sobreentrenamiento significativo · ΔR² = {r2_diff:.4f} (> 0.10)"

    st.markdown(
        f"<div style='border:1px solid {ovf_color};border-radius:10px;background:rgba(0,0,0,0.15);"
        f"padding:14px 20px;margin:10px 0 24px;display:flex;align-items:center;gap:14px'>"
        f"<span style='font-size:22px'>{ovf_icon}</span>"
        f"<span style='font-family:Space Mono,monospace;font-size:13px;color:{ovf_color}'>{ovf_msg}</span></div>",
        unsafe_allow_html=True,
    )

    # ── Gráficos ──
    c1, c2 = st.columns(2)

    with c1:
        section("", "Dispersión + recta de regresión (test)")
        x_line = np.linspace(X_te.min(), X_te.max(), 200)
        y_line = b0 + b1 * x_line
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=X_te, y=y_te, mode="markers", name="Datos reales",
            marker=dict(color=C["blue"], size=5, opacity=0.4, line=dict(width=0)),
            hovertemplate="Temp: %{x:.1f}°C<br>Vibración real: %{y:.2f} mm/s<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines", name="Recta de regresión",
            line=dict(color=C["green"], width=2),
        ))
        fig.update_xaxes(title="Temperatura (°C)")
        fig.update_yaxes(title="Vibración (mm/s)")
        st.plotly_chart(style_fig(fig, 340), use_container_width=True)

    with c2:
        section("", "Distribución de residuos (test)")
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=residuals, nbinsx=40,
            marker=dict(color=C["orange"], opacity=0.7, line=dict(color=C["bg"], width=0.5)),
            hovertemplate="Residuo: %{x:.2f} mm/s<br>Frecuencia: %{y}<extra></extra>",
        ))
        fig.add_vline(x=0, line=dict(color=C["green"], width=1.5, dash="dash"))
        fig.update_xaxes(title="Error (real − predicho) en mm/s")
        fig.update_yaxes(title="Frecuencia")
        st.plotly_chart(style_fig(fig, 340, legend=False), use_container_width=True)
        st.markdown(
            f"<p style='font-family:Space Mono,monospace;font-size:11px;color:{C['text3']};margin-top:-8px'>"
            "Residuos centrados en 0 indican modelo bien calibrado.</p>", unsafe_allow_html=True)

    # ── Predicción en vivo ──
    section("", "Predicción en vivo")
    st.markdown(
        f"<p style='color:{C['text2']};font-size:13px;margin-top:-8px'>"
        "Ingresa una temperatura y el modelo predice la vibración esperada del motor.</p>",
        unsafe_allow_html=True,
    )
    temp_val = st.slider("🌡️ Temperatura (°C)", 0.0, 130.0, 45.0, 0.5, key="ml_temp")
    vib_pred = b0 + b1 * temp_val

    eq_live = (
        f"<div style='background:{C['bg3']};border:1px solid {C['border']};border-radius:10px;"
        f"padding:16px 24px;margin:16px 0;font-family:Space Mono,monospace;font-size:14px'>"
        f"<span style='color:{C['text3']};font-size:11px;letter-spacing:1px'>CÁLCULO</span><br><br>"
        f"<span style='color:{C['text']}'>"
        f"Vibración = {b0:.4f} {sign} {abs(b1):.4f} × {temp_val:.1f}"
        f" = <strong style='color:{C['green']};font-size:18px'>{vib_pred:.4f} mm/s</strong>"
        f"</span></div>"
    )
    st.markdown(eq_live, unsafe_allow_html=True)

    # Métricas junto al resultado
    st.markdown(
        f"<div style='font-family:Space Mono,monospace;font-size:11px;color:{C['text3']};"
        f"letter-spacing:1.5px;text-transform:uppercase;margin:18px 0 12px'>Métricas del modelo</div>",
        unsafe_allow_html=True,
    )
    mm = st.columns(4)
    mm[0].markdown(f"""<div class="kpi" style="--ac:{C['green']}">
      <div class="kpi-lbl">R² Test</div>
      <div class="kpi-val">{metrics['r2_test']:.4f}</div>
      <div class="kpi-sub">varianza explicada</div></div>""", unsafe_allow_html=True)
    mm[1].markdown(f"""<div class="kpi" style="--ac:{C['blue']}">
      <div class="kpi-lbl">MAE Test</div>
      <div class="kpi-val">{metrics['mae_test']:.4f}<span class="kpi-unit">mm/s</span></div>
      <div class="kpi-sub">error absoluto medio</div></div>""", unsafe_allow_html=True)
    mm[2].markdown(f"""<div class="kpi" style="--ac:{C['orange']}">
      <div class="kpi-lbl">RMSE Test</div>
      <div class="kpi-val">{metrics['rmse_test']:.4f}<span class="kpi-unit">mm/s</span></div>
      <div class="kpi-sub">raíz error cuadrático</div></div>""", unsafe_allow_html=True)
    mm[3].markdown(f"""<div class="kpi" style="--ac:{ovf_color}">
      <div class="kpi-lbl">Sobreentrenamiento</div>
      <div class="kpi-val" style="font-size:18px">{ovf_icon}</div>
      <div class="kpi-sub">ΔR² = {r2_diff:.4f}</div></div>""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════
def main():
    inject_css()
    df, source, loaded_at = load_data()
    now = datetime.now()
    n = len(df)

    # Topbar
    src_txt = ("<span class='live-dot'></span>Supabase · en vivo" if source == "supabase"
               else "CSV local · respaldo")
    topbar = (
        "<div class=\"topbar\">"
        f"<div class=\"tb-icon\">{emblem(30)}</div>"
        f"<div><div class=\"tb-title\">{BRAND} · MONITOREO DE RIESGO</div>"
        "<div class=\"tb-sub\">Plataforma de control operacional · 4 variables · 4 niveles de riesgo</div></div>"
        f"<div class=\"tb-right\">{src_txt}<br>{n:,} registros · {now:%d/%m/%Y %H:%M}</div>"
        "</div>"
    )
    st.markdown(topbar, unsafe_allow_html=True)

    if df.empty:
        st.error("No se pudieron cargar datos. Configura `.streamlit/secrets.toml` "
                 "con tus credenciales de Supabase, o coloca el CSV junto a main.py.")
        st.stop()

    # Sidebar
    with st.sidebar:
        brand_html = (
            "<div style='display:flex;align-items:center;gap:11px;padding:6px 4px 22px'>"
            "<div style='width:40px;height:40px;border-radius:10px;background:#1e2535;"
            "border:1px solid rgba(34,211,160,0.25);display:flex;align-items:center;"
            f"justify-content:center;flex-shrink:0'>{emblem(34)}</div>"
            "<div>"
            f"<div style='font-family:Space Mono,monospace;font-size:13px;font-weight:700;"
            f"letter-spacing:-.2px;color:{C['text']}'>{BRAND}</div>"
            f"<div style='font-family:Space Mono,monospace;font-size:9.5px;color:{C['text3']};"
            f"letter-spacing:1px'>{BRAND_SUB}</div></div></div>"
        )
        st.markdown(brand_html, unsafe_allow_html=True)

        st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;font-weight:700;"
                    f"color:{C['text3']};letter-spacing:1.5px;padding:0 4px 12px'>NAVEGACIÓN</div>",
                    unsafe_allow_html=True)
        page = st.radio("Sección", [
            "📊  Resumen general",
            "🩺  Diagnóstico en vivo",
            "📈  Análisis de datos",
            "🤖  Modelo de ML",
            "📋  Referencia operacional",
            "🔍  Análisis de registros",
        ], label_visibility="collapsed")

        src_color = C["green"] if source == "supabase" else C["yellow"]
        src_label = "SUPABASE · EN VIVO" if source == "supabase" else "CSV LOCAL"
        legend_rows = "".join(
            f"<div style='display:flex;align-items:center;gap:9px;margin-bottom:7px'>"
            f"<span style='width:9px;height:9px;border-radius:3px;background:{LEVELS[l]['color']};"
            f"display:inline-block;flex-shrink:0'></span>"
            f"<span style='font-family:Space Mono,monospace;font-size:11px;color:{C['text2']}'>"
            f"{LEVELS[l]['label']}</span></div>"
            for l in ORDER
        )
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        fecha_txt = f"{dias[now.weekday()]}, {now.day:02d} {meses[now.month-1]} {now.year}"
        hora_txt = f"{now:%H:%M}"
        carga_txt = f"{loaded_at:%d/%m/%Y · %H:%M}"

        mono = "font-family:Space Mono,monospace"
        lbl = f"{mono};font-size:10px;font-weight:700;color:{C['text3']};letter-spacing:1.5px"
        sep = f"border-top:1px solid {C['border']}"

        footer = (
            f"<div style='margin-top:26px;{sep};padding-top:18px'>"
            f"<div style='{lbl};margin-bottom:14px'>NIVELES DE RIESGO</div>{legend_rows}</div>"
            f"<div style='margin-top:22px;{sep};padding-top:16px'>"
            f"<div style='{lbl}'>ESTADO DEL SISTEMA</div>"
            f"<div style='display:flex;align-items:baseline;gap:8px;margin-top:12px'>"
            f"<span style='{mono};font-size:24px;font-weight:700;color:{C['text']};letter-spacing:1px'>{hora_txt}</span>"
            f"<span style='{mono};font-size:11px;color:{C['text3']}'>hrs</span></div>"
            f"<div style='{mono};font-size:11px;color:{C['text2']};margin-top:3px'>{fecha_txt}</div></div>"
            f"<div style='margin-top:18px;{sep};padding-top:16px'>"
            f"<div style='{lbl};margin-bottom:8px'>ÚLTIMA CARGA DE DATOS</div>"
            f"<div style='{mono};font-size:11px;color:{C['text2']}'>{carga_txt}</div></div>"
            f"<div style='margin-top:16px;{sep};padding-top:16px'>"
            f"<div style='display:flex;align-items:center;gap:7px;margin-bottom:9px'>"
            f"<span style='width:7px;height:7px;border-radius:50%;background:{src_color};display:inline-block'></span>"
            f"<span style='{mono};font-size:10px;color:{C['text2']};letter-spacing:.5px'>{src_label}</span></div>"
            f"<div style='{mono};font-size:10px;color:{C['text3']};line-height:1.8'>{n:,} REGISTROS · 4 VARIABLES</div></div>"
        )
        st.markdown(footer, unsafe_allow_html=True)

    if page.startswith("📊"):
        view_overview(df)
    elif page.startswith("🩺"):
        view_live_diagnostic(df)
    elif page.startswith("📈"):
        view_analytics(df)
    elif page.startswith("🤖"):
        view_ml(df)
    elif page.startswith("📋"):
        view_reference(df)
    else:
        view_explorer(df)

    st.markdown(f"""<div style="border-top:1px solid {C['border']};margin-top:34px;padding-top:16px;
      display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
      <span style="font-size:11px;color:{C['text3']};font-family:Space Mono">MOTOR INDUSTRIAL · PLATAFORMA DE MONITOREO</span>
      <span style="font-size:11px;color:{C['text3']};font-family:Space Mono">Base: {n:,} registros · clasificación en 4 niveles</span>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()