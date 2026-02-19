import streamlit as st
from groq import Groq
import requests
from fpdf import FPDF
from tavily import TavilyClient
import plotly.express as px
import pandas as pd
import PyPDF2
import base64

# --- PAGE CONFIG ---
st.set_page_config(page_title="Pro Life Planner & Health Bot", page_icon="📍", layout="wide")

# --- SECRETS MANAGEMENT ---
try:
    GROQ_KEY = st.secrets["groq_api_key"]
    WEATHER_KEY = st.secrets["weather_api_key"]
    TAVILY_KEY = st.secrets["tavily_api_key"]
except FileNotFoundError:
    st.error("Secrets file not found. Please check your .streamlit/secrets.toml file.")
    st.stop()
except KeyError as e:
    st.error(f"Missing key in secrets: {e}. Please add it to Hugging Face Settings.")
    st.stop()

# --- INITIALIZE SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "medical_data" not in st.session_state:
    st.session_state.medical_data = ""

# --- TOOLS & FUNCTIONS ---

def get_current_weather(city, api_key):
    """Fetches current weather snapshot."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url).json()
        if response.get("cod") != 200:
            return None, f"Error: {response.get('message', 'Unknown error')}"
        
        main = response["main"]
        weather_desc = response["weather"][0]["description"]
        data = {
            "desc": weather_desc,
            "temp": main["temp"],
            "humidity": main["humidity"],
            "feels_like": main["feels_like"]
        }
        return data, None
    except Exception as e:
        return None, f"Weather fetch failed: {str(e)}"

def get_forecast(city, api_key):
    """Fetches 5-day/3-hour forecast for graphs."""
    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        response = requests.get(url).json()
        if response.get("cod") != "200":
            return None
        
        forecast_list = []
        for item in response['list']:
            forecast_list.append({
                "Date": item['dt_txt'],
                "Temperature (°C)": item['main']['temp'],
                "Rain Chance (%)": item.get('pop', 0) * 100,
                "Condition": item['weather'][0]['main']
            })
        return pd.DataFrame(forecast_list)
    except:
        return None

def search_places_tavily(query):
    """Finds places using Tavily AI."""
    try:
        tavily = TavilyClient(api_key=TAVILY_KEY)
        response = tavily.search(query=query, search_depth="basic", max_results=3)
        
        results = []
        for result in response.get('results', []):
            title = result.get('title', 'No Title')
            content = result.get('content', 'No Content')
            url = result.get('url', '#')
            results.append(f"- **{title}**: {content} [Link]({url})")
            
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Tavily Search Error: {str(e)}"

def extract_text_from_pdf(pdf_file):
    """Extracts text from uploaded PDF."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def encode_image(image_file):
    """Encodes image to base64 for API."""
    return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_medical_image(image_file, client):
    """Uses Vision model to read medical reports from images."""
    base64_image = encode_image(image_file)
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe this medical report text exactly. Do not interpret yet, just extract the data."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-90b-vision-preview",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error analyzing image: {e}"

