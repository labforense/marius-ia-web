import streamlit as st
import google.generativeai as genai
from PIL import Image

NOME = "Marius Web"
# --- CONFIGURAÇÃO SEGURA (MUDANÇA AQUI) ---
# O Streamlit vai buscar a chave nos "Secrets" do servidor, não no código.
try:
    MINHA_CHAVE = st.secrets["GEMINI_KEY"]
except:
    # Caso você rode localmente e esqueça de configurar, mostra erro amigável
    st.error("A chave da API não foi encontrada. Configure os Secrets.")
    st.stop()

genai.configure(api_key=MINHA_CHAVE)
model = genai.GenerativeModel('gemini-2.5-flash')

# ... O RESTO DO CÓDIGO CONTINUA IGUAL ...

# --- INTERFACE VISUAL ---
st.set_page_config(page_title=NOME, page_icon="🤖", layout="centered")

st.title(f"💬 {NOME}")
st.caption("Versão Web - Acessível de qualquer lugar")

# Inicializa histórico
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "model", "content": f"Olá! Sou {NOME}. Como posso ajudar?"}]

# Exibe histórico
for msg in st.session_state.messages:
    # Define o avatar (ícone)
    avatar = "👤" if msg["role"] == "user" else "🤖"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

# --- ÁREA DE INPUT ---
# Upload de imagem (Opcional)
arquivo_img = st.sidebar.file_uploader("Anexar Imagem", type=["png", "jpg", "jpeg"])

# Caixa de texto
prompt = st.chat_input("Digite sua mensagem...")

if prompt:
    # 1. Mostra msg do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").write(prompt)

    # 2. Processa IA
    try:
        if arquivo_img:
            img = Image.open(arquivo_img)
            response = model.generate_content([prompt, img])
            st.sidebar.success("Imagem processada!")
        else:
            # Envia histórico para manter contexto
            chat = model.start_chat(history=[
                {"role": "user" if m["role"] == "user" else "model", "parts": m["content"]}
                for m in st.session_state.messages
            ])
            response = chat.send_message(prompt)
        
        texto_resp = response.text
        
        # 3. Mostra resposta
        st.session_state.messages.append({"role": "model", "content": texto_resp})
        st.chat_message("model", avatar="🤖").write(texto_resp)
        
    except Exception as e:

        st.error(f"Erro: {e}")
