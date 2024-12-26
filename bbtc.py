import pandas as pd
import mysql.connector
import streamlit as st
import requests

from google.cloud import secretmanager
import gspread
from google.oauth2.service_account import Credentials
import json
from babel.numbers import format_currency


def formatar_moeda(valor):
        return format_currency(valor, 'BRL', locale='pt_BR')

def formatacao_importacao(row):
    styles = [''] * len(row)  # Inicializa com estilos vazios para todas as colunas
    if row['Status_OMIE'] == 'OK':
        styles[row.index.get_loc('Status_OMIE')] = 'background-color: lightgreen; color: green;'
    return styles

def BD_Vendas():
    # Parametros de Login AWS
    config = {
    'user': 'user_automation_jpa',
    'password': 'luck_jpa_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': 'test_phoenix_joao_pessoa'
    }
    # Conexão as Views
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    # Script MySql para requests
    cursor.execute('''
        SELECT 
            Cod_Reserva,
            Nome_Parceiro,
            Canal_de_Vendas,
            Vendedor,
            Nome_Segundo_Vendedor,
            Status_Financeiro,
            Data_Venda,
            Status_do_Servico,
            Valor_Venda,
            Nome_Servico,
            Status_da_Conciliacao
        FROM vw_sales
        ''')
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas o cabecalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e muda o tipo de decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)

    df['Data_Venda'] = pd.to_datetime(df['Data_Venda'], format='%Y-%m-%d', errors='coerce')
    df = df[df['Status_Financeiro'] == 'Pago']
    df = df[df['Status_da_Conciliacao'] == 'Conciliado']
    data_inicio = pd.to_datetime('2024-11-30')
    df = df[df["Data_Venda"] >= data_inicio]

    return df

def consultar_base():
    # GCP project in which to store secrets in Secret Manager.
    project_id = "luckjpa"

    # ID of the secret to create.
    secret_id = "Cred"

    # Create the Secret Manager client.
    secret_client = secretmanager.SecretManagerServiceClient()

    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})

    secret_payload = response.payload.data.decode("UTF-8")

    credentials_info = json.loads(secret_payload)

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Use the credentials to authorize the gspread client
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key('123bfZXeVGLoQrxhPXH9E_cZWJvo5GMHOxWVHP_IgQaE')

    # Select the desired worksheet
    sheet = spreadsheet.worksheet("Base")

    # Get all values from the sheet
    sheet_data = sheet.get_all_values()
    df = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])
    df['valor_documento'] = df['valor_documento'].str.replace(',', '.')
    return df

def lancar_titulo(api_key, app_secret, dados):
    
    url = "https://app.omie.com.br/api/v1/financas/contareceber/"
    
    payload = {
        "call": "IncluirContaReceber",
        "app_key": api_key,
        "app_secret": app_secret,
        "param": [dados]
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        response_data = response.json()

        # Logar o retorno completo para entender o problema
        print("Payload enviado:", json.dumps(payload, indent=4))
        print("Resposta da API:", json.dumps(response_data, indent=4))

        # Verificar se o retorno tem dados que indicam sucesso
        if response.status_code == 200:
            # Conferir se há algum campo que indique sucesso no retorno
            if "codigo_status" in response_data and response_data['codigo_status'] == '0':
                return f"Lançamento Realizado: {response_data.get('descricao_status')}"
            else:
                return f"Erro: {response_data.get('descricao_status', 'Erro desconhecido')}"
        else:
            return f"Erro HTTP: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Erro: {str(e)}"

def lancar_df(df, api_key, app_secret):
    colunas_relevantes = [
        "numero_documento",
        "codigo_lancamento_integracao",
        "codigo_cliente_fornecedor",
        "data_vencimento",
        "valor_documento",
        "codigo_categoria",
        "data_previsao",
        "id_conta_corrente",
        "observacao",
        "status_titulo",
        "codigo_departamento",
        "perc_departamento"
    ]
    
    # Garantir que apenas essas colunas serão usadas
    df = df[colunas_relevantes]

    # Loop para enviar os dados linha por linha
    for _, linha in df.iterrows():
        dados = linha.to_dict()
        distribuicao = [
    {
      "cCodDep": dados.pop("codigo_departamento"),
      "nPerDep": dados.pop("perc_departamento")
    }
        ]
        dados['distribuicao'] = distribuicao
        dados['data_emissao'] = dados['data_vencimento']
        resultado = lancar_titulo(api_key, app_secret, dados)
        if 'Lançamento Realizado' in resultado:
            df.loc[_, 'Status_Migracao'] = 'OK'
        else:
             df.loc[_, 'Status_Migracao'] = ''
        print(f"Lançamento do documento {dados['numero_documento']}: {resultado}")

    return df

def atualizar_historico(df):
    
    project_id = "luckjpa"
    secret_id = "Cred"

    # Create the Secret Manager client.
    secret_client = secretmanager.SecretManagerServiceClient()

    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})

    secret_payload = response.payload.data.decode("UTF-8")

    credentials_info = json.loads(secret_payload)

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    # Use the credentials to authorize the gspread client
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key('123bfZXeVGLoQrxhPXH9E_cZWJvo5GMHOxWVHP_IgQaE')

    # Seleciona a Aba da planilha
    sheet = spreadsheet.worksheet("Base")

    # puxa todos os valores de todas as celulas
    sheet_data = sheet.get('A:N')
    #sheet_data = sheet.get_all_values()

    # joga os valores em dataframe
    df_hist = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

    if 'numero_documento' in df_hist.columns and 'Status_Migracao' in df_hist.columns:
        df_hist['Status_Migracao'] = df_hist['numero_documento'].apply(
            lambda x: 'OK' if x in df['numero_documento'].values else df_hist.loc[df_hist['numero_documento'] == x, 'Status_Migracao'].iloc[0]
        )
    data = [df_hist.columns.values.tolist()] + df_hist.values.tolist()

    # Atualizar a planilha com os dados
    sheet.update('A1', data)

def excluir_conta_receber(app_key, app_secret, df):
    url = 'https://app.omie.com.br/api/v1/financas/contareceber/'
    headers = {'Content-Type': 'application/json'}
    resultados = []

    for codigo in df['codigo_lancamento_omie']:
        payload = {
            'call': 'ExcluirContaReceber',
            'app_key': app_key,
            'app_secret': app_secret,
            'param': [{'chave_lancamento': codigo}]
        }
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json

        codigo_status = response_data.get('codigo_status', 'Erro Desconhecido')
        descricao_status = response_data.get('descricao_status', 'Sem descricao')

        if codigo_status == '0':
            status = 'Excluido'
        else:
            status = 'Erro! Favor Excluir manual'

            resultados.append({'codigo': codigo, 
                               'codigo_status': status,
                               'descricao_status': descricao_status
                               })

    return pd.DataFrame(resultados)

#dados = {'codigo_lancamento_omie': [9924264460, 9924264532, 9924264557]}
#df = pd.DataFrame(dados)
#st.write(df.dtypes)
#app_key = '4160074839921'
#app_secret = '7039eb471a6d2bed119c50a4e9def7b8'

#st.dataframe(df)

#resultado = excluir_conta_receber(app_key, app_secret, df)
#st.write(resultado)

#resultado_df = pd.DataFrame(resultado)
#st.write(resultado_df)





