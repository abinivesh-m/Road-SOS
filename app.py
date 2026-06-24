import os
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
from ui import (
    inject_theme,
    render_hero,
    render_dashboard,
    render_emergency_banner,
    render_section_header,
    render_service_card_header,
    render_secondary_row,
    render_map_header,
    render_location_card,
    render_no_data,
)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(APP_DIR, "data.csv")

st.set_page_config(
    page_title="NexusSOS",
    layout="centered",
    page_icon="🚨",
    initial_sidebar_state="collapsed",
)

# Inject theme FIRST (before anything renders)
inject_theme()

# Session state defaults

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
}
for key, default in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

lang = st.session_state.language

# Sidebar: language, admin panel

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    lang_options = {code: TRANSLATIONS[code]["lang_name"] for code in TRANSLATIONS}
    selected_lang = st.selectbox(
        t(lang, "language"),
        options=list(lang_options.keys()),
        format_func=lambda code: lang_options[code],
        index=list(lang_options.keys()).index(st.session_state.language),
    )
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()

    if st.session_state.recent_locations:
        with st.expander(t(lang, "recent_locations")):
            for i, loc in enumerate(st.session_state.recent_locations):
                if st.button(
                    f"📍 {loc['label']}", key=f"recent_{i}", use_container_width=True
                ):
                    st.session_state.lat = loc["lat"]
                    st.session_state.lon = loc["lon"]
                    st.session_state.recent_search_trigger = True
                    st.rerun()

    with st.expander(t(lang, "admin_panel")):
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
        else:
            st.caption(t(lang, "admin_add_entry"))
            with st.form("admin_add_form", clear_on_submit=True):
                a_name = st.text_input("Name")
                a_type = st.selectbox(
                    "Type",
                    ["Hospital", "Ambulance", "Police", "Rescue", "Fire",
                     "Towing", "Puncture Shop", "Showroom"],
                )
                a_phone = st.text_input("Phone")
                a_city = st.text_input("City")
                a_country = st.text_input("Country")
                a_lat = st.number_input("Latitude", format="%.6f")
                a_lon = st.number_input("Longitude", format="%.6f")
                submitted = st.form_submit_button("Save")
                if submitted:
                    if a_name and a_phone and a_city and a_country:
                    
                        new_row = {
                                      "Name": a_name,
                                               "Category": a_type,
                                             "Phone": a_phone,
                            "City": a_city, "Country": a_country,
                            "Latitude": a_lat, "Longitude": a_lon,
                        }
                        try:
                            existing_cols = pd.read_csv(DATA_PATH, nrows=0).columns.tolist()
                            row_df = pd.DataFrame(
                                [{c: new_row.get(c, "") for c in existing_cols}]
                            )
                            row_df.to_csv(DATA_PATH, mode="a", header=False, index=False)
                            st.success(t(lang, "admin_entry_saved"))
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not save: {e}")
                    else:
                        st.warning("Please fill in Name, Phone, City and Country.")

# Load & clean data

if not os.path.exists(DATA_PATH):
    st.error(
        f"⚠️ Could not find **data.csv**.\n\n"
        f"Expected:\n`{DATA_PATH}`\n\n"
        "Put `data.csv` in the same folder as `app.py` and reload."
    )
    st.stop()

REQUIRED_COLUMNS = {
    "City",
    "Country",
    "Latitude",
    "Longitude",
    "Name",
    "Phone",
    "Category"
}

try:
    data = pd.read_csv(DATA_PATH, dtype={"Phone": str})
except pd.errors.EmptyDataError:
    st.error("⚠️ **data.csv** is empty. Add at least one row of service data.")
    st.stop()
except Exception as e:
    st.error(f"⚠️ Could not read **data.csv** — it may be corrupted or misformatted.\n\n`{e}`")
    st.stop()

missing_cols = REQUIRED_COLUMNS - set(data.columns)
if missing_cols:
    st.error(
        f"⚠️ **data.csv** is missing required column(s): {', '.join(sorted(missing_cols))}.\n\n"
        f"Expected columns: {', '.join(sorted(REQUIRED_COLUMNS))}"
    )
    st.stop()

data = data.dropna(subset=["Country", "Category", "Latitude", "Longitude"])
data["Country"] = data["Country"].astype(str).str.strip()
data["Category"] = data["Category"].astype(str).str.strip().str.title()

# The CSV stores longer category names than the labels used throughout the

