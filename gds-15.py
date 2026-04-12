import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ================= CONFIGURAÇÕES DE E-MAIL =================
SEU_EMAIL = st.secrets["EMAIL_USUARIO"]
SENHA_DO_EMAIL = st.secrets["SENHA_USUARIO"]
# ===========================================================

# ================= CONEXÃO COM GOOGLE SHEETS =================
@st.cache_resource
def conectar_planilha():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS_JSON"])
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=escopos)
    client = gspread.authorize(creds)
    # CONECTA À PLANILHA CENTRAL DE TOKENS
    return client.open("Controle_Tokens").sheet1 

try:
    planilha = conectar_planilha()
except Exception as e:
    st.error(f"Erro de conexão com a planilha de controle: {e}")
    st.stop()
# =============================================================

def enviar_email_resultados(nome, token, data_nasc, idade, perguntas, respostas):
    # Lógica de Pontuação GDS-15 (Sim=1 ponto para itens depressivos / Não=1 ponto para itens protetores)
    # Itens onde SIM vale ponto: 2, 3, 4, 6, 8, 9, 10, 12, 14, 15
    # Itens onde NÃO vale ponto: 1, 5, 7, 11, 13
    pontos = 0
    itens_sim = [1, 2, 3, 5, 7, 8, 9, 11, 13, 14] # Índices da lista perguntas (0-14)
    itens_nao = [0, 4, 6, 10, 12]
    
    for i in itens_sim:
        if respostas[i] == "Sim": pontos += 1
    for i in itens_nao:
        if respostas[i] == "Não": pontos += 1

    total_sim = sum(1 for r in respostas.values() if r == "Sim")
    total_nao = sum(1 for r in respostas.values() if r == "Não")
    
    if pontos >= 11:
        resultado = "DEPRESSÃO GRAVE"
    elif pontos >= 5:
        resultado = "CLÍNICO (Indicativo de sintomas depressivos)"
    else:
        resultado = "NÃO CLÍNICO"

    assunto = f"Resultados GDS-15 - Paciente: {nome}"
    
    corpo = f"Avaliação GDS-15 (Escala de Depressão Geriátrica) concluída.\n\n"
    corpo += f"=== DADOS DO(A) PACIENTE ===\n\n"
    corpo += f"Nome Completo: {nome}\n"
    corpo += f"Data de Nascimento: {data_nasc}\n"
    corpo += f"Idade Calculada: {idade} anos\n"
    corpo += f"Token de Validação: {token}\n\n"
    
    corpo += f"=== RESUMO DO SCORE ===\n"
    corpo += f"TOTAL DE SIM: {total_sim}\n"
    corpo += f"TOTAL DE NÃO: {total_nao}\n"
    corpo += f"PONTUAÇÃO FINAL: {pontos} pontos\n"
    corpo += f"RESULTADO: {resultado}\n\n"
    
    corpo += "================ RESPOSTAS ================\n\n"
    for i, pergunta in enumerate(perguntas):
        corpo += f"{pergunta}\n"
        corpo += f"Resposta: {respostas[i]}\n\n"

    msg = MIMEMultipart()
    msg['From'] = SEU_EMAIL
    msg['To'] = "psicologabrunaligoski@gmail.com"
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SEU_EMAIL, SENHA_DO_EMAIL)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

st.set_page_config(page_title="GDS-15", layout="centered")

