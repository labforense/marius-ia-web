import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import os
import PyPDF2
from duckduckgo_search import DDGS
from streamlit_mic_recorder import mic_recorder

NOME = "Marius Web Ultimate"

# --- CONFIGURAÇÃO SEGURA ---
try:
    MINHA_CHAVE = st.secrets["GEMINI_KEY"]
except:
    st.error("Configure a GEMINI_KEY nos Secrets do Streamlit.")
    st.stop()

genai.configure(api_key=MINHA_CHAVE)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- CONFIGURAÇÃO DE VOZ (FIXED) ---
VOZ_ID = "pt-BR-AntonioNeural"
ARQUIVO_AUDIO = "audio_temp.mp3"

async def gerar_audio_async(texto):
    """Gera o áudio usando EdgeTTS"""
    if not texto: return
    communicate = edge_tts.Communicate(texto, VOZ_ID)
    await communicate.save(ARQUIVO_AUDIO)

def gerar_audio_sync(texto):
    """Wrapper para rodar o async dentro do Streamlit sem erro de Loop"""
    try:
        # Cria um novo loop isolado para essa tarefa
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(gerar_audio_async(texto))
        loop.close()
    except Exception as e:
        st.warning(f"Aviso de Áudio: {e}")

# --- FERRAMENTAS ---
def ler_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        texto = ""
        for i in range(min(len(reader.pages), 5)): texto += reader.pages[i].extract_text()
        return texto
    except: return ""

def pesquisar_web(termo):
    res = ""
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(termo, max_results=3): res += f"- {r['title']}: {r['body']}\n"
    except: pass
    return res

# --- INTERFACE ---
st.set_page_config(page_title=NOME, page_icon="🌐", layout="wide")
st.title(f"🌐 {NOME}")
st.caption("Voz Neural • Visão • PDF • Web • Mic")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "model", "content": "Sistemas online. Estou ouvindo."}]

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("🧰 Ferramentas")
    st.write("🎤 **Microfone:**")
    # Gravador simples
    audio_gravado = mic_recorder(start_prompt="Gravar", stop_prompt="Parar", key='recorder')
    
    st.markdown("---")
    img_file = st.file_uploader("📸 Imagem", type=["jpg", "png", "jpeg"])
    pdf_file = st.file_uploader("📄 PDF", type=["pdf"])

# --- CHAT ---
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])
        if "audio_bytes" in msg:
            st.audio(msg["audio_bytes"], format="audio/mp3")

prompt_texto = st.chat_input("Digite sua mensagem...")

# --- PROCESSAMENTO ---
input_final = None
tipo_input = "texto"

if audio_gravado:
    input_final = audio_gravado['bytes']
    tipo_input = "audio_input"
elif prompt_texto:
    input_final = prompt_texto
    tipo_input = "texto"

if input_final:
    # 1. Exibe Input do Usuário
    if tipo_input == "texto":
        st.session_state.messages.append({"role": "user", "content": input_final})
        st.chat_message("user", avatar="👤").write(input_final)
    else:
        st.session_state.messages.append({"role": "user", "content": "🎤 [Áudio]"})
        st.chat_message("user", avatar="👤").audio(input_final)

    # 2. Processa IA
    try:
        contexto = ""
        prompt_ia = "Responda a isso."

        if tipo_input == "texto":
            prompt_ia = input_final
            if any(x in input_final.lower() for x in ["pesquise", "quem é", "preço"]):
                with st.status("🔍 Pesquisando..."):
                    contexto += f"\n[WEB]: {pesquisar_web(input_final)}\n"

        if pdf_file:
            contexto += f"\n[PDF]: {ler_pdf(pdf_file)}\n"

        response = None

        # Tentativa de Envio para o Gemini
        try:
            if img_file:
                img = Image.open(img_file)
                response = model.generate_content([contexto + prompt_ia, img])
            elif tipo_input == "audio_input":
                # Tenta enviar o áudio. Se falhar, avisa.
                response = model.generate_content([
                    "Ouça e responda.",
                    {"mime_type": "audio/webm", "data": input_final}
                ])
            else:
                response = model.generate_content(contexto + prompt_ia)
        except Exception as e_api:
            # Se der erro de parâmetro aqui, pegamos o erro sem quebrar o app
            st.error(f"Erro na API do Google (Áudio incompatível): {e_api}")
            st.stop()

        texto_resp = response.text

        # 3. Gera Voz Neural (Marius Fala)
        gerar_audio_sync(texto_resp)

        # 4. Exibe Resposta
        audio_data = None
        if os.path.exists(ARQUIVO_AUDIO):
            with open(ARQUIVO_AUDIO, "rb") as f: audio_data = f.read()

        with st.chat_message("model", avatar="🤖"):
            st.write(texto_resp)
            if audio_data:
                st.audio(audio_data, format="audio/mp3", autoplay=True)

        st.session_state.messages.append({
            "role": "model", 
            "content": texto_resp,
            "audio_bytes": audio_data
        })

    except Exception as e:
        st.error(f"Erro Geral: {e}")
