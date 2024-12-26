import streamlit as st
import pandas as pd
from bbtc import BD_Vendas, formatacao_importacao, consultar_base, formatar_moeda, lancar_df, atualizar_historico, excluir_conta_receber
from dados_omie import dados_receber, atualizar_base
import time


st.set_page_config(layout='wide')

df_atualizar_dados = dados_receber()
atualizar_base(df_atualizar_dados)


if 'df' not in st.session_state:
    with st.spinner('Carregando dados do Phoenix...'):
        st.session_state.df = BD_Vendas()
df = st.session_state.df

if 'df_historico' not in st.session_state:
    with st.spinner('Carregando Historico do OMIE...'):
        st.session_state.df_base_dados = consultar_base()
df_historico = st.session_state.df_base_dados

if 'atualizar_omie_clicado' not in st.session_state:
    st.session_state.atualizar_omie_clicado = False

if "reload_page" not in st.session_state:
    st.session_state.reload_page = False

#
vendedores = [
    "ITALO - GUIA",
    "NATHAN - GUIA",
    "NATALIA - GUIA",
    "PALOMA - GUIA",
    "DUARTE - GUIA",
    "SORAYA - BASE AEROPORTO ",
    "LETICIA - PDV",
    "RAQUEL - PDV",
    'ANA - VENDAS ONLINE',
    'RAIRLA - VENDAS ONLINE',
    'MELO - VENDAS ONLINE',
    'LUCAS - VENDAS ONLINE',
    'NATY - VENDAS ONLINE'
]


lista_vendedor = df[df['Vendedor'].isin(vendedores)]
lista_vendedor = lista_vendedor['Vendedor'].unique().tolist()
lista_vendedor.sort()

col01, col02 = st.columns([8, 2])
with col01:
    st.title('Migrar Dados Empresas - OMIE')
with col02: 
    atualizar_omie = st.button('Atualizar Base OMIE')
    if atualizar_omie:
        st.session_state.atualizar_omie_clicado = True

    if st.session_state.atualizar_omie_clicado:
        with col01:
            with st.spinner('Buscando Dados...'):
                my_bar = st.progress(0, text='Carregando Dados')
                total_steps = 3
                
                my_bar.progress(40, text=f'Carregando... 40% concluido')
                df_atualizar_dados = dados_receber()
                
            
                my_bar.progress(80, text=f'Carregando... 80% concluido')
                atualizar_base(df_atualizar_dados)

                time.sleep(2)
                my_bar.progress(100, text=f'Carregando... 100% concluido')
                
                st.session_state.atualizar_omie_clicado = False
                my_bar.empty()
        



selecao_vendedor = st.multiselect('Selecione o Vendedor para Migrar os dados:', options=lista_vendedor, default=[], key='mig_0001')

#DataFrame filtrado apenas com vendedor
df_filtrado = df[df['Vendedor'].isin(selecao_vendedor)]

#Verifica apenas as colunas necessarias
df_filtrado = df_filtrado[['Cod_Reserva', 'Vendedor', 'Valor_Venda', 'Status_Financeiro']]

#Agrupa para o usuario verificar apenas as reservas e o valor de cada uma delas
df_filtrado = df_filtrado.groupby(['Cod_Reserva', 'Vendedor'], as_index=False).agg({
    'Cod_Reserva': 'first',
    'Vendedor': 'first',
    'Valor_Venda': 'sum'
})

#Cria o Status do Omie
df_filtrado['Status_OMIE'] = ''

# Remover duplicados de df_historico para mostrar apenas uma reserva e não as parcelas
df_historico_comparar = df_historico.drop_duplicates(subset='numero_documento')

# Atualizar a coluna 'Status_OMIE' em df_filtrado com base na correspondência entre 'Cod_Reserva' e 'numero_documento'
df_filtrado['Status_OMIE'] = df_filtrado['Cod_Reserva'].map(
    df_historico_comparar.set_index('numero_documento')['Status_Migracao']
)
df_filtrado['Status_OMIE'] = df_filtrado['Status_OMIE'].fillna('')
df_print = df_filtrado
df_print['Valor_Venda'] = df_print['Valor_Venda'].apply(formatar_moeda)

df_print = df_print.style.apply(formatacao_importacao, axis=1)

status_lista = {
    'OK': 'Baixado',
    '': 'A Baixar'
}

df_filtrado_lista_reserva = df_filtrado[df_filtrado['Status_OMIE'] == '']
lista_reserva = df_filtrado_lista_reserva['Cod_Reserva'].unique().tolist()
lista_reserva.sort()

selecao_reserva = st.multiselect('Selecione as Reservas para Importação:', options=lista_reserva, default=[], key='mig_0002')

col1, col2 = st.columns([8, 4])

exibir_status = False
mostrar_botao = False
status_selecionado = None 

with col2:
    if selecao_vendedor:
        selecao_status = st.radio('Selecione o Status a Filtrar', options=list(status_lista.values()), index= None)

        if selecao_status:
            exibir_status = True
            status_selecionado = {v: k for k, v in status_lista.items()}[selecao_status]

        if status_selecionado == '':
            mostrar_botao = True


with col1:
    if exibir_status:
        if not selecao_reserva:
            df_print_status = df_filtrado[df_filtrado['Status_OMIE'] == status_selecionado]
        else:
            df_print_status = df_filtrado[
                (df_filtrado['Status_OMIE'] == status_selecionado) & 
                (df_filtrado['Cod_Reserva'].isin(selecao_reserva))
            ]
            
            
        # FAZER UMA NOVA LISTA DAS RESERVAS


        st.session_state['df_print_status'] = df_print_status
        df_print_status1 = st.session_state['df_print_status'].style.apply(formatacao_importacao, axis=1)
        st.dataframe(df_print_status1, hide_index=True, use_container_width=True)
    else:
        st.dataframe(df_print, hide_index=True, use_container_width=True)


