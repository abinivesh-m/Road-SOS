"""
ai_chat.py — NexusSOS AI Assistant
Powered by Google Gemini with the RoadSOS AI system prompt
developed for IIT Madras CoERS / MoRTH Road Safety Hackathon.
"""

import json
import re
import time as _time
import google.generativeai as genai
import streamlit as st

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None


ROADSOS_SYSTEM_PROMPT = """
You are NexusSOS AI, an Emergency Operations Center assistant for the IIT Madras CoERS / MoRTH Road Safety Hackathon. You are not a chatbot — you analyse the emergency and return ONE JSON object. No markdown, no preamble, no explanation outside the JSON.

INCIDENT (pick exactly one): Road Accident | Vehicle Fire | Medical Emergency | Flood | Road Hazard | Vehicle Breakdown | Chemical Spill | Gas Leak | Electrical Accident | Landslide | Building Collapse | Unknown Emergency

SEVERITY: LOW = no injuries/breakdown/obstruction. MEDIUM = minor injuries, two-vehicle collision. HIGH = serious injuries, trapped persons, multiple victims. CRITICAL = unconscious/heavy bleeding/fire/explosion/multi-vehicle crash/children involved/bus or truck/hazardous chemicals/gas leak.

CONFIDENCE: High = clear description + named location + multiple detail keywords. Medium = partial description or implied location. Low = vague/short message.

ETA (minutes, single integer for the fastest critical unit): Urban — Ambulance 5-10, Fire 8-12, Police 5-8, Tow 15-25. Highway — Ambulance 10-15, Fire 12-20, Police 8-15, Tow 20-35. Unknown location → use highway values.

FIRST AID: 3-5 concise steps relevant to the incident.
RISKS: 2-4 realistic risks for the incident type.
POSSIBLE_INJURIES: one short phrase (3-6 words), e.g. "Severe trauma, possible fractures" or "None expected — breakdown only".
HAZARDS: 1-3 short scene-hazard phrases distinct from risks (e.g. "Fuel leakage"), or empty list if none.
LOCATION: extract a place name if present (e.g. "NH44", "OMR Chennai"), else null.
SMS: under 160 chars, format "[SEVERITY] [INCIDENT] at [LOCATION]. [KEY ACTION]. Call 112."

Return ONLY this JSON shape:
{
  "incident": "Road Accident",
  "severity": "CRITICAL",
  "location": "NH44 near Coimbatore",
  "confidence": "High",
  "possible_injuries": "Severe trauma, possible fractures",
  "hazards": ["Fuel leakage", "Traffic blockage"],
  "risks": ["Secondary collision", "Fuel leakage", "Traffic congestion"],
  "first_aid": [
    "Do not move injured persons unless there is fire risk.",
    "Apply firm pressure to any visible bleeding wounds.",
    "Keep victims conscious by talking to them calmly.",
    "Do not give water to unconscious persons.",
    "Wait for paramedics and guide them to the scene."
  ],
  "eta_minutes": 8,
  "sms": "CRITICAL: Road Accident at NH44 Coimbatore. Ambulance+Police dispatched ETA 8min. Call 112 now."
}

Example — Input: "Tyre burst on Chennai bypass, I am safe but stuck" → Output:
{
  "incident": "Vehicle Breakdown",
  "severity": "LOW",
  "location": "Chennai bypass",
  "confidence": "High",
  "possible_injuries": "None expected — breakdown only",
  "hazards": [],
  "risks": ["Secondary collision from passing traffic", "Night visibility hazard"],
  "first_aid": [
    "Turn on hazard warning lights immediately.",
    "Place reflective triangle 30 metres behind vehicle.",
    "Stay behind the crash barrier, not on the road.",
    "Wear bright clothing if available."
  ],
  "eta_minutes": 22,
  "sms": "LOW: Vehicle Breakdown at Chennai bypass. Tow Truck+Patrol en route ETA 22min. Hazards ON. Call 112."
}
""".strip()


QUICK_SCENARIOS = [
    ("🚗 Road Accident",    "There has been a serious road accident involving multiple vehicles on the highway. There are injured persons."),
    ("🔥 Vehicle Fire",     "A vehicle is on fire on the expressway. The driver is trying to escape."),
    ("🩺 Medical Emergency","A person has collapsed on the road and is unconscious. Possible cardiac arrest."),
    ("⚠️ Breakdown",        "My vehicle has broken down on a busy highway at night. I am alone and unsafe."),
    ("🌧️ Flood / Disaster", "Flash flooding has blocked the highway. Multiple vehicles are stranded in rising water."),
    ("🏗️ Road Hazard",      "A large pothole / missing manhole cover has caused multiple tyre bursts on OMR, Chennai."),
]


DISPATCH_RULES = {
    "Road Accident":      ["Ambulance", "Police"],
    "Vehicle Fire":       ["Fire Rescue", "Ambulance", "Police"],
    "Medical Emergency":  ["Ambulance"],
    "Flood":              ["Fire Rescue", "Disaster Response", "Police"],
    "Road Hazard":        ["Highway Patrol"],
    "Vehicle Breakdown":  ["Tow Truck", "Highway Patrol"],
    "Chemical Spill":     ["Hazmat", "Fire Rescue", "Police"],
    "Gas Leak":           ["Fire Rescue", "Police", "Ambulance"],
    "Electrical Accident":["Ambulance", "Electricity Department", "Fire Rescue"],
    "Landslide":          ["Disaster Response", "Police", "Ambulance"],
    "Building Collapse":  ["Fire Rescue", "Ambulance", "Police", "Disaster Response"],
    "Unknown Emergency":  ["Ambulance", "Police"],
}

UNIT_ICONS = {
    "Ambulance":             "🚑 Ambulance",
    "Police":                "👮 Police",
    "Fire Rescue":           "🚒 Fire & Rescue",
    "Tow Truck":             "🚛 Tow Truck",
    "Hazmat":                "🧪 Hazmat",
    "Electricity Department":"⚡ Electricity Dept",
    "Disaster Response":     "🌊 Disaster Response",
    "Highway Patrol":        "🚔 Highway Patrol",
}

