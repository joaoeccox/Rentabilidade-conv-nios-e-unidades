import streamlit as st
import pandas as pd
import os
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# CONFIGURAÇÕES
CREDENTIALS_FILE = "credentials.json"  # Arquivo de credenciais na raiz
PASTA_UNIDADE_ID = "12zGKH3GKxU4xagjEIj6aLXQzteFIJDFC"
PASTA_CONVENIO_ID = "16y9sqf-9vO6GMZVTCS8MnBlVtpAmOPYW"

def conectar_drive():
    if not os.path.exists(CREDENTIALS_FILE):
        st.error(f"Arquivo de credenciais '{CREDENTIALS_FILE}' não encontrado.")
        return None
    try:
        # Alteramos o escopo para acesso completo ao Drive
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        st.error(f"Erro ao conectar ao Google Drive: {e}")
        return None

def listar_arquivos(service, folder_id):
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='text/csv'",
            pageSize=100,
            fields="files(id, name)"
        ).execute()
        return results.get("files", [])
    except Exception as e:
        st.error(f"Erro ao listar arquivos: {e}")
        return []

def baixar_csv(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh, sep=";", encoding="latin1")
        return df
    except Exception as e:
        st.error(f"Erro ao baixar arquivo: {e}")
        return None

def calcular_faturamento(df):
    if "Bruto Fat." not in df.columns:
        st.warning("Coluna 'Bruto Fat.' não encontrada no CSV.")
        return 0.0
    try:
        df["Bruto Fat."] = df["Bruto Fat."].astype(str).str.replace(",", ".")
        df["Bruto Fat."] = pd.to_numeric(df["Bruto Fat."], errors="coerce")
        total = df["Bruto Fat."].sum()
        return total
    except Exception as e:
        st.error(f"Erro ao calcular faturamento: {e}")
        return 0.0

# Interface do App
st.title("📊 App de Rentabilidade - Laboratório João Paulo")
st.write("Selecione o tipo de análise, insira a alíquota de impostos (se aplicável) e escolha um arquivo CSV do Google Drive para análise.")

# Seleção do tipo de análise
tipo = st.selectbox("Tipo de Análise", ["Convênio Produção", "Convênio Tabela", "Unidade"])

# Caixa de texto para inserir alíquota de impostos (em %)
aliquota_input = st.text_input("Digite a alíquota de impostos (%) (deixe vazio para não aplicar)", value="9.86")
try:
    aliquota = float(aliquota_input) / 100 if aliquota_input.strip() != "" else 0.0
except Exception:
    st.error("Alíquota de impostos inválida.")
    aliquota = 0.0

service = conectar_drive()

if service:
    # Seleciona a pasta com base no tipo de análise
    if tipo.lower().startswith("convênio"):
        pasta_id = PASTA_CONVENIO_ID
    else:
        pasta_id = PASTA_UNIDADE_ID

    arquivos = listar_arquivos(service, pasta_id)
    
    if arquivos:
        nomes = [arquivo["name"] for arquivo in arquivos]
        selecionado = st.selectbox("Selecione o arquivo CSV", nomes)
        if st.button("Analisar"):
            file_id = next((arquivo["id"] for arquivo in arquivos if arquivo["name"] == selecionado), None)
            if file_id:
                df = baixar_csv(service, file_id)
                if df is not None:
                    st.subheader("Prévia dos dados (Primeiras 10 Linhas):")
                    st.dataframe(df.head(10))
                    total = calcular_faturamento(df)
                    if aliquota > 0:
                        total_com_impostos = total * (1 - aliquota)
                        st.success(f"Total da produção sem impostos: R$ {total_com_impostos:,.2f}")
                    else:
                        st.success(f"Total da produção: R$ {total:,.2f}")
            else:
                st.error("Arquivo não encontrado.")
    else:
        st.warning("Nenhum arquivo CSV encontrado na pasta selecionada.")
else:
    st.error("Não foi possível conectar ao Google Drive. Verifique as credenciais.")