CATEGORY_ALIASES = {
    "Fire Station": "Fire",
    "Tow Service": "Towing",
    "Vehicle Showroom": "Showroom",
    "Rescue Service": "Rescue",
}
data["Category"] = data["Category"].replace(CATEGORY_ALIASES)

if data.empty:
    st.error("⚠️ **data.csv** has no usable rows after cleaning. Check Country/Type/Latitude/Longitude values.")
    st.stop()

# Distance function

def distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Results — CSV only

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
            "live": False,
            "source": "csv",
        })
    return results


def badge_for(_result):
    return t(lang, "csv_data_badge")

# Accent colors per service type

SERVICE_ACCENT = {
    "Hospital":     "#dc2626",
    "Ambulance":    "#f97316",
    "Police":       "#3b82f6",
    "Fire":         "#991b1b",
    "Towing":       "#7c3aed",
    "Puncture Shop":"#0891b2",
    "Showroom":     "#4b5563",
}

SERVICE_MAP_STYLE = {
    "Hospital":     {"color": "red",        "icon": "plus-sign"},
    "Ambulance":    {"color": "orange",     "icon": "ambulance",  "prefix": "fa"},
    "Police":       {"color": "blue",       "icon": "shield",     "prefix": "fa"},
    "Fire":         {"color": "darkred",    "icon": "fire",       "prefix": "fa"},
    "Towing":       {"color": "darkpurple", "icon": "truck",      "prefix": "fa"},
    "Puncture Shop":{"color": "cadetblue",  "icon": "wrench",     "prefix": "fa"},
    "Showroom":     {"color": "gray",       "icon": "car",        "prefix": "fa"},
}

# render_result — uses ui.py card components

def render_result(result, label, key_prefix, service_type, highlight=False):
    badge    = badge_for(result)
    phone    = result["phone"]
    accent   = SERVICE_ACCENT.get(service_type, "#dc2626")
    maps_url = (
        f"https://www.google.com/maps/dir/?api=1&destination="
        f"{result['lat']},{result['lon']}"
    )

    if highlight:
        render_service_card_header(
            result["name"], result["distance_km"], phone, badge, accent_color=accent
        )
    else:
        render_secondary_row(result["name"], result["distance_km"], phone, badge)
        return  # secondary rows don't get buttons

    show_share = service_type in ("Hospital", "Ambulance")
    n_cols = (1 if phone else 0) + 1 + (2 if show_share else 0)
    cols   = st.columns(n_cols)
    col_i  = 0

    if phone:
        with cols[col_i]:
            st.link_button(t(lang, "call_now"), f"tel:{phone}", key=f"{key_prefix}_call")
        col_i += 1

    with cols[col_i]:
        st.link_button(t(lang, "navigate"), maps_url, key=f"{key_prefix}_nav")
    col_i += 1

    if show_share:
        from utils import build_emergency_share_message as _bem
        share_msg = _bem(
            result["name"], result["distance_km"], phone or "N/A",
            result["lat"], result["lon"], label,
        )
        with cols[col_i]:
            st.link_button(
                t(lang, "share_whatsapp"), whatsapp_share_link(share_msg),
                key=f"{key_prefix}_wa"
            )
        col_i += 1
        with cols[col_i]:
            st.link_button(
                t(lang, "share_sms"), sms_share_link(share_msg),
                key=f"{key_prefix}_sms"
            )

# Map renderer

def render_map(user_lat, user_lon, map_points):
    render_map_header()

    if not FOLIUM_AVAILABLE:
        st.caption("Install `folium streamlit-folium` for the interactive map.")
        fallback_df = pd.DataFrame(
            [{"lat": user_lat, "lon": user_lon}]
            + [{"lat": r["lat"], "lon": r["lon"]} for _, r in map_points]
        )
        st.map(fallback_df, latitude="lat", longitude="lon")
        return

    fmap = folium.Map(location=[user_lat, user_lon], tiles="OpenStreetMap")
    folium.Marker(
        [user_lat, user_lon],
        popup="📍 You are here",
        tooltip="Your location",
        icon=folium.Icon(color="green", icon="user", prefix="fa"),
    ).add_to(fmap)

    all_points = [[user_lat, user_lon]]

    for service_type, r in map_points:
        style = SERVICE_MAP_STYLE.get(service_type, {"color": "gray", "icon": "info-sign"})
        popup_html = (
            f"<b>{r['name']}</b><br>"
            f"{service_label(lang, service_type)}<br>"
            f"{round(r['distance_km'], 2)} km away"
        )
        if r["phone"]:
            popup_html += f"<br>📞 {r['phone']}"
        popup_html += (
            f'<br><a href="https://www.google.com/maps/dir/?api=1&destination='
            f'{r["lat"]},{r["lon"]}" target="_blank">Directions</a>'
        )
        folium.Marker(
            [r["lat"], r["lon"]],
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=r["name"],
            icon=folium.Icon(
                color=style["color"],
                icon=style["icon"],
                prefix=style.get("prefix", "glyphicon"),
            ),
        ).add_to(fmap)
        all_points.append([r["lat"], r["lon"]])

    if len(all_points) > 1:
        fmap.fit_bounds(all_points, padding=(40, 40))
    else:
        fmap.location = [user_lat, user_lon]
        fmap.zoom_start = 13

    st_folium(fmap, width=None, height=420, returned_objects=[])

