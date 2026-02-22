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
# PAGE CONFIG & INITIAL SETUP
# ============================================================
st.set_page_config(page_title="Ultimate Planner & Tourism Guide", page_icon="🌍", layout="wide")


# ============================================================
# (Rest of your original code follows exactly as before)
# ============================================================
# Initialize theme in session state
if "theme" not in st.session_state:
    st.session_state.theme = "light"
    
# Function to toggle theme
def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

# ============================================================
# THEME-DEPENDENT CSS
# ============================================================
def get_theme_css(theme):
    if theme == "light":
        return """
        <style>
            :root {
                --bg-primary: #ffffff;
                --bg-secondary: #f8fafc;
                --bg-card: #ffffff;
                --bg-card-hover: #f1f5f9;
                --bg-sidebar: #f1f3f5;
                --text-primary: #0f172a;
                --text-secondary: #334155;
                --text-muted: #64748b;
                --text-accent: #047857;
                --border-color: #e2e8f0;
                --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                --shadow-hover: 0 12px 20px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                --gradient-header: linear-gradient(0deg, #4b90ff, #ff5546);
                --gradient-panel: linear-gradient(135deg, #ffffff 0%, #f1f3f5 100%);
                --gradient-panel-selected: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
                --button-bg: #f8f9fa;
                --button-text: #333;
                --button-border: #e0e0e0;
                --button-hover-bg: #e8eaed;
                --button-hover-border: #d2d2d2;
                --input-bg: #ffffff;
                --input-border: #e2e8f0;
                --code-bg: #f1f5f9;
            }
            body { background-color: var(--bg-primary); color: var(--text-primary); font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif; }
            .stApp { background-color: var(--bg-primary); }
        </style>
        """
    else:
        return """
        <style>
            :root {
                --bg-primary: #0f172a;
                --bg-secondary: #1e293b;
                --bg-card: #1e293b;
                --bg-card-hover: #334155;
                --bg-sidebar: #1e293b;
                --text-primary: #f1f5f9;
                --text-secondary: #cbd5e1;
                --text-muted: #94a3b8;
                --text-accent: #4ade80;
                --border-color: #334155;
                --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
                --shadow-hover: 0 12px 20px -3px rgba(0, 0, 0, 0.4);
                --gradient-header: linear-gradient(0deg, #60a5fa, #f87171);
                --gradient-panel: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                --gradient-panel-selected: linear-gradient(135deg, #14532d 0%, #166534 100%);
                --button-bg: #1e293b;
                --button-text: #f1f5f9;
                --button-border: #475569;
                --button-hover-bg: #334155;
                --button-hover-border: #64748b;
                --input-bg: #1e293b;
                --input-border: #475569;
                --code-bg: #1e293b;
            }
            body { background-color: var(--bg-primary); color: var(--text-primary); font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif; }
            .stApp { background-color: var(--bg-primary); }
            .js-plotly-plot .plotly .main-svg { background: var(--bg-card) !important; }
        </style>
        """

# ============================================================
# GLOBAL CSS (shared across themes, uses variables)
# ============================================================
base_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* General */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        color: var(--text-primary);
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    p, li, span, div {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        color: var(--text-secondary);
        line-height: 1.6;
    }
    a {
        color: var(--text-accent);
        text-decoration: none;
        transition: color 0.2s;
    }
    a:hover {
        text-decoration: underline;
    }

    /* Buttons (Gemini-style vertical suggestions) */
    .stButton>button {
        border-radius: 12px;
        background-color: var(--button-bg);
        color: var(--button-text);
        border: 1px solid var(--button-border);
        height: 50px;
        width: 100%;
        text-align: left;
        padding-left: 20px;
        transition: all 0.2s;
        font-weight: 500;
        font-family: 'Inter', sans-serif;
    }
    .stButton>button:hover {
        background-color: var(--button-hover-bg);
        border-color: var(--button-hover-border);
        transform: translateX(5px);
        box-shadow: var(--shadow-hover);
    }

    /* Greeting */
    .greeting-header {
        font-size: 42px !important;
        font-weight: 800;
        background: var(--gradient-header);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .greeting-sub {
        font-size: 20px !important;
        color: var(--text-muted);
        margin-bottom: 30px;
    }

    /* Input Toolbar */
    div[data-testid="stPopover"] > button {
        border-radius: 50%;
        height: 48px;
        width: 48px;
        border: 1px solid var(--border-color);
        margin-top: 28px;
        background-color: var(--input-bg);
    }
    .stAudioInput {
        margin-top: 0px;
    }

    /* Floating Scroll Button */
    .scroll-btn {
        position: fixed;
        bottom: 110px;
        right: 40px;
        background-color: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 50%;
        width: 45px;
        height: 45px;
        text-align: center;
        line-height: 45px;
        font-size: 20px;
        text-decoration: none;
        box-shadow: var(--shadow);
        z-index: 1000;
        transition: 0.3s;
    }
    .scroll-btn:hover {
        background-color: var(--bg-card-hover);
        transform: scale(1.1);
    }

    /* Sidebar / Info Panel Header */
    .info-panel-header {
        font-size: 24px !important;
        font-weight: 800;
        background: var(--gradient-header);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Professional Radio Tabs (for sidebar) */
    div[role="radiogroup"] {
        gap: 10px;
    }
    div[role="radiogroup"] > label {
        background: var(--gradient-panel);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 14px 18px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: var(--text-primary);
        transition: all 0.2s ease-in-out;
        box-shadow: var(--shadow);
        cursor: pointer;
        width: 100%;
        display: block;
    }
    div[role="radiogroup"] > label:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-hover);
        border-color: var(--button-hover-border);
    }
    div[role="radiogroup"] > label > div:first-child {
        display: none;
    }
    div[role="radiogroup"] > label[aria-checked="true"] {
        background: var(--gradient-panel-selected);
        border: 1px solid var(--text-accent);
        color: var(--text-accent);
        border-left: 6px solid var(--text-accent);
    }

    /* Cards */
    .premium-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-top: 4px solid var(--text-accent);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 15px;
        box-shadow: var(--shadow);
        transition: all 0.3s ease;
        height: 100%;
    }
    .premium-card:hover {
        transform: translateY(-5px);
        box-shadow: var(--shadow-hover);
        border-color: var(--text-muted);
    }
    .feature-card {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: var(--shadow);
    }
    .feature-card:hover {
        background: var(--bg-card);
        border-color: var(--text-muted);
        box-shadow: var(--shadow-hover);
        transform: scale(1.02);
    }

    /* Expanders */
    .streamlit-expanderHeader {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: var(--text-primary);
        background-color: var(--bg-secondary);
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }

    /* Dataframes */
    .stDataFrame {
        background-color: var(--bg-card);
        color: var(--text-primary);
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }
    .stDataFrame th {
        background-color: var(--bg-secondary);
        color: var(--text-primary);
        font-weight: 600;
    }
    .stDataFrame td {
        color: var(--text-secondary);
    }

    /* Code blocks */
    .stCodeBlock {
        background-color: var(--code-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
    }

    /* Metrics */
    .stMetric {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 15px;
        box-shadow: var(--shadow);
    }
    .stMetric label {
        color: var(--text-muted);
        font-weight: 500;
    }
    .stMetric .metric-value {
        color: var(--text-primary);
        font-weight: 700;
        font-size: 1.8rem;
    }

    /* Chat messages */
    .stChatMessage {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 10px 15px;
        margin-bottom: 10px;
        box-shadow: var(--shadow);
    }
    .stChatMessage[data-testid="chat-message-user"] {
        background-color: var(--bg-secondary);
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        background-color: var(--input-bg);
        color: var(--text-primary);
        border: 1px solid var(--input-border);
        border-radius: 8px;
        padding: 10px;
        font-family: 'Inter', sans-serif;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--text-accent);
        box-shadow: 0 0 0 2px rgba(4, 120, 87, 0.2);
    }

    /* File uploader */
    .stFileUploader {
        background-color: var(--bg-secondary);
        border: 1px dashed var(--border-color);
        border-radius: 8px;
        padding: 10px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: var(--bg-secondary);
        border-radius: 8px 8px 0 0;
        padding: 10px 16px;
        color: var(--text-muted);
        font-weight: 600;
        border: 1px solid var(--border-color);
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--bg-card);
        color: var(--text-accent);
        border-bottom: 2px solid var(--text-accent);
    }

    /* Divider */
    hr {
        border-color: var(--border-color);
    }

    /* Theme toggle button (small, top right) */
    .theme-toggle-btn {
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
        border-radius: 30px;
        padding: 8px 18px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        box-shadow: var(--shadow);
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    .theme-toggle-btn:hover {
        background: var(--bg-card-hover);
        transform: translateY(-2px);
    }
    .theme-toggle-btn .icon {
        font-size: 18px;
    }

    /* Gallery images */
    .gallery-img-container {
        overflow: hidden;
        border-radius: 15px;
        margin-bottom: 20px;
        box-shadow: var(--shadow);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        background-color: var(--bg-card);
    }
    .gallery-img-container:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: var(--shadow-hover);
    }
    .gallery-img-container img {
        width: 100%;
        height: 250px;
        object-fit: cover;
        display: block;
    }
    .gallery-img-caption {
        text-align: center;
        padding: 10px;
        margin: 0;
        font-size: 0.95em;
        font-weight: 600;
        color: var(--text-primary);
        border-top: 1px solid var(--border-color);
    }

    /* ===== NEW ANIMATIONS FOR GENERATE BUTTON ===== */
    @keyframes pulse-glow {
        0% { box-shadow: 0 0 0 0 rgba(4, 120, 87, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(4, 120, 87, 0); }
        100% { box-shadow: 0 0 0 0 rgba(4, 120, 87, 0); }
    }
    
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(45deg, #047857, #10b981, #047857);
        background-size: 200% 200%;
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.2rem !important;
        border: none !important;
        animation: pulse-glow 2s infinite, gradient-shift 5s ease infinite !important;
        transition: transform 0.3s ease !important;
    }
    
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: scale(1.02) !important;
        animation: pulse-glow 1s infinite, gradient-shift 3s ease infinite !important;
    }
    
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Colored section headings for trip plan */
    .plan-heading-emergency {
        color: #dc2626;
        font-size: 1.5rem;
        font-weight: 700;
        border-left: 6px solid #dc2626;
        padding-left: 15px;
        margin: 25px 0 15px 0;
    }
    .plan-heading-clothing {
        color: #2563eb;
        font-size: 1.5rem;
        font-weight: 700;
        border-left: 6px solid #2563eb;
        padding-left: 15px;
        margin: 25px 0 15px 0;
    }
    .plan-heading-schedule {
        color: #7c3aed;
        font-size: 1.5rem;
        font-weight: 700;
        border-left: 6px solid #7c3aed;
        padding-left: 15px;
        margin: 25px 0 15px 0;
    }
    .plan-heading-behavior {
        color: #b45309;
        font-size: 1.5rem;
        font-weight: 700;
        border-left: 6px solid #b45309;
        padding-left: 15px;
        margin: 25px 0 15px 0;
    }
    .plan-heading-scams {
        color: #be185d;
        font-size: 1.5rem;
        font-weight: 700;
        border-left: 6px solid #be185d;
        padding-left: 15px;
        margin: 25px 0 15px 0;
    }
    .plan-heading-tips {
        color: #059669;
        font-size: 1.5rem;
        font-weight: 700;
        border-left: 6px solid #059669;
        padding-left: 15px;
        margin: 25px 0 15px 0;
    }
    
    /* Card fade-in animation */
    .fade-in-card {
        animation: fadeIn 0.8s ease-in;
    }
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
</style>
"""

# ============================================================
# SECRETS MANAGEMENT & CONFIG
# ============================================================
try:
    GROQ_KEY = st.secrets["groq_api_key"]
    WEATHER_KEY = st.secrets["weather_api_key"]
    TAVILY_KEY = st.secrets["tavily_api_key"]
    DEEPSEEK_KEY = st.secrets["deepseek_api_key"]  # NEW: DeepSeek API key
except FileNotFoundError:
    st.error("Secrets file not found.")
    st.stop()
except KeyError:
    st.error("Missing keys in secrets. Please ensure groq_api_key, weather_api_key, tavily_api_key, and deepseek_api_key are set.")
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
if "autoplay_audio" not in st.session_state:
    st.session_state.autoplay_audio = None
if "tourism_chat_history" not in st.session_state:
    st.session_state.tourism_chat_history = []
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False
if "show_info_panel" not in st.session_state:
    st.session_state.show_info_panel = True
if "current_tourism_module" not in st.session_state:
    st.session_state.current_tourism_module = "📊 Executive Dashboard"

# New state for planner navigation
if "planner_module" not in st.session_state:
    st.session_state.planner_module = "📋 Dashboard"

def clear_chat():
    st.session_state.chat_history = []
    st.session_state.medical_data = ""
    st.session_state.last_audio = None
    st.session_state.autoplay_audio = None

def update_planner_module():
    st.session_state.planner_module = st.session_state.planner_nav

def update_tourism_module():
    st.session_state.current_tourism_module = st.session_state.tourism_nav

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
# DUAL AI FUNCTION FOR HEALTH COMPANION
# ============================================================
def get_ai_response(messages, model="llama-3.3-70b-versatile"):
    """
    Attempts to get response from Groq first.
    If Groq fails, falls back to DeepSeek.
    If both fail, returns an error message.
    """
    # Try Groq first
    try:
        groq_client = Groq(api_key=GROQ_KEY)
        response = groq_client.chat.completions.create(
            messages=messages,
            model=model
        )
        return response.choices[0].message.content, "groq"
    except Exception as e:
        st.warning(f"Groq API failed: {str(e)[:100]}. Falling back to DeepSeek...")
        
        # Fallback to DeepSeek
        try:
            # DeepSeek API call (assuming OpenAI-compatible endpoint)
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7
            }
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"], "deepseek"
        except Exception as e2:
            st.error(f"Both AI services failed. Groq: {str(e)[:100]}, DeepSeek: {str(e2)[:100]}")
            return "I'm sorry, but I'm unable to process your request at the moment. Please try again later.", None

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
# TOURISM PAGES VIEWS (unchanged, with CSS variables)
# ============================================================
def page_home():
    st.markdown("""
