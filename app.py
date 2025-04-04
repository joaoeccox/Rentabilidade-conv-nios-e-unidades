import streamlit as st
import os
import tempfile

# Importa as bibliotecas para acesso à API do Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def analisar_csv(file_content, tipo, impostos):
    """
    Função para processar o CSV:
      - Decodifica o conteúdo usando 'latin-1'.
      - Separa as linhas e ignora o cabeçalho.
      - Faz split manual usando ';' e converte o valor da segunda coluna.
      - Aplica desconto de 9,86% se 'impostos' for True.
    """
    decoded = file_content.decode('latin-1')
    linhas = decoded.splitlines()
    total = 0.0

    # Pula o cabeçalho (primeira linha)
    for linha in linhas[1:]:
        linha = linha.strip()
        if not linha or "TOTAL" in linha.upper():
            continue
        partes = linha.split(";")
        if len(partes) < 2:
            continue
        try:
            valor_str = partes[1].strip('"').replace(",", ".")
            valor = float(valor_str)
            total += valor
        except Exception as e:
            st.write(f"Erro ao converter '{partes[1]}': {e}")
    if impostos:
        total *= 0.9014  # Aplica o desconto de 9,86%
    return f"Análise: {tipo}\nTotal da produção: R$ {total:.2f}"

def upload_to_drive(file_path, folder_id):
    """
    Função para fazer o upload do arquivo CSV para o Google Drive.
    Utiliza as credenciais da conta de serviço a partir do arquivo JSON.
    """
    try:
        creds = service_account.Credentials.from_service_account_file(
            'rentabilidadeapp-f242aaa02497.json',  # Certifique-se de que o nome está correto
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        raise Exception(f"Erro no upload para o Google Drive: {e}")

# Interface do Streamlit
st.title("App de Rentabilidade - Laboratório João Paulo")
st.write("Envie o arquivo CSV para análise e upload para o Google Drive.")

# Seletor para escolher o tipo de análise
tipo = st.selectbox("Escolha o tipo de análise:", ["Convênio - Produção", "Unidade"])

# Checkbox para definir se deve incluir impostos
impostos = st.checkbox("Incluir impostos no cálculo?", value=True)

# Widget para upload do arquivo CSV
uploaded_file = st.file_uploader("Envie a planilha de produção (.csv)", type="csv")

if uploaded_file is not None:
    st.write("### Preview do arquivo:")
    st.text(uploaded_file.getvalue().decode('latin-1'))
    
    if st.button("Processar e Enviar"):
        # Lê o conteúdo do arquivo em bytes
        file_content = uploaded_file.getvalue()
        
        # Processa o CSV e gera o resultado da análise
        resultado = analisar_csv(file_content, tipo, impostos)
        
        # Salva o arquivo temporariamente para fazer o upload
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        temp_file.write(file_content)
        temp_file.close()
        
        # Define a pasta do Google Drive com base no tipo de análise
        if "convênio" in tipo.lower() or "convenio" in tipo.lower():
            folder_id = "16y9sqf-9vO6GMZVTCS8MnBlVtpAmOPYW"  # Pasta Convênio
        else:
            folder_id = "12zGKH3GKxU4xagjEIj6aLXQzteFIJDFC"  # Pasta Unidade

        # Tenta fazer o upload do arquivo para o Google Drive
        try:
            drive_file_id = upload_to_drive(temp_file.name, folder_id)
            st.success(f"Arquivo enviado com sucesso para o Google Drive! ID do arquivo: {drive_file_id}")
        except Exception as e:
            st.error(str(e))
        
        # Exibe o resultado da análise
        st.write("### Resultado da Análise:")
        st.text(resultado)
        
        # Remove o arquivo temporário
        os.remove(temp_file.name)