UNIT_BASE_REASON = {
    "Road Accident":      {"Ambulance": "Road accidents may involve injuries",
                            "Police": "Traffic control and incident clearance"},
    "Vehicle Fire":       {"Fire Rescue": "Active fire requires suppression",
                            "Ambulance": "Burn / smoke inhalation risk",
                            "Police": "Traffic control around the fire zone"},
    "Medical Emergency":  {"Ambulance": "Direct medical response required"},
    "Flood":              {"Fire Rescue": "Water rescue capability needed",
                            "Disaster Response": "Multi-vehicle stranding likely",
                            "Police": "Route closure and crowd control"},
    "Road Hazard":        {"Highway Patrol": "Hazard needs marking / clearing"},
    "Vehicle Breakdown":  {"Tow Truck": "Vehicle recovery required",
                            "Highway Patrol": "Roadside safety for stranded vehicle"},
    "Chemical Spill":     {"Hazmat": "Specialised hazardous material handling",
                            "Fire Rescue": "Containment and fire risk",
                            "Police": "Area cordon required"},
    "Gas Leak":           {"Fire Rescue": "Explosion / fire risk containment",
                            "Police": "Area evacuation and cordon",
                            "Ambulance": "Inhalation injury risk"},
    "Electrical Accident":{"Ambulance": "Electrical injury requires medical care",
                            "Electricity Department": "Power isolation required",
                            "Fire Rescue": "Fire risk from electrical fault"},
    "Landslide":          {"Disaster Response": "Heavy debris clearance needed",
                            "Police": "Route closure and crowd control",
                            "Ambulance": "Trapped/injured persons likely"},
    "Building Collapse":  {"Fire Rescue": "Structural rescue required",
                            "Ambulance": "Trapped/injured persons likely",
                            "Police": "Area cordon required",
                            "Disaster Response": "Heavy debris clearance needed"},
    "Unknown Emergency":  {"Ambulance": "Precautionary medical response",
                            "Police": "General scene assessment"},
}

UNIT_SUPPORTING_SIGNAL = {
    "Ambulance":  ["Injury keywords detected", "Children involved"],
    "Fire Rescue": ["Fire / explosion risk", "Hazardous material risk"],
    "Police":     ["Multiple vehicles involved", "Highway / expressway location"],
    "Hazmat":     ["Hazardous material risk"],
}


def get_unit_dispatch_reasons(incident: str, units: list, confidence_reasons: list) -> dict:
    base_reasons = UNIT_BASE_REASON.get(incident, {})
    reasons = {}
    for unit in units:
        lines = []
        base = base_reasons.get(unit)
        if base:
            lines.append(base)
        relevant_signals = UNIT_SUPPORTING_SIGNAL.get(unit, [])
        for signal in confidence_reasons:
            if signal in relevant_signals:
                lines.append(signal)
        if not lines:
            lines.append(f"Standard response unit for {incident}")
        reasons[unit] = lines
    return reasons


OFFLINE_INCIDENT_RULES = [
    ("Vehicle Fire",      ["fire", "burning", "smoke", "explosion"], "HIGH"),
    ("Medical Emergency", ["unconscious", "cardiac", "collapsed", "not breathing"], "HIGH"),
    ("Flood",             ["flood", "flooding", "water level", "submerged"], "MEDIUM"),
    ("Chemical Spill",    ["chemical", "spill", "toxic"], "HIGH"),
    ("Gas Leak",          ["gas leak", "gas smell"], "HIGH"),
    ("Road Hazard",       ["pothole", "manhole", "debris on road"], "LOW"),
    ("Vehicle Breakdown", ["breakdown", "broke down", "flat tyre", "tyre burst", "stalled"], "LOW"),
    ("Road Accident",     ["accident", "collision", "crash", "collided"], "MEDIUM"),
]


AVERAGE_EMERGENCY_SPEED_KMH = {
    "urban":   28,
    "highway": 55,
}

ROAD_DISTANCE_FACTOR = 1.3


def calculate_deterministic_eta(distance_km: float, is_highway: bool = False) -> int:
    if not distance_km or distance_km <= 0:
        return 5
    speed = AVERAGE_EMERGENCY_SPEED_KMH["highway" if is_highway else "urban"]
    road_distance = distance_km * ROAD_DISTANCE_FACTOR
    minutes = (road_distance / speed) * 60
    return max(3, round(minutes))


def offline_classify(raw_message: str) -> dict:
    text = (raw_message or "").lower()

    incident, severity = "Unknown Emergency", "MEDIUM"
    for inc, keywords, sev in OFFLINE_INCIDENT_RULES:
        if any(kw in text for kw in keywords):
            incident, severity = inc, sev
            break

    reasons = extract_confidence_reasons(raw_message)
    if "Injury keywords detected" in reasons or "Fire / explosion risk" in reasons:
        severity = "CRITICAL"

    units = DISPATCH_RULES.get(incident, DISPATCH_RULES["Unknown Emergency"])
    eta_defaults = {"CRITICAL": 8, "HIGH": 10, "MEDIUM": 12, "LOW": 20}

    return {
        "incident": incident,
        "severity": severity,
        "location": None,
        "confidence": "Low",
        "confidence_reasons": reasons,
        "confidence_percent": calculate_confidence_percent("Low", reasons),
        "risks": ["Assessment limited — offline mode active"],
        "possible_injuries": "Unknown — AI unavailable, confirm on scene",
        "hazards": [],
        "first_aid": [
            "Call 112 immediately for professional guidance.",
            "Keep the area around the incident clear.",
            "Do not move injured persons unless there is immediate danger.",
        ],
        "units": units,
        "unit_reasons": get_unit_dispatch_reasons(incident, units, reasons),
        "unit_services": {},
        "eta_minutes": eta_defaults.get(severity, 12),
        "eta_is_calculated": False,
        "sms": f"{severity}: {incident} reported. AI offline — confirm details. Call 112.",
        "nearest_hospital": None,
        "is_offline": True,
        "timeline_clock": [],
        "metadata": {
            "location_raw": None,
            "incident_type": incident,
            "severity_level": severity,
            "confidence_score": 0.0,
        },
        "dispatch_pipeline": {
            "units_activated": units,
            "eta_estimation_minutes": eta_defaults.get(severity, 12),
        },
        "offline_sms_payload": f"{severity}: {incident} reported. AI offline — confirm details. Call 112.",
    }