# Hero

render_hero(
    gps_active=st.session_state.lat is not None,
    total_contacts=len(data),
    total_countries=data["Country"].nunique(),
    total_service_types=data["Category"].nunique(),
)

# ONE TAP BUTTON

one_tap_clicked = st.button(
    t(lang, "one_tap"), use_container_width=True, type="primary"
)
if one_tap_clicked:
    st.session_state.emergency_mode = True
    log_event("one_tap_pressed", language=lang)

one_tap = st.session_state.emergency_mode

if one_tap:
    col_exit, _ = st.columns([1, 3])
    with col_exit:
        if st.button("✖ Exit Emergency Mode", key="exit_emergency"):
            st.session_state.emergency_mode = False
            st.rerun()

# Location detector

if not one_tap:
    st.caption(t(lang, "click_below"))
else:
    st.caption(
        "Tap **Allow** when your browser asks — we need your location to find the nearest help."
    )

loc_col1, loc_col2 = st.columns([3, 1])
with loc_col1:
    st.caption(
        "On iPhone or Android, make sure Location is enabled for your browser in phone Settings."
    )
with loc_col2:
    gps_retry = st.button("🔄 Retry", key="gps_retry_btn", use_container_width=True)

if gps_retry:
    st.session_state.gps_attempted = True

if one_tap:
    with st.spinner("📍 Locating nearest emergency services..."):
        loc = streamlit_geolocation()
else:
    loc = streamlit_geolocation()

st.session_state.gps_attempted = True

got_fresh_fix = bool(loc) and loc.get("latitude") is not None

if got_fresh_fix:
    st.session_state.lat = loc["latitude"]
    st.session_state.lon = loc["longitude"]
    st.session_state.gps_accuracy = loc.get("accuracy")
    st.session_state.used_ip_fallback = False
    st.success("📍 Location confirmed — searching for nearest services.")
elif loc and loc.get("latitude") is None and st.session_state.get("gps_attempted"):
    # Component responded but browser didn't return coordinates — permission denied/blocked.
    st.warning(
        "📍 Location access was blocked. "
        "Tap the lock icon in your address bar, set Location to **Allow**, then press **Retry**."
    )

lat = st.session_state.lat
lon = st.session_state.lon

# One Tap with no location → offer IP fallback

if one_tap and (lat is None or lon is None):
    st.error(t(lang, "allow_location"))
    if st.button("📶 " + t(lang, "ip_fallback_used"), key="ip_fallback_btn"):
        with st.spinner("Estimating your approximate location…"):
            ip_lat, ip_lon = get_ip_location()
        if ip_lat is not None:
            st.session_state.lat = ip_lat
            st.session_state.lon = ip_lon
            st.session_state.used_ip_fallback = True
            st.rerun()
        else:
            st.error("Could not detect an approximate location. Check your connection.")
    st.stop()

if st.session_state.used_ip_fallback and lat is not None:
    st.warning(t(lang, "ip_fallback_used") + " (city-level accuracy, not your exact position)")

# Manual fields (hidden during ONE TAP)

recent_search_trigger = st.session_state.pop("recent_search_trigger", False)

if not one_tap:
    use_gps = st.checkbox(t(lang, "use_gps"))
    countries = sorted(data["Country"].unique())
    default_index = countries.index("India") if "India" in countries else 0
    country = st.selectbox(t(lang, "country"), countries, index=default_index)
    city = st.text_input(t(lang, "city"), disabled=use_gps)
    find_clicked = st.button(t(lang, "find_services"))
