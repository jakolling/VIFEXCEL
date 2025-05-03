import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process

# ======================================
# FUNÇÕES AUXILIARES
# ======================================

def converter_para_excel(dataframe):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='DadosProcessados')
    return buffer.getvalue()

def gerar_link_download(dataframe, nome_arquivo, texto_link):
    dados_excel = converter_para_excel(dataframe)
    b64 = base64.b64encode(dados_excel).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{nome_arquivo}">{texto_link}</a>'

def encontrar_melhor_correspondencia(nome, opcoes, pontuacao_minima=65):
    if not isinstance(nome, str) or not opcoes:
        return None
    
    partes_nome = nome.strip().split()
    if len(partes_nome) < 2:
        return None
    
    primeira_letra = partes_nome[0][0].lower()
    ultimo_nome = partes_nome[-1].lower()
    
    opcoes_filtradas = [
        opcao for opcao in opcoes 
        if isinstance(opcao, str) and 
        len(opcao.split()) > 0 and
        opcao.split()[0][0].lower() == primeira_letra and
        opcao.lower().endswith(ultimo_nome)
    ]
    
    if not opcoes_filtradas:
        opcoes_filtradas = [
            opcao for opcao in opcoes 
            if isinstance(opcao, str) and 
            len(opcao.split()) > 0 and
            opcao.split()[0][0].lower() == primeira_letra
        ]
    
    if opcoes_filtradas:
        melhor_correspondencia = process.extractOne(nome, opcoes_filtradas, scorer=fuzz.token_sort_ratio)
        return melhor_correspondencia[0] if melhor_correspondencia and melhor_correspondencia[1] >= pontuacao_minima else None
    return None

# ======================================
# CONFIGURAÇÃO INICIAL
# ======================================

st.set_page_config(layout="wide", page_title="Ferramenta de Correspondência de Jogadores")
st.title("🔗 Sistema Integrado de Análise de Desempenho")

# ======================================
# GERENCIAMENTO DE ESTADO
# ======================================

estado_padrao = {
    'correspondencias_confirmadas': {},
    'jogadores_rejeitados': set(),
    'historico_acoes': [],
    'jogadores_skillcorner_processados': set(),
    'sugestao_automatica': None,
    'auto_correspondencia': False
}

for chave, valor in estado_padrao.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

# ======================================
# VALIDAÇÃO DE ARQUIVOS
# ======================================

def validar_arquivo_skillcorner(dataframe, tipo_arquivo):
    colunas_necessarias = {'Player'}
    colunas_faltantes = colunas_necessarias - set(dataframe.columns)
    
    if colunas_faltantes:
        st.error(f"❌ Erro crítico: O arquivo {tipo_arquivo} não contém a(s) coluna(s) obrigatória(s): {', '.join(colunas_faltantes)}")
        st.stop()

# ======================================
# INTERFACE DE UPLOAD
# ======================================

coluna_esquerda, coluna_direita = st.columns(2)

with coluna_esquerda:
    arquivo_wyscout = st.file_uploader("Selecione o arquivo WyScout", type=['xlsx', 'xls', 'csv'])

with coluna_direita:
    arquivos_skillcorner = st.file_uploader(
        "Selecione os arquivos SkillCorner (Físico/Pressão)",
        type=['xlsx', 'xls', 'csv'],
        accept_multiple_files=True
    )

# ======================================
# PROCESSAMENTO PRINCIPAL
# ======================================