<div style='text-align:center; padding: 30px 0 10px 0;'>
    <h1 style='font-size: 3.2em; font-weight: 800; color: var(--text-primary); font-family: "Inter", sans-serif; letter-spacing: -0.5px; margin-bottom: 5px;'>
        Discover <span style='color: var(--text-accent);'>Pakistan</span>
    </h1>
    <p style='font-size: 1.3em; color: var(--text-muted); font-weight: 400; letter-spacing: 0.5px;'>Your Exclusive Digital Tourism Concierge</p>
</div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
<div style='font-size: 1.1em; color: var(--text-secondary); line-height: 1.8; text-align: center; max-width: 900px; margin: 0 auto 40px auto; font-family: "Inter", serif;'>
Embark on an unparalleled expedition through a land of majestic topographies, profound heritage, and legendary hospitality. From the formidable peaks of the Karakoram range to the vibrant, cosmopolitan pulse of Lahore, we curate an elite travel experience tailored for the discerning explorer.
</div>
    """, unsafe_allow_html=True)
    
    dests = load_json("destinations.json")
    
    if not dests:
        dests = [
            {"name": "Hunza Valley", "region": "Gilgit-Baltistan", "access_level": "Moderate", "best_season": "April - October", "budget_per_day": {"budget": 5000}},
            {"name": "Skardu", "region": "Gilgit-Baltistan", "access_level": "Moderate", "best_season": "May - September", "budget_per_day": {"budget": 6000}},
            {"name": "Swat Valley", "region": "Khyber Pakhtunkhwa", "access_level": "Easy", "best_season": "March - October", "budget_per_day": {"budget": 4000}},
            {"name": "Lahore", "region": "Punjab", "access_level": "Easy", "best_season": "October - March", "budget_per_day": {"budget": 3000}}
        ]
        
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>✨ Curated Destinations</h2>", unsafe_allow_html=True)
    
    cols = st.columns(min(len(dests), 4))
    for i, dest in enumerate(dests[:4]):
        with cols[i % 4]:
            budget = dest.get('budget_per_day', {}).get('budget', 'N/A')
            budget_str = f"{budget:,}" if isinstance(budget, (int, float)) else str(budget)
            
            st.markdown(f"""
<div class="premium-card">
    <h3 style='color: var(--text-primary); font-size: 1.4em; font-weight: 800; margin: 0 0 5px 0;'>{dest.get('name', 'N/A')}</h3>
    <p style='color: var(--text-muted); font-size: 0.85em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin: 0 0 20px 0;'>{dest.get('region', 'N/A')}</p>
    <div style='display: flex; flex-direction: column; gap: 8px;'>
        <div style='font-size: 0.9em; color: var(--text-secondary);'>🧭 <b>Accessibility:</b> {dest.get('access_level', 'N/A')}</div>
        <div style='font-size: 0.9em; color: var(--text-secondary);'>🌤️ <b>Optimal Window:</b> {dest.get('best_season', 'N/A')}</div>
        <div style='font-size: 1.05em; color: var(--text-accent); font-weight: 700; margin-top: 15px; border-top: 1px solid var(--border-color); padding-top: 15px;'>💳 Starts at PKR {budget_str} / day</div>
    </div>
</div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🏛️ Premium Concierge Services</h2>", unsafe_allow_html=True)
    
    features = [
        ("🗺️", "Destination Intelligence", "Comprehensive insights into elite locales."),
        ("🧠", "AI Travel Strategist", "Personalized cognitive assistance for your itinerary."),
        ("📊", "Financial Architect", "Precision budget forecasting and resource allocation."),
        ("🧭", "Geospatial Navigation", "High-fidelity interactive mapping systems."),
        ("🌤️", "Meteorological Data", "Real-time atmospheric conditions and forecasts."),
        ("🛡️", "Security Protocol", "Immediate access to critical emergency networks."),
        ("🖼️", "Visual Archive", "Curated high-resolution photographic galleries."),
        ("📖", "Cultural Etiquette", "Guidelines for respectful and immersive travel.")
    ]
    
    cols1 = st.columns(4)
    for i in range(4):
        icon, title, desc = features[i]
        with cols1[i]:
            st.markdown(f"""
<div class="feature-card">
    <div style='font-size: 2.5em; margin-bottom: 15px;'>{icon}</div>
    <h4 style='color: var(--text-primary); font-size: 1.05em; font-weight: 700; margin: 0 0 10px 0;'>{title}</h4>
    <p style='color: var(--text-muted); font-size: 0.85em; line-height: 1.5; margin: 0;'>{desc}</p>
</div>
<br>
            """, unsafe_allow_html=True)
            
    cols2 = st.columns(4)
    for i in range(4, 8):
        icon, title, desc = features[i]
        with cols2[i-4]:
            st.markdown(f"""
<div class="feature-card">
    <div style='font-size: 2.5em; margin-bottom: 15px;'>{icon}</div>
    <h4 style='color: var(--text-primary); font-size: 1.05em; font-weight: 700; margin: 0 0 10px 0;'>{title}</h4>
    <p style='color: var(--text-muted); font-size: 0.85em; line-height: 1.5; margin: 0;'>{desc}</p>
</div>
            """, unsafe_allow_html=True)

def page_destinations():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🧭 Geospatial Destination Archive</h2>", unsafe_allow_html=True)
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
                "description": "The Hunza Valley stands as one of Pakistan's most resplendent topographical marvels, ensconced by formidable snow-capped summits including Rakaposhi and Ultar Sar. The domain is globally recognized for its superlative landscapes, ancient fortified structures, and the profound hospitality of the indigenous populace.",
                "history": "Historically functioning as an autonomous princely state for nearly a millennium under the sovereign rule of the Mir of Hunza, the region served as a pivotal node along the ancient Silk Route. It was fully integrated into the Federation of Pakistan in 1974. The territory is predominantly inhabited by the Burushaski-speaking demographic, utilizing a language isolate bereft of known genealogical affiliations.",
                "landmarks": [{"name": "Baltit Fort", "description": "A heptacentennial fortress strategically positioned above Karimabad, currently functioning as a UNESCO-endorsed heritage conservatory."}],
                "activities": ["High-altitude trekking and alpine ascents", "Historical fortification reconnaissance", "Nautical navigation across Attabad Lake"],
                "transport": {"Islamabad": {"road": "14-16 hours via the Karakoram Highway corridor"}},
                "accommodation": {"budget": ["Economical lodging facilities in Karimabad"], "luxury": ["Serena Hotel - Premium accommodations"]},
                "connectivity": {"mobile_networks": ["SCOM (Optimal Infrastructure)", "Telenor"], "internet": "Broadband accessible in primary establishments", "tips": "Procurement of an SCOM cellular subscription in Gilgit is highly advised."}
            },
            {
                "name": "Skardu",
                "region": "Gilgit-Baltistan",
                "access_level": "Moderate",
                "altitude_m": 2228,
                "best_season": "May - September",
                "budget_per_day": {"budget": 6000},
                "description": "Serving as the principal gateway to the Karakoram's eight-thousanders, Skardu is a high-altitude sanctuary characterized by stark alpine deserts, cerulean lakes, and monumental geological formations.",
                "history": "Capital of the historic Baltistan region, Skardu possesses a profoundly rich Tibetan-influenced heritage, often referred to as 'Little Tibet', manifesting in its architectural vernacular and local gastronomy.",
                "landmarks": [{"name": "Kharpocho Fort", "description": "An ancient fortification offering panoramic surveillance of the Indus River."}],
                "activities": ["High-altitude acclimatization", "Deosai National Park traversal", "Engagement with local Balti heritage"],
                "transport": {"Islamabad": {"road": "20-22 hours via rigorous alpine routes", "air": "45-minute scenic aerial transit"}},
                "accommodation": {"budget": ["Standard alpine guest houses"], "luxury": ["Shangrila Resort Skardu"]},
                "connectivity": {"mobile_networks": ["SCOM", "Zong"], "internet": "Intermittent broadband within municipal limits", "tips": "Total telecommunication blackout expected in peripheral zones like Deosai."}
            },
            {
                "name": "Swat Valley",
                "region": "Khyber Pakhtunkhwa",
                "access_level": "Easy",
                "altitude_m": 980,
                "best_season": "March - October",
                "budget_per_day": {"budget": 4000},
                "description": "Historically chronicled as the 'Switzerland of the East', the Swat Valley is an emerald expanse of dense coniferous forests, crystalline glacial rivers, and undulating meadows.",
                "history": "A pivotal epicenter for early Buddhist civilization, the valley functions as a vast repository of ancient stupas and Gandharan archaeological artifacts.",
                "landmarks": [{"name": "Malam Jabba", "description": "A premier high-altitude ski resort."}, {"name": "Butkara Stupa", "description": "A monumental relic of Gandharan antiquity."}],
                "activities": ["Alpine skiing", "Trout fishing", "Archaeological expeditions"],
                "transport": {"Islamabad": {"road": "4-5 hours via the Swat Motorway infrastructure"}},
                "accommodation": {"budget": ["Mingora municipal lodgings"], "luxury": ["Serena Hotel Swat"]},
                "connectivity": {"mobile_networks": ["Jazz", "Telenor", "Zong"], "internet": "Robust 4G LTE saturation in primary urban nodes", "tips": "Signal integrity diminishes in elevated extremities like Kalam."}
            },
            {
                "name": "Lahore",
                "region": "Punjab",
                "access_level": "Easy",
                "altitude_m": 217,
                "best_season": "October - March",
                "budget_per_day": {"budget": 3000},
                "description": "The undisputed cultural epicenter of the Republic, Lahore is a vibrant metropolis that seamlessly amalgamates majestic Mughal architecture with contemporary urban dynamism.",
                "history": "Serving as the imperial capital for multiple dynasties, Lahore's historical tapestry is woven with the legacies of Mughal emperors, Sikh monarchs, and British colonial administrators.",
                "landmarks": [{"name": "Badshahi Mosque", "description": "A monolithic marvel of 17th-century Mughal engineering."}, {"name": "Lahore Fort", "description": "A formidable citadel recognized globally as a UNESCO World Heritage site."}],
                "activities": ["Gastronomic exploration in the Walled City", "Heritage walking tours", "Attendance at the Wagah Border ceremonial protocol"],
                "transport": {"Islamabad": {"road": "4 hours via the M-2 Motorway", "air": "45-minute commercial flight"}},
                "accommodation": {"budget": ["Central municipal hostels"], "luxury": ["Pearl Continental Lahore"]},
                "connectivity": {"mobile_networks": ["Universal coverage across all major carriers"], "internet": "High-velocity fiber-optic and 4G/5G infrastructure universally accessible", "tips": "Procure localized ride-hailing applications for optimal municipal transit."}
            },
            {
                "name": "Islamabad",
                "region": "Capital Territory",
                "access_level": "Easy",
                "altitude_m": 540,
                "best_season": "October - April",
                "budget_per_day": {"budget": 4500},
                "description": "The meticulously master-planned federal capital, distinguished by its verdant expanses, systematic sectorial grid, and immediate proximity to the forested Margalla Hills.",
                "history": "Conceptualized and actualized in the 1960s to replace Karachi as the national capital, integrating modern architectural paradigms with profound Islamic geometric influences.",
                "landmarks": [{"name": "Faisal Mosque", "description": "An architectural masterpiece capable of accommodating 100,000 worshippers."}, {"name": "Pakistan Monument", "description": "A comprehensive homage to the nation's heritage."}],
                "activities": ["Hiking the Margalla trail network", "Diplomatic enclave traversal", "Elite culinary dining"],
                "transport": {"Lahore": {"road": "4 hours via M-2 Motorway", "air": "45-minute commercial transit"}},
                "accommodation": {"budget": ["Sector G-9 standard accommodations"], "luxury": ["Serena Hotel Islamabad", "Marriott Hotel"]},
                "connectivity": {"mobile_networks": ["Universal 4G/5G coverage"], "internet": "Optimal high-speed connectivity across all vectors", "tips": "Utilize dedicated municipal transit paths for rapid sector-to-sector movement."}
            },
            {
                "name": "Fairy Meadows",
                "region": "Gilgit-Baltistan",
                "access_level": "Difficult",
                "altitude_m": 3300,
                "best_season": "June - September",
                "budget_per_day": {"budget": 8000},
                "description": "An elevated, isolated alpine pasture functioning as the primary observational platform for Nanga Parbat, the ninth highest terrestrial summit globally.",
                "history": "Historically utilized as a base camp for global mountaineering expeditions attempting the perilous ascent of the 'Killer Mountain'.",
                "landmarks": [{"name": "Nanga Parbat Base Camp", "description": "The ultimate destination for advanced trekkers."}, {"name": "Reflection Lake", "description": "A pristine alpine pool mirroring the Nanga Parbat massif."}],
                "activities": ["Strenuous high-altitude trekking", "Nocturnal astrophotography", "Survivalist camping"],
                "transport": {"Islamabad": {"road": "16 hours to Raikot Bridge, followed by extreme off-road jeep transit and a 3-hour vertical hike"}},
                "accommodation": {"budget": ["Basic wooden alpine huts"], "luxury": ["Premium glamping pods with localized heating"]},
                "connectivity": {"mobile_networks": ["Severely restricted"], "internet": "Functional telecommunication blackout", "tips": "Satellite communication recommended for critical emergencies."}
            },
            {
                "name": "Mohenjo-Daro",
                "region": "Sindh",
                "access_level": "Easy",
                "altitude_m": 47,
                "best_season": "November - February",
                "budget_per_day": {"budget": 3500},
                "description": "An archaeological masterwork representing one of the earliest and most sophisticated urban settlements in human history, situated adjacent to the Indus River.",
                "history": "Flourishing circa 2500 BCE, this Indus Valley Civilization metropolis featured advanced civil engineering, including complex drainage systems and standardized brick architecture.",
                "landmarks": [{"name": "The Great Bath", "description": "A monumental public aquatic structure."}, {"name": "The Buddhist Stupa", "description": "A subsequent addition overlaying the ancient ruins."}],
                "activities": ["Archaeological site immersion", "Historical museum analysis"],
                "transport": {"Karachi": {"road": "7-8 hours via the Indus Highway", "air": "Domestic flight to Sukkur followed by vehicular transit"}},
                "accommodation": {"budget": ["Larkana municipal guest houses"], "luxury": ["PTDC Motel Larkana"]},
                "connectivity": {"mobile_networks": ["Jazz", "Zong", "Telenor"], "internet": "Standard 3G/4G within the vicinity", "tips": "Deploy rigorous ultraviolet mitigation protocols during daylight hours."}
            },
            {
                "name": "Neelum Valley",
                "region": "Azad Kashmir",
                "access_level": "Moderate",
                "altitude_m": 1500,
                "best_season": "May - October",
                "budget_per_day": {"budget": 4500},
                "description": "A bow-shaped, densely forested gorge spanning 144 kilometers, celebrated for its sapphire-hued river, cascading waterfalls, and profound tranquility.",
                "history": "Serving as a critical historical artery in the Kashmir region, the valley is steeped in complex geopolitical history and regional folklore.",
                "landmarks": [{"name": "Arang Kel", "description": "An idyllic, highly elevated settlement accessible via cable car."}, {"name": "Sharda", "description": "A breathtaking panoramic viewpoint containing ancient university ruins."}],
                "activities": ["Riverine navigation", "Botanical exploration", "Alpine lodging"],
                "transport": {"Islamabad": {"road": "8-10 hours via Muzaffarabad"}},
                "accommodation": {"budget": ["Keran riverside huts"], "luxury": ["State-operated luxury cabins in Sharda"]},
                "connectivity": {"mobile_networks": ["SCOM exclusive"], "internet": "Highly intermittent; substantial localized blackouts", "tips": "Verification of border proximity restrictions is mandatory prior to transit."}
            }
        ]

    regions = sorted(set(d.get("region", "Unspecified Territory") for d in dests))
    col1, col2 = st.columns(2)
    with col1:
        sel_region = st.selectbox("Isolate by Provincial Territory", ["Comprehensive Archival View"] + regions)
    with col2:
        sel_access = st.selectbox("Isolate by Accessibility Threshold", ["Unrestricted", "Easy", "Moderate", "Difficult"])

    filtered = dests
    if sel_region != "Comprehensive Archival View":
        filtered = [d for d in filtered if d.get("region") == sel_region]
    if sel_access != "Unrestricted":
        filtered = [d for d in filtered if d.get("access_level") == sel_access]

    if not filtered:
        st.info("No topographical records match the designated parameters.")
        return

    selected = st.selectbox("Designate a Specific Geographic Locale", [d["name"] for d in filtered])
    dest = next(d for d in filtered if d["name"] == selected)

    st.markdown(f"<h3 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>📍 {dest['name']} — <span style='color: var(--text-muted); font-weight: 400;'>{dest.get('region', 'Unspecified')}</span></h3>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accessibility Threshold", dest.get("access_level", "N/A"))
    c2.metric("Topographical Elevation", f"{dest.get('altitude_m', 'N/A')}m")
    c3.metric("Optimal Transit Window", dest.get("best_season", "N/A"))
    
    budget = dest.get('budget_per_day', {}).get('budget', 'N/A')
    c4.metric("Estimated Daily Expenditure", f"PKR {budget:,}+" if isinstance(budget, int) else f"PKR {budget}+")

    st.markdown(f"<p style='font-size: 1.05em; color: var(--text-secondary); line-height: 1.7; font-family: \"Inter\", serif;'><b>📄 Topographical Synopsis:</b> {dest.get('description', '')}</p>", unsafe_allow_html=True)

    with st.expander("🏛️ Historical & Heritage Context", expanded=False):
        st.markdown(f"<p style='color: var(--text-secondary); font-family: \"Inter\", serif; line-height: 1.6;'>{dest.get('history', 'Historical records currently unavailable.')}</p>", unsafe_allow_html=True)

    if "landmarks" in dest and dest["landmarks"]:
        with st.expander("🏛️ Key Architectural & Natural Landmarks", expanded=False):
            for lm in dest["landmarks"]:
                st.markdown(f"<b style='color:var(--text-primary);'>{lm['name']}</b> — <span style='color:var(--text-secondary);'>{lm['description']}</span>", unsafe_allow_html=True)

    if "activities" in dest and dest["activities"]:
        with st.expander("⛷️ Recommended Expeditionary Excursions", expanded=False):
            for act in dest["activities"]:
                st.markdown(f"<li style='color:var(--text-secondary);'>{act}</li>", unsafe_allow_html=True)

    if "transport" in dest and dest["transport"]:
        with st.expander("🚆 Logistical & Transit Framework", expanded=False):
            for origin, modes in dest["transport"].items():
                st.markdown(f"<b style='color:var(--text-primary);'>Originating from {origin.replace('_',' ').title()}:</b>", unsafe_allow_html=True)
                for mode, info in modes.items():
                    st.markdown(f"<li style='color:var(--text-secondary);'><i>{mode.title()}:</i> {info}</li>", unsafe_allow_html=True)

    if "accommodation" in dest and dest["accommodation"]:
        with st.expander("🏨 Premium Lodging & Accommodations", expanded=False):
            for tier, hotels in dest["accommodation"].items():
                st.markdown(f"<b style='color:var(--text-primary);'>{tier.title()} Classification:</b>", unsafe_allow_html=True)
                for h in hotels:
                    st.markdown(f"<li style='color:var(--text-secondary);'>{h}</li>", unsafe_allow_html=True)

    if "connectivity" in dest and dest["connectivity"]:
        with st.expander("📡 Telecommunication Infrastructure", expanded=False):
            conn = dest["connectivity"]
            st.markdown(f"<p style='color:var(--text-secondary);'><b>Cellular Networks:</b> {', '.join(conn.get('mobile_networks', []))}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:var(--text-secondary);'><b>Broadband Access:</b> {conn.get('internet', 'N/A')}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:var(--text-accent);'><b>💡 Strategic Advisory:</b> {conn.get('tips', 'N/A')}</p>", unsafe_allow_html=True)