REASON_KEYWORDS = [
    ("Highway / expressway location",
     ["highway", "expressway", "nh44", "nh-44", "bypass", "flyover", "freeway"]),
    ("Multiple vehicles involved",
     ["multiple vehicle", "multi-vehicle", "multiple vehicles", "several vehicles",
      "two-vehicle", "2 vehicle", "collided", "pile-up", "pileup"]),
    ("Injury keywords detected",
     ["injur", "bleeding", "unconscious", "trapped", "fracture", "wound",
      "collapsed", "cardiac", "not breathing"]),
    ("Fire / explosion risk",
     ["fire", "burning", "smoke", "explosion", "flame"]),
    ("Children involved",
     ["child", "children", "kid", "infant", "school bus"]),
    ("Hazardous material risk",
     ["chemical", "gas leak", "fuel leak", "spill", "toxic"]),
    ("Named location provided",
     ["road", "street", "chennai", "coimbatore", "bengaluru", "mumbai",
      "delhi", "hyderabad", "omr", "gst road", "bypass", "junction"]),
]


def extract_confidence_reasons(raw_message: str) -> list:
    if not raw_message:
        return []
    text = raw_message.lower()
    matched = []
    for label, keywords in REASON_KEYWORDS:
        if any(kw in text for kw in keywords):
            matched.append(label)
    return matched


CONFIDENCE_BAND = {
    "HIGH":   (70, 95),
    "MEDIUM": (40, 70),
    "LOW":    (15, 40),
}


def calculate_confidence_percent(confidence_label: str, confidence_reasons: list) -> int:
    label = (confidence_label or "Medium").upper()
    low, high = CONFIDENCE_BAND.get(label, CONFIDENCE_BAND["MEDIUM"])
    n_reasons = len(confidence_reasons or [])
    pct = min(high, low + n_reasons * 6)
    return pct


SEVERITY_CONFIG = {
    "CRITICAL": {"color": "#dc2626", "bg": "rgba(220,38,38,0.12)", "border": "rgba(220,38,38,0.4)",  "label": "🔴 CRITICAL", "pulse": True},
    "HIGH":     {"color": "#f97316", "bg": "rgba(249,115,22,0.10)", "border": "rgba(249,115,22,0.35)", "label": "🟠 HIGH",     "pulse": False},
    "MEDIUM":   {"color": "#eab308", "bg": "rgba(234,179,8,0.10)",  "border": "rgba(234,179,8,0.35)",  "label": "🟡 MEDIUM",   "pulse": False},
    "LOW":      {"color": "#22c55e", "bg": "rgba(34,197,94,0.08)",  "border": "rgba(34,197,94,0.3)",   "label": "🟢 LOW",      "pulse": False},
    "MODERATE": {"color": "#f97316", "bg": "rgba(249,115,22,0.10)", "border": "rgba(249,115,22,0.35)", "label": "🟠 MODERATE", "pulse": False},
    "MINOR":    {"color": "#22c55e", "bg": "rgba(34,197,94,0.08)",  "border": "rgba(34,197,94,0.3)",   "label": "🟢 LOW",      "pulse": False},
}


try:
    from google.api_core import exceptions as _google_exceptions
    _TRANSIENT_EXCEPTIONS = (
        _google_exceptions.ResourceExhausted,
        _google_exceptions.ServiceUnavailable,
        _google_exceptions.DeadlineExceeded,
        _google_exceptions.InternalServerError,
        _google_exceptions.TooManyRequests,
    )
except ImportError:
    _google_exceptions = None
    _TRANSIENT_EXCEPTIONS = ()

_TRANSIENT_MESSAGE_HINTS = (
    "429", "resource_exhausted", "rate limit", "quota",
    "503", "service unavailable", "internal error", "500",
    "deadline exceeded", "timeout",
)


def _is_transient_error(exc: Exception) -> bool:
    if _TRANSIENT_EXCEPTIONS and isinstance(exc, _TRANSIENT_EXCEPTIONS):
        return True
    msg = str(exc).lower()
    return any(hint in msg for hint in _TRANSIENT_MESSAGE_HINTS)


def call_roadsos_ai(messages, api_key, max_retries=3, on_retry=None):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = ROADSOS_SYSTEM_PROMPT + "\n\n"
    for msg in messages:
        prompt += f"{msg['role'].upper()}: {msg['content']}\n"

    last_exc = None
    total_attempts = max_retries + 1
    for attempt in range(1, total_attempts + 1):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_exc = e
            is_last_attempt = attempt == total_attempts
            if is_last_attempt or not _is_transient_error(e):
                raise
            wait_seconds = min(2 ** attempt, 16)
            if on_retry:
                try:
                    on_retry(attempt, wait_seconds, total_attempts)
                except Exception:
                    pass
            _time.sleep(wait_seconds)

    raise last_exc


