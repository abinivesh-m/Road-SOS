"""
Helper utilities for RoadSOS.
Keeps app.py focused on UI/flow; all "extra" logic lives here.
"""

import csv
import os
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests

ANALYTICS_FILE = "analytics_log.csv"
RECENT_LOCATIONS_LIMIT = 5


# ---------------------------------------------------------------------------
# IP-based location fallback (used only when browser GPS is unavailable)
# ---------------------------------------------------------------------------
def get_ip_location():
    """
    Best-effort approximate location using the requester's IP address.
    No API key required (ipapi.co free tier). Returns (lat, lon) or (None, None).
    NOTE: This is only approximate (city-level) and should never be used for
    the actual ONE TAP EMERGENCY flow if real GPS is available.
    """
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


# ---------------------------------------------------------------------------
# Usage analytics (simple local CSV log — no external service needed)
# ---------------------------------------------------------------------------
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
                    datetime.utcnow().isoformat(),
                    event_type,
                    round(lat, 3) if lat is not None else "",
                    round(lon, 3) if lon is not None else "",
                    language,
                    extra,
                ]
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Share links (WhatsApp / SMS) — no API key needed, just deep links
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Recent locations (kept in session, not written to shared disk —
# avoids leaking one user's location history to another user)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Pending submissions queue (public sign-in users suggest entries here;
# they only reach the live data.csv once an admin approves them)
# ---------------------------------------------------------------------------
PENDING_COLUMNS = [
    "Name", "Type", "Phone", "City", "Country", "Latitude", "Longitude",
    "SubmittedBy", "SubmittedAt", "Status",
]


def add_pending_entry(pending_path: str, entry: dict):
    """Append one submitted entry to the pending queue CSV."""
    file_exists = os.path.isfile(pending_path)
    row = {col: entry.get(col, "") for col in PENDING_COLUMNS}
    row_df = pd.DataFrame([row])
    row_df.to_csv(
        pending_path,
        mode="a",
        header=not file_exists,
        index=False,
    )


def load_pending_entries(pending_path: str) -> pd.DataFrame:
    """Load all entries still awaiting review (Status == 'pending')."""
    if not os.path.isfile(pending_path):
        return pd.DataFrame(columns=PENDING_COLUMNS)
    try:
        df = pd.read_csv(pending_path, dtype={"Phone": str})
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=PENDING_COLUMNS)
    if "Status" not in df.columns:
        return pd.DataFrame(columns=PENDING_COLUMNS)
    return df[df["Status"] == "pending"].copy()


def approve_pending_entry(data_path: str, pending_path: str, row_index: int):
    """
    Move one pending row into the live data.csv, then mark it approved
    in the pending file (kept for an audit trail rather than deleted).
    """
    pending_df = pd.read_csv(pending_path, dtype={"Phone": str})
    row = pending_df.loc[row_index]

    existing_cols = pd.read_csv(data_path, nrows=0).columns.tolist()
    new_row = {c: row.get(c, "") for c in existing_cols}
    pd.DataFrame([new_row]).to_csv(data_path, mode="a", header=False, index=False)

    pending_df.loc[row_index, "Status"] = "approved"
    pending_df.to_csv(pending_path, index=False)


def reject_pending_entry(pending_path: str, row_index: int):
    """Mark one pending row as rejected (kept for an audit trail)."""
    pending_df = pd.read_csv(pending_path, dtype={"Phone": str})
    pending_df.loc[row_index, "Status"] = "rejected"
    pending_df.to_csv(pending_path, index=False)