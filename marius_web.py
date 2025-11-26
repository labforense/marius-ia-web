import streamlit as st
import google.generativeai as genai
from PIL import Image
import PyPDF2
from duckduckgo_search import DDGS

# --- CONFIGURAÇÕES ---
NOME = "Marius Analista"

st.set_page_config(page_title=NOME, page_icon="🧐", layout="wide")

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
    """Extrai texto de arquivos PDF"""
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        texto = ""
        # Lê até 10 páginas (ajuste conforme necessidade)
        for i in range(min(len(reader.pages), 10)):
            texto += reader.pages[i].extract_text() + "\n"
        return texto
    except Exception as e:
        return f"Erro ao ler PDF: {e}"

def pesquisar_web(termo):
    """Busca informações na internet (DuckDuckGo)"""
    res = ""
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(termo, max_results=3):
                res += f"- {r['title']}: {r['body']}\n"
    except: pass
    return res

# --- INTERFACE ---
st.title(f"🧐 {NOME}")
st.caption("Especialista em Análise: Texto • Imagem • PDF • Web")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Olá. Envie imagens ou PDFs na barra lateral e vamos analisar."}]

# --- BARRA LATERAL (INPUTS) ---
with st.sidebar:
    st.header("📂 Arquivos")
    
    # 1. Upload Imagem
    img_file = st.file_uploader("📸 Analisar Imagem", type=["jpg", "png", "jpeg"])
    if img_file:
        st.image(img_file, caption="Imagem carregada", use_container_width=True)
    
    st.markdown("---")
    
    # 2. Upload PDF
    pdf_file = st.file_uploader("📄 Analisar PDF", type=["pdf"])
    if pdf_file:
        st.info(f"PDF '{pdf_file.name}' pronto para leitura.")

# --- CHAT ---
# Mostra histórico
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

# Input de Texto
prompt = st.chat_input("Digite sua mensagem aqui...")

if prompt:
    # Mostra mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").write(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty() # Espaço para o texto aparecer
        placeholder.markdown("🧠 *Analisando dados...*")

        try:
            # CONSTRUÇÃO DO CONTEXTO
            contexto = ""
            
            # 1. Se tiver PDF, lê e adiciona ao contexto
            if pdf_file:
                conteudo_pdf = ler_pdf(pdf_file)
                contexto += f"\n--- CONTEÚDO DO PDF ANEXADO ---\n{conteudo_pdf}\n-------------------------------\n"

            # 2. Se o usuário pedir pesquisa web (gatilhos)
            if any(x in prompt.lower() for x in ["pesquise", "busque", "quem é", "atual", "notícia"]):
                dados_web = pesquisar_web(prompt)
                contexto += f"\n--- DADOS DA WEB (FONTE EXTERNA) ---\n{dados_web}\n------------------------------------\n"

            prompt_final = contexto + "PERGUNTA DO USUÁRIO: " + prompt

            # ENVIO PARA A IA
            response = None
            
            # Cenário A: Texto + Imagem
            if img_file:
                img_pil = Image.open(img_file)
                response = model.generate_content([prompt_final, img_pil])
            
            # Cenário B: Apenas Texto (com ou sem PDF/Web)
            else:
                response = model.generate_content(prompt_final)
            
            texto_resp = response.text
            
            # Exibe e Salva
            placeholder.markdown(texto_resp)
            st.session_state.messages.append({"role": "assistant", "content": texto_resp})

        except Exception as e:
            placeholder.error(f"Erro: {e}")
