import os
import json
import pandas as pd
import streamlit as st
from math import radians, sin, cos, sqrt, atan2
from streamlit_geolocation import streamlit_geolocation

try:
    from streamlit_folium import st_folium
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from translations import t, service_label, TRANSLATIONS
from utils import (
    get_ip_location,
    log_event,
    whatsapp_share_link,
    sms_share_link,
    build_emergency_share_message,
    add_recent_location,
)


APP_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "data.csv")

CATEGORY_ALIASES = {
    "Fire Station":     "Fire",
    "Tow Service":      "Towing",
    "Vehicle Showroom": "Showroom",
    "Rescue Service":   "Rescue",
}

SERVICE_ACCENT = {
    "Hospital":      "#dc2626",
    "Ambulance":     "#f97316",
    "Police":        "#3b82f6",
    "Fire":          "#991b1b",
    "Towing":        "#7c3aed",
    "Puncture Shop": "#0891b2",
    "Showroom":      "#4b5563",
}

SERVICE_MAP_STYLE = {
    "Hospital":      {"color": "red",        "icon": "plus-sign"},
    "Ambulance":     {"color": "orange",     "icon": "ambulance",  "prefix": "fa"},
    "Police":        {"color": "blue",       "icon": "shield",     "prefix": "fa"},
    "Fire":          {"color": "darkred",    "icon": "fire",       "prefix": "fa"},
    "Towing":        {"color": "darkpurple", "icon": "truck",      "prefix": "fa"},
    "Puncture Shop": {"color": "cadetblue",  "icon": "wrench",     "prefix": "fa"},
    "Showroom":      {"color": "gray",       "icon": "car",        "prefix": "fa"},
}

SERVICE_ICONS = {
    "Hospital":      "🏥",
    "Ambulance":     "🚑",
    "Police":        "🚓",
    "Fire":          "🚒",
    "Towing":        "🚛",
    "Puncture Shop": "🛞",
    "Showroom":      "🏪",
}

REQUIRED_COLUMNS = {"City", "Country", "Latitude", "Longitude", "Name", "Phone", "Category"}

APP_VERSION = "2.0.0"


st.set_page_config(
    page_title="NexusSOS",
    layout="centered",
    page_icon="🚨",
    initial_sidebar_state="collapsed",
)


