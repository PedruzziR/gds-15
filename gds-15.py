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
    return client.open("GDS-15").sheet1  # Aponta para a nova planilha

try:
    planilha = conectar_planilha()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()
# =============================================================

def enviar_email_resultados(nome, cpf, data_nasc, idade, perguntas, respostas):
    assunto = f"Resultados GDS-15 - Paciente: {nome}"
    
    corpo = f"Avaliação GDS-15 concluída.\n\n"
    corpo += f"=== DADOS DO(A) PACIENTE ===\n"
    corpo += f"Nome Completo: {nome}\n"
    corpo += f"Data de Nascimento: {data_nasc}\n"
    corpo += f"CPF (Login): {cpf}\n"
    corpo += f"Idade Calculada: {idade} anos\n\n"
    corpo += "================ RESULTADOS ================\n\n"
    
    # Adiciona cada pergunta e a resposta do paciente logo abaixo
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

if "logado" not in st.session_state:
    st.session_state.logado = False
if "avaliacao_concluida" not in st.session_state:
    st.session_state.avaliacao_concluida = False

st.title("Clínica de Psicologia e Psicanálise Bruna Ligoski")

# ================= TELA DE LOGIN =================
if not st.session_state.logado:
    st.write("Bem-vindo(a) à Avaliação GDS-15.")
    
    with st.form("form_login"):
        cpf_input = st.text_input("CPF do Paciente (Apenas números)")
        senha_input = st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            if senha_input == st.secrets["SENHA_MESTRA"]:
                try:
                    cpfs = planilha.col_values(1)
                except:
                    cpfs = []
                if cpf_input in cpfs:
                    st.error("Acesso bloqueado. CPF já registrado.")
                else:
                    st.session_state.logado = True
                    st.session_state.cpf_paciente = cpf_input
                    st.rerun()
            else:
                st.error("Senha incorreta.")

# ================= TELA FINAL =================
elif st.session_state.avaliacao_concluida:
    st.success("Avaliação concluída e enviada com sucesso! Muito obrigado pela sua colaboração.")

# ================= QUESTIONÁRIO GDS-15 =================
else:
    st.write("### GDS-15")
    st.write("Por favor, responda o questionário a seguir de acordo com o modo como se tem sentido durante a última semana.")
    st.divider()
    
    perguntas = [
        "1. Está satisfeito(a) com sua vida?",
        "2. Interrompeu muitas de suas atividades?",
        "3. Acha sua vida vazia?",
        "4. Aborrece-se com frequência?",
        "5. Sente-se bem com a vida na maior parte do tempo?",
        "6. Teme que algo ruim lhe aconteça?",
        "7. Sente-se alegre a maior parte do tempo?",
        "8. Sente-se desamparado com frequência?",
        "9. Prefere ficar em casa a sair e fazer coisas novas?",
        "10. Acha que tem mais problemas de memória que outras pessoas?",
        "11. Acha que é maravilhoso estar vivo(a)?",
        "12. Sente-se inútil?",
        "13. Sente-se cheio(a) de energia?",
        "14. Sente-se sem esperança?",
        "15. Acha que os outros têm mais sorte que você?"
    ]

    opcoes_respostas = ["Sim", "Não"]

    with st.form("formulario_avaliacao"):
        st.subheader("Identificação do Paciente")
        nome_paciente = st.text_input("Nome Completo *")
        
        # Calendário iniciando em branco (value=None)
        data_nasc = st.date_input("Data de Nascimento *", value=None, format="DD/MM/YYYY", min_value=datetime(1900, 1, 1), max_value=datetime.today())
        st.divider()

        respostas_coletadas = {}
        for i, p in enumerate(perguntas):
            st.write(f"**{p}**")
            respostas_coletadas[i] = st.radio(f"q_{i}", opcoes_respostas, index=None, label_visibility="collapsed")
            st.write("---")

        if st.form_submit_button("Finalizar"):
            # Validação: verifica se nome e data foram preenchidos e se todas as 15 perguntas têm resposta
            if not nome_paciente or data_nasc is None or any(r is None for r in respostas_coletadas.values()):
                st.error("Preencha todos os campos e responda todas as questões.")
            else:
                hoje = datetime.today().date()
                idade = hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))
                
                # Envia o e-mail passando a lista de perguntas e o dicionário de respostas
                if enviar_email_resultados(nome_paciente, st.session_state.cpf_paciente, data_nasc.strftime("%d/%m/%Y"), idade, perguntas, respostas_coletadas):
                    try:
                        planilha.append_row([st.session_state.cpf_paciente])
                    except:
                        pass
                    st.session_state.avaliacao_concluida = True
                    st.rerun()
                else:
                    st.error("Houve um erro no envio. Avise a profissional responsável.")
