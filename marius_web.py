import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import os
import PyPDF2
from duckduckgo_search import DDGS
from streamlit_mic_recorder import mic_recorder # OUVIDOS

NOME = "Marius Web Ultimate"

# --- CONFIGURAÇÃO SEGURA ---
try:
    MINHA_CHAVE = st.secrets["GEMINI_KEY"]
except:
    st.error("Configure a GEMINI_KEY nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=MINHA_CHAVE)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- CONFIGURAÇÃO DE VOZ ---
VOZ_ID = "pt-BR-AntonioNeural"
ARQUIVO_AUDIO = "audio_temp.mp3"

async def gerar_audio(texto):
    communicate = edge_tts.Communicate(texto, VOZ_ID)
    await communicate.save(ARQUIVO_AUDIO)

# --- FERRAMENTAS ---
def ler_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        texto = ""
        for i in range(min(len(reader.pages), 5)): texto += reader.pages[i].extract_text()
        return texto
    except: return "Erro ao ler PDF."

def pesquisar_web(termo):
    res = ""
    with DDGS() as ddgs:
        for r in ddgs.text(termo, max_results=3): res += f"- {r['title']}: {r['body']}\n"
    return res

# --- INTERFACE ---
st.set_page_config(page_title=NOME, page_icon="🌐", layout="wide")
st.title(f"🌐 {NOME}")
st.caption("Voz Neural • Visão • PDF • Web Search • Microfone")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "model", "content": "Sistemas online. Pode falar comigo!"}]

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("🧰 Ferramentas")
    
    # 1. Microfone (NOVO!)
    st.subheader("🎤 Falar com Marius")
    audio_gravado = mic_recorder(start_prompt="Gravar 🔴", stop_prompt="Parar ⏹️", key='recorder')
    
    # 2. Uploads
    st.markdown("---")
    img_file = st.file_uploader("📸 Analisar Imagem", type=["jpg", "png", "jpeg"])
    pdf_file = st.file_uploader("📄 Ler PDF", type=["pdf"])

# --- CHAT ---
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])
        if "audio_bytes" in msg:
            st.audio(msg["audio_bytes"], format="audio/mp3")

# Input de Texto
prompt_texto = st.chat_input("Digite sua mensagem...")

# --- LÓGICA CENTRAL (PROCESSADOR) ---
input_final = None
tipo_input = "texto" # texto, audio_input

if audio_gravado:
    input_final = audio_gravado['bytes'] # Pega os bytes do áudio
    tipo_input = "audio_input"
elif prompt_texto:
    input_final = prompt_texto
    tipo_input = "texto"

if input_final:
    # Mostra input do usuário
    if tipo_input == "texto":
        st.session_state.messages.append({"role": "user", "content": input_final})
        st.chat_message("user", avatar="👤").write(input_final)
    else:
        st.session_state.messages.append({"role": "user", "content": "🎤 [Áudio enviado]"})
        st.chat_message("user", avatar="👤").audio(input_final)

    # --- PROCESSAMENTO IA ---
    try:
        contexto_extra = ""
        prompt_ia = "Responda a isso." # Prompt base se for áudio

        # Se for texto, verifica busca web
        if tipo_input == "texto":
            prompt_ia = input_final
            if any(x in input_final.lower() for x in ["pesquise", "notícia", "preço", "quem é"]):
                with st.status("🔍 Pesquisando na web..."):
                    web_data = pesquisar_web(input_final)
                    contexto_extra += f"\n[DADOS WEB]:\n{web_data}\n"

        # Se tiver PDF
        if pdf_file:
            conteudo_pdf = ler_pdf(pdf_file)
            contexto_extra += f"\n[PDF CONTEXTO]:\n{conteudo_pdf}\n"

        # GERAÇÃO DA RESPOSTA
        response = None
        
        # Cenário A: Tem Imagem
        if img_file:
            img = Image.open(img_file)
            instrucao = contexto_extra + (prompt_ia if tipo_input == "texto" else "Analise a imagem e o áudio.")
            response = model.generate_content([instrucao, img])
            st.sidebar.image(img, caption="Imagem Analisada")
            
        # Cenário B: Tem Áudio de Entrada (Microfone)
        elif tipo_input == "audio_input":
            # O Gemini Flash ouve o áudio diretamente!
            response = model.generate_content([
                contexto_extra + "Ouça este áudio e responda em português.",
                {"mime_type": "audio/wav", "data": input_final}
            ])
            
        # Cenário C: Só Texto
        else:
            response = model.generate_content(contexto_extra + prompt_ia)

        texto_resp = response.text
        
        # Gera Voz de Resposta (Marius fala)
        asyncio.run(gerar_audio(texto_resp))
        with open(ARQUIVO_AUDIO, "rb") as f:
            audio_data = f.read()

        # Mostra resposta
        with st.chat_message("model", avatar="🤖"):
            st.write(texto_resp)
            st.audio(audio_data, format="audio/mp3", autoplay=True)

        st.session_state.messages.append({
            "role": "model", 
            "content": texto_resp,
            "audio_bytes": audio_data
        })

    except Exception as e:
        st.error(f"Erro: {e}")