def page_weather():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🌤️ Meteorological Forecast & Conditions</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1em; color: var(--text-secondary); line-height: 1.8; font-family: \"Inter\", serif;'>Access real-time atmospheric data and extended meteorological projections to meticulously plan your expeditionary window.</p>", unsafe_allow_html=True)
    
    dests = load_json("destinations.json")
    
    if not dests:
        dests = [
            {"name": "Hunza Valley", "region": "Gilgit-Baltistan", "latitude": 36.3167, "longitude": 74.6500},
            {"name": "Skardu", "region": "Gilgit-Baltistan", "latitude": 35.2971, "longitude": 75.6333},
            {"name": "Swat Valley", "region": "Khyber Pakhtunkhwa", "latitude": 35.2227, "longitude": 72.4258},
            {"name": "Lahore", "region": "Punjab", "latitude": 31.5204, "longitude": 74.3587},
            {"name": "Islamabad", "region": "Capital Territory", "latitude": 33.6844, "longitude": 73.0479},
            {"name": "Fairy Meadows", "region": "Gilgit-Baltistan", "latitude": 35.3850, "longitude": 74.5786}
        ]

    selected = st.selectbox("Designate Geographic Locale for Atmospheric Analysis", [d["name"] for d in dests], key="w_dest")
    dest = next(d for d in dests if d["name"] == selected)
    
    lat = dest.get("latitude", 30.3753)
    lon = dest.get("longitude", 69.3451)
    
    with st.spinner("Acquiring real-time meteorological telemetry..."):
        weather = fetch_weather_tourism(lat, lon)
        
    if weather and "current" in weather:
        st.markdown(f"<h3 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; margin-top: 20px;'>📍 Current Atmospheric Telemetry: {dest['name']}</h3>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Thermal Reading", f"{weather['current']['temperature_2m']} °C")
        c2.metric("Relative Humidity", f"{weather['current']['relative_humidity_2m']} %")
        c3.metric("Prevailing Conditions", weather_code_to_text(weather['current']['weather_code']))
        
        if "daily" in weather:
            st.markdown("<h3 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; margin-top: 30px;'>📈 7-Day Extended Meteorological Projection</h3>", unsafe_allow_html=True)
            daily = weather["daily"]
            df = pd.DataFrame({
                "Date": daily["time"],
                "Maximum Thermal (°C)": daily["temperature_2m_max"],
                "Minimum Thermal (°C)": daily["temperature_2m_min"],
                "Precipitation Volume (mm)": daily["precipitation_sum"]
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Maximum Thermal (°C)"], name="Max Thermal", line=dict(color="#e11d48", width=3)))
            fig.add_trace(go.Scatter(x=df["Date"], y=df["Minimum Thermal (°C)"], name="Min Thermal", line=dict(color="#0284c7", width=3)))
            fig.add_trace(go.Bar(x=df["Date"], y=df["Precipitation Volume (mm)"], name="Precipitation", marker_color="#059669", opacity=0.3, yaxis="y2"))
            
            template = "plotly_dark" if st.session_state.theme == "dark" else "plotly"
            fig.update_layout(
                yaxis2=dict(title="Precipitation (mm)", overlaying="y", side="right"),
                yaxis=dict(title="Thermal Reading (°C)"),
                legend=dict(orientation="h", y=1.12),
                height=450,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                template=template
            )
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='var(--border-color)')
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='var(--border-color)')
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("Meteorological telemetry currently inaccessible. Please initiate a retry sequence.")

