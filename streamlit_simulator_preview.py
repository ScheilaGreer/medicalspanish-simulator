import streamlit as st
import os
import json
import random
from gtts import gTTS
import speech_recognition as sr
import datetime

SCENARIO_FOLDER = "scenarios"
AUDIO_FOLDER = "audio"
LOG_FILE = "log_streamlit.csv"
NO_ENTIENDO_RESPONSES = [
    "Lo siento, no entendí eso.",
    "¿Puede repetirlo, por favor?",
    "No estoy seguro de lo que quiere decir.",
    "¿Podría decirlo de otra forma?",
    "Perdón, no comprendí bien."
]

def list_scenarios():
    files = sorted([f for f in os.listdir(SCENARIO_FOLDER) if f.endswith(".json")])
    return files

def load_scenario(file_name):
    file_path = os.path.join(SCENARIO_FOLDER, file_name)
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def match_response(user_input, responses):
    user_input = user_input.lower()
    for item in responses:
        for keyword in item["keywords"]:
            if keyword.lower() in user_input:
                return item["reply"]
    return random.choice(NO_ENTIENDO_RESPONSES)

def speak(text, filename):
    tts = gTTS(text=text, lang='es')
    if not os.path.exists(AUDIO_FOLDER):
        os.makedirs(AUDIO_FOLDER)
    file_path = os.path.join(AUDIO_FOLDER, filename)
    tts.save(file_path)
    return file_path

def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎙️ Escuchando... hable ahora en español")
        try:
            audio = r.listen(source, timeout=5)
            st.success("✅ Voz capturada. Procesando...")
            text = r.recognize_google(audio, language="es-ES")
            return text
        except sr.WaitTimeoutError:
            return "⏱️ Tiempo agotado. Intente de nuevo."
        except sr.UnknownValueError:
            return "🤷 No entendí."
        except sr.RequestError as e:
            return f"⚠️ Error de reconocimiento: {e}"

# --- Streamlit UI ---
st.set_page_config(page_title="Medical Spanish AI Simulator", page_icon="🧠")
st.title("🧠 Medical Spanish AI Simulator")

# Session state initialization
if "scenario" not in st.session_state:
    st.session_state["scenario"] = None
    st.session_state["filename"] = ""
    st.session_state["history"] = []
    st.session_state["student"] = ""
    st.session_state["diagnosis_revealed"] = False
    st.session_state["conversation_ended"] = False

student_name = st.text_input("👤 What is your name?", value=st.session_state["student"])
scenario_files = list_scenarios()
case_labels = [f"Patient Case #{i+1}" for i in range(len(scenario_files))]
selected_label = st.selectbox("📁 Choose a patient scenario:", case_labels)
selected_index = case_labels.index(selected_label)
selected_file = scenario_files[selected_index]

if st.button("🟢 Start Scenario") and student_name:
    scenario = load_scenario(selected_file)
    st.session_state.update({
        "scenario": scenario,
        "filename": selected_file,
        "student": student_name,
        "history": [],
        "diagnosis_revealed": False,
        "conversation_ended": False
    })
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        now = datetime.datetime.now().isoformat()
        f.write(f"{now},{student_name},{selected_file}\n")

    intro = scenario.get("start", "Hola.")
    audio_path = speak(intro, "start.mp3")
    st.audio(audio_path)
    st.session_state["history"].append(("Patient", intro))

# Main interaction
if st.session_state["scenario"]:
    col1, col2, col3 = st.columns(3)

    with col1:
        if not st.session_state.get("conversation_ended", False):
            if st.button("🎙️ Record your question (in Spanish)"):
                user_input = recognize_speech()
                st.session_state["history"].append(("You", user_input))

                reply = match_response(user_input, st.session_state["scenario"]["responses"])
                st.session_state["history"].append(("Patient", reply))

                audio_path = speak(reply, f"reply_{random.randint(1000,9999)}.mp3")
                st.audio(audio_path)
                st.session_state["diagnosis_revealed"] = True
        else:
            st.info("🔴 The conversation has ended. Click 'Reset Simulation' to start over.")

    with col2:
        if st.button("📜 Show chat history"):
            st.subheader("🧾 Chat Transcript")
            for speaker, msg in st.session_state["history"]:
                st.markdown(f"**{speaker}:** {msg}")

    with col3:
        if st.button("🔄 Reset Simulation"):
            st.session_state.update({
                "scenario": None,
                "filename": "",
                "history": [],
                "diagnosis_revealed": False,
                "conversation_ended": False
            })
            st.rerun()

    if st.button("🔴 End Conversation"):
        st.session_state["conversation_ended"] = True
        st.success("🔴 Conversation ended. You can now review the transcript or reset.")

    if st.session_state["diagnosis_revealed"] and not st.session_state["conversation_ended"]:
        st.subheader("🧠 Reflection: What is the main concern?")
        student_answer = st.text_input("Type your answer in English:")
        if st.button("Check My Answer"):
            scenario = st.session_state["scenario"]
            correct = scenario.get("answer", "").strip().lower()
            guess = student_answer.strip().lower()

            if not student_answer:
                st.warning("⚠️ Please type your answer first.")
            elif guess == correct:
                st.success("✅ Correct! You identified the main concern.")
            else:
                st.error(f"❌ That's not correct. The correct answer is: **{correct}**")

    if st.session_state["diagnosis_revealed"]:
        if st.button("🩺 Reveal Diagnosis"):
            scenario = st.session_state["scenario"]
            name = scenario.get("name", "Unknown")
            condition = scenario.get("condition", "Unknown Condition")
            st.success(f"🧑‍⚕️ Patient Name: **{name}**\n\n💡 Diagnosis: **{condition}**")

    if st.button("💾 Export conversation"):
        filename = f"chat_{student_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        chat_lines = [f"{speaker}: {msg}" for speaker, msg in st.session_state["history"]]
        chat_text = "\n".join(chat_lines)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Student: {student_name}\nScenario: {st.session_state['filename']}\n\n")
            f.write(chat_text)
        with open(filename, "rb") as f:
            st.download_button("⬇️ Download Chat History", f, file_name=filename)
