import requests
import pandas as pd
from datetime import datetime, timedelta

from google.cloud import secretmanager
import gspread
from google.oauth2.service_account import Credentials
import json

# Suas credenciais da API OMIE
APP_KEY = "4160082506580"
APP_SECRET = "d57cab7f7d1186dbd6b0fa2d11d49877"
data_inicio = (datetime.now() - timedelta(days=20)).strftime('%d/%m/%Y')
data_hoje = (datetime.now() + timedelta(days=365)).strftime('%d/%m/%Y')

# URL da API
URL = "https://app.omie.com.br/api/v1/financas/contareceber/"

def listar_todas_contas_receber(app_key, app_secret):
    registros_por_pagina = 500  # Máximo permitido por página
    todas_contas = []  # Lista para armazenar todos os registros
    npagina = 1  # Página inicial
    total_paginas = None  # Será definido na primeira iteração

    while True:
        # Parâmetros para a requisição
        payload = {
            "call": "ListarContasReceber",
            "app_key": app_key,
            "app_secret": app_secret,
            "param": [
                {
                    "pagina": npagina,
                    "registros_por_pagina": registros_por_pagina,
                    "apenas_importado_api": "S",
                    "exibir_obs": "S",
                    "filtrar_por_data_de": data_inicio,
                    "filtrar_por_data_ate": data_hoje,
                    "filtrar_apenas_inclusao": "N",
                    "filtrar_apenas_alteracao": "N"
                }
            ]
        }
        headers = {
            'Content-Type': 'application/json'
        }

        try:
            # Enviando a requisição para a API
            response = requests.post(URL, headers=headers, json=payload)

            # Verificando o status da requisição
            if response.status_code == 200:
                # Convertendo a resposta em JSON
                data = response.json()

                # Depuração: Verificando a estrutura do JSON retornado
                print(f"Resposta da página {npagina}:")
                #print(data)

                # Atualizando o total de páginas na primeira iteração
                if total_paginas is None:
                    total_registros = data.get('total_de_registros', 0)
                    total_paginas = (total_registros // registros_por_pagina) + (1 if total_registros % registros_por_pagina > 0 else 0)
                    print(f"Total de Registros: {total_registros}")
                    print(f"Total de Páginas: {total_paginas}")

                # Verificando se a chave 'contas_receber_cadastro' existe no JSON
                if "conta_receber_cadastro" not in data:
                    print(f"Erro: Chave 'conta_receber_cadastro' não encontrada na resposta da página {npagina}.")
                    break

                # Obtendo os registros
                contas_receber = data.get("conta_receber_cadastro", [])
                print(f"Página {npagina}: {len(contas_receber)} registros encontrados")

                # Adicionando registros ao acumulador
                if contas_receber:
                    for conta in contas_receber:
                        todas_contas.append({
                            "numero_documento": conta.get("numero_documento", ""),
                            "codigo_lancamento_integracao": conta.get("codigo_lancamento_integracao", ""),
                            "codigo_cliente_fornecedor": conta.get("codigo_cliente_fornecedor", ""),
                            "data_vencimento": conta.get("data_vencimento", ""),
                            "valor_documento": conta.get("valor_documento", ""),
                            "codigo_categoria": conta.get("codigo_categoria", ""),
                            "data_previsao": conta.get("data_previsao", ""),
                            "id_conta_corrente": conta.get("id_conta_corrente", ""),
                            "observacao": conta.get("observacao", ""),
                            "status_titulo": conta.get("status_titulo", ""),
                            "codigo_departamento": 3516953137,
                            "perc_departamento": 100,
                            "Status_Migracao": "",
                            "codigo_lancamento_omie": conta.get("codigo_lancamento_omie","")
                        })

                # Verificando se todas as páginas foram processadas
                if npagina >= total_paginas:
                    print("Todas as páginas foram processadas.")
                    break

                # Incrementar a página
                npagina += 1

            else:
                print(f"Erro na requisição: {response.status_code}")
                print(response.text)
                break

        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            break

    return todas_contas

def dados_receber():
    # Executando a função e listando as contas
    todas_contas = listar_todas_contas_receber(APP_KEY, APP_SECRET)

    # Processando os dados em um DataFrame com as colunas desejadas
    if todas_contas:
        print(f"Total de registros processados: {len(todas_contas)}")
        df_contas = pd.DataFrame(todas_contas)
        df_contas = df_contas[df_contas['codigo_categoria'] == '1.01.02']
        df_contas = df_contas[df_contas['codigo_cliente_fornecedor'] == 3508914982]

        return df_contas
    else:

        return "Nenhuma conta a receber encontrada."

def atualizar_base(df):
    
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
    df_novos_reg = df[~df['numero_documento'].isin(df_hist['numero_documento'])]

    df_geral = pd.concat([df_hist, df_novos_reg], ignore_index=True)

    data = [df_geral.columns.values.tolist()] + df_geral.values.tolist()

    # Atualizar a planilha com os dados
    sheet.update('A1', data)


#df_omie = dados_receber()

#atualizar_base(df_omie)




