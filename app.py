import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
import requests
from fpdf import FPDF
from tavily import TavilyClient
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import PyPDF2
import base64
import edge_tts
import asyncio
import tempfile
import json
import os
import hashlib
from datetime import datetime

# ============================================================
# PAGE CONFIG & CSS
# ============================================================
st.set_page_config(page_title="Ultimate Planner & Tourism Guide", page_icon="🌍", layout="wide")

st.markdown("""
<style>
    /* Gemini-style Vertical Suggestion Buttons */
    .stButton>button {
        border-radius: 12px;
        background-color: #f8f9fa; 
        color: #333;
        border: 1px solid #e0e0e0;
        height: 50px;
        width: 100%;
        text-align: left; 
        padding-left: 20px;
        transition: all 0.2s;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #e8eaed;
        border-color: #d2d2d2;
        transform: translateX(5px); 
        color: #000;
    }
    
    /* Greeting Styles */
    .greeting-header {
        font-size: 42px !important;
        font-weight: 600;
        background: -webkit-linear-gradient(0deg, #4b90ff, #ff5546);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .greeting-sub {
        font-size: 20px !important;
        color: #5f6368;
        margin-bottom: 30px;
    }

    /* Input Toolbar Styling */
    div[data-testid="stPopover"] > button {
        border-radius: 50%;
        height: 48px;
        width: 48px;
        border: 1px solid #ddd;
        margin-top: 28px; 
    }
    
    .stAudioInput {
        margin-top: 0px;
    }

    /* Floating Auto-Scroll Button */
    .scroll-btn {
        position: fixed;
        bottom: 110px;
        right: 40px;
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #ddd;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        text-align: center;
        line-height: 45px;
        font-size: 20px;
        text-decoration: none;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        z-index: 1000;
        transition: 0.3s;
    }
    .scroll-btn:hover {
        background-color: #f0f2f6;
        transform: scale(1.1);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SECRETS MANAGEMENT & CONFIG
# ============================================================
try:
    GROQ_KEY = st.secrets["groq_api_key"]
    WEATHER_KEY = st.secrets["weather_api_key"]
    TAVILY_KEY = st.secrets["tavily_api_key"]
except FileNotFoundError:
    st.error("Secrets file not found.")
    st.stop()
except KeyError:
    st.error("Missing keys in secrets.")
    st.stop()

# Tourism Config
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TOURISM_SYSTEM_PROMPT = """You are the Pakistan Tourism Smart Assistant, an expert AI guide specializing exclusively in Pakistan tourism. You help tourists with:
- Travel safety advice specific to Pakistani regions
- Cultural guidance, local customs, dress codes, and etiquette
- National and regional laws relevant to tourists
- Finding trusted services (hospitals, money exchange, SIM vendors, embassies)
- Destination recommendations, itineraries, and travel planning
- Budget advice and money-saving tips
Rules:
1. ONLY answer questions related to Pakistan tourism and travel.
2. If asked about non-Pakistan topics, politely redirect to Pakistan tourism.
3. Be accurate, helpful, and safety-conscious.
4. Mention emergency numbers when discussing safety: Police 15, Rescue 1122, Edhi 115.
"""

# ============================================================
# INITIALIZE STATE
# ============================================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "medical_data" not in st.session_state:
    st.session_state.medical_data = ""
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None
if "tourism_chat_history" not in st.session_state:
    st.session_state.tourism_chat_history = []
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

def clear_chat():
    st.session_state.chat_history = []
    st.session_state.medical_data = ""
    st.session_state.last_audio = None

# ============================================================
# HEALTH & PLANNER FUNCTIONS
# ============================================================
def get_current_weather(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url).json()
        if response.get("cod") != 200: return None, "Error"
        main = response["main"]
        return {"desc": response["weather"][0]["description"], "temp": main["temp"], "humidity": main["humidity"], "feels_like": main["feels_like"]}, None
    except: return None, "Error"

def get_forecast(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        res = requests.get(url).json()
        if res.get("cod") != "200": return None
        data = []
        for i in res['list']:
            dt = pd.to_datetime(i['dt_txt'])
            day_night = "Day ☀️" if 6 <= dt.hour < 18 else "Night 🌙"
            data.append({"Datetime": i['dt_txt'], "Date": dt.strftime('%Y-%m-%d'), "Time": dt.strftime('%I:%M %p'), "Period": day_night, "Temperature (°C)": i['main']['temp'], "Rain Chance (%)": int(i.get('pop', 0) * 100), "Condition": i['weather'][0]['description'].title()})
        return pd.DataFrame(data)
    except: return None

def search_tavily(query):
    try:
        tavily = TavilyClient(api_key=TAVILY_KEY)
        res = tavily.search(query=query, max_results=3)
        return "\n".join([f"- {r['title']}: {r['url']}" for r in res['results']])
    except: return "No results."

def extract_pdf(file):
    reader = PyPDF2.PdfReader(file)
    return "".join([p.extract_text() for p in reader.pages])

def analyze_image(file, client):
    img = base64.b64encode(file.read()).decode('utf-8')
    res = client.chat.completions.create(
        messages=[{"role": "user", "content": [{"type": "text", "text": "Extract text."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}]}],
        model="llama-3.2-90b-vision-preview"
    )
    return res.choices[0].message.content

async def tts(text, lang):
    voice = "ur-PK-UzmaNeural" if lang == "UR" else "hi-IN-SwaraNeural" if lang == "HI" else "en-US-AriaNeural"
    comm = edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        await comm.save(f.name)
        return f.name

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

# ============================================================
# TOURISM FUNCTIONS
# ============================================================
def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return [] if filename == "destinations.json" else {}

def save_json(filename, data):
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_admin_hash():
    return hashlib.sha256("admin123".encode()).hexdigest()

def sanitize_messages(messages):
    if not messages: return messages
    cleaned = [messages[0]]
    for msg in messages[1:]:
        if cleaned and msg["role"] == cleaned[-1]["role"] and msg["role"] != "system":
            cleaned[-1] = {"role": msg["role"], "content": cleaned[-1]["content"] + "\n" + msg["content"]}
        else: cleaned.append(msg)
    return cleaned

def fetch_weather_tourism(lat, lon):
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code", "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code", "timezone": "Asia/Karachi", "forecast_days": 7}
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        return resp.json()
    except: return None

def weather_code_to_text(code):
    codes = {0:"☀️ Clear",1:"🌤️ Mainly Clear",2:"⛅ Partly Cloudy",3:"☁️ Overcast", 45:"🌫️ Foggy",51:"🌦️ Light Drizzle",61:"🌧️ Slight Rain",63:"🌧️ Moderate Rain",65:"🌧️ Heavy Rain",71:"🌨️ Slight Snow",95:"⛈️ Thunderstorm"}
    return codes.get(code, f"Code {code}")

# ============================================================
# TOURISM PAGES VIEWS
# ============================================================
def page_home():
    st.markdown("""
    <div style='text-align:center; padding:20px 0;'>
        <h1 style='font-size:2.8em; color:#1B5E20; margin-bottom: 0;'>🇵🇰 Welcome to Pakistan</h1>
        <p style='font-size:1.3em; color:#555;'>Your Complete Smart Tourism Guide</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    **Pakistan** — A land of breathtaking mountains, ancient civilizations, rich culture, and legendary hospitality. 
    From the mighty Karakoram and Himalayan ranges to the ancient ruins of Mohenjo-daro, from the vibrant streets of Lahore to the serene valleys of Hunza and Swat — Pakistan offers experiences that rival the world's best destinations.
    """)
    
    dests = load_json("destinations.json")
    
    if not dests:
        dests = [
            {"name": "Hunza Valley", "region": "Gilgit-Baltistan", "access_level": "Moderate", "best_season": "April - October", "budget_per_day": {"budget": 5000}},
            {"name": "Skardu", "region": "Gilgit-Baltistan", "access_level": "Moderate", "best_season": "May - September", "budget_per_day": {"budget": 6000}},
            {"name": "Swat Valley", "region": "Khyber Pakhtunkhwa", "access_level": "Easy", "best_season": "March - October", "budget_per_day": {"budget": 4000}},
            {"name": "Lahore", "region": "Punjab", "access_level": "Easy", "best_season": "October - March", "budget_per_day": {"budget": 3000}}
        ]
        
    st.subheader("🌟 Featured Destinations")
    cols = st.columns(min(len(dests), 4))
    for i, dest in enumerate(dests[:4]):
        with cols[i % 4]:
            budget = dest.get('budget_per_day', {}).get('budget', 'N/A')
            st.markdown(f"""
            <div style='background:linear-gradient(135deg,#E8F5E9,#C8E6C9);padding:20px;
            border-radius:15px;text-align:center;margin:5px 0;min-height:220px; color:#333; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
            <h3 style='color:#1B5E20;margin:0; font-weight:bold;'>{dest.get('name', 'N/A')}</h3>
            <p style='color:#555;font-size:0.9em;margin-bottom:15px;'>{dest.get('region', 'N/A')}</p>
            <p style='font-size:0.85em; margin:5px;'>📍 <span style='color:#d32f2f;'>{dest.get('access_level', 'N/A')} Access</span></p>
            <p style='font-size:0.85em; margin:5px;'>📅 <span style='color:#1976d2;'>{dest.get('best_season', 'N/A')}</span></p>
            <p style='font-size:0.9em; margin-top:15px; color:#d84315; font-weight:bold;'>💰 From PKR {budget:,}/day</p>
            </div>""", unsafe_allow_html=True)
            
    st.divider()
    st.subheader("📋 What This App Offers")
    features = [
        ("🏔️","Destinations","10+ curated tourist destinations"),
        ("🤖","AI Assistant","Smart travel assistant powered by AI"),
        ("💰","Budget Planner","Plan your trip budget"),
        ("🗺️","Interactive Maps","Explore Pakistan visually"),
        ("🌦️","Weather Info","Real-time weather data"),
        ("🚨","Emergency","Quick access to emergency contacts"),
        ("📸","Photo Gallery","Visual tour of Pakistan"),
        ("📜","Travel Tips","Safety & cultural guidelines")
    ]
    
    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 4]:
            st.markdown(f"**{icon} {title}**\n\n<span style='font-size:0.9em;color:#666;'>{desc}</span>", unsafe_allow_html=True)

def page_destinations():
    st.header("🏔️ Tourist Destinations")
    dests = load_json("destinations.json")
    
    if not dests:
        dests = [
            {
                "name": "Hunza Valley",
                "region": "Gilgit-Baltistan",
                "access_level": "Moderate",
                "altitude_m": 2438,
                "best_season": "April - October",
                "budget_per_day": {"budget": 5000},
                "description": "Hunza Valley is one of the most breathtaking destinations in Pakistan, surrounded by snow-capped peaks including Rakaposhi (7,788m) and Ultar Sar. The valley is known for its stunning landscapes, ancient forts, and the warmth of the Hunza people.",
                "history": "Hunza was an independent princely state for over 900 years, ruled by the Mir of Hunza. The region was part of the ancient Silk Route and has connections to the legendary Shangri-La. It became part of Pakistan in 1974.",
                "landmarks": [{"name": "Baltit Fort", "description": "A 700-year-old fort perched above Karimabad."}],
                "activities": ["Trekking and hiking", "Visit ancient forts", "Boating at Attabad Lake"],
                "transport": {"islamabad": {"road": "14-16 hours via Karakoram Highway"}},
                "accommodation": {"budget": ["Backpacker hostels in Karimabad"], "luxury": ["Serena Hotel"]},
                "connectivity": {"mobile_networks": ["SCOM (Best)", "Telenor"], "internet": "Available in most hotels", "tips": "Buy an SCOM SIM card in Gilgit."}
            }
        ]

    regions = sorted(set(d.get("region", "Unknown") for d in dests))
    col1, col2 = st.columns(2)
    with col1:
        sel_region = st.selectbox("Filter by Region", ["All Regions"] + regions)
    with col2:
        sel_access = st.selectbox("Filter by Access Level", ["All", "Easy", "Moderate", "Difficult"])

    filtered = dests
    if sel_region != "All Regions":
        filtered = [d for d in filtered if d.get("region") == sel_region]
    if sel_access != "All":
        filtered = [d for d in filtered if d.get("access_level") == sel_access]

    if not filtered:
        st.info("No destinations match your filters.")
        return

    selected = st.selectbox("Select a Destination", [d["name"] for d in filtered])
    dest = next(d for d in filtered if d["name"] == selected)

    st.subheader(f"📍 {dest['name']} — {dest.get('region', 'N/A')}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Access Level", dest.get("access_level", "N/A"))
    c2.metric("Altitude", f"{dest.get('altitude_m', 'N/A')}m")
    c3.metric("Best Season", dest.get("best_season", "N/A"))
    
    budget = dest.get('budget_per_day', {}).get('budget', 'N/A')
    c4.metric("Budget/day", f"PKR {budget:,}+" if isinstance(budget, int) else f"PKR {budget}+")

    st.markdown(f"📄 **Description:** {dest.get('description', '')}")

    with st.expander("📜 Historical Background", expanded=False):
        st.write(dest.get("history", "No history available."))

    if "landmarks" in dest and dest["landmarks"]:
        with st.expander("🏛️ Key Landmarks", expanded=False):
            for lm in dest["landmarks"]:
                st.markdown(f"**{lm['name']}** — {lm['description']}")

    if "activities" in dest and dest["activities"]:
        with st.expander("🎯 Recommended Activities", expanded=False):
            for act in dest["activities"]:
                st.markdown(f"- {act}")

    if "transport" in dest and dest["transport"]:
        with st.expander("🚌 Transportation Details", expanded=False):
            for origin, modes in dest["transport"].items():
                st.markdown(f"**From {origin.replace('_',' ').title()}:**")
                for mode, info in modes.items():
                    st.markdown(f"  - *{mode.title()}:* {info}")

    if "accommodation" in dest and dest["accommodation"]:
        with st.expander("🏨 Accommodation", expanded=False):
            for tier, hotels in dest["accommodation"].items():
                st.markdown(f"**{tier.title()}:**")
                for h in hotels:
                    st.markdown(f"  - {h}")

    if "connectivity" in dest and dest["connectivity"]:
        with st.expander("📱 Connectivity", expanded=False):
            conn = dest["connectivity"]
            st.markdown(f"**Networks:** {', '.join(conn.get('mobile_networks', []))}")
            st.markdown(f"**Internet:** {conn.get('internet', 'N/A')}")
            st.markdown(f"**💡 Tip:** {conn.get('tips', 'N/A')}")

def page_weather():
    st.header("🌦️ Destination Weather")
    dests = load_json("destinations.json")
    if not dests: return
    selected = st.selectbox("Select Destination", [d["name"] for d in dests], key="w_dest")
    dest = next(d for d in dests if d["name"] == selected)
    weather = fetch_weather_tourism(dest.get("latitude", 30), dest.get("longitude", 70))
    if weather and "current" in weather:
        c1, c2 = st.columns(2)
        c1.metric("Temperature", f"{weather['current']['temperature_2m']}°C")
        c2.metric("Conditions", weather_code_to_text(weather['current']['weather_code']))

def page_smart_assistant():
    st.header("🤖 Pakistan Tourism AI")
    if prompt := st.chat_input("Ask about Pakistan tourism..."):
        st.session_state.tourism_chat_history.append({"role": "user", "content": prompt})
    for msg in st.session_state.tourism_chat_history:
        st.chat_message(msg["role"]).write(msg["content"])
    if prompt:
        client = Groq(api_key=GROQ_KEY)
        messages = [{"role": "system", "content": TOURISM_SYSTEM_PROMPT}] + st.session_state.tourism_chat_history
        res = client.chat.completions.create(messages=sanitize_messages(messages), model="llama-3.3-70b-versatile")
        reply = res.choices[0].message.content
        st.chat_message("assistant").write(reply)
        st.session_state.tourism_chat_history.append({"role": "assistant", "content": reply})

def page_maps():
    st.header("🗺️ Interactive Map of Pakistan")
    destinations = load_json("destinations.json")
    
    # Enhanced Fallback Data with Coordinates
    if not destinations:
        destinations = [
            {"name": "Hunza Valley", "region": "Gilgit-Baltistan", "access_level": "Moderate", "latitude": 36.3167, "longitude": 74.6500, "altitude_m": 2438, "best_season": "April - October", "budget_per_day": {"budget": 5000}},
            {"name": "Skardu", "region": "Gilgit-Baltistan", "access_level": "Moderate", "latitude": 35.2971, "longitude": 75.6333, "altitude_m": 2228, "best_season": "May - September", "budget_per_day": {"budget": 6000}},
            {"name": "Swat Valley", "region": "Khyber Pakhtunkhwa", "access_level": "Easy", "latitude": 35.2227, "longitude": 72.4258, "altitude_m": 980, "best_season": "March - October", "budget_per_day": {"budget": 4000}},
            {"name": "Lahore", "region": "Punjab", "access_level": "Easy", "latitude": 31.5204, "longitude": 74.3587, "altitude_m": 217, "best_season": "October - March", "budget_per_day": {"budget": 3000}},
            {"name": "Fairy Meadows", "region": "Gilgit-Baltistan", "access_level": "Difficult", "latitude": 35.3850, "longitude": 74.5786, "altitude_m": 3300, "best_season": "June - September", "budget_per_day": {"budget": 8000}},
            {"name": "Mohenjo-Daro", "region": "Sindh", "access_level": "Easy", "latitude": 27.3292, "longitude": 68.1389, "altitude_m": 47, "best_season": "November - February", "budget_per_day": {"budget": 3500}}
        ]

    # Map Controls (3 Columns)
    col1, col2, col3 = st.columns(3)
    with col1:
        show_dest = st.checkbox("📍 Show Destinations", value=True)
    with col2:
        show_routes = st.checkbox("🛣️ Show Major Routes", value=True)
    with col3:
        map_lang = st.radio("🌐 Map Language", ["English", "اردو (Urdu)"], horizontal=True, key="map_lang")
        
    st.markdown("🟢 **Easy Access** | 🟠 **Moderate** | 🔴 **Difficult**")
    
    # Process Markers Data
    marker_colors = {"Easy": "#4CAF50", "Moderate": "#FF9800", "Difficult": "#F44336"}
    markers_data = []
    if show_dest and destinations:
        for d in destinations:
            color = marker_colors.get(d.get("access_level", ""), "#2196F3")
            budget_val = d.get('budget_per_day', {}).get('budget', 'N/A')
            budget_str = f"PKR {budget_val:,}+/day" if isinstance(budget_val, int) else f"PKR {budget_val}+/day"
            markers_data.append({
                "lat": d.get("latitude", 30.0),
                "lng": d.get("longitude", 70.0),
                "name": d.get("name", "Unknown"),
                "region": d.get("region", "Unknown"),
                "access": d.get("access_level", "N/A"),
                "budget": budget_str,
                "altitude": f"{d.get('altitude_m', 0):,}m",
                "season": d.get("best_season", "N/A"),
                "color": color
            })
    markers_json = json.dumps(markers_data, ensure_ascii=False)

    # Process Routes Data
    routes_data = []
    if show_routes:
        routes_data = [
            {"name": "N-35 Karakoram Highway (KKH)", "color": "#1B5E20", "coords": [[35.92,74.31],[36.05,74.50],[36.32,74.65],[36.46,74.88],[36.30,75.10],[35.88,74.48],[35.55,75.20],[35.30,75.63]]},
            {"name": "M-2 Motorway (Islamabad → Lahore)", "color": "#0D47A1", "coords": [[33.68,73.05],[33.50,73.10],[33.10,72.80],[32.70,72.60],[32.16,72.68],[31.85,73.50],[31.55,74.34]]},
            {"name": "N-15 Swat Expressway", "color": "#6A1B9A", "coords": [[33.95,72.35],[34.20,72.10],[34.50,72.05],[34.77,72.36],[35.22,72.35]]},
            {"name": "N-5 GT Road (Lahore → Karachi)", "color": "#E65100", "coords": [[31.55,74.34],[31.40,74.20],[30.20,71.47],[28.42,68.77],[27.60,68.35],[25.39,68.37],[24.86,67.08]]},
            {"name": "N-25 RCD Highway (Karachi → Quetta)", "color": "#B71C1C", "coords": [[24.86,67.08],[25.50,66.60],[26.20,66.00],[27.00,66.50],[28.50,66.80],[29.50,66.90],[30.18,66.97]]}
        ]
    routes_json = json.dumps(routes_data, ensure_ascii=False)

    # Inject Leaflet Map with logic
    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; }}
            #map {{ width: 100%; height: 580px; border-radius: 12px; border: 1px solid #ccc; }}
            .dest-popup h4 {{ margin: 0 0 5px; color: #1B5E20; font-family: sans-serif; }}
            .dest-popup p {{ margin: 2px 0; font-size: 13px; font-family: sans-serif; }}
            .dest-popup hr {{ margin: 5px 0; border-color: #eee; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([30.3753, 69.3451], 5);
            var lang = '{"en" if map_lang == "English" else "ur"}';
            
            if (lang === 'en') {{
                L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
                    attribution: '&copy; OpenStreetMap &copy; CARTO',
                    maxZoom: 19
                }}).addTo(map);
            }} else {{
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; OpenStreetMap',
                    maxZoom: 18
                }}).addTo(map);
            }}

            var markers = {markers_json};
            markers.forEach(function(m) {{
                var popupContent = '<div class="dest-popup">' +
                    '<h4>' + m.name + '</h4>' +
                    '<p style="color:#555;">' + m.region + '</p>' +
                    '<hr>' +
                    '<p>⛰️ Altitude: ' + m.altitude + '</p>' +
                    '<p>📍 Access: <b style="color:'+m.color+';">' + m.access + '</b></p>' +
                    '<p>📅 Best: ' + m.season + '</p>' +
                    '<p>💰 ' + m.budget + '</p>' +
                    '</div>';
                
                L.circleMarker([m.lat, m.lng], {{
                    radius: 10, fillColor: m.color, color: '#fff', weight: 2,
                    opacity: 1, fillOpacity: 0.85
                }}).addTo(map).bindPopup(popupContent).bindTooltip(m.name);
            }});

            var routes = {routes_json};
            routes.forEach(function(r) {{
                L.polyline(r.coords, {{
                    color: r.color, weight: 3, dashArray: '8,6', opacity: 0.8
                }}).addTo(map).bindTooltip(r.name, {{sticky: true}});
            }});
        </script>
    </body>
    </html>
    """
    components.html(map_html, height=600)

def page_budget():
    st.header("💰 Budget Planner")
    
    budget_data = load_json("budget_templates.json")
    destinations = load_json("destinations.json")
    
    if not destinations:
        destinations = [{"name": "Hunza Valley"}, {"name": "Skardu"}, {"name": "Swat Valley"}, {"name": "Lahore"}]
        
    if not budget_data or "categories" not in budget_data:
        budget_data = {
            "travel_styles": ["Budget", "Standard", "Luxury"],
            "categories": [
                {"name": "Accommodation", "icon": "🏨", "budget": 2000, "standard": 5000, "luxury": 15000},
                {"name": "Food (3 meals)", "icon": "🍔", "budget": 1200, "standard": 3000, "luxury": 8000},
                {"name": "Local Transport", "icon": "🚕", "budget": 800, "standard": 2500, "luxury": 8000},
                {"name": "Activities & Entry Fees", "icon": "🎟️", "budget": 300, "standard": 1000, "luxury": 3000},
                {"name": "Communication (SIM/Data)", "icon": "📱", "budget": 150, "standard": 300, "luxury": 500},
                {"name": "Miscellaneous", "icon": "🛍️", "budget": 500, "standard": 1500, "luxury": 5000}
            ],
            "currency_rates": {
                "USD": 0.0036, "EUR": 0.0033, "GBP": 0.0028, "AED": 0.013, "CNY": 0.026
            },
            "tips": [
                "Use local transport like Careem or InDrive instead of traditional taxis.",
                "Eat at local dhabas for authentic and cheap food.",
                "Book accommodation in advance during peak season (June-August)."
            ]
        }

    st.subheader("🧮 Trip Budget Calculator")
    
    c1, c2 = st.columns(2)
    with c1:
        sel_dest = st.selectbox("Destination", [d["name"] for d in destinations], key="bp_dest")
        num_days = st.slider("Number of Days", 1, 30, 5)
    with c2:
        style = st.selectbox("Travel Style", budget_data.get("travel_styles", ["Budget", "Standard", "Luxury"]))
        num_people = st.slider("Number of Travelers", 1, 10, 2)
        
    style_key = style.lower()
    categories = budget_data.get("categories", [])
    
    items = []
    total = 0
    pie_data = []
    pie_labels = []
    
    for cat in categories:
        daily = cat.get(style_key, 0)
        cost = daily * num_days * num_people
        total += cost
        items.append({
            "Category": f"{cat.get('icon','')} {cat['name']}", 
            "Daily/Person (PKR)": f"{daily:,}", 
            "Total (PKR)": f"{cost:,}"
        })
        pie_data.append(cost)
        pie_labels.append(cat['name'])
        
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Total Budget", f"PKR {total:,}")
    c2.metric("👤 Per Person", f"PKR {total // max(num_people,1):,}")
    c3.metric("📅 Per Day", f"PKR {total // max(num_days,1):,}")
    
    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    
    st.subheader("📊 Expense Distribution")
    fig = px.pie(values=pie_data, names=pie_labels, color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("💱 Currency Conversion")
    rates = budget_data.get("currency_rates", {})
    sel_currency = st.selectbox("Convert to", [c for c in rates.keys()])
    rate = rates.get(sel_currency, 1)
    st.info(f"**PKR {total:,}** ≈ **{sel_currency} {total * rate:,.2f}**")
    
    st.divider()
    st.subheader("💡 Money-Saving Tips")
    for tip in budget_data.get("tips", []):
        st.markdown(f"- {tip}")


def page_admin():
    st.header("🔐 Admin Panel")
    if not st.session_state.admin_logged_in:
        pw = st.text_input("Admin Password:", type="password")
        if st.button("Login"):
            if hashlib.sha256(pw.encode()).hexdigest() == get_admin_hash():
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("Invalid")
    else:
        st.success("Logged in")
        if st.button("Logout"): 
            st.session_state.admin_logged_in = False
            st.rerun()
        st.info("Admin features active. Use JSON files in the 'data' folder to manage extensive records.")

# ============================================================
# MAIN APP LAYOUT
# ============================================================
st.title("🗺️ Ultimate Planner & Hub")
main_tab, companion_tab, tourism_tab = st.tabs(["📅 Trip Planner", "🤖 Health Companion", "🇵🇰 Pakistan Tourism"])

# --- TAB 1: TRIP PLANNER ---
with main_tab:
    with st.form("trip_form"):
        c1, c2 = st.columns(2)
        city = c1.text_input("City", "New York")
        mood = c1.text_input("Activity", "Relaxing walk")
        routine = c2.text_area("Routine", "Mon-Fri 9-5 work")
        submitted = st.form_submit_button("🚀 Generate Plan")

    if submitted:
        client = Groq(api_key=GROQ_KEY)
        weather, err = get_current_weather(city, WEATHER_KEY)
        if err: st.error("Weather Error")
        else:
            with st.spinner("🤖 Analyzing weather, routines, and searching web..."):
                q_res = client.chat.completions.create(messages=[{"role": "user", "content": f"Create search query for {mood} in {city} 2025. Keywords only."}], model="llama-3.1-8b-instant")
                search_data = search_tavily(q_res.choices[0].message.content)
                final_res = client.chat.completions.create(messages=[{"role": "user", "content": f"Plan trip. Routine: {routine}, Weather: {weather}, Places: {search_data}"}], model="llama-3.3-70b-versatile")
                plan = final_res.choices[0].message.content
                st.markdown(plan)
                st.download_button("📥 Download PDF", create_pdf(plan), "plan.pdf")
                
                df = get_forecast(city, WEATHER_KEY)
                if df is not None:
                    st.divider()
                    c1, c2 = st.columns(2)
                    with c1:
                        fig_temp = px.line(df, x="Datetime", y="Temperature (°C)", title="🌡️ Temp Trend", markers=True)
                        st.plotly_chart(fig_temp, use_container_width=True)
                    with c2:
                        fig_rain = px.bar(df, x="Datetime", y="Rain Chance (%)", title="☔ Rain Chance", range_y=[0, 100])
                        st.plotly_chart(fig_rain, use_container_width=True)

# --- TAB 2: HEALTH COMPANION ---
with companion_tab:
    client = Groq(api_key=GROQ_KEY)
    
    if not st.session_state.chat_history:
        st.markdown('<div class="greeting-header">Hello dear, how can I help you?</div>', unsafe_allow_html=True)
        st.markdown('<div class="greeting-sub">Tell me what you want or choose an option below</div>', unsafe_allow_html=True)
        col_buttons, col_space = st.columns([1, 2]) 
        with col_buttons:
            if st.button("📄 Share Reports & Get Analysis"): st.session_state.chat_history.append({"role": "assistant", "content": "Upload your report using the ➕ button below!"}); st.rerun()
            if st.button("🥦 Prepare a Diet Plan"): st.session_state.chat_history.append({"role": "user", "content": "I need a diet plan."}); st.rerun()

    for i, msg in enumerate(st.session_state.chat_history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            with st.expander("📋 Copy Text"): st.code(msg["content"], language="markdown")
            if msg["role"] == "user" and "pdf" in msg["content"].lower() and i > 0:
                st.download_button("📥 Download", create_pdf(st.session_state.chat_history[i-1]["content"]), f"doc_{i}.pdf", key=f"dl_{i}")

    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)
    if st.session_state.chat_history:
        st.markdown('<a href="#chat-bottom" class="scroll-btn">⬇️</a>', unsafe_allow_html=True)

    col_plus, col_clear, col_voice = st.columns([0.08, 0.08, 0.84]) 
    with col_plus:
        with st.popover("➕", use_container_width=True):
            uploaded_file = st.file_uploader("Upload", type=["pdf", "jpg", "png"], label_visibility="collapsed")
    with col_clear: st.button("🗑️", help="Clear Chat Memory", on_click=clear_chat, use_container_width=True)
    with col_voice: audio_val = st.audio_input("Voice", label_visibility="collapsed")

    if uploaded_file:
        txt = extract_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else analyze_image(uploaded_file, client)
        st.session_state.medical_data = txt
        res = client.chat.completions.create(messages=[{"role": "system", "content": "You are a nutritionist. Always use emojis. Ask 'Do you want its PDF file?' at the end."}, {"role": "user", "content": f"Analyze: {txt}. Give diet plan."}], model="llama-3.3-70b-versatile")
        st.session_state.chat_history.extend([{"role": "user", "content": f"📎 {uploaded_file.name}"}, {"role": "assistant", "content": res.choices[0].message.content}])
        st.rerun()

    if audio_val and audio_val != st.session_state.last_audio:
        st.session_state.last_audio = audio_val
        txt = client.audio.transcriptions.create(file=("v.wav", audio_val), model="whisper-large-v3-turbo").text
        res = client.chat.completions.create(messages=[{"role": "system", "content": "Reply in same language. Use emojis."}, {"role": "user", "content": txt}], model="llama-3.3-70b-versatile")
        raw = res.choices[0].message.content
        lang = "UR" if "[LANG:UR]" in raw else "HI" if "[LANG:HI]" in raw else "EN"
        clean = raw.replace(f"[LANG:{lang}]", "").strip()
        st.session_state.chat_history.extend([{"role": "user", "content": f"🎙️ {txt}"}, {"role": "assistant", "content": clean}])
        st.audio(asyncio.run(tts(clean, lang)), autoplay=True)
        st.rerun()

    if prompt := st.chat_input("Message..."):
        ctx = f"Medical Context: {st.session_state.medical_data}" if st.session_state.medical_data else ""
        res = client.chat.completions.create(messages=[{"role": "system", "content": f"Helpful AI. Use emojis. Ask 'What else can I do for you today?'. {ctx}"}, {"role": "user", "content": prompt}], model="llama-3.3-70b-versatile")
        st.session_state.chat_history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": res.choices[0].message.content}])
        st.rerun()

# --- TAB 3: PAKISTAN TOURISM ---
with tourism_tab:
    st.markdown("### 🇵🇰 Pakistan Tourism Hub")
    
    tourism_pages = {
        "🏠 Home": page_home,
        "🏔️ Destinations": page_destinations,
        "🗺️ Interactive Map": page_maps,
        "🌦️ Weather": page_weather,
        "🤖 Smart Assistant": page_smart_assistant,
        "💰 Budget Planner": page_budget,
        "🔐 Admin Panel": page_admin,
    }
    
    # Sub-Navigation Dropdown
    selection = st.selectbox("Navigate Tourism Modules:", list(tourism_pages.keys()), key="tourism_nav")
    st.divider()
    
    # Render Selected Page
    tourism_pages[selection]()