def page_smart_assistant():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🧠 Artificial Intelligence Concierge</h2>", unsafe_allow_html=True)
    if prompt := st.chat_input("Inquire regarding Pakistani topography, heritage, or logistics..."):
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
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🗺️ Interactive Geospatial Mapping</h2>", unsafe_allow_html=True)
    destinations = load_json("destinations.json")
    
    if not destinations:
        destinations = [
            {"name": "Hunza Valley", "region": "Gilgit-Baltistan", "access_level": "Moderate", "latitude": 36.3167, "longitude": 74.6500, "altitude_m": 2438, "best_season": "April - October", "budget_per_day": {"budget": 5000}},
            {"name": "Skardu", "region": "Gilgit-Baltistan", "access_level": "Moderate", "latitude": 35.2971, "longitude": 75.6333, "altitude_m": 2228, "best_season": "May - September", "budget_per_day": {"budget": 6000}},
            {"name": "Swat Valley", "region": "Khyber Pakhtunkhwa", "access_level": "Easy", "latitude": 35.2227, "longitude": 72.4258, "altitude_m": 980, "best_season": "March - October", "budget_per_day": {"budget": 4000}},
            {"name": "Lahore", "region": "Punjab", "access_level": "Easy", "latitude": 31.5204, "longitude": 74.3587, "altitude_m": 217, "best_season": "October - March", "budget_per_day": {"budget": 3000}},
            {"name": "Fairy Meadows", "region": "Gilgit-Baltistan", "access_level": "Difficult", "latitude": 35.3850, "longitude": 74.5786, "altitude_m": 3300, "best_season": "June - September", "budget_per_day": {"budget": 8000}},
            {"name": "Mohenjo-Daro", "region": "Sindh", "access_level": "Easy", "latitude": 27.3292, "longitude": 68.1389, "altitude_m": 47, "best_season": "November - February", "budget_per_day": {"budget": 3500}}
        ]

    col1, col2, col3 = st.columns(3)
    with col1:
        show_dest = st.checkbox("📍 Display Topographical Markers", value=True)
    with col2:
        show_routes = st.checkbox("🛣️ Illuminate Primary Transit Arteries", value=True)
    with col3:
        map_lang = st.radio("🌐 Linguistic Preference", ["English", "اردو (Urdu)"], horizontal=True, key="map_lang")
        
    st.markdown("<p style='font-family: \"Inter\", sans-serif; color:var(--text-muted);'>🟢 <b>High Accessibility</b> | 🟠 <b>Intermediate Accessibility</b> | 🔴 <b>Restricted / Expeditionary</b></p>", unsafe_allow_html=True)
    
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

    map_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            body {{ margin: 0; padding: 0; background: var(--bg-primary); }}
            #map {{ width: 100%; height: 580px; border-radius: 12px; border: 1px solid var(--border-color); }}
            .dest-popup h4 {{ margin: 0 0 5px; color: var(--text-accent); font-family: 'Inter', sans-serif; font-weight: bold; }}
            .dest-popup p {{ margin: 2px 0; font-size: 13px; font-family: 'Inter', sans-serif; color: var(--text-secondary); }}
            .dest-popup hr {{ margin: 5px 0; border-color: var(--border-color); }}
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
                    '<p style="color:var(--text-muted);">' + m.region + '</p>' +
                    '<hr>' +
                    '<p>⛰️ Elevation: ' + m.altitude + '</p>' +
                    '<p>📍 Index: <b style="color:'+m.color+';">' + m.access + '</b></p>' +
                    '<p>📅 Optimal: ' + m.season + '</p>' +
                    '<p>💳 ' + m.budget + '</p>' +
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
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>📊 Financial Architecture & Resource Allocation</h2>", unsafe_allow_html=True)
    
    budget_data = load_json("budget_templates.json")
    destinations = load_json("destinations.json")
    
    if not destinations:
        destinations = [{"name": "Hunza Valley"}, {"name": "Skardu"}, {"name": "Swat Valley"}, {"name": "Lahore"}]
        
    if not budget_data or "categories" not in budget_data:
        budget_data = {
            "travel_styles": ["Budget", "Standard", "Luxury"],
            "categories": [
                {"name": "Premium Accommodations", "icon": "🏨", "budget": 2000, "standard": 5000, "luxury": 15000},
                {"name": "Culinary Sustenance", "icon": "🍽️", "budget": 1200, "standard": 3000, "luxury": 8000},
                {"name": "Logistical Transit", "icon": "🚙", "budget": 800, "standard": 2500, "luxury": 8000},
                {"name": "Excursions & Admissions", "icon": "🎟️", "budget": 300, "standard": 1000, "luxury": 3000},
                {"name": "Telecommunications", "icon": "📡", "budget": 150, "standard": 300, "luxury": 500},
                {"name": "Contingency Capital", "icon": "💼", "budget": 500, "standard": 1500, "luxury": 5000}
            ],
            "currency_rates": {
                "USD": 0.0036, "EUR": 0.0033, "GBP": 0.0028, "AED": 0.013, "CNY": 0.026
            },
            "tips": [
                "Utilize verified ride-hailing networks (Careem/InDrive) in lieu of traditional municipal taxis to ensure pricing transparency.",
                "Engage with localized gastronomic establishments for an authentic and economically optimized culinary experience.",
                "Execute lodging reservations pre-emptively during peak meteorological windows (June–August) to avert demand-surge pricing."
            ]
        }

    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>Parametrize Your Expedition</h4>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        sel_dest = st.selectbox("Designate Primary Hub", [d["name"] for d in destinations], key="bp_dest")
        num_days = st.slider("Expedition Duration (Days)", 1, 30, 5)
    with c2:
        style = st.selectbox("Designate Expenditure Tier", budget_data.get("travel_styles", ["Budget", "Standard", "Luxury"]))
        num_people = st.slider("Total Personnel Count", 1, 10, 2)
        
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
            "Financial Category": f"{cat.get('icon','')} {cat['name']}", 
            "Per Capita Daily Allocation (PKR)": f"{daily:,}", 
            "Cumulative Valuation (PKR)": f"{cost:,}"
        })
        pie_data.append(cost)
        pie_labels.append(cat['name'])
        
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Total Capital Required", f"PKR {total:,}")
    c2.metric("👤 Per Capita Liability", f"PKR {total // max(num_people,1):,}")
    c3.metric("📅 Daily Burn Rate", f"PKR {total // max(num_days,1):,}")
    
    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
    
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; margin-top:20px;'>Proportional Expenditure Allocation</h4>", unsafe_allow_html=True)
    template = "plotly_dark" if st.session_state.theme == "dark" else "plotly"
    fig = px.pie(values=pie_data, names=pie_labels, color_discrete_sequence=px.colors.qualitative.Set3, template=template)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; margin-top:10px;'>Global Currency Conversion</h4>", unsafe_allow_html=True)
    rates = budget_data.get("currency_rates", {})
    sel_currency = st.selectbox("Designate Target Currency", [c for c in rates.keys()])
    rate = rates.get(sel_currency, 1)
    st.info(f"**Calculated Exchange:** PKR {total:,} ≈ **{sel_currency} {total * rate:,.2f}**")
    
    st.divider()
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>💡 Strategic Fiscal Optimization Directives</h4>", unsafe_allow_html=True)
    for tip in budget_data.get("tips", []):
        st.markdown(f"<li style='color:var(--text-secondary); font-family: \"Inter\", serif;'>{tip}</li>", unsafe_allow_html=True)

def page_emergency():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🛡️ Critical Response & Emergency Protocols</h2>", unsafe_allow_html=True)
    st.error("**In the event of an exigency, initiate contact immediately:** Law Enforcement **15** | Rapid Rescue **1122** | Medical Evacuation **115** | Fire Services **16**")
    
    data = load_json("emergency_contacts.json")
    
    if not data:
        data = {
            "national": [
                {"service": "Federal Police Emergency Command", "number": "15", "coverage": "Nationwide"},
                {"service": "Rapid Deployment Rescue 1122", "number": "1122", "coverage": "Punjab, KPK, Islamabad, AJK, GB"},
                {"service": "Edhi Foundation Medical Evacuation", "number": "115", "coverage": "Nationwide"},
                {"service": "Municipal Fire Brigade Services", "number": "16", "coverage": "Nationwide"},
                {"service": "National Tourism Assistance Protocol", "number": "1422", "coverage": "Nationwide"},
                {"service": "Federal Motorway Security Forces", "number": "130", "coverage": "All Federal Transit Arteries"},
                {"service": "Federal Investigation Agency (FIA)", "number": "9911", "coverage": "Nationwide"},
                {"service": "National Disaster Management Authority", "number": "051-9205037", "coverage": "Nationwide"}
            ],
            "regional": {
                "Punjab": {
                    "rescue": "1122",
                    "police": "15",
                    "hospitals": [
                        {"name": "Mayo Premier Medical Facility", "city": "Lahore", "phone": "042-99211111"},
                        {"name": "Services Hospital Complex", "city": "Lahore", "phone": "042-99200601"},
                        {"name": "Nishtar Hospital Pavilion", "city": "Multan", "phone": "061-9200432"},
                        {"name": "Allied Regional Medical Center", "city": "Faisalabad", "phone": "041-9210079"}
                    ]
                },
                "Sindh": {
                    "rescue": "1122 / 115",
                    "police": "15",
                    "hospitals": [
                        {"name": "Jinnah Postgraduate Medical Centre", "city": "Karachi", "phone": "021-99201300"},
                        {"name": "Civil Hospital Central Infrastructure", "city": "Karachi", "phone": "021-99215740"}
                    ]
                },
                "Gilgit-Baltistan": {
                    "rescue": "1122",
                    "police": "15",
                    "hospitals": [
                        {"name": "District Headquarters (DHQ) Gilgit", "city": "Gilgit", "phone": "05811-920253"},
                        {"name": "District Headquarters (DHQ) Skardu", "city": "Skardu", "phone": "05815-920282"}
                    ]
                }
            },
            "embassies": [
                {"country": "United States of America", "city": "Islamabad", "phone": "051-2014000", "address": "Diplomatic Enclave, Ramna 5"},
                {"country": "United Kingdom", "city": "Islamabad", "phone": "051-2012000", "address": "Diplomatic Enclave, Ramna 5"},
                {"country": "People's Republic of China", "city": "Islamabad", "phone": "051-2260113", "address": "No. 1, Zhou-Enlai Avenue, Diplomatic Enclave"}
            ],
            "tourist_police": {
                "description": "Specialized constabulary units deployed specifically to facilitate, protect, and escort international and domestic travelers.",
                "contacts": [
                    {"service": "Islamabad Tourism Constabulary", "phone": "1015"}
                ]
            }
        }

    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>📞 Federal Emergency Infrastructures</h4>", unsafe_allow_html=True)
    for contact in data.get("national", []):
        c1, c2, c3 = st.columns([4, 2, 3])
        c1.markdown(f"<b style='color:var(--text-primary);'>{contact['service']}</b>", unsafe_allow_html=True)
        c2.code(contact["number"])
        c3.markdown(f"<span style='color:var(--text-muted);'>{contact['coverage']}</span>", unsafe_allow_html=True)

    st.divider()
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>🏥 Provincial Medical & Security Apparatus</h4>", unsafe_allow_html=True)
    regions = list(data.get("regional", {}).keys())
    sel_region = st.selectbox("Designate Provincial Jurisdiction", regions, key="emg_region")
    region_data = data["regional"][sel_region]
    
    c1, c2 = st.columns(2)
    c1.metric("Rapid Evacuation Protocols", region_data.get("rescue", "N/A"))
    c2.metric("Law Enforcement Apparatus", region_data.get("police", "N/A"))
    
    if region_data.get("hospitals"):
        st.markdown("<b style='color:var(--text-primary);'>Primary Medical Facilities:</b>", unsafe_allow_html=True)
        for h in region_data["hospitals"]:
            st.markdown(f"<li style='color:var(--text-secondary);'>⚕️ <b>{h['name']}</b> ({h['city']}) — <code style='color:var(--text-accent);'>{h['phone']}</code></li>", unsafe_allow_html=True)
            
    st.divider()
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>🏛️ Diplomatic Missions & Consulates</h4>", unsafe_allow_html=True)
    for emb in data.get("embassies", []):
        with st.expander(f"🛂 Sovereign Territory: {emb['country']} — {emb['city']}"):
            st.markdown(f"<p style='color:var(--text-secondary);'><b>Encrypted Channel / Phone:</b> {emb['phone']}</p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:var(--text-secondary);'><b>Geospatial Coordinates:</b> {emb['address']}</p>", unsafe_allow_html=True)
            
    tp = data.get("tourist_police", {})
    if tp:
        st.divider()
        st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>👮 Specialized Tourism Constabulary</h4>", unsafe_allow_html=True)
        st.info(tp.get("description", ""))
        for c in tp.get("contacts", []):
            st.markdown(f"<li style='color:var(--text-secondary);'><b>{c['service']}</b>: <code>{c['phone']}</code></li>", unsafe_allow_html=True)

