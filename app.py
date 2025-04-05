import streamlit as st
import os
import tempfile
import pandas as pd
from io import BytesIO
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configurações
CREDENTIALS_FILE = "credentials.json"  # Arquivo de credenciais renomeado
PASTA_UNIDADE_ID = "12zGKH3GKxU4xagjEIj6aLXQzteFIJDFC"
PASTA_CONVENIO_ID = "16y9sqf-9vO6GMZVTCS8MnBlVtpAmOPYW"

def conectar_drive():
    if not os.path.exists(CREDENTIALS_FILE):
        st.error(f"Arquivo de credenciais '{CREDENTIALS_FILE}' não encontrado.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/drive.file"]
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
        # Converte valores para float, tratando vírgula como separador decimal
        df["Bruto Fat."] = df["Bruto Fat."].astype(str).str.replace(",", ".")
        df["Bruto Fat."] = pd.to_numeric(df["Bruto Fat."], errors="coerce")
        total = df["Bruto Fat."].sum()
        return total
    except Exception as e:
        st.error(f"Erro ao calcular faturamento: {e}")
        return 0.0

# Interface do app
st.title("📊 App de Rentabilidade - Laboratório João Paulo")
st.write("Selecione o tipo de produção e escolha um arquivo CSV do Google Drive para análise.")

tipo = st.selectbox("Tipo de Produção", ["Convênio", "Unidade"])

service = conectar_drive()

if service:
    pasta_id = PASTA_CONVENIO_ID if tipo.lower() == "convênio" else PASTA_UNIDADE_ID
    arquivos = listar_arquivos(service, pasta_id)
    
    if arquivos:
        nomes = [f["name"] for f in arquivos]
        selecionado = st.selectbox("Selecione o arquivo CSV", nomes)
        if st.button("Analisar"):
            file_id = next((f["id"] for f in arquivos if f["name"] == selecionado), None)
            if file_id:
                df = baixar_csv(service, file_id)
                if df is not None:
                    st.write("🔍 Prévia dos dados (primeiras 10 linhas):")
                    st.dataframe(df.head(10))
                    total = calcular_faturamento(df)
                    st.success(f"💰 Total da produção (Bruto Fat.): R$ {total:,.2f}")
            else:
                st.error("Arquivo não encontrado.")
    else:
        st.warning("Nenhum arquivo CSV encontrado na pasta selecionada.")
else:
    st.error("Não foi possível conectar ao Google Drive. Verifique as credenciais.")
