import csv
import os
from datetime import datetime, timezone
from urllib.parse import quote

import requests

ANALYTICS_FILE = "analytics_log.csv"
RECENT_LOCATIONS_LIMIT = 5

# IP-based location fallback (used only when browser GPS is unavailable)

def get_ip_location():
    try:
        resp = requests.get("https://ipapi.co/json/", timeout=4)
        if resp.status_code == 200:
            j = resp.json()
            lat, lon = j.get("latitude"), j.get("longitude")
            if lat is not None and lon is not None:
                return float(lat), float(lon)
    except Exception:
        pass
    return None, None

# Usage analytics

def log_event(event_type: str, lat=None, lon=None, language="en", extra=""):
    """
    Append a row to analytics_log.csv. Fails silently — analytics should
    never break the emergency flow.
    """
    try:
        file_exists = os.path.isfile(ANALYTICS_FILE)
        with open(ANALYTICS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(
                    ["timestamp", "event", "lat", "lon", "language", "extra"]
                )
            writer.writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    event_type,
                    round(lat, 3) if lat is not None else "",
                    round(lon, 3) if lon is not None else "",
                    language,
                    extra,
                ]
            )
    except Exception:
        pass

# Share links (WhatsApp / SMS) — no API key needed, just deep links

def whatsapp_share_link(message: str) -> str:
    return f"https://wa.me/?text={quote(message)}"


def sms_share_link(message: str) -> str:
    # sms: URI works on most mobile browsers; body param support varies by OS
    return f"sms:?body={quote(message)}"


def build_emergency_share_message(name, distance_km, phone, lat, lon, label):
    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"
    return (
        f"🚨 Emergency — {label}\n"
        f"{name} ({round(distance_km, 2)} km away)\n"
        f"Phone: {phone}\n"
        f"Directions: {maps_url}"
    )

# Recent locations (kept in session, not written to shared disk —
# avoids leaking one user's location history to another user)

def add_recent_location(session_state, label, lat, lon):
    if "recent_locations" not in session_state:
        session_state.recent_locations = []
    entry = {"label": label, "lat": lat, "lon": lon}
    session_state.recent_locations = [
        loc
        for loc in session_state.recent_locations
        if round(loc["lat"], 3) != round(lat, 3)
        or round(loc["lon"], 3) != round(lon, 3)
    ]
    session_state.recent_locations.insert(0, entry)
    session_state.recent_locations = session_state.recent_locations[
        :RECENT_LOCATIONS_LIMIT
    ]