def page_gallery():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🖼️ Curated Visual Archives</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1em; color: var(--text-secondary); line-height: 1.8; font-family: \"Inter\", serif;'>Engage with a high-fidelity visual compendium showcasing the profound topographical and architectural heritage of Pakistan.</p>", unsafe_allow_html=True)
    
    dests = load_json("destinations.json")
    
    if not dests or not any(d.get("gallery_images") for d in dests):
        dests = [
            {
                "name": "Hunza Valley",
                "region": "Gilgit-Baltistan",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1589553416260-f586c8f1514f?auto=format&fit=crop&w=800&q=80", 
                    "https://images.unsplash.com/photo-1627896157734-4bc0a2b027b4?auto=format&fit=crop&w=800&q=80", 
                    "https://images.unsplash.com/photo-1600100397608-f010f423b971?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1542358814-c18d1840801a?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Skardu",
                "region": "Gilgit-Baltistan",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1621217036665-27a3c75eb2a7?auto=format&fit=crop&w=800&q=80", 
                    "https://images.unsplash.com/photo-1595166373721-653557e4e164?auto=format&fit=crop&w=800&q=80", 
                    "https://images.unsplash.com/photo-1633511116666-9eebc3f25b2d?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1434394354979-a235cd36269d?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Lahore",
                "region": "Punjab",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1584288079521-4f1816bb6e4b?auto=format&fit=crop&w=800&q=80", 
                    "https://images.unsplash.com/photo-1610408552174-8b65e90dcb0a?auto=format&fit=crop&w=800&q=80", 
                    "https://images.unsplash.com/photo-1620358823101-b6a482b8a0df?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1518398046578-8cca57782e17?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Swat Valley",
                "region": "Khyber Pakhtunkhwa",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1624389964522-42171850119b?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1650367310574-12eb60f09a15?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1601931535038-1647a7b8e5c6?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1433086966358-54859d0ed716?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Islamabad",
                "region": "Capital Territory",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1601004838634-11883c8c7eb2?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1622396481328-9b1b78cdd9fd?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1579208035657-320d3f2fcb9f?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1510414842594-a61c69b5ae57?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1444703686981-a3abbc4d4fe3?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1449844908441-8829872d2607?auto=format&fit=crop&w=800&q=80"
                ]
            },
            {
                "name": "Fairy Meadows",
                "region": "Gilgit-Baltistan",
                "gallery_images": [
                    "https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1483728642387-6c3ba6c6af5f?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1506744626753-1492d2426c11?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?auto=format&fit=crop&w=800&q=80",
                    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?auto=format&fit=crop&w=800&q=80"
                ]
            }
        ]

    dest_names = ["Isolate Comprehensive Archive"] + [d["name"] for d in dests]
    sel = st.selectbox("Designate Archival Target", dest_names, key="gal_dest")
    
    st.divider()
    
    show_dests = dests if sel == "Isolate Comprehensive Archive" else [d for d in dests if d["name"] == sel]
    
    for dest in show_dests:
        images = dest.get("gallery_images", [])
        if images:
            st.markdown(f"<h3 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>📍 {dest['name']} — <span style='color:var(--text-muted); font-size: 0.7em;'>{dest.get('region', 'Pakistan')}</span></h3>", unsafe_allow_html=True)
            cols = st.columns(3)
            for i, img_url in enumerate(images):
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="gallery-img-container">
                        <img src="{img_url}" alt="{dest['name']}">
                        <p class="gallery-img-caption">Topographical Capture of {dest['name']}</p>
                    </div>
                    """, unsafe_allow_html=True)
            st.write("\n")
            st.divider()

def page_travel_tips():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>📖 Comprehensive Expeditionary Directives</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1em; color: var(--text-secondary); line-height: 1.8; font-family: \"Inter\", serif;'>Assimilate these strategic protocols encompassing cultural integration, personal security, and logistical preparedness to ensure an optimal and deferential traversal of the region.</p>", unsafe_allow_html=True)
    
    tips_data = [
        {
            "title": "💼 Essential Provisioning & Requisites",
            "items": [
                "Deploy versatile, multi-layered garments to counteract severe thermal fluctuations (particularly imperative in northern alpine zones).",
                "Equip oneself with high-traction, structurally reinforced footwear for uneven topographies.",
                "Implement rigorous ultraviolet mitigation protocols: SPF barrier, ocular protection, and cranial coverage.",
                "Procure portable energetic reservoirs (power banks) and universal electrical adaptors (Type C/D form factors dominate the region).",
                "Maintain a sustainable hydration vessel integrated with microbiological filtration apparatus.",
                "Retain a comprehensive pharmaceutical kit comprising requisite personal medications and primary first-aid implements.",
                "Pack conservative aquatic attire exclusively designated for isolated hotel facilities or coastal environments."
            ]
        },
        {
            "title": "🤝 Societal Norms & Behavioral Etiquette",
            "items": [
                "Adhere strictly to conservative sartorial standards. Female constituents are strongly advised to utilize a 'dupatta' (fabric drape) whilst traversing religious sanctuaries. Male constituents should eschew abbreviated garments in public domain.",
                "It is a mandatory societal imperative to divest oneself of footwear prior to entering ecclesiastical structures and private domiciles.",
                "Exclusively utilize the right appendage for the transfer of objects and gastronomic consumption, aligned with regional purity paradigms.",
                "Overt manifestations of romantic affection (PDA) are culturally verboten and socially censured.",
                "Exhibit profound deference to local inhabitants; explicit verbal authorization must be acquired prior to capturing photographic documentation of individuals, particularly women."
            ]
        },
        {
            "title": "🛡️ Security Protocols & Risk Mitigation",
            "items": [
                "Continuously monitor and evaluate diplomatic travel advisories regarding specific geopolitical jurisdictions.",
                "Strategically partition certified duplications of critical identification (visas, passports) from their original counterparts.",
                "Exclusively employ authenticated and corporately monitored transit networks (e.g., Careem, InDrive).",
                "Circumvent solitary pedestrian traversal through unfamiliar or insufficiently illuminated municipal sectors post-crepuscule.",
                "Exercise extreme vigilance regarding uncertified street cuisine; mandate the exclusive consumption of factory-sealed hydration products.",
                "Memorize and maintain immediate access to federal response networks (Law Enforcement: 15, Rapid Rescue: 1122)."
            ]
        },
        {
            "title": "💳 Fiscal Operations & Currency Dynamics",
            "items": [
                "The sovereign monetary unit is the Pakistani Rupee (PKR).",
                "Physical capital (cash) remains the paramount transactional medium in rural peripheries and traditional bazaars. Ensure an adequate supply of lower-denomination currency.",
                "Automated Teller Machines (ATMs) are ubiquitous within metropolitan hubs but become increasingly sporadic in remote northern altitudes.",
                "Pre-emptively notify domestic financial institutions of intended geographic displacement to neutralize automated fraud-prevention card blocks.",
                "Execute currency conversion exclusively via federally sanctioned financial institutions or certified exchange brokerages."
            ]
        },
        {
            "title": "🗣️ Linguistic Nuances & Interpersonal Discourse",
            "items": [
                "Urdu operates as the lingua franca, while English is a co-official medium deployed extensively across administrative, commercial, and metropolitan sectors.",
                "The deployment of rudimentary Urdu salutations—such as 'Assalam-o-Alaikum' (Greetings) and 'Shukriya' (Gratitude)—precipitates significant reciprocal goodwill from the indigenous population.",
                "Procure a localized telecommunications subscription (SIM card) immediately upon arrival to secure uninterrupted navigational and communicative capabilities."
            ]
        }
    ]
    
    for category in tips_data:
        with st.expander(category["title"]):
            for item in category["items"]:
                st.markdown(f"<li style='color:var(--text-secondary); font-family: \"Inter\", serif;'>{item}</li>", unsafe_allow_html=True)
                
    st.divider()
    
    st.markdown("<h3 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>✅ Imperatives and ❌ Prohibitions</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<h4 style='color: var(--text-accent); font-family: \"Inter\", sans-serif;'>✅ Operational Imperatives</h4>", unsafe_allow_html=True)
        dos = [
            "Do adhere to conservative sartorial standards, particularly for women, specifically when navigating religious sanctuaries.",
            "Do secure explicit authorization prior to initiating photographic capture of the local populace.",
            "Do execute fundamental Urdu salutations: 'Assalam-o-Alaikum' (Hello), 'Shukriya' (Thank you), 'Kya Haal Hai' (How are you?).",
            "Do graciously accept offerings of steeped tea (chai)—a paramount manifestation of regional hospitality.",
            "Do divest footwear prior to crossing the threshold of mosques, private residences, and specific commercial establishments.",
            "Do accommodate the diurnal prayer schedule; commercial operations may temporarily suspend activities during these intervals.",
            "Do engage with indigenous gastronomy—the regional culinary profile is internationally acclaimed.",
            "Do execute gratuity distributions to service personnel, guides, and porters (a 10-15% margin is standard).",
            "Do retain insulated thermal layers even during the summer solstice when operating in high-altitude zones.",
            "Do engage in strategic fiscal negotiation (haggling) within traditional market environments; it is a culturally anticipated interaction."
        ]
        for d in dos:
            st.markdown(f"<li style='color:var(--text-secondary); font-size:0.95em;'>{d}</li>", unsafe_allow_html=True)
            
    with c2:
        st.markdown("<h4 style='color: #b91c1c; font-family: \"Inter\", sans-serif;'>❌ Strict Prohibitions</h4>", unsafe_allow_html=True)
        donts = [
            "Do not consume sustenance or hydration in public domains during the diurnal fasting parameters of Ramadan, irrespective of personal theological affiliations.",
            "Do not deploy abbreviated or revealing garments within the public sphere.",
            "Do not execute photographic captures of military infrastructure, defensive perimeters, or uniformed security personnel.",
            "Do not initiate discourse regarding volatile geopolitical or theological paradigms with unverified individuals.",
            "Do not deploy the left appendage for the transfer of items or nutritional consumption, as it contravenes established purity doctrines.",
            "Do not orient the plantar aspect of your feet toward individuals or theological manuscripts.",
            "Do not consume ethanol-based intoxicating beverages in the public domain (subject to stringent federal prohibition).",
            "Do not penetrate restricted sovereign or border territories bereft of a federally issued No Objection Certificate (NOC).",
            "Do not disperse non-biodegradable refuse, particularly within ecologically protected alpine and aquatic zones.",
            "Do not articulate disparaging assessments regarding regional theological convictions or established cultural methodologies."
        ]
        for d in donts:
            st.markdown(f"<li style='color:var(--text-secondary); font-size:0.95em;'>{d}</li>", unsafe_allow_html=True)
            
    st.divider()
    
    st.markdown("<h3 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>📚 Advanced Societal Context</h3>", unsafe_allow_html=True)
    cultural_notes = [
        {"topic": "Paradigms of Hospitality", "desc": "Pakistani hospitality represents a foundational societal pillar. The indigenous population will frequently deploy extraordinary measures to assist foreign entities. Invitations to partake in culinary or tea-based engagements are profound reflections of genuine cultural tradition, absent of ulterior commercial motives."},
        {"topic": "Theological Dominance", "desc": "Islam operates as the paramount state religion, dictating the rhythm of daily societal functions. Explorers are explicitly required to defer to these Islamic traditions. Notably, during the holy month of Ramadan, the public ingestion of food, liquids, or combustible inhalants during daylight hours is both legally constrained and perceived as culturally antagonistic."},
        {"topic": "Linguistic Distribution", "desc": "While Urdu commands the status of the national medium, English functions comprehensively as the co-official language of jurisprudence, corporate commerce, and higher academia. Consequently, anglophone communication is seamlessly executed in metropolitan parameters, though the deployment of fundamental Urdu syntax generates significant cultural rapport."},
        {"topic": "Fiscal Infrastructure", "desc": "The domestic economic system is anchored by the Pakistani Rupee (PKR). Electronic transaction processing (credit infrastructure) is exclusively operational within elite metropolitan commercial zones and hospitality sectors. It is an absolute requisite to secure physical fiat currency prior to navigating into rural or high-altitude sectors."},
        {"topic": "Sartorial Parameters", "desc": "Modesty in attire is non-negotiable. Male entities are advised to utilize full-length trousers and shirts. Female entities must deploy voluminous garments obscuring the extremities; a scarf (dupatta) is requisite for access to religious perimeters. The traditional 'Shalwar Kameez' offers optimal climatic comfort and maximum cultural alignment."},
        {"topic": "Bureaucratic Access Requirements", "desc": "Specific geographic classifications—notably border adjacent sectors in Gilgit-Baltistan, Azad Jammu & Kashmir, and Balochistan—mandate the procurement of a federal 'No Objection Certificate' (NOC) for foreign nationals. Verification with authoritative operators prior to mobilization is essential."}
    ]
    
    for note in cultural_notes:
        with st.expander(f"📖 {note['topic']}"):
            st.markdown(f"<p style='color:var(--text-secondary); font-family: \"Inter\", serif; line-height:1.6;'>{note['desc']}</p>", unsafe_allow_html=True)

def page_communication():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>📡 Telecommunication & Digital Connectivity</h2>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>📶 Cellular Infrastructure Providers</h4>", unsafe_allow_html=True)
    operators = [
        {"Provider Identity": "Jazz (Mobilink)", "Spectrum Tech": "4G/LTE", "Topographical Coverage": "Superior macro-coverage; optimal performance in metropolitan hubs and resilient signal in northern alpine regions.", "Tourist Pre-paid Availability": "Affirmed — 'Jazz Super SIM' provisioned at primary aeronautical hubs."},
        {"Provider Identity": "Zong (CMPak)", "Spectrum Tech": "4G/LTE", "Topographical Coverage": "Secondary macro-coverage; exceptional penetration in Gilgit-Baltistan and extreme northern vectors.", "Tourist Pre-paid Availability": "Affirmed — Attainable at terminal kiosks and franchised corporate centers."},
        {"Provider Identity": "Telenor Pakistan", "Spectrum Tech": "4G/LTE", "Topographical Coverage": "Competent urban penetration; progressively degrades in remote expeditionary sectors.", "Tourist Pre-paid Availability": "Affirmed — 'Telenor Easy Card' architecture."},
        {"Provider Identity": "Ufone (PTCL)", "Spectrum Tech": "4G/LTE", "Topographical Coverage": "Reliable within the Punjab province and urban sectors; highly restrictive functionality in Gilgit-Baltistan.", "Tourist Pre-paid Availability": "Affirmed — Restricted to designated corporate outlets."},
        {"Provider Identity": "SCOM", "Spectrum Tech": "3G/4G", "Topographical Coverage": "Exclusive monopolistic provider for Azad Jammu & Kashmir and deeply remote Gilgit-Baltistan parameters.", "Tourist Pre-paid Availability": "Highly Conditional — Acquired via regional military/administrative depots."},
    ]
    df_ops = pd.DataFrame(operators)
    st.dataframe(df_ops, use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>🪪 Protocols for Acquiring Foreigner Telecommunication Subscriptions</h4>", unsafe_allow_html=True)
    steps = [
        "1. **Required Documentation:** A legally valid international passport embedded with a certified entry visa, coupled with one physical passport-dimensional photograph.",
        "2. **Authorized Procurement Vectors:** Aeronautical terminal counters (highly advised for immediate integration), or certified corporate franchise nodes within major municipalities.",
        "3. **Biometric Authentication:** Mandatory federal processing requiring fingerprint scanning and facial capture (a non-negotiable security protocol for all telecommunication modules within the Republic).",
        "4. **Fiscal Outlay:** Hardware acquisition ranges between PKR 200–500. Ancillary data provisions (10-30GB) span an additional PKR 300–1,000.",
        "5. **Strategic Recommendation:** Jazz or Zong infrastructure is strongly endorsed for maximal up-time during traversal of northern tourist corridors.",
        "6. **Activation Latency:** Module initialization generally occurs instantaneously, or within a maximum latency window of 120 minutes post-biometric verification."
    ]
    for step in steps:
        st.markdown(f"<p style='color:var(--text-secondary);'>{step}</p>", unsafe_allow_html=True)
        
    st.divider()
    
    st.markdown("<h4 style='color: var(--text-primary); font-family: \"Inter\", sans-serif;'>⚠️ Topographical Network Distribution</h4>", unsafe_allow_html=True)
    conn_data = [
        {"Provincial / Topographical Sector": "Islamabad / Lahore / Karachi", "Signal Integrity Parameter": "Uninterrupted 4G/LTE + Broad WiFi Saturation", "Operational Status": "🟢 Optimal"},
        {"Provincial / Topographical Sector": "Swat / Naran / Kaghan Valleys", "Signal Integrity Parameter": "Competent 3G/4G penetration confined to principal municipal zones", "Operational Status": "🟢 Optimal"},
        {"Provincial / Topographical Sector": "Hunza / Gilgit Epicenters", "Signal Integrity Parameter": "3G/4G functional in townships; rapid degradation upon entering peripheral limits", "Operational Status": "🟡 Intermittent"},
        {"Provincial / Topographical Sector": "Skardu Proper", "Signal Integrity Parameter": "3G/4G functional within city perimeters; absolute blackout at Deosai Plains", "Operational Status": "🟡 Intermittent"},
        {"Provincial / Topographical Sector": "Fairy Meadows Base Camp", "Signal Integrity Parameter": "Absolute telecommunication blackout", "Operational Status": "🔴 Null / Void"},
        {"Provincial / Topographical Sector": "Kalash Valley Territories", "Signal Integrity Parameter": "Severely restricted; localized strictly to legacy 2G spectrums", "Operational Status": "🔴 Null / Void"},
        {"Provincial / Topographical Sector": "Deep Neelum Valley Operations", "Signal Integrity Parameter": "Highly constrained to non-existent connectivity", "Operational Status": "🔴 Null / Void"},
    ]
    df_conn = pd.DataFrame(conn_data)
    st.dataframe(df_conn, use_container_width=True, hide_index=True)

def page_admin():
    st.markdown("<h2 style='color: var(--text-primary); font-family: \"Inter\", sans-serif; font-weight: 700; margin-bottom: 20px; border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>⚙️ Administrative Command Console</h2>", unsafe_allow_html=True)
    if not st.session_state.admin_logged_in:
        pw = st.text_input("Deploy Cryptographic Access Key:", type="password")
        if st.button("Initiate Authentication Handshake"):
            if hashlib.sha256(pw.encode()).hexdigest() == get_admin_hash():
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("Authentication Failure: Cryptographic mismatch.")
    else:
        st.success("Authentication Validated: Level 1 Clearance Achieved.")
        if st.button("Terminate Session"): 
            st.session_state.admin_logged_in = False
            st.rerun()
        st.info("System Configuration Active: Modulate the internal JSON architecture within the 'data' directory to execute extensive systemic alterations.")

# ============================================================
# NEW PLANNER PAGES (Expanded Trip Planner)
# ============================================================
def planner_dashboard():
    st.markdown("""