DEFAULTS = {
    "lat": None,
    "lon": None,
    "gps_accuracy": None,
    "gps_attempted": False,
    "emergency_mode": False,
    "used_ip_fallback": False,
    "recent_locations": [],
    "cached_data_use": None,
    "cached_label": None,
    "language": "en",
    "dark_mode": True,
    "admin_authed": False,
    "show_settings": False,
    "show_admin": False,
    "show_about": False,
    "analytics_data": [],
    "search_count": 0,
    "one_tap_count": 0,
    "gps_success_count": 0,
    "category_counts": {},
    "city_counts": {},
    "lang_counts": {},
    "favorites": [],
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

lang = st.session_state.language


def inject_theme(dark_mode=True):
    if dark_mode:
        vars_ = """
            --bg:       #0a0f1e;
            --surface:  #131929;
            --surface2: #1a2236;
            --surface3: #202c42;
            --red:      #dc2626;
            --red2:     #b91c1c;
            --orange:   #f97316;
            --green:    #22c55e;
            --blue:     #3b82f6;
            --purple:   #7c3aed;
            --text:     #f1f5f9;
            --muted:    #64748b;
            --border:   rgba(255,255,255,0.07);
            --radius:   14px;
            --radius-sm:8px;
            --shadow:   0 4px 24px rgba(0,0,0,0.4);
        """
    else:
        vars_ = """
            --bg:       #f0f4f8;
            --surface:  #ffffff;
            --surface2: #e4ecf4;
            --surface3: #d6e1ee;
            --red:      #dc2626;
            --red2:     #b91c1c;
            --orange:   #ea6c0a;
            --green:    #15803d;
            --blue:     #1d4ed8;
            --purple:   #5b21b6;
            --text:     #0f172a;
            --muted:    #3d5068;
            --border:   rgba(0,0,0,0.12);
            --radius:   14px;
            --radius-sm:8px;
            --shadow:   0 4px 24px rgba(0,0,0,0.10);
        """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    :root {{ {vars_} }}

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', system-ui, sans-serif !important;
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }}

    #MainMenu, footer, header {{ visibility: hidden; }}

    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 4rem !important;
        max-width: 700px !important;
    }}

    /* Inputs */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stPasswordInput > div > div > input {{
        background-color: var(--surface2) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: var(--radius-sm) !important;
    }}
    .stCheckbox label p, .stRadio label p {{ color: var(--text) !important; }}
    div[data-testid="stMarkdownContainer"] p {{
        color: var(--text) !important;
        font-size: 0.92rem;
    }}

    /* Buttons */
    .stButton > button {{
        background: var(--surface2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.16s ease !important;
    }}
    .stButton > button:hover {{
        background: var(--surface3) !important;
        transform: translateY(-1px);
        box-shadow: var(--shadow);
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
        border: none !important;
        color: #fff !important;
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.04em !important;
        padding: 0.95rem 1.5rem !important;
        border-radius: 16px !important;
        animation: pulse-red 2.4s infinite;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 30px rgba(220,38,38,.4) !important;
    }}

    /* Link buttons */
    .stLinkButton > a {{
        background: var(--surface2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        transition: all 0.14s ease !important;
        text-decoration: none !important;
    }}
    .stLinkButton > a:hover {{
        background: var(--red) !important;
        border-color: var(--red) !important;
        color: #fff !important;
        transform: translateY(-1px) !important;
    }}

    /* Alerts */
    div[data-testid="stAlert"] {{
        border-radius: var(--radius) !important;
        border: none !important;
    }}

    /* Expanders */
    details {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }}
    details summary {{
        color: var(--text) !important;
        font-weight: 600 !important;
    }}

    /* Divider */
    hr {{ border-color: var(--border) !important; }}

    /* Sidebar — keep collapsed/hidden on mobile */
    section[data-testid="stSidebar"] {{ display: none !important; }}

    /* Toggle */
    .stToggle label {{ color: var(--text) !important; }}

    /* Progress */
    div[data-testid="stProgressBar"] > div {{
        background: linear-gradient(90deg, var(--red), var(--orange)) !important;
        border-radius: 99px !important;
    }}
    div[data-testid="stProgressBar"] {{
        background: var(--surface2) !important;
        border-radius: 99px !important;
    }}

    /* Metric */
    div[data-testid="stMetric"] {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        padding: 0.8rem !important;
    }}
    div[data-testid="stMetricValue"] {{
        color: var(--text) !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: var(--muted) !important;
    }}

    /* Tabs */
    div[data-testid="stTabs"] button {{
        color: var(--muted) !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stTabs"] button[aria-selected="true"] {{
        color: var(--text) !important;
        border-bottom-color: var(--red) !important;
    }}

    /* Dataframe */
    div[data-testid="stDataFrame"] {{
        background: var(--surface) !important;
        border-radius: var(--radius-sm) !important;
        border: 1px solid var(--border) !important;
    }}

    /* Caption */
    div[data-testid="stCaptionContainer"] p {{
        color: var(--muted) !important;
    }}

    /* st.write / markdown strong */
    div[data-testid="stMarkdownContainer"] strong {{
        color: var(--text) !important;
    }}

    /* File uploader */
    div[data-testid="stFileUploader"] {{
        background: var(--surface2) !important;
        border: 1.5px dashed var(--border) !important;
        border-radius: var(--radius) !important;
    }}
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] p {{
        color: var(--muted) !important;
    }}

    /* Download button */
    div[data-testid="stDownloadButton"] > button {{
        background: var(--surface2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stDownloadButton"] > button:hover {{
        background: var(--blue) !important;
        color: #fff !important;
        border-color: var(--blue) !important;
    }}

    /* ── Animations ─────────────────────── */
    @keyframes pulse-red {{
        0%   {{ box-shadow: 0 0 0 0 rgba(220,38,38,.6); }}
        70%  {{ box-shadow: 0 0 0 16px rgba(220,38,38,0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(220,38,38,0); }}
    }}
    @keyframes blink {{
        0%, 100% {{ opacity: 1; }}
        50%       {{ opacity: .45; }}
    }}
    @keyframes slide-in {{
        from {{ transform: translateY(-10px); opacity: 0; }}
        to   {{ transform: translateY(0);     opacity: 1; }}
    }}
    @keyframes fade-in {{
        from {{ opacity: 0; }}
        to   {{ opacity: 1; }}
    }}
    @keyframes spin {{
        to {{ transform: rotate(360deg); }}
    }}
    </style>
    """, unsafe_allow_html=True)

inject_theme(dark_mode=st.session_state.dark_mode)


if not os.path.exists(DATA_PATH):
    st.error(f"⚠️ **data.csv** not found.\n\nExpected: `{DATA_PATH}`\n\nPlace `data.csv` in the same folder as `app.py`.")
    st.stop()

try:
    data = pd.read_csv(DATA_PATH, dtype={"Phone": str})
except pd.errors.EmptyDataError:
    st.error("⚠️ **data.csv** is empty.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Could not read **data.csv**: `{e}`")
    st.stop()

missing_cols = REQUIRED_COLUMNS - set(data.columns)
if missing_cols:
    st.error(f"⚠️ **data.csv** missing columns: {', '.join(sorted(missing_cols))}")
    st.stop()

data = data.dropna(subset=["Country", "Category", "Latitude", "Longitude"])
data["Country"]  = data["Country"].astype(str).str.strip()
data["Category"] = data["Category"].astype(str).str.strip().str.title().replace(CATEGORY_ALIASES)

if data.empty:
    st.error("⚠️ No usable rows in data.csv after cleaning.")
    st.stop()


def distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def get_results(service_type, data_use, user_lat, user_lon, n=1):
    subset = data_use[data_use["Category"] == service_type].sort_values("Distance").head(n)
    results = []
    for _, row in subset.iterrows():
        phone = str(row["Phone"]).replace(".0", "")
        results.append({
            "name": row["Name"],
            "phone": phone,
            "lat": row["Latitude"],
            "lon": row["Longitude"],
            "distance_km": row["Distance"],
        })
    return results

def track(event, category=None, city=None):
    """Update in-session analytics counters."""
    if event == "search":
        st.session_state.search_count += 1
    elif event == "one_tap":
        st.session_state.one_tap_count += 1
    elif event == "gps_ok":
        st.session_state.gps_success_count += 1
    if category:
        st.session_state.category_counts[category] = st.session_state.category_counts.get(category, 0) + 1
    if city:
        st.session_state.city_counts[city] = st.session_state.city_counts.get(city, 0) + 1
    lang_k = st.session_state.language
    st.session_state.lang_counts[lang_k] = st.session_state.lang_counts.get(lang_k, 0) + 1

def is_favorite(name):
    return name in st.session_state.favorites

def toggle_favorite(name):
    if is_favorite(name):
        st.session_state.favorites.remove(name)
    else:
        st.session_state.favorites.append(name)


def ui_hero():
    gps_active   = st.session_state.lat is not None
    n_services   = len(data)
    n_countries  = data["Country"].nunique()

    if gps_active:
        gps_dot   = '#22c55e'
        gps_blink = 'animation:blink 1.4s infinite;'
        gps_label = '🟢 GPS Connected'
    else:
        gps_dot   = '#64748b'
        gps_blink = ''
        gps_label = '🔴 GPS Not Connected'

    stats = [
        ("🏥", f"{n_services:,}", "Services"),
        ("🌍", str(n_countries),  "Countries"),
        ("⚡", "&lt;2s",          "GPS Lock"),
        ("🚑", "24/7",            "Emergency"),
    ]
    stat_cards = ""
    for icon, val, lbl in stats:
        stat_cards += (
            f'<div style="flex:1;min-width:0;background:rgba(255,255,255,.04);'
            f'border:1px solid rgba(255,255,255,.08);border-radius:12px;'
            f'padding:.55rem .35rem;text-align:center;">'
            f'<div style="font-size:1.1rem;line-height:1;">{icon}</div>'
            f'<div style="font-size:1rem;font-weight:900;color:#f1f5f9;'
            f'letter-spacing:-.01em;line-height:1.15;margin:.15rem 0 .1rem;">{val}</div>'
            f'<div style="font-size:.6rem;color:#64748b;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:.05em;">{lbl}</div>'
            f'</div>'
        )

    st.markdown(
        '<div style="background:linear-gradient(160deg,#1a2d4a 0%,#0d1829 55%,#0f172a 100%);'
        'border:1px solid rgba(220,38,38,.3);border-radius:20px;'
        'padding:1.1rem 1.25rem .95rem;margin-bottom:.75rem;'
        'animation:fade-in .35s ease;'
        'box-shadow:0 4px 32px rgba(0,0,0,.45),0 0 0 1px rgba(220,38,38,.08);">'


        '<div style="display:flex;align-items:center;gap:.85rem;margin-bottom:.8rem;">'
        '<div style="width:46px;height:46px;min-width:46px;'
        'background:linear-gradient(135deg,#dc2626,#f97316);'
        'border-radius:14px;display:flex;align-items:center;'
        'justify-content:center;font-size:1.5rem;'
        'box-shadow:0 6px 18px rgba(220,38,38,.4);">🚨</div>'
        '<div style="flex:1;min-width:0;">'
        '<div style="font-size:1.45rem;font-weight:900;color:#ffffff;'
        'letter-spacing:-.025em;line-height:1.1;">NexusSOS</div>'
        '<div style="font-size:.72rem;color:#94a3b8;font-weight:500;'
        'margin-top:.1rem;letter-spacing:.01em;">Respond Faster. Save Lives.</div>'
        '</div>'
        f'<div style="display:flex;align-items:center;gap:5px;'
        f'background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);'
        f'border-radius:99px;padding:.28rem .75rem;white-space:nowrap;">'
        f'<span style="width:7px;height:7px;border-radius:50%;'
        f'background:{gps_dot};display:inline-block;{gps_blink}"></span>'
        f'<span style="font-size:.7rem;font-weight:700;color:{gps_dot};">{gps_label}</span>'
        f'</div>'
        '</div>'


        '<div style="height:1px;background:rgba(255,255,255,.07);margin-bottom:.7rem;"></div>'


        f'<div style="display:flex;gap:.45rem;">{stat_cards}</div>'


        '<div style="margin-top:.7rem;display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;">'
        '<span style="font-size:.65rem;color:#475569;font-weight:600;'
        'text-transform:uppercase;letter-spacing:.06em;">'
        '🛡️ IIT Madras CoERS · MoRTH · Road Safety Hackathon 2026'
        '</span>'
        '<span style="margin-left:auto;font-size:.65rem;font-weight:700;color:#22c55e;'
        'background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.25);'
        'padding:.15rem .55rem;border-radius:99px;">● LIVE</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

def ui_settings_panel():
    """Inline settings expander — replaces the sidebar entirely."""
    with st.expander("⚙️  Settings", expanded=st.session_state.show_settings):
        lang_options = {code: TRANSLATIONS[code]["lang_name"] for code in TRANSLATIONS}
        c1, c2 = st.columns([2, 1])
        with c1:
            selected_lang = st.selectbox(
                t(lang, "language"),
                options=list(lang_options.keys()),
                format_func=lambda code: lang_options[code],
                index=list(lang_options.keys()).index(st.session_state.language),
                key="lang_selector",
            )
        with c2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            dark_mode = st.toggle(
                "🌙 Dark",
                value=st.session_state.dark_mode,
                key="dark_mode_toggle",
            )

        changed = False
        if selected_lang != st.session_state.language:
            st.session_state.language = selected_lang
            changed = True
        if dark_mode != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_mode
            changed = True
        if changed:
            st.rerun()

        st.divider()


        if st.session_state.recent_locations:
            st.markdown("**🕘 Recent Locations**")
            for i, loc in enumerate(st.session_state.recent_locations):
                if st.button(f"📍 {loc['label']}", key=f"recent_{i}", use_container_width=True):
                    st.session_state.lat = loc["lat"]
                    st.session_state.lon = loc["lon"]
                    st.session_state.recent_search_trigger = True
                    st.rerun()
            st.divider()


        if st.session_state.favorites:
            st.markdown("**⭐ Favorite Hospitals**")
            for name in st.session_state.favorites:
                col_a, col_b = st.columns([5, 1])
                with col_a:
                    st.markdown(f"<small>🏥 {name}</small>", unsafe_allow_html=True)
                with col_b:
                    if st.button("✕", key=f"unfav_{name}"):
                        toggle_favorite(name)
                        st.rerun()
            st.divider()


        st.markdown(f"""
        <div style="background:var(--surface2);border:1px solid var(--border);
                    border-radius:10px;padding:.85rem 1rem;font-size:.8rem;color:var(--muted);">
          <strong style="color:var(--text);">NexusSOS v{APP_VERSION}</strong><br>
          AI-Powered Emergency Response Platform<br><br>
          📋 {len(data):,} services &nbsp;·&nbsp; 🌍 {data["Country"].nunique()} countries
          &nbsp;·&nbsp; 🗂️ {data["Category"].nunique()} categories<br><br>
          Built for speed when every second counts.
        </div>
        """, unsafe_allow_html=True)

def ui_admin_panel():
    """Full admin panel as an inline expander."""
    with st.expander("🔐  Admin Panel"):
        if not st.session_state.admin_authed:
            pw = st.text_input(t(lang, "admin_password"), type="password", key="admin_pw")
            if st.button(t(lang, "admin_login"), key="admin_login_btn"):
                try:
                    real_pw = st.secrets.get("ADMIN_PASSWORD", "admin123")
                except Exception:
                    real_pw = "admin123"
                if pw == real_pw:
                    st.session_state.admin_authed = True
                    st.rerun()
                else:
                    st.error(t(lang, "admin_wrong_password"))
            return


        tab_add, tab_search, tab_csv, tab_pending, tab_analytics = st.tabs(
            ["➕ Add", "🔍 Search", "📁 CSV", "📋 Pending", "📊 Analytics"]
        )


        with tab_add:
            st.markdown("**Add New Service**")
            a_name    = st.text_input("Name",    key="a_name")
            a_type    = st.selectbox("Type", list(SERVICE_ICONS.keys()), key="a_type")
            a_phone   = st.text_input("Phone",   key="a_phone")
            a_city    = st.text_input("City",    key="a_city")
            a_country = st.text_input("Country", key="a_country")
            col_lat, col_lon = st.columns(2)
            with col_lat:
                a_lat = st.number_input("Latitude",  format="%.6f", key="a_lat")
            with col_lon:
                a_lon = st.number_input("Longitude", format="%.6f", key="a_lon")

            if st.button("💾 Save Entry", key="save_entry_btn", use_container_width=True):
                if a_name and a_phone and a_city and a_country:
                    new_row = {
                        "Name": a_name, "Category": a_type, "Phone": a_phone,
                        "City": a_city, "Country": a_country,
                        "Latitude": a_lat, "Longitude": a_lon,
                    }
                    try:
                        existing_cols = pd.read_csv(DATA_PATH, nrows=0).columns.tolist()
                        row_df = pd.DataFrame([{c: new_row.get(c, "") for c in existing_cols}])
                        row_df.to_csv(DATA_PATH, mode="a", header=False, index=False)
                        st.success(t(lang, "admin_entry_saved"))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Save failed: {e}")
                else:
                    st.warning("Fill in Name, Phone, City and Country.")


        with tab_search:
            st.markdown("**Search & Manage Services**")
            q = st.text_input("Search by name or city", key="admin_search_q")
            if q:
                mask   = (
                    data["Name"].str.contains(q, case=False, na=False) |
                    data["City"].str.contains(q, case=False, na=False)
                )
                result = data[mask].head(20)
                if result.empty:
                    st.info("No matching records.")
                else:
                    for idx, row in result.iterrows():
                        with st.expander(f"{SERVICE_ICONS.get(row['Category'], '📍')} {row['Name']} — {row['City']}"):
                            st.write(f"**Type:** {row['Category']}  ·  **Phone:** {row['Phone']}")
                            st.write(f"**Country:** {row['Country']}  ·  **Coords:** {row['Latitude']}, {row['Longitude']}")
                            if st.button(f"🗑️ Delete {row['Name']}", key=f"del_{idx}"):
                                try:
                                    df_full = pd.read_csv(DATA_PATH, dtype={"Phone": str})
                                    df_full = df_full.drop(df_full[df_full["Name"] == row["Name"]].index[:1])
                                    df_full.to_csv(DATA_PATH, index=False)
                                    st.success("Deleted.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Delete failed: {e}")


        with tab_csv:
            st.markdown("**Upload CSV**")
            uploaded = st.file_uploader("Upload new data.csv", type=["csv"], key="csv_upload")
            if uploaded:
                try:
                    df_new = pd.read_csv(uploaded, dtype={"Phone": str})
                    missing = REQUIRED_COLUMNS - set(df_new.columns)
                    if missing:
                        st.error(f"Missing columns: {', '.join(sorted(missing))}")
                    else:
                        df_new.to_csv(DATA_PATH, index=False)
                        st.success(f"✅ Uploaded {len(df_new):,} rows.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {e}")

            st.divider()
            st.markdown("**Download CSV**")
            try:
                csv_bytes = data.to_csv(index=False).encode()
                st.download_button(
                    "⬇️ Download data.csv",
                    data=csv_bytes,
                    file_name="nexussos_data.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Could not prepare download: {e}")

            st.divider()
            st.markdown("**Export Analytics Report**")
            report = {
                "total_searches":   st.session_state.search_count,
                "one_tap_count":    st.session_state.one_tap_count,
                "gps_success":      st.session_state.gps_success_count,
                "category_counts":  st.session_state.category_counts,
                "city_counts":      st.session_state.city_counts,
                "lang_counts":      st.session_state.lang_counts,
            }
            st.download_button(
                "⬇️ Export Analytics JSON",
                data=json.dumps(report, indent=2),
                file_name="nexussos_analytics.json",
                mime="application/json",
                use_container_width=True,
            )


        with tab_pending:
            st.markdown("**Pending Service Requests**")
            st.info("No pending requests. (Connect a database to enable real-time submissions.)")


        with tab_analytics:
            ui_analytics()

def ui_analytics():
    """Analytics dashboard — in-session counters + data insights."""
    st.markdown("**Session Analytics**")

    c1, c2, c3 = st.columns(3)
    c1.metric("🔍 Searches",  st.session_state.search_count)
    c2.metric("🚨 One-Tap",   st.session_state.one_tap_count)
    c3.metric("📍 GPS OK",    st.session_state.gps_success_count)

    if st.session_state.category_counts:
        st.markdown("**Most Used Categories**")
        cat_df = pd.DataFrame(
            [{"Category": k, "Count": v} for k, v in sorted(
                st.session_state.category_counts.items(), key=lambda x: -x[1]
            )]
        )
        st.bar_chart(cat_df.set_index("Category"))

    if st.session_state.city_counts:
        st.markdown("**Most Searched Cities**")
        city_df = pd.DataFrame(
            [{"City": k, "Count": v} for k, v in sorted(
                st.session_state.city_counts.items(), key=lambda x: -x[1]
            )][:10]
        )
        st.bar_chart(city_df.set_index("City"))

    if st.session_state.lang_counts:
        st.markdown("**Language Usage**")
        lang_df = pd.DataFrame(
            [{"Language": TRANSLATIONS.get(k, {}).get("lang_name", k), "Count": v}
             for k, v in st.session_state.lang_counts.items()]
        )
        st.bar_chart(lang_df.set_index("Language"))

    st.divider()
    st.markdown("**Dataset Overview**")
    col1, col2 = st.columns(2)
    with col1:
        cat_counts = data["Category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Services"]
        st.dataframe(cat_counts, use_container_width=True, hide_index=True)
    with col2:
        country_counts = data["Country"].value_counts().head(10).reset_index()
        country_counts.columns = ["Country", "Services"]
        st.dataframe(country_counts, use_container_width=True, hide_index=True)

def ui_dashboard(gps_active, hospitals, ambulances, police):
    items = [
        ("📍", "GPS",       "Active"   if gps_active else "Standby", "#22c55e" if gps_active else "#64748b"),
        ("🏥", "Hospitals", str(hospitals), "#dc2626"),
        ("🚑", "Ambulance", str(ambulances), "#f97316"),
        ("🚓", "Police",    str(police),    "#3b82f6"),
    ]
    cols_html = ""
    for icon, label, value, color in items:
        cols_html += (
            f'<div style="background:var(--surface);border:1px solid var(--border);'
            f'border-top:3px solid {color};border-radius:var(--radius);'
            'padding:.8rem .4rem;text-align:center;flex:1;min-width:0;">'
            f'<div style="font-size:1.2rem;margin-bottom:.15rem;">{icon}</div>'
            f'<div style="font-size:1.2rem;font-weight:800;color:{color};line-height:1;">{value}</div>'
            '<div style="font-size:.65rem;color:var(--muted);font-weight:600;'
            f'text-transform:uppercase;letter-spacing:.05em;margin-top:.15rem;">{label}</div>'
            '</div>'
        )
    st.markdown(
        f'<div style="display:flex;gap:.5rem;margin-bottom:1rem;">{cols_html}</div>',
        unsafe_allow_html=True,
    )

def ui_emergency_banner():
    st.markdown("""
    <div style="background:linear-gradient(135deg,rgba(220,38,38,.12),rgba(185,28,28,.08));
                border:1.5px solid rgba(220,38,38,.5);border-radius:var(--radius);
                padding:.9rem 1.2rem;text-align:center;margin-bottom:.8rem;
                animation:slide-in .3s ease;">
      <div style="font-size:1rem;font-weight:800;color:#dc2626;
                  letter-spacing:.07em;text-transform:uppercase;">
        <span style="animation:blink 1s infinite;display:inline-block;">🚨</span>
        &nbsp;EMERGENCY ACTIVE
      </div>
      <div style="font-size:.78rem;color:#b91c1c;margin-top:.3rem;font-weight:600;">
        Golden Hour Response Protocol Enabled — Help is on the way
      </div>
    </div>
    """, unsafe_allow_html=True)

def ui_location_card(lat, lon, accuracy=None):
    acc_html = (
        f'<span style="color:#16a34a;font-size:.72rem;font-weight:600;">±{round(accuracy)}m</span>'
        if accuracy else ""
    )
    st.markdown(f"""
    <div style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.35);
                border-radius:var(--radius);padding:.75rem 1rem;display:flex;
                align-items:center;gap:.7rem;margin-bottom:.6rem;">
      <div style="font-size:1.3rem;">📍</div>
      <div style="flex:1;">
        <div style="font-size:.85rem;font-weight:700;color:#16a34a;">Location Confirmed</div>
        <div style="font-size:.72rem;color:var(--muted);font-family:monospace;margin-top:.1rem;">
          {round(lat, 5)}, {round(lon, 5)} {acc_html}
        </div>
      </div>
      <div style="background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.35);
                  border-radius:99px;padding:.18rem .6rem;font-size:.7rem;
                  color:#16a34a;font-weight:700;white-space:nowrap;">
        <span style="animation:blink 1.2s infinite;display:inline-block;">●</span> LIVE
      </div>
    </div>
    """, unsafe_allow_html=True)

def ui_section_header(icon, title, subtitle=None):
    sub_html = (
        f'<div style="font-size:.75rem;color:var(--muted);margin-top:.1rem;">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:.6rem;margin:1.3rem 0 .7rem;">
      <span style="background:var(--surface2);border-radius:10px;
                   padding:.38rem .48rem;font-size:1.15rem;line-height:1;">{icon}</span>
      <div>
        <div style="font-size:.97rem;font-weight:700;color:var(--text);">{title}</div>
        {sub_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

def ui_service_card(name, distance_km, phone, badge, accent, key_prefix, service_type, show_fav=False):
    fav_icon = "⭐" if is_favorite(name) else "☆"
    phone_html = (
        f'<span style="color:var(--muted);font-size:.78rem;">📞 {phone}</span>'
        if phone else ""
    )
    st.markdown(f"""
    <div style="background:var(--surface);border:1px solid var(--border);
                border-left:4px solid {accent};border-radius:var(--radius);
                padding:.95rem 1.1rem;margin-bottom:.5rem;animation:slide-in .3s ease;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;
                  flex-wrap:wrap;gap:.3rem;">
        <div style="font-weight:700;font-size:.95rem;color:var(--text);flex:1;min-width:0;">
          {name}
        </div>
        <span style="background:{accent}22;color:{accent};font-size:.66rem;
                     font-weight:700;letter-spacing:.05em;padding:.16rem .5rem;
                     border-radius:99px;white-space:nowrap;border:1px solid {accent}44;">{badge}</span>
      </div>
      <div style="margin-top:.4rem;display:flex;gap:.9rem;flex-wrap:wrap;align-items:center;">
        <span style="color:#ea6c0a;font-size:.8rem;font-weight:700;background:rgba(234,108,10,.1);
                     padding:.1rem .45rem;border-radius:6px;">
          📍 {round(distance_km, 2)} km away
        </span>
        {phone_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    maps_url   = f"https://www.google.com/maps/dir/?api=1&destination={name.replace(' ', '+')}"
    show_share = service_type in ("Hospital", "Ambulance")
    n_cols     = (1 if phone else 0) + 1 + (2 if show_share else 0) + (1 if service_type == "Hospital" else 0)
    cols       = st.columns(n_cols)
    ci         = 0

    if phone:
        with cols[ci]:
            st.link_button(t(lang, "call_now"), f"tel:{phone}", key=f"{key_prefix}_call")
        ci += 1

    with cols[ci]:
        st.link_button(t(lang, "navigate"), maps_url, key=f"{key_prefix}_nav")
    ci += 1

    if show_share:
        msg = build_emergency_share_message(name, distance_km, phone or "N/A", 0, 0, service_type)
        with cols[ci]:
            st.link_button(t(lang, "share_whatsapp"), whatsapp_share_link(msg), key=f"{key_prefix}_wa")
        ci += 1
        with cols[ci]:
            st.link_button(t(lang, "share_sms"), sms_share_link(msg), key=f"{key_prefix}_sms")
        ci += 1

    if service_type == "Hospital":
        with cols[ci]:
            fav_label = f"{fav_icon} Fav"
            if st.button(fav_label, key=f"{key_prefix}_fav", use_container_width=True):
                toggle_favorite(name)
                st.rerun()

def ui_secondary_row(name, distance_km, phone, badge):
    ph = f" · 📞 {phone}" if phone else ""
    st.markdown(f"""
    <div style="background:var(--surface2);border:1px solid var(--border);
                border-radius:var(--radius-sm);padding:.5rem .9rem;margin-bottom:.3rem;
                font-size:.81rem;color:var(--muted);">
      <span style="color:var(--text);font-weight:600;">{name}</span>
      &nbsp;·&nbsp;📍 {round(distance_km,2)} km{ph}
      <span style="font-size:.66rem;color:var(--muted);font-weight:600;margin-left:.4rem;">{badge}</span>
    </div>
    """, unsafe_allow_html=True)

def ui_no_data(service_type):
    st.markdown(f"""
    <div style="background:var(--surface2);border:1.5px dashed var(--border);
                border-radius:var(--radius);padding:.9rem;text-align:center;
                color:var(--muted);font-size:.83rem;">
      No {service_type} data found nearby
    </div>
    """, unsafe_allow_html=True)

def ui_map(user_lat, user_lon, map_points):
    st.markdown("""
    <div style="background:var(--surface);border:1px solid var(--border);
                border-radius:var(--radius) var(--radius) 0 0;padding:.7rem 1rem;
                display:flex;align-items:center;gap:.55rem;margin-bottom:-4px;">
      <span style="font-size:1.05rem;">🗺️</span>
      <span style="font-weight:700;font-size:.93rem;color:var(--text);">Emergency Response Map</span>
      <span style="margin-left:auto;font-size:.7rem;color:#22c55e;font-weight:600;
                   background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.25);
                   padding:.14rem .5rem;border-radius:99px;">● LIVE</span>
    </div>
    """, unsafe_allow_html=True)


    legend = [("#22c55e","You"),("#dc2626","Hospital"),("#f97316","Ambulance"),
              ("#3b82f6","Police"),("#7c3aed","Towing"),("#991b1b","Fire")]
    dots = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:.7rem;color:var(--muted);">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{c};display:inline-block;"></span>'
        f'{lbl}</span>'
        for c, lbl in legend
    )
    st.markdown(
        f'<div style="background:var(--surface);border-left:1px solid var(--border);'
        f'border-right:1px solid var(--border);padding:.45rem .9rem;'
        f'display:flex;gap:.8rem;flex-wrap:wrap;">{dots}</div>',
        unsafe_allow_html=True,
    )

    if not FOLIUM_AVAILABLE:
        st.caption("Install `folium streamlit-folium` for the interactive map.")
        fallback_df = pd.DataFrame(
            [{"lat": user_lat, "lon": user_lon}]
            + [{"lat": r["lat"], "lon": r["lon"]} for _, r in map_points]
        )
        st.map(fallback_df)
        return

    fmap = folium.Map(location=[user_lat, user_lon], tiles="OpenStreetMap")
    folium.Marker(
        [user_lat, user_lon], popup="📍 You are here", tooltip="Your location",
        icon=folium.Icon(color="green", icon="user", prefix="fa"),
    ).add_to(fmap)

    all_pts = [[user_lat, user_lon]]
    for service_type, r in map_points:
        style    = SERVICE_MAP_STYLE.get(service_type, {"color": "gray", "icon": "info-sign"})
        popup_html = (
            f"<b>{r['name']}</b><br>{service_label(lang, service_type)}"
            f"<br>{round(r['distance_km'], 2)} km away"
        )
        if r["phone"]:
            popup_html += f"<br>📞 {r['phone']}"
        popup_html += (
            f'<br><a href="https://www.google.com/maps/dir/?api=1'
            f'&destination={r["lat"]},{r["lon"]}" target="_blank">Directions</a>'
        )
        folium.Marker(
            [r["lat"], r["lon"]],
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=r["name"],
            icon=folium.Icon(
                color=style["color"], icon=style["icon"],
                prefix=style.get("prefix", "glyphicon"),
            ),
        ).add_to(fmap)
        all_pts.append([r["lat"], r["lon"]])

    if len(all_pts) > 1:
        fmap.fit_bounds(all_pts, padding=(40, 40))
    else:
        fmap.zoom_start = 13

    st_folium(fmap, width=None, height=430, returned_objects=[])

def ui_sos_countdown():
    """Visual countdown hint for ONE TAP mode."""
    st.markdown("""
    <div style="background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.35);
                border-radius:var(--radius);padding:.7rem 1rem;text-align:center;
                font-size:.82rem;color:#b91c1c;font-weight:600;">
      🚨 Locating nearest emergency services — GPS may take 5–15 seconds on first use
    </div>
    """, unsafe_allow_html=True)

def ui_voice_search_hint():
    """Prompt for voice input on mobile."""
    st.markdown("""
    <div style="background:var(--surface2);border:1px solid var(--border);
                border-radius:var(--radius-sm);padding:.55rem .9rem;
                font-size:.78rem;color:var(--muted);">
      🎤 <span style="color:var(--text);font-weight:600;">Voice tip:</span>
      On mobile, tap the microphone on your keyboard to speak a city name
    </div>
    """, unsafe_allow_html=True)

def ui_footer():
    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0 .5rem;color:var(--muted);font-size:.74rem;">
      NexusSOS v{APP_VERSION} &nbsp;·&nbsp; Emergency use only
      &nbsp;·&nbsp; Always call official emergency numbers
    </div>
    """, unsafe_allow_html=True)


def render_result(result, label, key_prefix, service_type, highlight=False):
    badge  = "📋 Directory"
    accent = SERVICE_ACCENT.get(service_type, "#dc2626")
    if highlight:
        ui_service_card(
            result["name"], result["distance_km"], result["phone"],
            badge, accent, key_prefix, service_type,
        )
    else:
        ui_secondary_row(result["name"], result["distance_km"], result["phone"], badge)


try:
    from ai_chat import render_ai_chat_tab
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


ui_hero()

tab_labels = ["🚨 Emergency Services", "🤖 AI Triage"]
tab_services, tab_ai = st.tabs(tab_labels)

with tab_services:
    ui_settings_panel()
    ui_admin_panel()

    st.divider()


    one_tap_clicked = st.button(
        t(lang, "one_tap"), use_container_width=True, type="primary"
    )
    if one_tap_clicked:
        st.session_state.emergency_mode = True
        track("one_tap")
        log_event("one_tap_pressed", language=lang)

    one_tap = st.session_state.emergency_mode

    if one_tap:
        c_exit, _ = st.columns([1, 3])
        with c_exit:
            if st.button("✖ Exit Emergency", key="exit_em"):
                st.session_state.emergency_mode = False
                st.rerun()
        ui_sos_countdown()


    if not one_tap:
        st.caption(t(lang, "click_below"))
    else:
        st.caption("📍 **Allow** location access when prompted — GPS may take a moment.")

    loc_c1, loc_c2 = st.columns([4, 1])
    with loc_c1:
        st.caption("iPhone/Android: ensure Location is enabled for your browser in phone Settings.")
    with loc_c2:
        gps_retry = st.button("🔄", key="gps_retry_btn", use_container_width=True)

    if gps_retry:
        st.session_state.gps_attempted = True

    if one_tap:
        with st.spinner("📍 Acquiring GPS…"):
            loc = streamlit_geolocation()
    else:
        loc = streamlit_geolocation()

    st.session_state.gps_attempted = True

    got_fresh_fix = bool(loc) and loc.get("latitude") is not None
    if got_fresh_fix:
        st.session_state.lat          = loc["latitude"]
        st.session_state.lon          = loc["longitude"]
        st.session_state.gps_accuracy = loc.get("accuracy")
        st.session_state.used_ip_fallback = False
        track("gps_ok")
        st.success("📍 Location confirmed — finding nearest services.")
    elif loc and loc.get("latitude") is None and st.session_state.gps_attempted:
        st.warning(
            "📍 Location blocked. Tap the 🔒 lock icon in your address bar → "
            "set Location to **Allow** → press 🔄 Retry."
        )

    lat = st.session_state.lat
    lon = st.session_state.lon


    if one_tap and (lat is None or lon is None):
        st.error(t(lang, "allow_location"))
        if st.button("📶 Use Approximate Network Location", key="ip_fallback_btn"):
            with st.spinner("Estimating location from network…"):
                ip_lat, ip_lon = get_ip_location()
            if ip_lat is not None:
                st.session_state.lat = ip_lat
                st.session_state.lon = ip_lon
                st.session_state.used_ip_fallback = True
                st.rerun()
            else:
                st.error("Could not detect approximate location. Check your connection.")
        st.stop()

    if st.session_state.used_ip_fallback and lat is not None:
        st.warning("📶 Using city-level network location (GPS unavailable) — not your exact position.")


    recent_search_trigger = st.session_state.pop("recent_search_trigger", False)

    if not one_tap:
        use_gps = st.checkbox(t(lang, "use_gps"))
        countries = sorted(data["Country"].unique())
        default_idx = countries.index("India") if "India" in countries else 0
        country = st.selectbox(t(lang, "country"), countries, index=default_idx)
        city    = st.text_input(t(lang, "city"), disabled=use_gps)
        ui_voice_search_hint()
        find_clicked = st.button(t(lang, "find_services"), use_container_width=True)
    else:
        use_gps = False
        country = None
        city    = ""
        find_clicked = False


    if find_clicked or one_tap or recent_search_trigger:
        user_lat = user_lon = None
        data_use = location_label = None


        if (one_tap or use_gps or recent_search_trigger) and lat is not None and lon is not None:
            user_lat, user_lon = lat, lon
            location_label     = f"{round(lat, 3)}, {round(lon, 3)}"
            if not recent_search_trigger:
                st.info(t(lang, "using_gps"))
            data_use = data.copy()
            track("search")
            track("gps_ok")

        elif city != "":
            city_t    = city.title()
            city_data = data[(data["City"] == city_t) & (data["Country"] == country)]
            if city_data.empty:
                st.error(t(lang, "city_not_found"))
                st.stop()
            user_lat, user_lon = city_data.iloc[0]["Latitude"], city_data.iloc[0]["Longitude"]
            location_label     = f"{city_t}, {country}"
            st.info(location_label)
            data_use = data[data["Country"] == country].copy()
            track("search", city=city_t)

        else:
            st.warning(t(lang, "enter_city_or_gps"))
            if st.session_state.cached_data_use is not None:
                if st.button(t(lang, "using_cached"), key="use_cached_btn"):
                    data_use       = st.session_state.cached_data_use
                    location_label = st.session_state.cached_label
                else:
                    st.stop()
            else:
                st.stop()


        if "Distance" not in data_use.columns:
            data_use["Distance"] = data_use.apply(
                lambda row: distance(user_lat, user_lon, row["Latitude"], row["Longitude"]), axis=1
            )
            data_use = data_use.sort_values("Distance")


        st.session_state.cached_data_use = data_use
        st.session_state.cached_label    = location_label
        add_recent_location(st.session_state, location_label, user_lat, user_lon)


        h_found  = len(data_use[data_use["Category"] == "Hospital"])
        a_found  = len(data_use[data_use["Category"] == "Ambulance"])
        p_found  = len(data_use[data_use["Category"] == "Police"])

        ui_dashboard(gps_active=lat is not None, hospitals=h_found, ambulances=a_found, police=p_found)
        log_event("search", user_lat, user_lon, lang)


        if one_tap:
            ui_location_card(user_lat, user_lon, st.session_state.get("gps_accuracy"))
            ui_emergency_banner()
            log_event("emergency_results_shown", user_lat, user_lon, lang)

            priority = [
                ("Hospital", "🏥", t(lang, "nearest_hospital")),
                ("Ambulance","🚑", t(lang, "nearest_ambulance")),
                ("Police",   "🚓", t(lang, "nearest_police")),
                ("Fire",     "🚒", t(lang, "nearest_fire")),
            ]

            map_points = []
            for service, icon, label in priority:
                ui_section_header(icon, label)
                results = get_results(service, data_use, user_lat, user_lon, n=1)
                if results:
                    render_result(results[0], label, f"em_{service}", service, highlight=True)
                    map_points.append((service, results[0]))
                    track(event="search", category=service)
                else:
                    ui_no_data(service)

            st.divider()
            ui_map(user_lat, user_lon, map_points)

            st.markdown("""
            <div style="background:rgba(220,38,38,.08);border:1px solid rgba(220,38,38,.3);
                        border-radius:var(--radius);padding:.7rem 1rem;margin-top:.8rem;
                        font-size:.8rem;color:#b91c1c;text-align:center;font-weight:600;">
              ⚠️ Always call official emergency numbers in a life-threatening situation.
              This app is a directory — response times may vary.
            </div>
            """, unsafe_allow_html=True)
            ui_footer()
            st.stop()


        ui_section_header("📍", t(lang, "nearby_services"), "Top results per category · closest first")
        log_event("manual_search", user_lat, user_lon, lang)

        services_order = [
            ("Hospital",      "🏥"),
            ("Ambulance",     "🚑"),
            ("Police",        "🚓"),
            ("Fire",          "🚒"),
            ("Towing",        "🚛"),
            ("Puncture Shop", "🛞"),
            ("Showroom",      "🏪"),
        ]

        map_points = []
        for s, icon in services_order:
            ui_section_header(icon, service_label(lang, s))
            results = get_results(s, data_use, user_lat, user_lon, n=5)
            if not results:
                ui_no_data(s)
            else:
                for i, result in enumerate(results):
                    render_result(result, service_label(lang, s), f"{s}_{i}", s, highlight=(i == 0))
                    if i == 0:
                        map_points.append((s, result))
                        track(event="search", category=s)

        st.divider()
        ui_map(user_lat, user_lon, map_points)
        st.info(t(lang, "tip_ambulance"))
        ui_footer()

def find_nearest_hospital(lat, lon):
    """
    Look up the nearest real Hospital from data.csv for the AI Triage tab's
    incident report. Returns {"name", "distance_km"} or None if no hospital
    rows exist — kept separate from the LLM so the report never shows a
    hospital name the AI invented.
    """
    hospitals = data[data["Category"] == "Hospital"]
    if hospitals.empty:
        return None
    nearest = hospitals.loc[
        hospitals.apply(
            lambda row: distance(lat, lon, row["Latitude"], row["Longitude"]), axis=1
        ).idxmin()
    ]
    return {
        "name": nearest["Name"],
        "distance_km": distance(lat, lon, nearest["Latitude"], nearest["Longitude"]),
    }


AI_UNIT_TO_CATEGORY = {
    "Ambulance":              "Ambulance",
    "Police":                 "Police",
    "Fire Rescue":            "Fire",
    "Tow Truck":              "Towing",
    "Highway Patrol":         "Police",
    "Hazmat":                 "Fire",
    "Disaster Response":      "Fire",
    "Electricity Department": "Police",
}

def find_services_for_units(lat, lon, units, n_each=1):
    """
    For each AI-recommended unit, look up the nearest REAL service(s) from
    data.csv. Returns {unit_name: [ {name, phone, distance_km, lat, lon}, ... ]}.
    Never invents data — only returns rows that actually exist.
    """
    if lat is None or lon is None:
        return {}

    work = data.copy()
    work["Distance"] = work.apply(
        lambda r: distance(lat, lon, r["Latitude"], r["Longitude"]), axis=1
    )

    out = {}
    for unit in units:
        category = AI_UNIT_TO_CATEGORY.get(unit)
        if not category:
            out[unit] = []
            continue
        subset = work[work["Category"] == category].sort_values("Distance").head(n_each)
        rows = []
        for _, row in subset.iterrows():
            phone = str(row["Phone"]).replace(".0", "")
            rows.append({
                "name": row["Name"],
                "phone": phone,
                "distance_km": row["Distance"],
                "lat": row["Latitude"],
                "lon": row["Longitude"],
            })
        out[unit] = rows
    return out

with tab_ai:
    if AI_AVAILABLE:
        render_ai_chat_tab(
            user_lat=st.session_state.lat,
            user_lon=st.session_state.lon,
            hospital_lookup_fn=find_nearest_hospital,
        )
    else:
        st.error("ai_chat.py not found — place it in the same folder as app.py.")