if arquivo_wyscout and arquivos_skillcorner:
    # Inicialização de DataFrames
    dados_fisicos, dados_pressao = None, None
    
    # Processamento SkillCorner
    for arquivo in arquivos_skillcorner:
        nome_arquivo = arquivo.name.lower()
        
        if 'físico' in nome_arquivo or 'physical' in nome_arquivo:
            dados_fisicos = pd.read_csv(arquivo) if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)
            validar_arquivo_skillcorner(dados_fisicos, "Desempenho Físico")
        
        elif 'pressão' in nome_arquivo or 'overcome' in nome_arquivo:
            dados_pressao = pd.read_csv(arquivo) if arquivo.name.endswith('.csv') else pd.read_excel(arquivo)
            validar_arquivo_skillcorner(dados_pressao, "Superação de Pressão")
    
    # Processamento WyScout
    dados_wyscout = pd.read_csv(arquivo_wyscout) if arquivo_wyscout.name.endswith('.csv') else pd.read_excel(arquivo_wyscout)
    
    # Combinação de jogadores SkillCorner
    lista_jogadores_skillcorner = []
    if dados_fisicos is not None:
        lista_jogadores_skillcorner.extend(dados_fisicos['Player'].dropna().tolist())
    if dados_pressao is not None:
        lista_jogadores_skillcorner.extend(dados_pressao['Player'].dropna().tolist())
    lista_jogadores_skillcorner = list(set(lista_jogadores_skillcorner))
    
    # Listagem de jogadores disponíveis
    jogadores_disponiveis = [
        jogador for jogador in lista_jogadores_skillcorner 
        if jogador not in st.session_state.jogadores_skillcorner_processados
    ]
    
    jogadores_wyscout = [
        jogador for jogador in dados_wyscout['Player'].dropna().unique()
        if jogador not in st.session_state.jogadores_rejeitados and
        jogador not in st.session_state.correspondencias_confirmadas
    ]
    
    # ======================================
    # SELEÇÃO DE MÉTRICAS
    # ======================================
    
    st.markdown("---")
    st.subheader("🔧 Configuração de Métricas")
    
    coluna_metrica1, coluna_metrica2 = st.columns(2)
    metricas_fisicas, metricas_pressao = [], []
    
    with coluna_metrica1:
        if dados_fisicos is not None:
            colunas_fisicas = [coluna for coluna in dados_fisicos.columns if coluna != 'Player']
            metricas_fisicas = st.multiselect(
                "Métricas de Desempenho Físico:",
                colunas_fisicas,
                default=colunas_fisicas
            )
    
    with coluna_metrica2:
        if dados_pressao is not None:
            colunas_pressao = [coluna for coluna in dados_pressao.columns if coluna != 'Player']
            metricas_pressao = st.multiselect(
                "Métricas de Superação de Pressão:",
                colunas_pressao,
                default=colunas_pressao
            )
    
    # ======================================
    # INTERFACE DE CORRESPONDÊNCIA
    # ======================================
    
    st.markdown("---")
    
    if jogadores_wyscout:
        jogador_atual = jogadores_wyscout[0]
        st.subheader(f"🔍 Processando: {jogador_atual}")
        
        if not st.session_state.auto_correspondencia:
            st.session_state.sugestao_automatica = encontrar_melhor_correspondencia(jogador_atual, jogadores_disponiveis)
            st.session_state.auto_correspondencia = True
        
        coluna_selecao, coluna_controles = st.columns([3, 1])
        
        with coluna_selecao:
            indice_selecao = 0
            if st.session_state.sugestao_automatica and st.session_state.sugestao_automatica in jogadores_disponiveis:
                indice_selecao = jogadores_disponiveis.index(st.session_state.sugestao_automatica) + 1
            
            selecao = st.selectbox(
                "Selecione o jogador correspondente:",
                [""] + jogadores_disponiveis,
                index=indice_selecao
            )
        
        with coluna_controles:
            if st.button("✅ Confirmar Correspondência", key="confirmar", disabled=not selecao):
                st.session_state.correspondencias_confirmadas[jogador_atual] = selecao
                st.session_state.jogadores_skillcorner_processados.add(selecao)
                st.session_state.historico_acoes.append(('confirmacao', jogador_atual, selecao))
                st.session_state.auto_correspondencia = False
                st.rerun()
            
            if st.button("❌ Rejeitar Jogador", key="rejeitar"):
                st.session_state.jogadores_rejeitados.add(jogador_atual)
                st.session_state.historico_acoes.append(('rejeicao', jogador_atual, None))
                st.session_state.auto_correspondencia = False
                st.rerun()
            
            if st.button("↩️ Desfazer Última Ação", key="desfazer", disabled=len(st.session_state.historico_acoes) == 0):
                acao, jogador, correspondencia = st.session_state.historico_acoes.pop()
                
                if acao == 'confirmacao':
                    del st.session_state.correspondencias_confirmadas[jogador]
                    st.session_state.jogadores_skillcorner_processados.remove(correspondencia)
                elif acao == 'rejeicao':
                    st.session_state.jogadores_rejeitados.remove(jogador)
                
                st.session_state.auto_correspondencia = False
                st.rerun()
        
        # Barra de progresso
        total_jogadores = len(dados_wyscout['Player'].dropna().unique())
        progresso = len(st.session_state.correspondencias_confirmadas) / total_jogadores
        st.progress(progresso)
        st.caption(f"Progresso: {len(st.session_state.correspondencias_confirmadas)} de {total_jogadores} jogadores processados")
    
    else:
        st.success("🎉 Processamento concluído! Todos os jogadores foram analisados.")
    
    # ======================================
    # EXPORTAÇÃO DE DADOS
    # ======================================
    
    st.markdown("---")
    st.subheader("📤 Exportação de Resultados")
    
    if st.button("Gerar Arquivo Consolidado"):
        dataframe_final = dados_wyscout.copy()
        
        # Adicionar métricas físicas
        if dados_fisicos is not None and metricas_fisicas:
            mapeamento_fisico = dados_fisicos.set_index('Player')[metricas_fisicas]
            dataframe_final = dataframe_final.join(
                dataframe_final['Player'].map(st.session_state.correspondencias_confirmadas).map(mapeamento_fisico)
            )
        
        # Adicionar métricas de pressão
        if dados_pressao is not None and metricas_pressao:
            mapeamento_pressao = dados_pressao.set_index('Player')[metricas_pressao]
            dataframe_final = dataframe_final.join(
                dataframe_final['Player'].map(st.session_state.correspondencias_confirmadas).map(mapeamento_pressao)
            )
        
        # Filtrar apenas correspondências válidas
        dataframe_final = dataframe_final[dataframe_final['Player'].isin(st.session_state.correspondencias_confirmadas.keys())]
        
        # Gerar link de download
        link_download = gerar_link_download(dataframe_final, 'dados_consolidados.xlsx', '⬇️ Baixar Dados Consolidados')
        st.markdown(link_download, unsafe_allow_html=True)

else:
    st.info("📁 Por favor, carregue o arquivo WyScout e pelo menos um arquivo SkillCorner para iniciar o processamento.")