<div style='text-align:center; padding: 30px 0 10px 0;'>
    <h1 style='font-size: 3.2em; font-weight: 800; color: var(--text-primary); font-family: "Inter", sans-serif; letter-spacing: -0.5px; margin-bottom: 5px;'>
        Welcome to Your <span style='color: var(--text-accent);'>Ultimate Planner</span>
    </h1>
    <p style='font-size: 1.3em; color: var(--text-muted); font-weight: 400; letter-spacing: 0.5px;'>Intelligent time management and travel orchestration</p>
</div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
<div style='font-size: 1.1em; color: var(--text-secondary); line-height: 1.8; text-align: center; max-width: 900px; margin: 0 auto 40px auto; font-family: "Inter", serif;'>
This integrated planning suite empowers you to harmonize your daily routine with extraordinary experiences. 
Whether you need a personalized itinerary, safety guidance, budget insights, or cultural knowledge, 
every tool is at your fingertips.
</div>
    """, unsafe_allow_html=True)
    
    # Feature highlights
    features = [
        ("🗓️", "Generate Trip", "Create a tailored plan based on your routine and preferences."),
        ("🏙️", "Explore Destinations", "Discover famous places around the world."),
        ("🛡️", "Safety & Emergency", "Essential safety tips and global emergency numbers."),
        ("💰", "Budget Planner", "Smart advice for managing travel expenses."),
        ("🧳", "Travel Tips", "Practical recommendations for smooth journeys."),
        ("🤝", "Local Customs", "Understand cultural norms and etiquette.")
    ]
    
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>✨ Core Modules</h2>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    for i, (icon, title, desc) in enumerate(features):
        with cols[i % 3]:
            st.markdown(f"""
<div class="feature-card">
    <div style='font-size: 2.5em; margin-bottom: 15px;'>{icon}</div>
    <h4 style='color: var(--text-primary); font-size: 1.1em; font-weight: 700; margin: 0 0 10px 0;'>{title}</h4>
    <p style='color: var(--text-muted); font-size: 0.9em;'>{desc}</p>
</div>
            """, unsafe_allow_html=True)

def planner_explore():
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🏙️ Explore Famous World Destinations</h2>", unsafe_allow_html=True)
    
    # World destinations data (name, region, description, image URL)
    world_destinations = [
        {"name": "Paris", "region": "France", "description": "The City of Light, renowned for the Eiffel Tower, Louvre Museum, and romantic ambiance.", "image": "https://images.unsplash.com/photo-1502602898657-3b9175d9c7c1?auto=format&fit=crop&w=800&q=80"},
        {"name": "Tokyo", "region": "Japan", "description": "A bustling metropolis blending ultramodern and traditional, from neon-lit skyscrapers to historic temples.", "image": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=800&q=80"},
        {"name": "New York", "region": "USA", "description": "The Big Apple, iconic for Times Square, Central Park, Broadway, and the Statue of Liberty.", "image": "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?auto=format&fit=crop&w=800&q=80"},
        {"name": "Rome", "region": "Italy", "description": "The Eternal City, home to the Colosseum, Vatican City, and countless ancient ruins.", "image": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=800&q=80"},
        {"name": "Cairo", "region": "Egypt", "description": "Gateway to the Pyramids of Giza, the Sphinx, and the rich history of the Nile.", "image": "https://images.unsplash.com/photo-1572252009284-6e9c6c8e3d6a?auto=format&fit=crop&w=800&q=80"},
        {"name": "Sydney", "region": "Australia", "description": "Famous for the Sydney Opera House, Harbour Bridge, and stunning beaches.", "image": "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?auto=format&fit=crop&w=800&q=80"},
        {"name": "Rio de Janeiro", "region": "Brazil", "description": "Christ the Redeemer, Sugarloaf Mountain, and vibrant Copacabana beach.", "image": "https://images.unsplash.com/photo-1483729558449-99ef09a8c325?auto=format&fit=crop&w=800&q=80"},
        {"name": "Cape Town", "region": "South Africa", "description": "Table Mountain, stunning coastlines, and diverse cultural heritage.", "image": "https://images.unsplash.com/photo-1580060839134-75a5edca2e99?auto=format&fit=crop&w=800&q=80"},
        {"name": "Bangkok", "region": "Thailand", "description": "Vibrant street life, ornate shrines, and world-famous cuisine.", "image": "https://images.unsplash.com/photo-1508009603885-50b6c3924c5b?auto=format&fit=crop&w=800&q=80"},
        {"name": "London", "region": "UK", "description": "Historic landmarks like Big Ben, Tower Bridge, and the British Museum.", "image": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=800&q=80"},
        {"name": "Dubai", "region": "UAE", "description": "Ultramodern architecture, luxury shopping, and the Burj Khalifa.", "image": "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?auto=format&fit=crop&w=800&q=80"},
        {"name": "Istanbul", "region": "Turkey", "description": "Where East meets West, with the Hagia Sophia and Grand Bazaar.", "image": "https://images.unsplash.com/photo-1541432901042-2d8bd64b4a9b?auto=format&fit=crop&w=800&q=80"},
    ]
    
    # Display in a grid
    cols = st.columns(3)
    for i, dest in enumerate(world_destinations):
        with cols[i % 3]:
            st.markdown(f"""
<div class="premium-card" style="padding: 15px;">
    <img src="{dest['image']}" style="width:100%; height:180px; object-fit:cover; border-radius:12px; margin-bottom:10px;">
    <h3 style='color: var(--text-primary); font-size: 1.3em; margin:10px 0 5px;'>{dest['name']}</h3>
    <p style='color: var(--text-muted); font-size: 0.9em; margin:0 0 10px;'>{dest['region']}</p>
    <p style='color: var(--text-secondary); font-size: 0.95em;'>{dest['description']}</p>
</div>
            """, unsafe_allow_html=True)

def planner_safety():
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🛡️ Safety & Emergency</h2>", unsafe_allow_html=True)
    
    st.markdown("""
<div style='background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px; margin-bottom: 20px;'>
    <h3 style='color: var(--text-accent);'>🌍 Global Emergency Numbers</h3>
    <p style='color: var(--text-secondary);'>In many countries, <b>112</b> or <b>911</b> are the universal emergency numbers. Below are specific numbers for popular destinations:</p>
</div>
    """, unsafe_allow_html=True)
    
    emergency_data = {
        "USA": "911",
        "UK": "999 or 112",
        "EU": "112",
        "Australia": "000",
        "Japan": "110 (police), 119 (fire/ambulance)",
        "India": "112",
        "China": "110 (police), 119 (fire), 120 (ambulance)",
        "Brazil": "190 (police), 192 (ambulance)",
        "South Africa": "10111 (police), 10177 (ambulance)",
        "UAE": "999",
        "Turkey": "112",
        "Pakistan": "15 (police), 1122 (rescue), 115 (ambulance)"
    }
    
    cols = st.columns(3)
    for i, (country, number) in enumerate(emergency_data.items()):
        with cols[i % 3]:
            st.markdown(f"""
<div style='background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 15px; margin-bottom: 15px;'>
    <h4 style='color: var(--text-primary); margin:0 0 5px;'>{country}</h4>
    <p style='color: var(--text-accent); font-size: 1.2em; font-weight:600;'>{number}</p>
</div>
            """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("""
<h3 style='color: var(--text-primary);'>🧾 General Safety Tips</h3>
<ul style='color: var(--text-secondary); font-size: 1.05em;'>
    <li>Always keep copies of your passport and visa (digital and physical).</li>
    <li>Register with your embassy when traveling to high-risk areas.</li>
    <li>Avoid isolated areas, especially at night.</li>
    <li>Use official taxis or ride-hailing apps.</li>
    <li>Keep emergency numbers saved on your phone.</li>
    <li>Ensure your travel insurance covers medical evacuation.</li>
    <li>Stay informed about local news and weather conditions.</li>
    <li>Respect local laws and customs to avoid misunderstandings.</li>
</ul>
    """, unsafe_allow_html=True)

def planner_budget():
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>💰 Budget Planner</h2>", unsafe_allow_html=True)
    
    st.markdown("""
<div style='background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px;'>
    <h3 style='color: var(--text-accent);'>📊 General Travel Budget Guidelines</h3>
    <p style='color: var(--text-secondary);'>Costs vary greatly by destination. Here are typical daily budgets (per person) for different travel styles:</p>
</div>
    """, unsafe_allow_html=True)
    
    budget_table = pd.DataFrame({
        "Destination Type": ["Southeast Asia", "Europe", "North America", "South America", "Middle East", "Australia"],
        "Budget (USD/day)": ["$20-40", "$70-150", "$80-200", "$30-70", "$50-120", "$60-150"],
        "Mid-Range (USD/day)": ["$40-80", "$150-250", "$200-350", "$70-150", "$120-200", "$150-250"],
        "Luxury (USD/day)": ["$100+", "$300+", "$400+", "$200+", "$300+", "$300+"]
    })
    
    st.dataframe(budget_table, use_container_width=True, hide_index=True)
    
    st.divider()
    
    st.markdown("""
<h3 style='color: var(--text-primary);'>💡 Money-Saving Tips</h3>
<ul style='color: var(--text-secondary);'>
    <li>Travel during shoulder seasons (spring/fall) for lower prices.</li>
    <li>Use public transportation instead of taxis.</li>
    <li>Eat where locals eat – street food is often delicious and cheap.</li>
    <li>Book accommodations with kitchen facilities to save on meals.</li>
    <li>Look for city tourist cards that offer free or discounted attractions.</li>
    <li>Withdraw local currency from ATMs rather than exchanging at airports.</li>
    <li>Use no-foreign-transaction-fee credit cards.</li>
</ul>
    """, unsafe_allow_html=True)

def planner_tips():
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🧳 Travel Tips</h2>", unsafe_allow_html=True)
    
    tips_categories = [
        ("📋 Before You Go", [
            "Check passport validity (at least 6 months).",
            "Research visa requirements.",
            "Get travel insurance.",
            "Make copies of important documents.",
            "Inform your bank of travel plans.",
            "Pack versatile clothing and a first-aid kit.",
            "Download offline maps and translation apps."
        ]),
        ("✈️ At the Airport", [
            "Arrive at least 2-3 hours before international flights.",
            "Keep valuables in your carry-on.",
            "Stay hydrated during long flights.",
            "Understand luggage restrictions."
        ]),
        ("🏨 Accommodation", [
            "Read recent reviews before booking.",
            "Consider location – near public transport.",
            "Check if breakfast is included.",
            "Inform yourself about check-in/out times."
        ]),
        ("🍽️ Food & Drink", [
            "Drink bottled water if tap water is unsafe.",
            "Try local specialties but be cautious with street food.",
            "Learn a few food-related phrases.",
            "Be aware of tipping customs."
        ]),
        ("📱 Connectivity", [
            "Buy a local SIM or eSIM for data.",
            "Download offline translators and maps.",
            "Keep a power bank handy.",
            "Use VPN on public Wi-Fi."
        ])
    ]
    
    for title, items in tips_categories:
        with st.expander(title, expanded=False):
            for item in items:
                st.markdown(f"<li style='color:var(--text-secondary);'>{item}</li>", unsafe_allow_html=True)

def planner_customs():
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🤝 Local Customs & Etiquette</h2>", unsafe_allow_html=True)
    
    st.markdown("""
<div style='background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 16px; padding: 20px; margin-bottom: 20px;'>
    <p style='color: var(--text-secondary); font-size: 1.1em;'>Understanding and respecting local customs is key to a positive travel experience. Here are general guidelines that apply in many cultures:</p>