# Estilização do botão em Azul
st.markdown("""
    <style>
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0047AB !important;
        color: white !important;
        border: none !important;
        padding: 0.6rem 2.5rem !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 16px !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #003380 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

if "avaliacao_concluida" not in st.session_state:
    st.session_state.avaliacao_concluida = False

# Título Centralizado
st.markdown("<h1 style='text-align: center;'>Clínica de Psicologia e Psicanálise Bruna Ligoski</h1>", unsafe_allow_html=True)

# TELA FINAL
if st.session_state.avaliacao_concluida:
    st.success("Avaliação concluída e enviada com sucesso! Muito obrigado(a) pela sua colaboração.")
    st.stop()

# ================= VALIDAÇÃO AUTOMÁTICA DO TOKEN (SEM LOGIN) =================
parametros = st.query_params
token_url = parametros.get("token", None)

if not token_url:
    st.warning("⚠️ Link de acesso inválido. Solicite um novo link à profissional.")
    st.stop()

try:
    registros = planilha.get_all_records()
    dados_token = None
    linha_alvo = 2 
    for i, reg in enumerate(registros):
        if str(reg.get("Token")) == token_url:
            dados_token = reg
            linha_alvo += i
            break
            
    if not dados_token or dados_token.get("Status") != "Aberto":
        st.error("⚠️ Este link é inválido ou já expirou.")
        st.stop()
except Exception:
    st.error("Erro técnico na validação do acesso.")
    st.stop()

# ================= QUESTIONÁRIO GDS-15 =================
linha_fina = "<hr style='margin-top: 8px; margin-bottom: 8px;'/>"
st.markdown(linha_fina, unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center;'>Escala de Depressão Geriátrica (GDS-15)</h3>", unsafe_allow_html=True)
st.markdown(linha_fina, unsafe_allow_html=True)

st.write("Por favor, responda o questionário a seguir de acordo com o modo como se tem sentido durante a última semana.")
st.markdown(linha_fina, unsafe_allow_html=True)

perguntas = [
    "1. Está satisfeito(a) com sua vida?",
    "2. Interrompeu muitas de suas atividades?",
    "3. Acha sua vida vazia?",
    "4. Aborrece-se com frequência?",
    "5. Sente-se bem com a vida na maior parte do tempo?",
    "6. Teme que algo ruim lhe aconteça?",
    "7. Sente-se alegre a maior parte do tempo?",
    "8. Sente-se desamparado(a) com frequência?",
    "9. Prefere ficar em casa a sair e fazer coisas novas?",
    "10. Acha que tem mais problemas de memória que outras pessoas?",
    "11. Acha que é maravilhoso estar vivo(a)?",
    "12. Sente-se inútil?",
    "13. Sente-se cheio(a) de energia?",
    "14. Sente-se sem esperança?",
    "15. Acha que os outros têm mais sorte que você?"
]

opcoes_respostas = ["Sim", "Não"]

with st.form("form_gds"):
    st.subheader("Identificação do(a) Paciente")
    nome_paciente = st.text_input("Nome Completo *")
    data_nasc = st.date_input("Data de Nascimento *", value=None, format="DD/MM/YYYY", min_value=datetime(1900, 1, 1), max_value=datetime.today())
    st.divider()

    respostas_coletadas = {}
    for i, p in enumerate(perguntas):
        st.write(f"**{p}**")
        respostas_coletadas[i] = st.radio(f"q_{i}", opcoes_respostas, index=None, label_visibility="collapsed")
        st.divider()

    st.markdown("<small>Fonte: Yesavage, J.A., et al. (1983). Development and validation of a geriatric depression screening scale.</small>", unsafe_allow_html=True)

    if st.form_submit_button("Enviar Avaliação"):
        if not nome_paciente or data_nasc is None or any(r is None for r in respostas_coletadas.values()):
            st.error("Por favor, preencha todos os campos e responda todas as questões.")
        else:
            hoje = datetime.today().date()
            idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
            
            if enviar_email_resultados(nome_paciente, token_url, data_nasc.strftime("%d/%m/%Y"), idade, perguntas, respostas_coletadas):
                try:
                    planilha.update_cell(linha_alvo, 5, "Respondido")
                    st.session_state.avaliacao_concluida = True
                    st.rerun()
                except:
                    st.session_state.avaliacao_concluida = True
                    st.rerun()
            else:
                st.error("Erro ao enviar. Tente novamente.")