def parse_ai_response(raw: str, user_message: str = "", nearest_hospital: dict = None) -> tuple:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return raw.strip(), None

    try:
        data = json.loads(match.group(0))
    except (json.JSONDecodeError, ValueError):
        return raw.strip(), None

    incident   = data.get("incident") or "Unknown Emergency"
    severity   = (data.get("severity") or "MEDIUM").upper()
    location   = data.get("location")
    confidence = data.get("confidence", "Medium")
    risks      = data.get("risks", [])
    possible_injuries = data.get("possible_injuries") or "Not specified"
    hazards    = data.get("hazards", [])
    first_aid  = data.get("first_aid", [])
    eta_min    = data.get("eta_minutes")
    sms        = data.get("sms", "")

    units = DISPATCH_RULES.get(incident, DISPATCH_RULES["Unknown Emergency"])
    confidence_reasons = extract_confidence_reasons(user_message)

    eta_is_calculated = False
    if nearest_hospital and nearest_hospital.get("distance_km"):
        is_highway = "highway" in (user_message or "").lower() or "expressway" in (user_message or "").lower()
        eta_min = calculate_deterministic_eta(nearest_hospital["distance_km"], is_highway)
        eta_is_calculated = True

    dispatch = {
        "incident":  incident,
        "severity":  severity,
        "location":  location,
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "confidence_percent": calculate_confidence_percent(confidence, confidence_reasons),
        "risks":     risks,
        "possible_injuries": possible_injuries,
        "hazards":   hazards,
        "first_aid": first_aid,
        "units":     units,
        "unit_reasons": get_unit_dispatch_reasons(incident, units, confidence_reasons),
        "unit_services": {},
        "eta_minutes": eta_min,
        "eta_is_calculated": eta_is_calculated,
        "sms":       sms,
        "nearest_hospital": nearest_hospital,
        "is_offline": False,
        "timeline_clock": [],
        "metadata": {
            "location_raw":    location,
            "incident_type":   incident,
            "severity_level":  severity,
            "confidence_score": 1.0,
        },
        "dispatch_pipeline": {
            "units_activated":      units,
            "eta_estimation_minutes": eta_min,
        },
        "offline_sms_payload": sms,
    }

    loc_str = location if location else "location not provided"
    conv_text = (
        f"🚨 Emergency classified as **{incident}** · Severity **{severity}**\n\n"
        f"📍 Location: {loc_str}\n\n"
        + ("**🩺 Immediate Actions:**\n" + "\n".join(f"• {s}" for s in first_aid[:3]) if first_aid else "")
    )

    return conv_text, dispatch