</div>
    """, unsafe_allow_html=True)
    
    customs = [
        ("🙏", "Greetings", "Learn basic greetings (hello, thank you, goodbye) in the local language. A smile is universal."),
        ("👗", "Dress Code", "In conservative countries, dress modestly – cover shoulders and knees, especially at religious sites."),
        ("🦶", "Feet", "In many Asian and Middle Eastern cultures, showing the soles of your feet is considered disrespectful."),
        ("🍽️", "Dining", "Wait to be seated. In some cultures, it's polite to leave a little food on your plate; in others, finishing everything is a compliment."),
        ("📸", "Photography", "Always ask permission before photographing people, especially in rural areas or religious settings."),
        ("🎁", "Gift Giving", "In some cultures, gifts are opened in private. Avoid giving alcohol in Muslim countries."),
        ("🗣️", "Public Behavior", "Public displays of affection may be frowned upon. Keep your voice moderate."),
        ("🕌", "Religious Sites", "Remove shoes before entering. Women may need to cover their hair. Silence your phone."),
        ("💵", "Tipping", "Research tipping customs – in some countries it's expected, in others it's not."),
    ]
    
    for icon, title, desc in customs:
        st.markdown(f"""
<div style='background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 15px; margin-bottom: 15px;'>
    <h4 style='color: var(--text-primary); margin:0 0 5px;'>{icon} {title}</h4>
    <p style='color: var(--text-secondary); margin:0;'>{desc}</p>
</div>
        """, unsafe_allow_html=True)

# ============================================================
# ENHANCED GENERATE TRIP MODULE (with colored button & detailed plan)
# ============================================================
def planner_generate():
    st.markdown("<h2 style='color: var(--text-primary); border-bottom: 2px solid var(--border-color); padding-bottom: 10px;'>🗓️ Generate Your Personalized Trip</h2>", unsafe_allow_html=True)
    
    # Add a subtle animation hint
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px; animation: fadeIn 1s ease-in;'>
        <span style='background: linear-gradient(45deg, #047857, #10b981); padding: 8px 20px; border-radius: 40px; color: white; font-weight: 600;'>
            ✨ Click the glowing button below for your ultra‑detailed plan
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("trip_form_enhanced"):
        st.markdown("<b style='color:var(--text-primary);'>1. Routine Configurator</b>", unsafe_allow_html=True)
        with st.expander("Configure Weekly Routine", expanded=False):
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            routine_dict = {}
            for day in days:
                routine_dict[day] = st.selectbox(day, ["Busy", "Free"], key=f"planner_day_{day}")
        
        st.markdown("<br><b style='color:var(--text-primary);'>2. Trip Details</b>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            city = st.text_input("📍 Destination City", "New York", key="planner_city")
            num_days = st.slider("📅 Trip Duration (Days)", 1, 14, 3, key="planner_days")
        with col2:
            mood = st.text_input("🎯 Desired Activity / Theme", "Relaxing walk or fine dining", key="planner_mood")
            travel_style = st.selectbox("🧳 Travel Style", ["Budget", "Standard", "Luxury"], key="planner_style")
            budget = st.selectbox("💰 Budget Level", ["Low", "Medium", "High"], key="planner_budget")
        
        st.markdown("<br>", unsafe_allow_html=True)
        # The button is automatically styled by CSS (pulse-glow + gradient)
        submitted = st.form_submit_button("🚀 GENERATE MY ULTIMATE TRIP PLAN", use_container_width=True)
    
    if submitted:
        routine = ", ".join([f"{k}: {v}" for k, v in routine_dict.items()])
        
        client = Groq(api_key=GROQ_KEY)
        weather, err = get_current_weather(city, WEATHER_KEY)
        if err: 
            st.error("Weather Error: Could not retrieve meteorological data.")
        else:
            with st.spinner("🤖 Crafting your ultra‑detailed travel blueprint..."):
                # Ultra‑detailed prompt covering all required aspects
                enhanced_prompt = f"""
You are the world's most meticulous travel planner. Create an extraordinarily detailed, day-by-day trip plan for {city} based on:

User's weekly routine: {routine}
Destination: {city}
Desired activity/mood: {mood}
Trip duration: {num_days} days
Travel style: {travel_style}
Budget level: {budget}
Current weather in {city}: {weather}

Your plan MUST include the following sections, each with a clear, colored heading (use emojis):

🆘 **EMERGENCY PREPAREDNESS**
- List exact emergency numbers for {city} (police, ambulance, fire, tourist police, nearest embassy).
- Describe common local scams and exactly how to avoid them.
- Provide safety tips for day and night, including neighborhoods to avoid.
- Health precautions (vaccinations, water safety, local health risks).

👔 **CLOTHING & PACKING GUIDE**
- Suggest specific clothing based on the current weather ({weather}) and local traditions.
- Include items for cultural sites (e.g., head coverings, modest dress).
- Packing list for activities mentioned in the itinerary.

⏰ **DAILY ITINERARY (Hour by Hour)**
- For each day, provide a detailed schedule from morning to evening.
- Include at least 3 specific attractions/restaurants/experiences per day.
- Mention approximate costs, travel times, and booking tips.

🧘 **LOCAL CULTURE & BEHAVIOR**
- Describe typical local behavior, communication styles, and social norms.
- Explain how locals greet, dine, queue, and interact with tourists.
- Include important "dos and don'ts" specific to {city}.

⚠️ **COMMON SCAMS & HOW TO AVOID THEM**
- Detail at least 5 common scams targeting tourists in {city}.
- Give clear, actionable advice to avoid each one.

💡 **PRACTICAL TIPS**
- Transportation options (public, taxis, ride‑sharing).
- Best SIM card / internet options.
- Tipping customs.
- Daily budget estimate.
- Useful local phrases.