else:
    use_gps = False
    country = None
    city = ""
    find_clicked = False

# MAIN LOGIC

if find_clicked or one_tap or recent_search_trigger:

    user_lat = None
    user_lon = None
    data_use = None
    location_label = None

    if (one_tap or use_gps or recent_search_trigger) and lat is not None and lon is not None:
        user_lat = lat
        user_lon = lon
        location_label = f"{round(lat, 3)}, {round(lon, 3)}"
        if not recent_search_trigger:
            st.info(t(lang, "using_gps"))
        data_use = data.copy()

    elif city != "":
        city_t = city.title()
        city_data = data[(data["City"] == city_t) & (data["Country"] == country)]
        if city_data.empty:
            st.error(t(lang, "city_not_found"))
            st.stop()
        user_lat = city_data.iloc[0]["Latitude"]
        user_lon = city_data.iloc[0]["Longitude"]
        location_label = f"{city_t}, {country}"
        st.info(location_label)
        data_use = data[data["Country"] == country].copy()

    else:
        st.warning(t(lang, "enter_city_or_gps"))
        if st.session_state.cached_data_use is not None:
            if st.button(t(lang, "using_cached"), key="use_cached_btn"):
                data_use = st.session_state.cached_data_use
                location_label = st.session_state.cached_label
            else:
                st.stop()
        else:
            st.stop()

    if "Distance" not in data_use.columns:
        data_use["Distance"] = data_use.apply(
            lambda row: distance(user_lat, user_lon, row["Latitude"], row["Longitude"]),
            axis=1,
        )
        data_use = data_use.sort_values("Distance")

    st.session_state.cached_data_use = data_use
    st.session_state.cached_label = location_label
    add_recent_location(st.session_state, location_label, user_lat, user_lon)

    # Count found services for dashboard
    hospitals_found  = len(data_use[data_use["Category"] == "Hospital"])
    ambulance_found  = len(data_use[data_use["Category"] == "Ambulance"])
    police_found     = len(data_use[data_use["Category"] == "Police"])

    # Dashboard stats
    render_dashboard(
        gps_active=lat is not None,
        hospitals=hospitals_found,
        ambulances=ambulance_found,
        police=police_found,
        countries=data["Country"].nunique(),
    )

    # ONE TAP EMERGENCY FLOW

    if one_tap:
        render_location_card(user_lat, user_lon, st.session_state.get("gps_accuracy"))
        render_emergency_banner()
        log_event("emergency_results_shown", user_lat, user_lon, lang)

        priority_services = [
            ("Hospital", "🏥", t(lang, "nearest_hospital")),
            ("Ambulance", "🚑", t(lang, "nearest_ambulance")),
            ("Police",   "🚓", t(lang, "nearest_police")),
            ("Fire",     "🚒", t(lang, "nearest_fire")),
        ]

        map_points = []
        ambulance_result = None

        for service, icon, label in priority_services:
            render_section_header(icon, label)
            results = get_results(service, data_use, user_lat, user_lon, n=1)
            if results:
                render_result(
                    results[0], label,
                    key_prefix=f"em_{service}",
                    service_type=service,
                    highlight=True,
                )
                map_points.append((service, results[0]))
                if service == "Ambulance":
                    ambulance_result = results[0]
            else:
                render_no_data(service)

        st.divider()
        render_map(user_lat, user_lon, map_points)
        st.stop()

    # NORMAL SEARCH FLOW
    
    render_section_header("📍", t(lang, "nearby_services"),
                          "Top results per category, closest first")
    log_event("manual_search", user_lat, user_lon, lang)

    services = {
        "Hospital":      "🏥",
        "Ambulance":     "🚑",
        "Police":        "🚓",
        "Fire":          "🚒",
        "Towing":        "🚛",
        "Puncture Shop": "🛞",
        "Showroom":      "🏪",
    }

    map_points = []
    for s, icon in services.items():
        render_section_header(icon, service_label(lang, s))
        results = get_results(s, data_use, user_lat, user_lon, n=5)
        if not results:
            render_no_data(s)
        else:
            for i, result in enumerate(results):
                render_result(
                    result, service_label(lang, s),
                    key_prefix=f"{s}_{i}",
                    service_type=s,
                    highlight=(i == 0),
                )
                if i == 0:
                    map_points.append((s, result))

    st.divider()
    render_map(user_lat, user_lon, map_points)
    st.info(t(lang, "tip_ambulance"))