def render_dispatch_card(dispatch: dict):
    if not dispatch:
        return

    is_offline = bool(dispatch.get("is_offline"))


    if is_offline:
        st.markdown(
            '<div style="background:linear-gradient(135deg,rgba(100,116,139,.18),rgba(71,85,105,.12));'
            'border:1.5px solid rgba(148,163,184,.45);border-radius:12px;padding:.8rem 1rem;'
            'margin-bottom:.6rem;">'
            '<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem;">'
            '<span style="font-size:1.1rem;">📡</span>'
            '<span style="font-size:.85rem;font-weight:800;color:#e2e8f0;">AI Offline</span>'
            '<span style="margin-left:auto;font-size:.62rem;font-weight:700;color:#fbbf24;'
            'background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.3);'
            'padding:.12rem .5rem;border-radius:99px;">RULE ENGINE ACTIVE</span></div>'
            '<div style="font-size:.74rem;color:#94a3b8;line-height:1.6;">'
            '✓ Using Emergency Rule Engine<br>'
            '✓ Nearest Services Still Available<br>'
            '<span style="color:#cbd5e1;font-weight:600;">The app still works — '
            'verify details on scene and call 112.</span></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    severity   = (dispatch.get("severity") or "MEDIUM").upper()
    sev        = SEVERITY_CONFIG.get(severity, SEVERITY_CONFIG["MEDIUM"])
    location   = dispatch.get("location") or None
    incident   = dispatch.get("incident") or "Unknown Emergency"
    confidence = dispatch.get("confidence", "Medium")
    confidence_reasons = dispatch.get("confidence_reasons") or []
    confidence_percent = dispatch.get("confidence_percent") or calculate_confidence_percent(confidence, confidence_reasons)
    units      = dispatch.get("units") or []
    risks      = dispatch.get("risks") or []
    first_aid  = dispatch.get("first_aid") or []
    eta_min    = dispatch.get("eta_minutes")
    eta_is_calculated = dispatch.get("eta_is_calculated", False)
    sms        = dispatch.get("sms") or dispatch.get("offline_sms_payload") or ""

    if not eta_min or eta_min == 0:
        eta_defaults = {"CRITICAL": 8, "HIGH": 10, "MEDIUM": 12, "LOW": 20,
                        "MODERATE": 12, "MINOR": 20}
        eta_min = eta_defaults.get(severity, 10)

    loc_display = location if location else "Not Provided"
    pulse_css = "animation:pulse-border 1.5s infinite;" if sev["pulse"] else ""


    st.markdown(
        f'<div style="background:{sev["bg"]};border:1.5px solid {sev["border"]};'
        f'border-radius:14px;padding:1rem 1.2rem;margin:.6rem 0;{pulse_css}">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:.4rem;margin-bottom:.75rem;">'
        f'<span style="font-size:.9rem;font-weight:800;color:{sev["color"]};'
        f'letter-spacing:.05em;">{sev["label"]}</span>'
        f'<span style="font-size:.72rem;color:#64748b;font-weight:600;">'
        f'Confidence: {confidence}</span>'
        f'</div>'
        f'<div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem;">'
        f'<div style="flex:1;height:8px;background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden;">'
        f'<div style="height:100%;width:{confidence_percent}%;border-radius:99px;'
        f'background:linear-gradient(90deg,{sev["color"]}99,{sev["color"]});'
        f'transition:width .4s ease;"></div></div>'
        f'<span style="font-size:.72rem;font-weight:800;color:{sev["color"]};min-width:32px;text-align:right;">'
        f'{confidence_percent}%</span>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:.55rem;'
        f'font-size:.8rem;margin-bottom:.25rem;">'
        f'<div><div style="color:#64748b;font-weight:600;font-size:.68rem;'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem;">📍 Location</div>'
        f'<div style="color:#f1f5f9;font-weight:700;word-break:break-word;">{loc_display}</div></div>'
        f'<div><div style="color:#64748b;font-weight:600;font-size:.68rem;'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.2rem;">🚗 Incident</div>'
        f'<div style="color:#f1f5f9;font-weight:700;word-break:break-word;">{incident}</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


    if confidence_reasons:
        reason_pills = "".join(
            f'<span style="background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);'
            f'border-radius:6px;padding:.2rem .55rem;font-size:.7rem;color:#86efac;'
            f'font-weight:600;">✓ {r}</span>'
            for r in confidence_reasons
        )
        st.markdown(
            f'<div style="margin:.1rem 0 .6rem;">'
            f'<div style="color:#64748b;font-weight:600;font-size:.68rem;text-transform:uppercase;'
            f'letter-spacing:.06em;margin:.2rem 0 .4rem;">❓ Why this severity?</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;">{reason_pills}</div>'
            f'<div style="font-size:.68rem;color:#64748b;margin-top:.4rem;">'
            f'→ Severity = {sev["label"].split(" ", 1)[-1].title()}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


    possible_injuries = dispatch.get("possible_injuries") or "Not specified"
    hazards    = dispatch.get("hazards") or []
    nearest_hospital = dispatch.get("nearest_hospital")

    hazard_html = (
        "".join(
            f'<span style="background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.3);'
            f'border-radius:6px;padding:.2rem .55rem;font-size:.7rem;color:#fdba74;'
            f'font-weight:600;margin-right:.25rem;display:inline-block;margin-bottom:.2rem;">'
            f'⚠ {h}</span>'
            for h in hazards
        )
        if hazards else
        '<span style="font-size:.78rem;color:#64748b;">No notable scene hazards</span>'
    )

    if nearest_hospital and nearest_hospital.get("name"):
        hospital_html = (
            f'<div style="color:#f1f5f9;font-weight:700;">{nearest_hospital["name"]}</div>'
            f'<div style="font-size:.72rem;color:#94a3b8;margin-top:.1rem;">'
            f'📍 {round(nearest_hospital.get("distance_km", 0), 1)} km away '
            f'<span style="color:#4ade80;">· From live directory</span></div>'
        )
    else:
        hospital_html = (
            '<div style="font-size:.78rem;color:#64748b;">'
            'No hospital data nearby — enable GPS or search by city</div>'
        )

    st.markdown(
        f'<div style="background:var(--surface);border:1px solid var(--border);'
        f'border-radius:10px;padding:.75rem 1rem;margin-bottom:.75rem;">'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:.7rem;font-size:.8rem;">'
        f'<div><div style="color:#64748b;font-weight:600;font-size:.68rem;'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.25rem;">🩹 Possible Injuries</div>'
        f'<div style="color:#f1f5f9;font-weight:600;">{possible_injuries}</div></div>'
        f'<div><div style="color:#64748b;font-weight:600;font-size:.68rem;'
        f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.25rem;">🏥 Nearest Hospital</div>'
        f'{hospital_html}</div></div>'
        f'<div style="margin-top:.65rem;">'
        f'<div style="color:#64748b;font-weight:600;font-size:.68rem;text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:.3rem;">⚠️ Scene Hazards</div>'
        f'{hazard_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


    if units:
        unit_services = dispatch.get("unit_services") or {}

        eta_basis = (
            "From real distance ÷ avg. speed" if eta_is_calculated
            else "AI estimate — no GPS distance available"
        )
        eta_block = (
            f'<div style="background:rgba(249,115,22,.12);border:1px solid rgba(249,115,22,.35);'
            f'border-radius:10px;padding:.5rem .8rem;text-align:center;min-width:90px;">'
            f'<div style="font-size:.62rem;color:#94a3b8;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.06em;">ETA</div>'
            f'<div style="font-size:1.45rem;font-weight:900;color:#f97316;line-height:1.1;">{eta_min}</div>'
            f'<div style="font-size:.62rem;color:#94a3b8;">min</div>'
            f'<div style="font-size:.58rem;color:#64748b;margin-top:.2rem;line-height:1.2;">{eta_basis}</div>'
            f'</div>'
        )

        st.markdown(
            '<div style="color:#64748b;font-weight:600;font-size:.68rem;text-transform:uppercase;'
            'letter-spacing:.06em;margin:.2rem 0 .4rem;">🚨 AI Recommended Response</div>',
            unsafe_allow_html=True,
        )

        for u in units:
            services = unit_services.get(u, [])
            unit_label = UNIT_ICONS.get(u, u)

            if services:
                svc = services[0]
                st.markdown(
                    f'<div style="background:#0f172a;border:1px solid #334155;'
                    f'border-radius:10px;padding:.6rem .85rem;margin-bottom:.4rem;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem;">'
                    f'<div style="font-size:.7rem;color:#94a3b8;font-weight:700;">{unit_label}</div>'
                    f'<div style="font-size:.68rem;color:#f97316;font-weight:700;">'
                    f'📍 {round(svc["distance_km"],1)} km</div></div>'
                    f'<div style="font-size:.88rem;color:#f1f5f9;font-weight:700;margin-top:.2rem;">'
                    f'{svc["name"]}</div>'
                    + (f'<div style="font-size:.72rem;color:#64748b;margin-top:.1rem;">📞 {svc["phone"]}</div>'
                       if svc["phone"] else "")
                    + '</div>',
                    unsafe_allow_html=True,
                )
                maps_url = (
                    f'https://www.google.com/maps/dir/?api=1'
                    f'&destination={svc["lat"]},{svc["lon"]}'
                )
                if svc["phone"]:
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        st.link_button("📞 Call", f'tel:{svc["phone"]}',
                                       key=f"ai_call_{u}_{hash(svc['name'])}",
                                       use_container_width=True)
                    with bc2:
                        st.link_button("🗺️ Navigate", maps_url,
                                       key=f"ai_nav_{u}_{hash(svc['name'])}",
                                       use_container_width=True)
                else:
                    st.link_button("🗺️ Navigate", maps_url,
                                   key=f"ai_nav_{u}_{hash(svc['name'])}",
                                   use_container_width=True)
            else:
                st.markdown(
                    f'<div style="background:#0f172a;border:1px solid #334155;border-radius:10px;'
                    f'padding:.55rem .85rem;margin-bottom:.4rem;font-size:.8rem;font-weight:700;'
                    f'color:#e2e8f0;">{unit_label}'
                    f'<span style="font-size:.68rem;color:#64748b;font-weight:500;margin-left:.4rem;">'
                    f'— enable GPS for nearest unit</span></div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;margin-bottom:.6rem;">{eta_block}</div>',
            unsafe_allow_html=True,
        )


        unit_reasons = dispatch.get("unit_reasons") or {}
        if unit_reasons:
            with st.expander("❓ Why these units?", expanded=False):
                for u in units:
                    lines = unit_reasons.get(u, [])
                    reason_text = "".join(f"<li>{line}</li>" for line in lines)
                    st.markdown(
                        f'<div style="margin-bottom:.6rem;">'
                        f'<div style="font-weight:700;font-size:.82rem;color:#e2e8f0;">'
                        f'{UNIT_ICONS.get(u, u)}</div>'
                        f'<ul style="margin:.25rem 0 0;padding-left:1.2rem;font-size:.76rem;'
                        f'color:#94a3b8;line-height:1.5;">{reason_text}</ul>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


    if risks:
        risk_pills = "".join(
            f'<span style="background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);'
            f'border-radius:6px;padding:.2rem .6rem;font-size:.7rem;color:#fca5a5;'
            f'font-weight:600;">⚠️ {r}</span>'
            for r in risks
        )
        st.markdown(
            f'<div style="margin-bottom:.75rem;">'
            f'<div style="color:#64748b;font-weight:600;font-size:.68rem;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:.4rem;">🔺 Identified Risks</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:.3rem;">{risk_pills}</div></div>',
            unsafe_allow_html=True,
        )


    if first_aid:
        fa_items = "".join(
            f'<li style="margin-bottom:.3rem;color:#e2e8f0;">{step}</li>'
            for step in first_aid
        )
        st.markdown(
            f'<div style="background:rgba(34,197,94,.06);border:1px solid rgba(34,197,94,.2);'
            f'border-radius:10px;padding:.7rem 1rem;margin-bottom:.75rem;">'
            f'<div style="color:#4ade80;font-weight:700;font-size:.75rem;text-transform:uppercase;'
            f'letter-spacing:.06em;margin-bottom:.45rem;">🩺 First Aid Instructions</div>'
            f'<ul style="margin:0;padding-left:1.2rem;font-size:.82rem;line-height:1.6;">{fa_items}</ul>'
            f'</div>',
            unsafe_allow_html=True,
        )


    if sms:
        st.markdown(
            '<div style="font-size:.68rem;color:#64748b;font-weight:700;text-transform:uppercase;'
            'letter-spacing:.06em;margin:.6rem 0 .25rem;">📱 Offline SMS Relay (160 chars)</div>',
            unsafe_allow_html=True,
        )
        col_sms, col_copy = st.columns([5, 1])
        with col_sms:
            st.code(sms, language=None)
        with col_copy:
            st.markdown("<div style='margin-top:.35rem;'></div>", unsafe_allow_html=True)
            if st.button("📋 Copy", key=f"copy_sms_{id(dispatch)}", use_container_width=True,
                         help="Copy SMS to clipboard"):
                st.write(
                    f"<script>navigator.clipboard.writeText({json.dumps(sms)})</script>",
                    unsafe_allow_html=True,
                )
                st.toast("SMS copied!", icon="✅")


    timeline_clock = dispatch.get("timeline_clock") or []
    if timeline_clock:
        with st.expander("🕒 Incident Timeline", expanded=False):
            rows = "".join(
                f'<div style="display:flex;align-items:baseline;gap:.7rem;margin-bottom:.5rem;">'
                f'<span style="font-size:.72rem;color:#64748b;font-weight:700;min-width:64px;'
                f'font-family:monospace;">{_time.strftime("%H:%M:%S", _time.localtime(ts))}</span>'
                f'<span style="font-size:.8rem;color:#4ade80;">✓</span>'
                f'<span style="font-size:.8rem;color:#e2e8f0;">{label}</span>'
                f'</div>'
                for label, ts in timeline_clock
            )
            st.markdown(
                f'<div style="border-left:2px solid rgba(74,222,128,.3);padding-left:.8rem;">'
                f'{rows}</div>',
                unsafe_allow_html=True,
            )
            st.caption("Timestamps are real wall-clock times measured during this request.")


def render_chat_message(role: str, text: str, dispatch: dict = None):
    if role == "user":
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;margin:.4rem 0;">'
            f'<div style="background:#1e3a5f;border:1px solid #1e4976;border-radius:14px 14px 4px 14px;'
            f'padding:.65rem 1rem;max-width:82%;font-size:.88rem;color:#e2e8f0;'
            f'line-height:1.5;">{text}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="display:flex;gap:.55rem;margin:.4rem 0;align-items:flex-start;">'
            f'<div style="background:linear-gradient(135deg,#dc2626,#f97316);border-radius:8px;'
            f'width:30px;height:30px;display:flex;align-items:center;justify-content:center;'
            f'font-size:.85rem;flex-shrink:0;margin-top:2px;">🤖</div>'
            f'<div style="background:#1e293b;border:1px solid rgba(255,255,255,0.08);'
            f'border-radius:4px 14px 14px 14px;padding:.65rem 1rem;max-width:88%;'
            f'font-size:.88rem;color:#e2e8f0;line-height:1.55;font-weight:500;">{text}</div></div>',
            unsafe_allow_html=True,
        )
        if dispatch:
            render_dispatch_card(dispatch)


def render_ai_chat_tab(user_lat=None, user_lon=None,
                       hospital_lookup_fn=None, service_lookup_fn=None):
    """
    Full AI Triage chat tab.

    hospital_lookup_fn: callable(lat, lon) -> {"name", "distance_km"} | None
    service_lookup_fn:  callable(lat, lon, units, n_each) -> {unit: [services]}
                        — grounds AI dispatch in real services from data.csv.
    """

    if "ai_messages"   not in st.session_state:
        st.session_state.ai_messages   = []
    if "ai_history"    not in st.session_state:
        st.session_state.ai_history    = []
    if "ai_input_key"  not in st.session_state:
        st.session_state.ai_input_key  = 0
    if "ai_pending"    not in st.session_state:
        st.session_state.ai_pending    = None

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None


    st.markdown(
        '<div style="background:linear-gradient(135deg,#1e293b,#0f172a);'
        'border:1px solid rgba(220,38,38,0.25);border-radius:16px;'
        'padding:1.1rem 1.4rem;margin-bottom:1rem;">'
        '<div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.35rem;">'
        '<div style="background:linear-gradient(135deg,#dc2626,#f97316);border-radius:10px;'
        'width:38px;height:38px;display:flex;align-items:center;justify-content:center;'
        'font-size:1.1rem;">🤖</div>'
        '<div>'
        '<div style="font-size:1rem;font-weight:800;color:#f1f5f9;">NexusSOS AI Assistant Engine</div>'
        '<div style="font-size:.73rem;color:#64748b;">IIT Madras CoERS · MoRTH · google gemini</div>'
        '</div></div>'
        '<div style="font-size:.78rem;color:#94a3b8;line-height:1.5;">'
        '<strong style="color:#cbd5e1;">Describe the emergency.</strong> NexusSOS AI classifies severity, '
        'recommends response units, finds the nearest emergency services, generates first-aid guidance, '
        'and prepares emergency alerts in seconds.'
        '</div></div>',
        unsafe_allow_html=True,
    )


    if user_lat and user_lon:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:.4rem;font-size:.74rem;'
            f'color:#4ade80;margin-bottom:.7rem;">📍 Location active · '
            f'{round(user_lat,4)}, {round(user_lon,4)}'
            f'<span style="color:#64748b;"> — nearest services + ETA use real distance</span></div>',
            unsafe_allow_html=True,
        )
    else:
     st.info(
        "Please enable location from the Home page first. Once enabled, the AI Assistant will automatically use your current location."
    )

    if st.button("🔄 Refresh Location", key="ai_refresh_location"):
        st.rerun()


    if not api_key:
        st.markdown(
            '<div style="background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.4);'
            'border-radius:12px;padding:.9rem 1.1rem;font-size:.82rem;">'
            '<strong style="color:#f97316;">⚙️ Setup Required</strong><br><br>'
            'Add your Gemini API Key to <code>.streamlit/secrets.toml</code>:'
            '<pre style="background:#0f172a;border-radius:8px;padding:.6rem;margin:.5rem 0 0;'
            'font-size:.78rem;color:#86efac;">GEMINI_API_KEY = "AIza..."</pre>'
            'Get a key at <strong>https://aistudio.google.com/apikey</strong>'
            '</div>',
            unsafe_allow_html=True,
        )
        return


    st.markdown(
        '<div style="font-size:.72rem;color:#64748b;font-weight:700;text-transform:uppercase;'
        'letter-spacing:.06em;margin-bottom:.4rem;">⚡ Quick Scenarios</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for i, (label, prompt) in enumerate(QUICK_SCENARIOS):
        with cols[i % 3]:
            if st.button(label, key=f"quick_{i}", use_container_width=True):
                st.session_state.ai_pending = prompt

    st.markdown("<div style='margin-bottom:.5rem;'></div>", unsafe_allow_html=True)


    loc_hint = (
        f" (GPS: {round(user_lat,4)}, {round(user_lon,4)})"
        if user_lat and user_lon else ""
    )
    user_input = st.chat_input(
        f"Describe the emergency{loc_hint}…",
        key=f"ai_chat_input_{st.session_state.ai_input_key}",
    )

    final_input = None
    if user_input and user_input.strip():
        final_input = user_input.strip()
    elif st.session_state.ai_pending:
        final_input = st.session_state.ai_pending
        st.session_state.ai_pending = None

    raw_user_text = final_input

    if final_input and user_lat and user_lon:
        if "gps" not in final_input.lower() and "lat" not in final_input.lower():
            final_input += f" [GPS: {round(user_lat,5)}, {round(user_lon,5)}]"


    if final_input:
        st.session_state.ai_messages.append({
            "role": "user", "content": final_input, "dispatch": None
        })
        st.session_state.ai_history.append({"role": "user", "content": final_input})

        t_start = _time.time()
        timeline = [("Emergency Reported", t_start)]

        nearest_hospital = None
        if hospital_lookup_fn and user_lat and user_lon:
            try:
                nearest_hospital = hospital_lookup_fn(user_lat, user_lon)
            except Exception:
                nearest_hospital = None
        timeline.append(("Nearest Hospital Selected", _time.time()))

        status_box = st.empty()

        LOADING_STEPS = [
            "Detecting incident",
            "Estimating severity",
            "Finding nearest responders",
            "Generating first aid",
            "Preparing emergency report",
        ]

        def _show_status(active_step_idx, sub=""):
            items_html = "".join(
                f'<div style="font-size:.74rem;color:{"#4ade80" if i < active_step_idx else "#64748b"};'
                f'margin-top:.2rem;">{"✓" if i < active_step_idx else "○"} {step}</div>'
                for i, step in enumerate(LOADING_STEPS)
            )
            sub_html = f'<div style="font-size:.68rem;color:#475569;margin-top:.3rem;">{sub}</div>' if sub else ""
            status_box.markdown(
                f'<div style="background:var(--surface);border:1px solid var(--border);'
                f'border-radius:10px;padding:.7rem 1rem;font-size:.82rem;color:#e2e8f0;">'
                f'🧠 AI analysing…{items_html}{sub_html}</div>',
                unsafe_allow_html=True,
            )

        _show_status(2)

        def _on_retry(attempt, wait_seconds, total_attempts):
            status_box.markdown(
                f'<div style="background:var(--surface);border:1px solid var(--border);'
                f'border-radius:10px;padding:.7rem 1rem;font-size:.82rem;color:#fdba74;">'
                f'⏳ AI temporarily busy — retrying…'
                f'<div style="font-size:.7rem;color:#64748b;margin-top:.15rem;">'
                f'Attempt {attempt + 1}/{total_attempts} · waiting {wait_seconds}s</div></div>',
                unsafe_allow_html=True,
            )

        ai_failed = False
        try:
            raw_response = call_roadsos_ai(
                st.session_state.ai_history, api_key, max_retries=3, on_retry=_on_retry
            )
            timeline.append(("AI Classified", _time.time()))
            _show_status(4, "Generating first aid · preparing SMS")

            conv_text, dispatch = parse_ai_response(
                raw_response, raw_user_text, nearest_hospital
            )
            timeline.append(("Dispatch Generated", _time.time()))

            st.session_state.ai_history.append({
                "role": "assistant",
                "content": raw_response,
            })

            if dispatch is None:
                ai_failed = True
                dispatch = offline_classify(raw_user_text)
                dispatch["nearest_hospital"] = nearest_hospital
                conv_text = (
                    "📡 **Offline Mode** — AI response could not be parsed, "
                    "using rule-based estimate.\n\n"
                    f"Classified as **{dispatch['incident']}** · Severity **{dispatch['severity']}**"
                )

        except Exception:
            ai_failed = True
            dispatch = offline_classify(raw_user_text)
            dispatch["nearest_hospital"] = nearest_hospital
            timeline.append(("AI Classified (Offline Fallback)", _time.time()))
            timeline.append(("Dispatch Generated", _time.time()))
            conv_text = (
                f"📡 **Offline Mode** — AI unavailable, using rule-based estimate.\n\n"
                f"Classified as **{dispatch['incident']}** · Severity **{dispatch['severity']}**\n\n"
                f"📍 Location: location not provided"
            )
            st.session_state.ai_history.append({
                "role": "assistant",
                "content": "[offline fallback — no AI response generated]",
            })

        if dispatch is None:
            dispatch = offline_classify(raw_user_text)
            dispatch["nearest_hospital"] = nearest_hospital


        dispatch["unit_services"] = {}
        if service_lookup_fn and user_lat and user_lon and dispatch.get("units"):
            try:
                dispatch["unit_services"] = service_lookup_fn(
                    user_lat, user_lon, dispatch["units"], 1
                )
            except Exception:
                dispatch["unit_services"] = {}
        timeline.append(("Nearest Services Located", _time.time()))
        timeline.append(("Emergency SMS Generated", _time.time()))

        status_box.empty()


        dispatch["timeline"] = [
            (label, round(ts - t_start, 1)) for label, ts in timeline
        ]
        dispatch["timeline_clock"] = [
            (label, ts) for label, ts in timeline
        ]

        st.session_state.ai_messages.append({
            "role": "assistant",
            "content": conv_text,
            "dispatch": dispatch,
        })
        st.session_state.ai_input_key += 1

        if ai_failed:
            st.toast("AI unavailable — switched to offline mode", icon="📡")


    if not st.session_state.ai_messages:
        st.markdown(
            '<div style="text-align:center;padding:2.5rem 1rem;color:#475569;font-size:.85rem;">'
            '<div style="font-size:2rem;margin-bottom:.5rem;">🚨</div>'
            'Describe a road incident above or tap a Quick Scenario.<br>'
            '<span style="font-size:.75rem;">The AI will triage severity, extract location, '
            'and activate the dispatch pipeline.</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.ai_messages:
            render_chat_message(msg["role"], msg["content"], msg.get("dispatch"))


    if st.session_state.ai_messages:
        st.markdown("<div style='margin-top:.75rem;'></div>", unsafe_allow_html=True)
        col_clr, _ = st.columns([1, 4])
        with col_clr:
            if st.button("🗑️ Clear Chat", key="ai_clear", use_container_width=True):
                st.session_state.ai_messages  = []
                st.session_state.ai_history   = []
                st.session_state.ai_input_key += 1
                st.rerun()


    ai_msgs = st.session_state.ai_messages
    ai_responses = [m for m in ai_msgs if m["role"] == "assistant" and m.get("dispatch")]
    if ai_responses:
        critical = sum(1 for m in ai_responses
                       if (m["dispatch"].get("severity") or "").upper() == "CRITICAL")
        high     = sum(1 for m in ai_responses
                       if (m["dispatch"].get("severity") or "").upper() in ("HIGH", "MODERATE"))
        low      = sum(1 for m in ai_responses
                       if (m["dispatch"].get("severity") or "").upper() in ("LOW", "MEDIUM", "MINOR"))
        total    = len(ai_responses)

        st.markdown(
            f'<div style="display:flex;gap:.4rem;margin-top:.6rem;flex-wrap:wrap;">'
            f'<div style="flex:1;background:rgba(220,38,38,.1);border:1px solid rgba(220,38,38,.3);'
            f'border-radius:10px;padding:.45rem .6rem;text-align:center;">'
            f'<div style="font-size:1.1rem;font-weight:800;color:#dc2626;">{critical}</div>'
            f'<div style="font-size:.62rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Critical</div></div>'
            f'<div style="flex:1;background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.3);'
            f'border-radius:10px;padding:.45rem .6rem;text-align:center;">'
            f'<div style="font-size:1.1rem;font-weight:800;color:#f97316;">{high}</div>'
            f'<div style="font-size:.62rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">High</div></div>'
            f'<div style="flex:1;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);'
            f'border-radius:10px;padding:.45rem .6rem;text-align:center;">'
            f'<div style="font-size:1.1rem;font-weight:800;color:#22c55e;">{low}</div>'
            f'<div style="font-size:.62rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Low / Medium</div></div>'
            f'<div style="flex:1;background:var(--surface);border:1px solid var(--border);'
            f'border-radius:10px;padding:.45rem .6rem;text-align:center;">'
            f'<div style="font-size:1.1rem;font-weight:800;color:#f1f5f9;">{total}</div>'
            f'<div style="font-size:.62rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">Total</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


    st.markdown(
        '<div style="background:rgba(220,38,38,.06);border:1px solid rgba(220,38,38,.2);'
        'border-radius:10px;padding:.55rem .9rem;margin-top:.8rem;font-size:.72rem;'
        'color:#b91c1c;text-align:center;font-weight:600;">'
        '⚠️ AI triage is a decision-support tool. Always call official emergency numbers '
        '(India: 112) in life-threatening situations.'
        '</div>',
        unsafe_allow_html=True,
    )