Format everything with bullet points, tables, and clear section breaks. Make it feel like a luxury travel consultant prepared it just for them.
                """
                
                # Search Tavily for additional real‑time info
                search_query = f"tourist attractions safety tips emergency numbers scams in {city}"
                search_data = search_tavily(search_query)
                
                final_res = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a premium travel planner. Always respond in beautifully formatted markdown with colored headings."},
                        {"role": "user", "content": enhanced_prompt + f"\n\nAdditional real‑time web data:\n{search_data}"}
                    ],
                    model="llama-3.3-70b-versatile"
                )
                plan = final_res.choices[0].message.content
                
                # Post‑process to add our custom CSS classes for colored headings
                # (The AI already includes emoji headings, but we'll ensure they match our CSS)
                plan = plan.replace("🆘 **EMERGENCY PREPAREDNESS**", "<div class='plan-heading-emergency'>🆘 EMERGENCY PREPAREDNESS</div>")
                plan = plan.replace("👔 **CLOTHING & PACKING GUIDE**", "<div class='plan-heading-clothing'>👔 CLOTHING & PACKING GUIDE</div>")
                plan = plan.replace("⏰ **DAILY ITINERARY (Hour by Hour)**", "<div class='plan-heading-schedule'>⏰ DAILY ITINERARY (Hour by Hour)</div>")
                plan = plan.replace("🧘 **LOCAL CULTURE & BEHAVIOR**", "<div class='plan-heading-behavior'>🧘 LOCAL CULTURE & BEHAVIOR</div>")
                plan = plan.replace("⚠️ **COMMON SCAMS & HOW TO AVOID THEM**", "<div class='plan-heading-scams'>⚠️ COMMON SCAMS & HOW TO AVOID THEM</div>")
                plan = plan.replace("💡 **PRACTICAL TIPS**", "<div class='plan-heading-tips'>💡 PRACTICAL TIPS</div>")
                
                # Display plan with fade‑in animation
                st.markdown(f"<div class='fade-in-card'>{plan}</div>", unsafe_allow_html=True)
                
                # Download button
                st.download_button("📥 Download This Ultimate Plan (PDF)", create_pdf(plan), "ultimate_trip_plan.pdf")
                
                # Enhanced weather forecast with dual charts
                df = get_forecast(city, WEATHER_KEY)
                if df is not None:
                    st.divider()
                    st.markdown(f"<h3 style='color:var(--text-primary);'>🌦️ 5‑Day Detailed Forecast for {city.title()}</h3>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    template = "plotly_dark" if st.session_state.theme == "dark" else "plotly"
                    
                    with col1:
                        # Temperature line with markers
                        fig_temp = px.line(df, x="Datetime", y="Temperature (°C)", 
                                          title="<b>Temperature Trend</b>", 
                                          markers=True, 
                                          template=template,
                                          color_discrete_sequence=["#e11d48"])
                        fig_temp.update_layout(hovermode="x unified")
                        st.plotly_chart(fig_temp, use_container_width=True)
                    
                    with col2:
                        # Rain chance bar chart
                        fig_rain = px.bar(df, x="Datetime", y="Rain Chance (%)", 
                                         title="<b>Rain Probability</b>", 
                                         range_y=[0, 100],
                                         template=template,
                                         color_discrete_sequence=["#2563eb"])
                        fig_rain.update_layout(hovermode="x unified")
                        st.plotly_chart(fig_rain, use_container_width=True)
                    
                    # Additional humidity/wind if available
                    if "humidity" in df.columns or "wind_speed" in df.columns:
                        st.markdown("#### Additional Metrics")
                        cols = st.columns(2)
                        if "humidity" in df.columns:
                            with cols[0]:
                                fig_hum = px.line(df, x="Datetime", y="humidity", title="Humidity (%)", template=template)
                                st.plotly_chart(fig_hum, use_container_width=True)
                        if "wind_speed" in df.columns:
                            with cols[1]:
                                fig_wind = px.line(df, x="Datetime", y="wind_speed", title="Wind Speed (m/s)", template=template)
                                st.plotly_chart(fig_wind, use_container_width=True)
    else:
        st.info("👈 Fill in your routine and preferences, then click the glowing button for your ultimate trip plan.")

# ============================================================
# MAIN APP LAYOUT with Theme Toggle
# ============================================================
# Apply theme CSS
st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)
st.markdown(base_css, unsafe_allow_html=True)

# Header with title and theme toggle
header_col1, header_col2, header_col3 = st.columns([4, 6, 2])
with header_col1:
    st.title("🗺️ Ultimate Planner & Hub")
with header_col3:
    if st.button(f"{'🌙 Dark' if st.session_state.theme == 'light' else '☀️ Light'}", key="theme_toggle", help="Switch theme"):
        toggle_theme()
        st.rerun()

# Tabs
main_tab, companion_tab, tourism_tab = st.tabs(["📅 Trip Planner", "🤖 Health Companion", "🇵🇰 Pakistan Tourism"])

# --- TAB 1: EXPANDED TRIP PLANNER ---
with main_tab:
    planner_sidebar_col, planner_content_col = st.columns([2.5, 7.5])
    
    with planner_sidebar_col:
        st.markdown("<div class='info-panel-header'>Planner Modules</div>", unsafe_allow_html=True)
        
        # Define planner modules
        planner_modules = {
            "📋 Dashboard": planner_dashboard,
            "🏙️ Explore Destinations": planner_explore,
            "🛡️ Safety & Emergency": planner_safety,
            "💰 Budget Planner": planner_budget,
            "🧳 Travel Tips": planner_tips,
            "🤝 Local Customs": planner_customs,
            "🗓️ Generate Trip": planner_generate,  # This now has the animated button
        }
        
        # Determine index for radio
        try:
            current_idx = list(planner_modules.keys()).index(st.session_state.planner_module)
        except ValueError:
            current_idx = 0
        
        selected = st.radio(
            "Planner Modules",
            list(planner_modules.keys()),
            index=current_idx,
            key="planner_nav",
            label_visibility="collapsed",
            on_change=update_planner_module
        )
    
    with planner_content_col:
        planner_modules[selected]()

# --- TAB 2: HEALTH COMPANION (now with dual‑AI fallback) ---
with companion_tab:
    # Use the dual‑AI function instead of direct Groq client
    if not st.session_state.chat_history:
        st.markdown('<div class="greeting-header">Hello dear, how can I help you?</div>', unsafe_allow_html=True)
        st.markdown('<div class="greeting-sub">Tell me what you want or choose an option below</div>', unsafe_allow_html=True)
        col_buttons, col_space = st.columns([1, 2]) 
        with col_buttons:
            if st.button("📄 Share Reports & Get Analysis"): 
                st.session_state.chat_history.append({"role": "assistant", "content": "Upload your report using the ➕ button below!"})
                st.rerun()
            if st.button("🥦 Prepare a Diet Plan"): 
                st.session_state.chat_history.append({"role": "user", "content": "I need a diet plan."})
                st.rerun()

    for i, msg in enumerate(st.session_state.chat_history):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            with st.expander("📋 Copy Text"): 
                st.code(msg["content"], language="markdown")
            if msg["role"] == "user" and "pdf" in msg["content"].lower() and i > 0:
                st.download_button("📥 Download", create_pdf(st.session_state.chat_history[i-1]["content"]), f"doc_{i}.pdf", key=f"dl_{i}")
                
    if st.session_state.autoplay_audio:
        st.audio(st.session_state.autoplay_audio, autoplay=True)
        st.session_state.autoplay_audio = None

    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)
    if st.session_state.chat_history:
        st.markdown('<a href="#chat-bottom" class="scroll-btn">⬇️</a>', unsafe_allow_html=True)

    col_plus, col_clear, col_voice = st.columns([0.08, 0.08, 0.84]) 
    with col_plus:
        with st.popover("➕", use_container_width=True):
            uploaded_file = st.file_uploader("Upload", type=["pdf", "jpg", "png"], label_visibility="collapsed")
    with col_clear: 
        st.button("🗑️", help="Clear Chat Memory", on_click=clear_chat, use_container_width=True)
    with col_voice: 
        audio_val = st.audio_input("Voice", label_visibility="collapsed")

    if uploaded_file:
        txt = extract_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else analyze_image(uploaded_file, Groq(api_key=GROQ_KEY))
        st.session_state.medical_data = txt
        # Use dual AI
        messages = [
            {"role": "system", "content": "You are a nutritionist. Always use emojis. Ask 'Do you want its PDF file?' at the end."},
            {"role": "user", "content": f"Analyze: {txt}. Give diet plan."}
        ]
        response, source = get_ai_response(messages, model="llama-3.3-70b-versatile")
        st.session_state.chat_history.extend([
            {"role": "user", "content": f"📎 {uploaded_file.name}"},
            {"role": "assistant", "content": response}
        ])
        st.rerun()

    if audio_val and audio_val != st.session_state.last_audio:
        st.session_state.last_audio = audio_val
        # Transcribe with Groq (still using Groq for audio)
        groq_client = Groq(api_key=GROQ_KEY)
        txt = groq_client.audio.transcriptions.create(file=("v.wav", audio_val), model="whisper-large-v3-turbo").text
        
        sys_prompt = "You are a friendly AI companion. Reply in the exact same language as the user. YOU MUST start your response with exactly [LANG:UR] for Urdu, [LANG:HI] for Hindi, or [LANG:EN] for English. Always use emojis."
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": txt}
        ]
        response, source = get_ai_response(messages, model="llama-3.3-70b-versatile")
        
        # Parse language tag
        lang = "UR" if "[LANG:UR]" in response else "HI" if "[LANG:HI]" in response else "EN"
        clean = response.replace("[LANG:UR]", "").replace("[LANG:HI]", "").replace("[LANG:EN]", "").strip()
        
        st.session_state.chat_history.extend([
            {"role": "user", "content": f"🎙️ {txt}"},
            {"role": "assistant", "content": clean}
        ])
        st.session_state.autoplay_audio = asyncio.run(tts(clean, lang))
        st.rerun()

    if prompt := st.chat_input("Message..."):
        ctx = f"Medical Context: {st.session_state.medical_data}" if st.session_state.medical_data else ""
        messages = [
            {"role": "system", "content": f"Helpful AI. Use emojis. Ask 'What else can I do for you today?'. {ctx}"},
            {"role": "user", "content": prompt}
        ]
        response, source = get_ai_response(messages, model="llama-3.3-70b-versatile")
        st.session_state.chat_history.extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ])
        st.rerun()

# --- TAB 3: PAKISTAN TOURISM (unchanged) ---
with tourism_tab:
    header_col, toggle_col = st.columns([8.5, 1.5])
    with header_col:
        st.markdown("<h3 style='color:var(--text-primary); font-weight:800;'>🇵🇰 Pakistan Tourism Hub</h3>", unsafe_allow_html=True)
    with toggle_col:
        if st.button("☰ Toggle Panel", use_container_width=True):
            st.session_state.show_info_panel = not st.session_state.show_info_panel
            st.rerun()
            
    st.divider()
    
    tourism_pages = {
        "📊 Executive Dashboard": page_home,
        "🧭 Geospatial Archive": page_destinations,
        "🗺️ Interactive Mapping": page_maps,
        "🌤️ Meteorological Data": page_weather,
        "🧠 AI Concierge": page_smart_assistant,
        "📉 Financial Architecture": page_budget,
        "🛡️ Emergency Protocols": page_emergency,
        "🖼️ Visual Archives": page_gallery,
        "📖 Expedition Directives": page_travel_tips,
        "📡 Telecommunications": page_communication,
        "⚙️ Command Console": page_admin,
    }
    
    if st.session_state.show_info_panel:
        tour_sidebar_col, tour_content_col = st.columns([2.5, 7.5])
        
        with tour_sidebar_col:
            st.markdown("<div class='info-panel-header'>Information Panel</div>", unsafe_allow_html=True)
            try:
                current_idx = list(tourism_pages.keys()).index(st.session_state.current_tourism_module)
            except ValueError:
                current_idx = 0
                
            selection = st.radio(
                "Modules", 
                list(tourism_pages.keys()), 
                index=current_idx,
                key="tourism_nav", 
                label_visibility="collapsed",
                on_change=update_tourism_module
            )
            
        with tour_content_col:
            tourism_pages[selection]()
    else:
        current_selection = st.session_state.current_tourism_module
        if current_selection in tourism_pages:
            tourism_pages[current_selection]()

# ============================================================
# MESHU CHATBOT – Floating AI Assistant (bottom‑center, with debug marker)
# ============================================================
def add_meshu_chatbot():
    """Inject DeepSeek‑powered chatbot – guaranteed to appear."""
    # Try to get the key; if missing, still inject but show error in chat
    try:
        deepseek_key = st.secrets["good"]
        key_ok = True
    except KeyError:
        deepseek_key = None
        key_ok = False
        st.warning("⚠️ MESHU: API key 'good' not found. Chatbot will show a demo message.")

    chatbot_html = f"""
    <div id="meshu-chatbot-placeholder"></div>
    <script>
        (function() {{
            // ---------- DEBUG: Add a tiny red dot to prove the script runs ----------
            const debugDot = window.parent.document.createElement('div');
            debugDot.id = 'meshu-debug-dot';
            debugDot.style.cssText = `
                position: fixed;
                top: 10px;
                left: 10px;
                width: 10px;
                height: 10px;
                background: red;
                border-radius: 50%;
                z-index: 10000;
            `;
            window.parent.document.body.appendChild(debugDot);
            console.log("MESHU: Debug dot added");

            // ---------- Now create the actual chatbot ----------
            const doc = window.parent.document;
            const containerId = 'meshu-chatbot-container';
            if (doc.getElementById(containerId)) {{
                console.log("MESHU: Already exists");
                return;
            }}

            const API_KEY = {f'"{deepseek_key}"' if key_ok else 'null'};
            const API_URL = 'https://api.deepseek.com/v1/chat/completions';
            const keyValid = {str(key_ok).lower()};

            // Create container – centered at bottom
            const container = doc.createElement('div');
            container.id = containerId;
            container.style.cssText = `
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 9999;
                font-family: 'Inter', sans-serif;
            `;

            // Toggle button
            const toggle = doc.createElement('button');
            toggle.id = 'meshu-toggle';
            toggle.innerHTML = '💬';
            toggle.style.cssText = `
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #2563eb, #7c3aed);
                border: none;
                color: white;
                font-size: 26px;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                animation: meshu-pulse 2s infinite;
            `;

            // Chat window – centered above the button
            const windowDiv = doc.createElement('div');
            windowDiv.id = 'meshu-window';
            windowDiv.style.cssText = `
                display: none;
                position: absolute;
                bottom: 80px;
                left: 50%;
                transform: translateX(-50%);
                width: 350px;
                height: 500px;
                background: rgba(30, 41, 59, 0.95);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.4);
                border: 1px solid rgba(255,255,255,0.1);
                overflow: hidden;
                flex-direction: column;
                color: #f1f5f9;
            `;

            // Header
            const header = doc.createElement('div');
            header.style.cssText = `
                padding: 16px 20px;
                background: rgba(15, 23, 42, 0.8);
                border-bottom: 1px solid rgba(255,255,255,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;
            const title = doc.createElement('span');
            title.innerHTML = 'MESHU';
            title.style.cssText = `
                font-weight: 700;
                font-size: 1.2rem;
                background: linear-gradient(135deg, #60a5fa, #c084fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            `;
            const closeBtn = doc.createElement('button');
            closeBtn.innerHTML = '&times;';
            closeBtn.style.cssText = `
                background: none;
                border: none;
                color: #94a3b8;
                font-size: 22px;
                cursor: pointer;
            `;
            header.appendChild(title);
            header.appendChild(closeBtn);

            // Messages area
            const messagesDiv = doc.createElement('div');
            messagesDiv.id = 'meshu-messages';
            messagesDiv.style.cssText = `
                flex: 1;
                padding: 16px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 8px;
            `;

            // Input area
            const inputArea = doc.createElement('div');
            inputArea.style.cssText = `
                padding: 12px;
                border-top: 1px solid rgba(255,255,255,0.1);
                display: flex;
                gap: 8px;
                background: rgba(15, 23, 42, 0.6);
            `;
            const inputField = doc.createElement('input');
            inputField.id = 'meshu-input';
            inputField.type = 'text';
            inputField.placeholder = 'Ask me anything...';
            inputField.style.cssText = `
                flex: 1;
                padding: 10px 14px;
                border-radius: 40px;
                border: none;
                background: #1e293b;
                color: #f1f5f9;
                font-size: 14px;
                outline: none;
            `;
            const sendBtn = doc.createElement('button');
            sendBtn.id = 'meshu-send';
            sendBtn.textContent = 'Send';
            sendBtn.style.cssText = `
                background: #2563eb;
                border: none;
                border-radius: 40px;
                padding: 8px 16px;
                color: white;
                font-weight: 600;
                cursor: pointer;
            `;
            inputArea.appendChild(inputField);
            inputArea.appendChild(sendBtn);

            windowDiv.appendChild(header);
            windowDiv.appendChild(messagesDiv);
            windowDiv.appendChild(inputArea);
            container.appendChild(toggle);
            container.appendChild(windowDiv);
            doc.body.appendChild(container);

            // Add animation styles
            const style = doc.createElement('style');
            style.textContent = `
                @keyframes meshu-pulse {{
                    0% {{ box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7); }}
                    70% {{ box-shadow: 0 0 0 15px rgba(37, 99, 235, 0); }}
                    100% {{ box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }}
                }}
                .meshu-message {{
                    max-width: 80%;
                    padding: 8px 14px;
                    border-radius: 20px;
                    font-size: 14px;
                    line-height: 1.5;
                    word-wrap: break-word;
                }}
                .meshu-user {{
                    align-self: flex-end;
                    background: #2563eb;
                    color: white;
                    border-bottom-right-radius: 4px;
                }}
                .meshu-assistant {{
                    align-self: flex-start;
                    background: #334155;
                    color: #f1f5f9;
                    border-bottom-left-radius: 4px;
                }}
                .meshu-typing {{
                    display: flex;
                    gap: 4px;
                    padding: 8px 12px;
                    background: #334155;
                    border-radius: 20px;
                    width: fit-content;
                }}
                .meshu-typing span {{
                    width: 8px;
                    height: 8px;
                    background: #94a3b8;
                    border-radius: 50%;
                    animation: meshu-bounce 1.4s infinite;
                }}
                .meshu-typing span:nth-child(2) {{ animation-delay: 0.2s; }}
                .meshu-typing span:nth-child(3) {{ animation-delay: 0.4s; }}
                @keyframes meshu-bounce {{
                    0%, 60%, 100% {{ transform: translateY(0); opacity: 0.6; }}
                    30% {{ transform: translateY(-6px); opacity: 1; }}
                }}
                #meshu-window {{
                    transition: opacity 0.2s ease, transform 0.2s ease;
                    transform-origin: bottom center;
                }}
            `;
            doc.head.appendChild(style);

            // ----- Chat Logic (with key check) -----
            function addMessage(text, sender) {{
                const msgDiv = doc.createElement('div');
                msgDiv.className = `meshu-message meshu-${{sender}}`;
                msgDiv.textContent = text;
                messagesDiv.appendChild(msgDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}

            function showTyping() {{
                const typingDiv = doc.createElement('div');
                typingDiv.className = 'meshu-typing';
                typingDiv.id = 'meshu-typing';
                typingDiv.innerHTML = '<span></span><span></span><span></span>';
                messagesDiv.appendChild(typingDiv);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }}

            function removeTyping() {{
                const typing = doc.getElementById('meshu-typing');
                if (typing) typing.remove();
            }}

            async function sendToDeepSeek(userMessage) {{
                const response = await fetch(API_URL, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${{API_KEY}}`
                    }},
                    body: JSON.stringify({{
                        model: 'deepseek-chat',
                        messages: [
                            {{ role: 'system', content: 'You are MESHU, a friendly assistant for this app. Answer the user\'s question concisely.' }},
                            {{ role: 'user', content: userMessage }}
                        ],
                        temperature: 0.7
                    }})
                }});

                if (!response.ok) {{
                    const errText = await response.text();
                    throw new Error(`HTTP ${{response.status}}: ${{errText}}`);
                }}

                const data = await response.json();
                if (!data.choices || !data.choices[0]?.message?.content) {{
                    throw new Error('Invalid response format');
                }}
                return data.choices[0].message.content;
            }}

            async function handleSend() {{
                const text = inputField.value.trim();
                if (text === '') return;

                if (!keyValid) {{
                    addMessage("❌ MESHU is disabled because the API key is missing. Please add 'good' to secrets.", 'assistant');
                    return;
                }}

                addMessage(text, 'user');
                inputField.value = '';
                showTyping();

                try {{
                    const reply = await sendToDeepSeek(text);
                    removeTyping();
                    addMessage(reply, 'assistant');
                }} catch (error) {{
                    console.error('MESHU error:', error);
                    removeTyping();
                    addMessage('❌ ' + error.message, 'assistant');
                }}
            }}

            // Event listeners
            toggle.onclick = () => {{
                const isHidden = windowDiv.style.display === 'none' || windowDiv.style.display === '';
                windowDiv.style.display = isHidden ? 'flex' : 'none';
                if (isHidden) inputField.focus();
            }};

            closeBtn.onclick = () => {{
                windowDiv.style.display = 'none';
            }};

            sendBtn.onclick = handleSend;
            inputField.addEventListener('keypress', (e) => {{
                if (e.key === 'Enter') handleSend();
            }});

            // Welcome message
            if (keyValid) {{
                addMessage("Hi! I'm MESHU, your personal assistant. How can I help you today?", 'assistant');
            }} else {{
                addMessage("⚠️ MESHU is in demo mode – API key missing. Please add 'good' to secrets.", 'assistant');
            }}
        }})();
    </script>
    """

    st.components.v1.html(chatbot_html, height=0)

add_meshu_chatbot()