def create_pdf(plan_text):
    """Generates a PDF of the trip/diet plan."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Your AI Health & Trip Plan", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=11)
    sanitized_text = plan_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=sanitized_text)
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP LAYOUT ---

st.title("🗺️ Pro Life Planner & Health Assistant")
st.markdown("Powered by **Groq** (Llama 3.3 & Vision), **Tavily**, & **OpenWeather**")

# Create 3 main tabs
main_tab, medical_tab, chat_tab = st.tabs(["📅 Trip Planner", "🏥 Medical Report Analyzer", "💬 Health Chat"])

# ==========================================
# TAB 1: TRIP PLANNER & WEATHER DASHBOARD
# ==========================================
with main_tab:
    with st.form("user_input_form"):
        col1, col2 = st.columns(2)
        with col1:
            user_city = st.text_input("Current City:", "Multan")
            user_needs = st.text_input("Specific Activity/Mood:", "Relaxing outdoor walk")
        with col2:
            user_routine = st.text_area("Your Routine/Schedule:", height=100, 
                                        placeholder="e.g., I work Mon-Fri 9-5. I am free Sunday.")
        
        submitted = st.form_submit_button("🚀 Generate Plan & Analysis")

    if submitted:
        with st.spinner("🤖 Analyzing weather, routines, and searching web..."):
            try:
                client = Groq(api_key=GROQ_KEY)
                current_weather, error_msg = get_current_weather(user_city, WEATHER_KEY)
                forecast_df = get_forecast(user_city, WEATHER_KEY)

                if error_msg:
                    st.error(error_msg)
                    st.stop()

                weather_summary = f"{current_weather['desc']}, {current_weather['temp']}°C"

                # Search Query Generation
                search_query_prompt = f"""
                Context: User in '{user_city}' wants '{user_needs}'.
                Task: Write a precise KEYWORD search query. 
                Rules: Use keywords only. Add 'best' and current year.
                Example: "best family parks Multan 2025"
                Output: ONLY query string. No quotes.
                """
                
                search_q_response = client.chat.completions.create(
                    messages=[{"role": "user", "content": search_query_prompt}],
                    model="llama-3.1-8b-instant" 
                )
                search_query = search_q_response.choices[0].message.content.strip().replace('"', '')
                
                places_info = search_places_tavily(search_query)

                # Final Plan Synthesis
                final_prompt = f"""
                You are an expert Trip Planner.
                **User Data:** Routine: {user_routine}, Prefs: {user_needs}, City: {user_city}
                **Live Data:** Weather: {weather_summary}, Search Results: {places_info}
                **Directives:**
                1. Suggest best time for trip based on routine.
                2. Suggest places from search results.
                3. Health tips based on weather ({current_weather['temp']}°C).
                """

                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": final_prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.6,
                )
                result_text = completion.choices[0].message.content
                
                st.success("Analysis Complete!")
                st.subheader("📝 Your Personalized Plan")
                st.markdown(result_text)
                
                pdf_bytes = create_pdf(result_text)
                st.download_button("📥 Download Plan PDF", pdf_bytes, "trip_plan.pdf", "application/pdf")

                st.divider()
                st.subheader(f"🌦️ Weather Intelligence: {user_city.title()}")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Temperature", f"{current_weather['temp']}°C", f"Feels like {current_weather['feels_like']}°C")
                m2.metric("Condition", current_weather['desc'].title())
                m3.metric("Humidity", f"{current_weather['humidity']}%")

                if forecast_df is not None:
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.markdown("##### 📈 5-Day Temperature")
                        fig_temp = px.line(forecast_df, x="Date", y="Temperature (°C)", markers=True)
                        st.plotly_chart(fig_temp, use_container_width=True)
                    with col_g2:
                        st.markdown("##### ☔ Rainfall Chance")
                        fig_rain = px.bar(forecast_df, x="Date", y="Rain Chance (%)", color="Rain Chance (%)")
                        st.plotly_chart(fig_rain, use_container_width=True)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# ==========================================
# TAB 2: MEDICAL REPORT ANALYZER (NEW)
# ==========================================
with medical_tab:
    st.header("🏥 Medical Report Analysis & Diet Plan")
    st.info("Upload your Lab Reports (PDF or Image) to get a custom diet plan.")
    
    uploaded_file = st.file_uploader("Upload Report", type=["pdf", "png", "jpg", "jpeg"])
    
    if uploaded_file:
        if st.button("🧬 Analyze Report"):
            with st.spinner("Reading document... (This uses AI Vision for images)"):
                client = Groq(api_key=GROQ_KEY)
                extracted_text = ""
                
                # 1. Extract Text
                if uploaded_file.type == "application/pdf":
                    extracted_text = extract_text_from_pdf(uploaded_file)
                else:
                    # Image processing with Vision Model
                    extracted_text = analyze_medical_image(uploaded_file, client)
                
                st.session_state.medical_data = extracted_text
                st.expander("View Extracted Data").write(extracted_text)

                # 2. Generate Diet Plan
                with st.spinner("Generating Diet Plan..."):
                    diet_prompt = f"""
                    You are a professional Nutritionist.
                    **Patient's Medical Data:**
                    {extracted_text}
                    
                    **Task:**
                    1. Summarize the key findings from the report (Highs/Lows).
                    2. Create a specific, safe Diet Plan based on these findings.
                    3. List foods to AVOID and foods to EAT.
                    4. DISCLAIMER: Start by stating you are an AI and this is not medical advice.
                    """
                    
                    completion = client.chat.completions.create(
                        messages=[{"role": "user", "content": diet_prompt}],
                        model="llama-3.3-70b-versatile"
                    )
                    
                    diet_plan = completion.choices[0].message.content
                    st.markdown(diet_plan)
                    
                    # Add to chat context so user can ask follow-ups
                    st.session_state.chat_history.append({"role": "assistant", "content": f"**Analysis of uploaded report:**\n\n{diet_plan}"})

# ==========================================
# TAB 3: HEALTH CHATBOT
# ==========================================
with chat_tab:
    st.header("💬 Health & Lifestyle Companion")
    st.caption("Ask follow-up questions about your report or general health.")
    
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ex: What fruits are safe for my sugar level?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    client = Groq(api_key=GROQ_KEY)
                    
                    # Include medical data in context if available
                    context_data = ""
                    if st.session_state.medical_data:
                        context_data = f"Context from uploaded report: {st.session_state.medical_data[:2000]}"

                    messages = [
                        {"role": "system", "content": f"You are a helpful Health Coach. {context_data}"}
                    ]
                    for msg in st.session_state.chat_history[-5:]: 
                        messages.append(msg)

                    chat_completion = client.chat.completions.create(
                        messages=messages,
                        model="llama-3.3-70b-versatile",
                        temperature=0.7,
                    )
                    
                    response = chat_completion.choices[0].message.content
                    st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    st.error(f"Chat Error: {str(e)}")
