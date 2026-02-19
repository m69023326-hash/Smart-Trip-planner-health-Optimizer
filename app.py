import streamlit as st
from groq import Groq
import requests
from fpdf import FPDF
from tavily import TavilyClient
import plotly.express as px
import pandas as pd
import PyPDF2
import base64
import edge_tts
import asyncio
import tempfile

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro Life Planner & Health Bot", page_icon="📍", layout="wide")

# --- CUSTOM CSS FOR GEMINI LOOK ---
st.markdown("""
<style>
    /* Gemini-style Suggestion Buttons */
    .stButton>button {
        border-radius: 20px;
        background-color: #f0f2f6; 
        color: black;
        border: none;
        height: 60px;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #dbe0e6;
        transform: scale(1.02);
    }
    
    /* Center Greeting */
    .greeting-container {
        text-align: center;
        margin-top: 40px;
        margin-bottom: 40px;
    }
    .big-font {
        font-size: 38px !important;
        font-weight: 600;
        background: -webkit-linear-gradient(45deg, #4b90ff, #ff5546);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-font {
        font-size: 18px !important;
        color: #666;
        margin-top: 5px;
    }

    /* Input Toolbar Styling - Making the + button look like an icon */
    div[data-testid="stPopover"] > button {
        border-radius: 50%;
        height: 45px;
        width: 45px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# --- SECRETS MANAGEMENT ---
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

# --- INITIALIZE STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "medical_data" not in st.session_state:
    st.session_state.medical_data = ""
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

# --- FUNCTIONS ---

def get_current_weather(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url).json()
        if response.get("cod") != 200: return None, "Error"
        main = response["main"]
        data = {
            "desc": response["weather"][0]["description"],
            "temp": main["temp"],
            "humidity": main["humidity"],
            "feels_like": main["feels_like"]
        }
        return data, None
    except: return None, "Error"

def get_forecast(city, api_key):
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        res = requests.get(url).json()
        if res.get("cod") != "200": return None
        data = []
        for i in res['list']:
            data.append({"Date": i['dt_txt'], "Temperature (°C)": i['main']['temp'], "Rain Chance (%)": i.get('pop', 0)*100})
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
    voice = "en-US-AriaNeural"
    if lang == "UR": voice = "ur-PK-UzmaNeural"
    elif lang == "HI": voice = "hi-IN-SwaraNeural"
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

# --- MAIN APP ---
st.title("🗺️ Pro Life Planner & Health Assistant")
main_tab, companion_tab = st.tabs(["📅 Trip Planner", "🤖 AI Health Companion"])

# --- TAB 1: TRIP PLANNER ---
with main_tab:
    with st.form("trip_form"):
        c1, c2 = st.columns(2)
        city = c1.text_input("City", "New York")
        mood = c1.text_input("Activity", "Relaxing walk")
        routine = c2.text_area("Routine", "Mon-Fri 9-5 work")
        if st.form_submit_button("🚀 Generate Plan"):
            client = Groq(api_key=GROQ_KEY)
            weather, err = get_current_weather(city, WEATHER_KEY)
            if err: st.error("Weather Error")
            else:
                q_res = client.chat.completions.create(
                    messages=[{"role": "user", "content": f"Create search query for {mood} in {city} 2025. Keywords only."}],
                    model="llama-3.1-8b-instant"
                )
                search_data = search_tavily(q_res.choices[0].message.content)
                
                final_res = client.chat.completions.create(
                    messages=[{"role": "user", "content": f"Plan trip. Routine: {routine}, Weather: {weather}, Places: {search_data}"}],
                    model="llama-3.3-70b-versatile"
                )
                plan = final_res.choices[0].message.content
                st.markdown(plan)
                st.download_button("📥 Download PDF", create_pdf(plan), "plan.pdf")
                
                df = get_forecast(city, WEATHER_KEY)
                if df is not None:
                    c1, c2 = st.columns(2)
                    c1.plotly_chart(px.line(df, x="Date", y="Temperature (°C)", title="Temp Trend"))
                    c2.plotly_chart(px.bar(df, x="Date", y="Rain Chance (%)", title="Rain Chance"))

# --- TAB 2: GEMINI-STYLE COMPANION ---
with companion_tab:
    client = Groq(api_key=GROQ_KEY)

    # 1. Zero State
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="greeting-container">
            <div class="big-font">Hello dear, how can I help you?</div>
            <div class="sub-font">Tell me what you want or use the options below</div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("📄 Share Reports & Get Analysis"):
            st.session_state.chat_history.append({"role": "assistant", "content": "Please upload your report using the ➕ button!"})
            st.rerun()
        if c2.button("🥦 Prepare a Diet Plan"):
            st.session_state.chat_history.append({"role": "user", "content": "I need a diet plan."})
            st.rerun()
            
        c3, c4 = st.columns(2)
        if c3.button("🎬 Suggest Movies"):
            st.session_state.chat_history.append({"role": "user", "content": "Suggest some good movies."})
            st.rerun()
        if c4.button("🩺 Check Symptoms"):
            st.session_state.chat_history.append({"role": "user", "content": "I'm not feeling well."})
            st.rerun()

    # 2. Chat History
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    # 3. COMPACT INPUT TOOLBAR
    # We use columns to create a tight row of icons right above the chat input
    col_plus, col_voice = st.columns([0.1, 0.9])
    
    with col_plus:
        # The "+" Icon is actually a small popover containing the file uploader
        with st.popover("➕", use_container_width=True):
            uploaded_file = st.file_uploader("Upload", type=["pdf", "jpg", "png"], label_visibility="collapsed")
            
    with col_voice:
        # The Microphone is the native audio input widget
        audio_val = st.audio_input("Voice", label_visibility="collapsed")

    # --- LOGIC HANDLING ---

    # A. File Upload
    if uploaded_file:
        with st.spinner("Analyzing Document..."):
            txt = extract_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else analyze_image(uploaded_file, client)
            st.session_state.medical_data = txt
            st.session_state.chat_history.append({"role": "user", "content": f"📎 Uploaded: {uploaded_file.name}"})
            
            res = client.chat.completions.create(
                messages=[{"role": "user", "content": f"Analyze this medical data: {txt}. Give diet plan."}],
                model="llama-3.3-70b-versatile"
            )
            resp = res.choices[0].message.content
            st.session_state.chat_history.append({"role": "assistant", "content": resp})
            st.rerun()

    # B. Voice Logic
    if audio_val and audio_val != st.session_state.last_audio:
        st.session_state.last_audio = audio_val
        with st.spinner("Listening..."):
            # Transcribe
            txt = client.audio.transcriptions.create(file=("v.wav", audio_val), model="whisper-large-v3-turbo").text
            st.chat_message("user").write(f"🎙️ {txt}")
            st.session_state.chat_history.append({"role": "user", "content": f"🎙️ {txt}"})
            
            # Detect Lang & Reply
            res = client.chat.completions.create(
                messages=[{"role": "system", "content": "Reply in same language. Start with [LANG:UR], [LANG:HI], or [LANG:EN]."}, {"role": "user", "content": txt}],
                model="llama-3.3-70b-versatile"
            )
            raw = res.choices[0].message.content
            lang = "EN"
            if "[LANG:UR]" in raw: lang = "UR"
            elif "[LANG:HI]" in raw: lang = "HI"
            clean_text = raw.replace(f"[LANG:{lang}]", "").strip()
            
            # Show & Speak
            st.chat_message("assistant").write(clean_text)
            st.session_state.chat_history.append({"role": "assistant", "content": clean_text})
            st.audio(asyncio.run(tts(clean_text, lang)), autoplay=True)

    # C. Text Logic
    if prompt := st.chat_input("Message..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        context = f"Medical Context: {st.session_state.medical_data[:1000]}" if st.session_state.medical_data else ""
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": "Helpful health assistant. " + context}, {"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        resp = res.choices[0].message.content
        st.chat_message("assistant").write(resp)
        st.session_state.chat_history.append({"role": "assistant", "content": resp})