if 'avancar' not in st.session_state:
    st.session_state['avancar'] = False

if 'empresa_selecionada' not in st.session_state:
    st.session_state['empresa_selecionada'] = None

if mostrar_botao and not st.session_state['avancar']:
    botao_migrar = st.button('Avançar')

    if botao_migrar:
        st.session_state['avancar'] = True
    
if st.session_state['avancar']:
    api_empresa = st.radio('Selecione a Empresa do Lançamento', ['Luck Conde', 'Tour Azul'], index=0)
    st.session_state['empresa_selecionada'] = api_empresa

    if api_empresa == 'Luck Conde':
        app_key = '4162934503728'
        app_secret = 'b0bdf05dfc25d028b4e8ee29d140d966'
        colunas = ['numero_documento','codigo_lancamento_integracao','codigo_cliente_conde', 'data_vencimento', 'valor_documento','codigo_categoria','data_previsao','id_conta_corrente_luck','observacao','status_titulo','codigo_departamento_luck', 'perc_departamento','Status_Migracao','codigo_lancamento_omie']
    elif api_empresa == 'Tour Azul':
        app_key = '4160074839921'
        app_secret = '7039eb471a6d2bed119c50a4e9def7b8'
        colunas = ['numero_documento','codigo_lancamento_integracao','codigo_cliente_rec','data_vencimento','valor_documento','codigo_categoria','data_previsao','id_conta_corrente_rec', 'observacao','status_titulo','codigo_departamento_rec','perc_departamento','Status_Migracao', 'codigo_lancamento_omie']

    st.session_state['app_key'] = app_key
    st.session_state['app_secret'] = app_secret
    st.session_state['colunas'] = colunas

    botao_migrar2 = st.button('Migrar Dados')

    if botao_migrar2:

        df_final = df_historico[df_historico['numero_documento'].isin(df_print_status['Cod_Reserva'])]
        df_final = df_final[st.session_state['colunas']]
        rename_dict = {}
        if 'codigo_cliente_conde' in df_final.columns:
            rename_dict['codigo_cliente_conde'] = 'codigo_cliente_fornecedor'
        if 'codigo_cliente_rec' in df_final.columns:
            rename_dict['codigo_cliente_rec'] = 'codigo_cliente_fornecedor'
        if 'id_conta_corrente_luck' in df_final.columns:
            rename_dict['id_conta_corrente_luck'] = 'id_conta_corrente'
        if 'id_conta_corrente_rec' in df_final.columns:
            rename_dict['id_conta_corrente_rec'] = 'id_conta_corrente'
        if 'codigo_departamento_luck' in df_final.columns:
            rename_dict['codigo_departamento_luck'] = 'codigo_departamento'
        if 'codigo_departamento_rec' in df_final.columns:
            rename_dict['codigo_departamento_rec'] = 'codigo_departamento'

        df_final = df_final.rename(columns=rename_dict)
        retorno = lancar_df(df_final, st.session_state['app_key'], st.session_state['app_secret'])
        st.dataframe(retorno)
        with st.status('Migrando dados para OMIE... Aguarde!'):
            time.sleep(10)
        fim = atualizar_historico(retorno)
        depurar_sucesso = st.success('Concluido')
        st.dataframe(fim)
        #st.dataframe(df_final)
        #st.rerun()



#        if 'botao_excluir' not in st.session_state:
#            st.session_state['botao_excluir'] = False
#        if 'resultado_exclusao' not in st.session_state:
#            st.session_state['resultado_exclusao'] = None

#        if depurar_sucesso:
#            botao_excluir = st.button('Excluir Titulos da Roger')

#            if botao_excluir:
#                st.session_state['botao_excluir'] = True
        
#        if st.session_state['botao_excluir']:
#            app_key_roger = "4160082506580"
#            app_secret_roger = "d57cab7f7d1186dbd6b0fa2d11d49877"

#            df_excluir = df_final[['codigo_lancamento_omie']]
                
#            st.session_state['resultado_exclusao'] = excluir_conta_receber(app_key_roger, app_secret_roger, df_excluir)
#            st.session_state['botao_excluir'] = False

#            if st.session_state['resultado_exclusao'] is not None:
#                st.dataframe(st.session_state['resultado_exclusao'])



        
        



       





#LUCK CONDE
# CATEGORIA ROGER
# CATEGORIA LUCK CONDE - "1.01.02"
# DEPARTAMENTO ROGER
# DEPARTAMENTO LUCK CONDE - "7333847088"
# CLIENTE FORNEDCEDOR ROGER
# CLIENTE FORNECEDOR LUCK CONDE -  7337052816 - VERIFICAR CNPJ
# CONTA CORRENTE ROGER
# CONTA CORRENTE LUCK CONDE - OK

# APP KEY - 4162934503728
# APP SECRET - b0bdf05dfc25d028b4e8ee29d140d966


#REC
# CATEGORIA ROGER
# CATEGORIA REC - "1.01.02"
# DEPARTAMENTO ROGER
# DEPARTAMENTO REC - "9793128959",
# CLIENTE FORNEDCEDOR ROGER
# CLIENTE FORNECEDOR REC -  9796866782 - VERIFICAR CNPJ
# CONTA CORRENTE ROGER
# CONTA CORRENTE REC - OK

# APP KEY - 4160074839921
# APP SECRET - 7039eb471a6d2bed119c50a4e9def7b8