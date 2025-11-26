import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
from duckduckgo_search import DDGS
import time

# --- CONFIGURAÇÕES VISUAIS (GEMINI STYLE) ---
st.set_page_config(page_title="Marius Gemini", page_icon="✨", layout="wide")

# CSS para imitar a interface limpa do Gemini
st.markdown("""
<style>
    /* Fundo escuro suave */
    .stApp { background-color: #0E1117; }
    
    /* Balões de chat mais arredondados e sem borda forte */
    .stChatMessage {
        border-radius: 20px;
        border: 1px solid #303030;
    }
    
    /* Remove o padding excessivo do topo */
    .block-container { padding-top: 2rem; }
    
    /* Estiliza o input de texto */
    .stChatInput textarea {
        border-radius: 20px;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

NOME = "Marius"

# --- SEGURANÇA ---
try:
    MINHA_CHAVE = st.secrets["GEMINI_KEY"]
except:
    st.error("Configure a GEMINI_KEY nos Secrets.")
    st.stop()

genai.configure(api_key=MINHA_CHAVE)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- FERRAMENTAS ---
def ler_pdf(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        texto = ""
        for i in range(min(len(reader.pages), 10)):
            texto += reader.pages[i].extract_text() + "\n"
        return texto
    except: return ""

def pesquisar_web(termo):
    res = ""
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(termo, max_results=3):
                res += f"- {r['title']}: {r['body']}\n"
    except: pass
    return res

# --- INTERFACE ---
st.title(f"✨ {NOME}")
st.caption("Powered by Gemini 2.5 Flash")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Olá. Pode anexar imagens ou PDFs na barra lateral."}]

# --- BARRA LATERAL (ARQUIVOS) ---
with st.sidebar:
    st.header("📂 Arquivos")
    img_file = st.file_uploader("📸 Imagem", type=["jpg", "png", "jpeg"])
    if img_file: st.image(img_file, use_container_width=True)
    
    st.markdown("---")
    pdf_file = st.file_uploader("📄 PDF", type=["pdf"])
    if pdf_file: st.info("PDF Carregado")

# --- HISTÓRICO ---
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "✨"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

# --- INPUT E LÓGICA DE STREAMING ---
prompt = st.chat_input("Pergunte ao Marius...")

if prompt:
    # 1. Mostra pergunta do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").write(prompt)

    # 2. Prepara o contexto
    contexto = ""
    
    # Busca Web Automática (Se necessário)
    if any(x in prompt.lower() for x in ["pesquise", "quem é", "preço", "notícia"]):
        with st.status("🔍 Pesquisando na web...", expanded=False) as status:
            web_data = pesquisar_web(prompt)
            contexto += f"\n[WEB DATA]: {web_data}\n"
            status.update(label="Pesquisa concluída!", state="complete")
    
    if pdf_file:
        contexto += f"\n[PDF]: {ler_pdf(pdf_file)}\n"

    prompt_final = contexto + prompt

    # 3. RESPOSTA COM STREAMING (O SEGREDO DA VELOCIDADE)
    with st.chat_message("assistant", avatar="✨"):
        try:
            # stream=True faz o Google mandar pedacinhos da resposta
            if img_file:
                img = Image.open(img_file)
                response = model.generate_content([prompt_final, img], stream=True)
            else:
                response = model.generate_content(prompt_final, stream=True)
            
            # st.write_stream cria o efeito de digitação automática
            full_response = st.write_stream(response)
            
            # Salva no histórico
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Erro: {e}")

