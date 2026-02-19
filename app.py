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
    
    # Fallback to default data if JSON is empty so it looks exactly like the image
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
    if not dests: st.warning("No destinations data."); return
    selected = st.selectbox("Select a Destination", [d["name"] for d in dests])
    dest = next(d for d in dests if d["name"] == selected)
    st.subheader(f"📍 {dest['name']} — {dest['region']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Altitude", f"{dest.get('altitude_m', 'N/A')}m")
    c2.metric("Best Season", dest.get("best_season", "N/A"))
    if 'budget_per_day' in dest: c3.metric("Budget/day", f"PKR {dest['budget_per_day'].get('budget', 'N/A')}+")
    st.write(dest.get("description", ""))

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
    st.header("🗺️ Interactive Map")
    dests = load_json("destinations.json")
    markers = json.dumps([{"lat": d.get("latitude", 30), "lng": d.get("longitude", 70), "name": d["name"]} for d in dests if "latitude" in d])
    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <div id="map" style="width: 100%; height: 500px; border-radius: 10px;"></div>
    <script>
        var map = L.map('map').setView([30.37, 69.34], 5);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
        var markers = {markers};
        markers.forEach(function(m) {{ L.marker([m.lat, m.lng]).addTo(map).bindPopup(m.name); }});
    </script>
    """
    components.html(html, height=520)

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
        "🔐 Admin Panel": page_admin,
    }
    
    # Sub-Navigation Dropdown
    selection = st.selectbox("Navigate Tourism Modules:", list(tourism_pages.keys()), key="tourism_nav")
    st.divider()
    
    # Render Selected Page
    tourism_pages[selection]()
