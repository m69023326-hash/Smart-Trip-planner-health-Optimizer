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

# --- CUSTOM CSS FOR PROFESSIONAL UI ---
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
        st.markdown('<div class="greeting-header">Hello dear, how can I help you?</div>', unsafe_allow_html=True)
        st.markdown('<div class="greeting-sub">Tell me what you want or choose an option below</div>', unsafe_allow_html=True)
        
        col_buttons, col_space = st.columns([1, 2]) 
        
        with col_buttons:
            if st.button("📄 Share Reports & Get Analysis"):
                st.session_state.chat_history.append({"role": "assistant", "content": "Sure! 🩺 Please upload your medical report using the ➕ button below.\n\nWhat else can I do for you today? ✨"})
                st.rerun()
            if st.button("🥦 Prepare a Diet Plan"):
                st.session_state.chat_history.append({"role": "user", "content": "I need a diet plan."})
                st.rerun()
            if st.button("🎬 Suggest Movies"):
                st.session_state.chat_history.append({"role": "user", "content": "Suggest some good movies."})
                st.rerun()
            if st.button("🩺 Check Symptoms"):
                st.session_state.chat_history.append({"role": "user", "content": "I'm not feeling well."})
                st.rerun()

    # 2. Chat History Display
    for i, msg in enumerate(st.session_state.chat_history):
        st.chat_message(msg["role"]).write(msg["content"])
        if msg["role"] == "user" and "pdf" in msg["content"].lower() and i > 0:
            prev_msg = st.session_state.chat_history[i-1]["content"]
            st.download_button("📥 Download Document", create_pdf(prev_msg), f"document_{i}.pdf", key=f"dl_{i}")

    # 3. PROFESSIONAL INPUT TOOLBAR
    col_plus, col_voice = st.columns([0.08, 0.92]) 
    
    with col_plus:
        with st.popover("➕", use_container_width=True):
            uploaded_file = st.file_uploader("Upload", type=["pdf", "jpg", "png"], label_visibility="collapsed")
            
    with col_voice:
        audio_val = st.audio_input("Voice", label_visibility="collapsed")

    # --- LOGIC HANDLING ---

    # A. File Upload (Diet Plan System Prompt)
    if uploaded_file:
        with st.spinner("Analyzing Document..."):
            txt = extract_pdf(uploaded_file) if uploaded_file.type == "application/pdf" else analyze_image(uploaded_file, client)
            st.session_state.medical_data = txt
            st.session_state.chat_history.append({"role": "user", "content": f"📎 Uploaded: {uploaded_file.name}"})
            
            sys_prompt = """
            You are a helpful nutritionist. 
            Rule 1: Always use emojis 🍎🥦. 
            Rule 2: Format the diet plan beautifully. Use Markdown headers (###), bullet points, and leave EMPTY LINES between paragraphs so it is easy to read.
            Rule 3: At the very end of your diet plan, on a NEW LINE, you MUST ask: "Do you want its PDF file? 📄"
            """
            res = client.chat.completions.create(
                messages=[{"role": "system", "content": sys_prompt}, 
                          {"role": "user", "content": f"Analyze this medical data: {txt}. Give diet plan."}],
                model="llama-3.3-70b-versatile"
            )
            resp = res.choices[0].message.content
            st.session_state.chat_history.append({"role": "assistant", "content": resp})
            st.rerun()

    # B. Voice Logic (Voice System Prompt)
    if audio_val and audio_val != st.session_state.last_audio:
        st.session_state.last_audio = audio_val
        with st.spinner("Listening..."):
            txt = client.audio.transcriptions.create(file=("v.wav", audio_val), model="whisper-large-v3-turbo").text
            st.chat_message("user").write(f"🎙️ {txt}")
            st.session_state.chat_history.append({"role": "user", "content": f"🎙️ {txt}"})
            
            sys_msg = """
            You are a friendly AI companion. 
            1. Reply in same language. Start with [LANG:UR], [LANG:HI], or [LANG:EN].
            2. ALWAYS use emojis 😊.
            3. Format your text response professionally. Leave clear EMPTY LINES between different thoughts or sentences so it does not look like a single block of text.
            4. If creating a plan, end on a NEW LINE asking: "Do you want its PDF file? 📄"
            5. If answering a normal question, end on a NEW LINE asking: "What else can I do for you today? ✨"
            """
            res = client.chat.completions.create(
                messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": txt}],
                model="llama-3.3-70b-versatile"
            )
            raw = res.choices[0].message.content
            lang = "EN"
            if "[LANG:UR]" in raw: lang = "UR"
            elif "[LANG:HI]" in raw: lang = "HI"
            clean_text = raw.replace(f"[LANG:{lang}]", "").strip()
            
            st.chat_message("assistant").write(clean_text)
            st.session_state.chat_history.append({"role": "assistant", "content": clean_text})
            st.audio(asyncio.run(tts(clean_text, lang)), autoplay=True)

    # C. Text Logic (Text System Prompt)
    if prompt := st.chat_input("Message..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        context = f"Medical Context: {st.session_state.medical_data[:1000]}" if st.session_state.medical_data else "No medical context."
        
        sys_prompt = f"""
        You are a highly empathetic and professional AI Companion.
        Follow these rules strictly:
        1. Always use relevant emojis to make your response engaging 🌟.
        2. Format your responses beautifully using Markdown. You MUST use clear paragraph breaks (leave an empty line between different thoughts) and bullet points where helpful. Never write a single giant block of text.
        3. If the user asks you to create a plan, leave an empty line at the end and ask exactly: "Do you want its PDF file? 📄"
        4. For general questions, leave an empty line at the end and ask: "What else can I do for you today? 😊" or "How else can I help? ✨".
        {context}
        """
        
        res = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        resp = res.choices[0].message.content
        st.chat_message("assistant").write(resp)
        st.session_state.chat_history.append({"role": "assistant", "content": resp})
