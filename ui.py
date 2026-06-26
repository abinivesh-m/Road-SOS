import streamlit as st


def inject_theme(dark_mode=True):
    if dark_mode:
        theme_vars = """
            --bg:        #0f172a;
            --surface:   #1e293b;
            --surface2:  #263248;
            --red:       #dc2626;
            --red-hover: #b91c1c;
            --orange:    #f97316;
            --text:      #f8fafc;
            --muted:     #94a3b8;
            --border:    rgba(255,255,255,0.08);
            --radius:    14px;
            --radius-sm: 8px;
        """
    else:
        theme_vars = """
            --bg:        #f8fafc;
            --surface:   #ffffff;
            --surface2:  #f1f5f9;
            --red:       #dc2626;
            --red-hover: #b91c1c;
            --orange:    #f97316;
            --text:      #0f172a;
            --muted:     #64748b;
            --border:    rgba(0,0,0,0.10);
            --radius:    14px;
            --radius-sm: 8px;
        """

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root {{
            {theme_vars}
        }}

        html, body, [class*="css"], .stApp {{
            font-family: 'Inter', system-ui, sans-serif !important;
            background-color: var(--bg) !important;
            color: var(--text) !important;
        }}

        #MainMenu, footer {{ visibility: hidden; }}
        /* Keep sidebar toggle arrow visible — only hide Streamlit branding */
        header [data-testid="stToolbar"] {{ visibility: hidden; }}
        header .stAppDeployButton {{ display: none; }}
        header {{ background: transparent !important; }}
        .block-container {{
            padding-top: 1.5rem !important;
            padding-bottom: 3rem !important;
            max-width: 680px !important;
        }}

        .stSelectbox > div > div,
        .stTextInput > div > div > input {{
            background-color: var(--surface) !important;
            border: 1px solid var(--border) !important;
            color: var(--text) !important;
            border-radius: var(--radius-sm) !important;
        }}
        .stCheckbox label p {{ color: var(--text) !important; }}
        div[data-testid="stMarkdownContainer"] p {{
            color: var(--text) !important;
            font-size: 0.93rem;
        }}

        .stButton > button {{
            background: var(--surface) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 0.55rem 1.2rem !important;
            transition: all 0.18s ease !important;
        }}
        .stButton > button:hover {{
            background: var(--surface2) !important;
            border-color: rgba(255,255,255,0.18) !important;
            transform: translateY(-1px);
        }}

        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
            border: none !important;
            color: #fff !important;
            font-size: 1.1rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.04em !important;
            padding: 1rem 1.5rem !important;
            border-radius: 16px !important;
            box-shadow: 0 0 0 0 rgba(220,38,38,0.7);
            animation: pulse-red 2.2s infinite;
        }}
        .stButton > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, #b91c1c 0%, #991b1b 100%) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(220,38,38,0.45) !important;
        }}

        .stLinkButton > a {{
            background: var(--surface2) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            transition: all 0.15s ease !important;
            text-decoration: none !important;
        }}
        .stLinkButton > a:hover {{
            background: var(--red) !important;
            border-color: var(--red) !important;
            transform: translateY(-1px) !important;
        }}

        div[data-testid="stAlert"] {{
            border-radius: var(--radius) !important;
            border: none !important;
        }}

        @keyframes pulse-red {{
            0%   {{ box-shadow: 0 0 0 0 rgba(220,38,38,0.55); }}
            70%  {{ box-shadow: 0 0 0 14px rgba(220,38,38,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(220,38,38,0); }}
        }}
        @keyframes blink-badge {{
            0%, 100% {{ opacity: 1; }}
            50%       {{ opacity: 0.5; }}
        }}
        @keyframes slide-in {{
            from {{ transform: translateY(-8px); opacity: 0; }}
            to   {{ transform: translateY(0);    opacity: 1; }}
        }}

        div[data-testid="stProgressBar"] > div {{
            background: linear-gradient(90deg, var(--red), var(--orange)) !important;
            border-radius: 99px !important;
        }}
        div[data-testid="stProgressBar"] {{
            background: var(--surface2) !important;
            border-radius: 99px !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: var(--surface) !important;
        }}
        section[data-testid="stSidebar"] * {{
            color: var(--text) !important;
        }}

        hr {{ border-color: var(--border) !important; }}

        details {{
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(gps_active=False, total_contacts=None, total_countries=None, total_service_types=None):
    n_services  = total_contacts  or 0
    n_countries = total_countries or 0

    if gps_active:
        gps_dot   = '#22c55e'
        gps_blink = 'animation:blink-badge 1.4s infinite;'
        gps_label = '🟢 GPS Connected'
    else:
        gps_dot   = '#64748b'
        gps_blink = ''
        gps_label = '🔴 GPS Not Connected'

    stats = [
        ("🏥", f"{n_services:,}" if n_services else "—", "Services"),
        ("🌍", str(n_countries) if n_countries else "—",  "Countries"),
        ("⚡", "&lt;2s",                                    "GPS Lock"),
        ("🚑", "24/7",                                      "Emergency"),
    ]
    stat_cards = "".join(
        f'<div style="flex:1;min-width:0;background:rgba(255,255,255,.04);'
        f'border:1px solid rgba(255,255,255,.08);border-radius:12px;'
        f'padding:.55rem .35rem;text-align:center;">'
        f'<div style="font-size:1.1rem;line-height:1;">{icon}</div>'
        f'<div style="font-size:1rem;font-weight:900;color:#f1f5f9;'
        f'letter-spacing:-.01em;line-height:1.15;margin:.15rem 0 .1rem;">{val}</div>'
        f'<div style="font-size:.6rem;color:#64748b;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:.05em;">{lbl}</div>'
        f'</div>'
        for icon, val, lbl in stats
    )

    hero_html = (
        '<div style="background:linear-gradient(160deg,#1a2d4a 0%,#0d1829 55%,#0f172a 100%);'
        'border:1px solid rgba(220,38,38,.3);border-radius:20px;'
        'padding:1.1rem 1.25rem .95rem;margin-bottom:.75rem;'
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
        '</div>'
    )

    st.markdown(hero_html, unsafe_allow_html=True)


def render_dashboard(gps_active, hospitals, ambulances, police, countries=None):
    items = [
        ("📍", "GPS", "Active" if gps_active else "Standby",
         "#22c55e" if gps_active else "#64748b"),
        ("🏥", "Hospitals", str(hospitals), "#dc2626"),
        ("🚑", "Ambulances", str(ambulances), "#f97316"),
        ("🚓", "Police", str(police), "#3b82f6"),
    ]

    cols_html = ""
    for icon, label, value, color in items:
        cols_html += (
            f'<div style="background: var(--surface);border: 1px solid var(--border);'
            f'border-top: 3px solid {color};border-radius: var(--radius);'
            'padding: 0.85rem 0.5rem;text-align: center;flex: 1;min-width: 0;">'
            f'<div style="font-size: 1.3rem; margin-bottom: 0.2rem;">{icon}</div>'
            f'<div style="font-size: 1.25rem;font-weight: 800;color: {color};'
            f'line-height: 1;">{value}</div>'
            '<div style="font-size: 0.7rem;color: #64748b;font-weight: 500;'
            'margin-top: 0.2rem;text-transform: uppercase;letter-spacing: 0.04em;">'
            f'{label}</div>'
            '</div>'
        )

    st.markdown(
        f'<div style="display: flex; gap: 0.6rem; margin-bottom: 1.2rem;">{cols_html}</div>',
        unsafe_allow_html=True,
    )


def render_emergency_banner():
    banner_html = (
        '<div style="background: linear-gradient(135deg, rgba(220,38,38,0.15), '
        'rgba(185,28,28,0.1));border: 1.5px solid rgba(220,38,38,0.5);'
        'border-radius: var(--radius);padding: 1rem 1.25rem;text-align: center;'
        'margin-bottom: 1rem;animation: slide-in 0.3s ease;">'
        '<div style="font-size: 1.05rem;font-weight: 800;color: #fca5a5;'
        'letter-spacing: 0.06em;text-transform: uppercase;">'
        '<span style="animation: blink-badge 1s infinite; display: inline-block;">🚨</span>'
        '&nbsp;EMERGENCY ACTIVE</div>'
        '<div style="font-size: 0.8rem;color: #f87171;margin-top: 0.35rem;'
        'font-weight: 500;">Golden Hour Response Protocol Enabled</div>'
        '</div>'
    )
    st.markdown(banner_html, unsafe_allow_html=True)


def render_section_header(icon, title, subtitle=None):
    sub_html = (
        f'<div style="font-size:0.78rem;color:#64748b;margin-top:0.1rem;">{subtitle}</div>'
        if subtitle else ""
    )
    header_html = (
        '<div style="display: flex;align-items: center;gap: 0.65rem;margin: 1.4rem 0 0.8rem;">'
        '<span style="background: var(--surface2);border-radius: 10px;'
        f'padding: 0.4rem 0.5rem;font-size: 1.2rem;line-height: 1;">{icon}</span>'
        '<div>'
        f'<div style="font-size: 1rem;font-weight: 700;color: var(--text);">{title}</div>'
        f'{sub_html}'
        '</div>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


def render_service_card_header(name, distance_km, phone, badge, accent_color="#dc2626"):
    phone_html = (
        f'<span style="color:#94a3b8;font-size:0.8rem;font-weight:500;">📞 {phone}</span>'
        if phone else ""
    )
    card_html = (
        f'<div style="background: var(--surface);border: 1px solid var(--border);'
        f'border-left: 4px solid {accent_color};border-radius: var(--radius);'
        'padding: 1rem 1.1rem;margin-bottom: 0.5rem;animation: slide-in 0.3s ease;">'
        '<div style="display: flex;justify-content: space-between;'
        'align-items: flex-start;flex-wrap: wrap;gap: 0.3rem;">'
        '<div style="font-weight: 700;font-size: 0.97rem;color: var(--text);'
        f'flex: 1;min-width: 0;">{name}</div>'
        '<span style="background: rgba(220,38,38,0.12);color: #fca5a5;'
        'font-size: 0.68rem;font-weight: 700;letter-spacing: 0.05em;'
        f'padding: 0.18rem 0.55rem;border-radius: 99px;white-space: nowrap;">{badge}</span>'
        '</div>'
        '<div style="margin-top:0.45rem; display:flex; gap:1rem; flex-wrap:wrap; align-items:center;">'
        '<span style="color: #f97316;font-size: 0.82rem;font-weight: 700;">'
        f'📍 {round(distance_km, 2)} km away</span>'
        f'{phone_html}'
        '</div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_secondary_row(name, distance_km, phone, badge):
    phone_text = f" · 📞 {phone}" if phone else ""
    row_html = (
        '<div style="background: rgba(255,255,255,0.025);border: 1px solid var(--border);'
        'border-radius: var(--radius-sm);padding: 0.55rem 0.9rem;margin-bottom: 0.35rem;'
        'font-size: 0.83rem;color: #94a3b8;">'
        f'<span style="color:var(--text);font-weight:500;">{name}</span>'
        f'&nbsp;·&nbsp;📍 {round(distance_km,2)} km{phone_text}'
        '&nbsp;&nbsp;<span style="font-size:0.68rem;color:#475569;font-weight:600;">'
        f'{badge}</span>'
        '</div>'
    )
    st.markdown(row_html, unsafe_allow_html=True)


def render_map_header():
    header_html = (
        '<div style="background: var(--surface);border: 1px solid var(--border);'
        'border-radius: var(--radius) var(--radius) 0 0;padding: 0.75rem 1rem;'
        'display: flex;align-items: center;gap: 0.6rem;margin-bottom: -4px;">'
        '<span style="font-size:1.1rem;">🗺️</span>'
        '<span style="font-weight:700;font-size:0.95rem;color:var(--text);">'
        'Emergency Response Map</span>'
        '<span style="margin-left: auto;font-size: 0.72rem;color: #22c55e;'
        'font-weight: 600;background: rgba(34,197,94,0.1);'
        'border: 1px solid rgba(34,197,94,0.25);padding: 0.15rem 0.55rem;'
        'border-radius: 99px;">● LIVE</span>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    legend_items = [
        ("#22c55e", "You"),
        ("#dc2626", "Hospital"),
        ("#f97316", "Ambulance"),
        ("#3b82f6", "Police"),
        ("#7c3aed", "Towing"),
        ("#991b1b", "Fire"),
    ]
    dots = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:0.73rem;color:#94a3b8;">'
        f'<span style="width:9px;height:9px;border-radius:50%;background:{c};display:inline-block;"></span>'
        f'{label}</span>'
        for c, label in legend_items
    )
    st.markdown(
        f'<div style="background: var(--surface);border-left: 1px solid var(--border);'
        f'border-right: 1px solid var(--border);padding: 0.5rem 1rem;'
        f'display: flex;gap: 0.9rem;flex-wrap: wrap;">{dots}</div>',
        unsafe_allow_html=True,
    )


def render_location_card(lat, lon, accuracy=None):
    card_html = (
        '<div style="background: rgba(34,197,94,0.07);border: 1px solid rgba(34,197,94,0.3);'
        'border-radius: var(--radius);padding: 0.85rem 1.1rem;display: flex;'
        'align-items: center;gap: 0.75rem;margin-bottom: 0.6rem;">'
        '<div style="width:38px;height:38px;min-width:38px;background:rgba(34,197,94,0.15);'
        'border-radius:10px;display:flex;align-items:center;justify-content:center;'
        'font-size:1.2rem;">📍</div>'
        '<div style="flex:1;min-width:0;">'
        '<div style="font-size:0.88rem;font-weight:700;color:#4ade80;letter-spacing:0.01em;">'
        'Location Confirmed</div>'
        '<div style="font-size:0.75rem;color:#64748b;margin-top:0.15rem;'
        f'font-family:monospace;">{round(lat,5)}, {round(lon,5)}</div>'
        '</div>'
        '<div style="display:flex;align-items:center;gap:5px;background:rgba(34,197,94,0.12);'
        'border:1px solid rgba(34,197,94,0.25);border-radius:99px;padding:0.2rem 0.65rem;'
        'white-space:nowrap;">'
        '<span style="width:7px;height:7px;border-radius:50%;background:#4ade80;'
        'display:inline-block;animation: blink-badge 1.2s infinite;"></span>'
        '<span style="font-size:0.72rem;color:#4ade80;font-weight:700;">LIVE</span>'
        '</div>'
        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_no_data(service_type):
    st.markdown(
        '<div style="background: var(--surface);border: 1px dashed var(--border);'
        'border-radius: var(--radius);padding: 1rem;text-align: center;'
        f'color: #475569;font-size: 0.85rem;">No {service_type} data found nearby</div>',
        unsafe_allow_html=True,
    )
