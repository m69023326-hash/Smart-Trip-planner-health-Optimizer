# Ultimate Planner & Tourism Guide 🌍

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)  
[![GitHub license](https://img.shields.io/github/license/yourusername/ultimate-planner)](https://github.com/yourusername/ultimate-planner/blob/main/LICENSE)

**Three powerful tools in one seamless experience** – a Health Companion, a Trip Planner, and a Pakistan Tourism Hub. Built with Streamlit and powered by Groq, DeepSeek, Tavily, and OpenWeather APIs.

---

## ✨ Features at a Glance

| Module             | Key Features                                                                                                 |
|--------------------|--------------------------------------------------------------------------------------------------------------|
| **Health Companion**  | Conversational AI that asks about your condition, accepts file uploads (no analysis), and generates a personalized diet plan based on your symptoms. |
| **Trip Planner**      | Multi‑page planner with world destination explorer, safety tips, budget guides, local customs, and an AI‑powered trip generator with real‑time weather & web search. |
| **Pakistan Tourism**  | Comprehensive guides for Pakistani destinations, interactive maps, weather forecasts, AI concierge, budget calculator, emergency contacts, photo galleries, and cultural tips. |
| **MESHU Chatbot**     | Floating chatbot (powered by Groq) for quick questions, available across all pages.                         |
| **Theme Support**     | Light/Dark mode toggle with beautifully crafted CSS.                                                         |

---

## 🖥️ Demo

*(Replace with actual screenshots or GIFs)*

| Health Companion | Trip Planner | Pakistan Tourism |
|------------------|--------------|------------------|
| ![Health](https://via.placeholder.com/300x200?text=Health+Chat) | ![Planner](https://via.placeholder.com/300x200?text=Trip+Planner) | ![Tourism](https://via.placeholder.com/300x200?text=Pakistan+Tourism) |

---

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ultimate-planner.git
   cd ultimate-planner
   graph TD
    A[Streamlit App] --> B[Health Companion]
    A --> C[Trip Planner]
    A --> D[Pakistan Tourism]
    A --> E[MESHU Chatbot]

    B --> F[Groq / DeepSeek]
    B --> G[Edge-TTS]

    C --> H[OpenWeatherMap]
    C --> I[Tavily]
    C --> J[Groq]

    D --> K[Open-Meteo]
    D --> L[Groq]
    D --> M[Local JSON Data]

    E --> N[Groq]
