import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process

# ===================================================
# FUNÇÕES AUXILIARES
# ===================================================

def converter_dataframe_para_excel(dataframe):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False)
    return buffer.getvalue()

def gerar_link_download(dataframe, nome_arquivo, texto_link):
    dados_excel = converter_dataframe_para_excel(dataframe)
    b64 = base64.b64encode(dados_excel).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{nome_arquivo}">{texto_link}</a>'

def encontrar_melhor_correspondencia(nome_jogador, lista_candidatos, pontuacao_minima=70):
    try:
        if not isinstance(nome_jogador, str) or not lista_candidatos:
            return None
        
        partes_nome = nome_jogador.strip().split()
        if len(partes_nome) < 2:
            return None
        
        primeira_letra = partes_nome[0][0].lower()
        ultimo_nome = partes_nome[-1].lower()
        
        # Primeiro filtro: primeira letra e último nome
        candidatos_filtrados = [
            candidato for candidato in lista_candidatos
            if isinstance(candidato, str) and
            len(candidato.split()) >= 1 and
            candidato.split()[0][0].lower() == primeira_letra and
            candidato.lower().endswith(ultimo_nome)
        ]
        
        # Segundo filtro: apenas primeira letra se o primeiro falhar
        if not candidatos_filtrados:
            candidatos_filtrados = [
                candidato for candidato in lista_candidatos
                if isinstance(candidato, str) and
                len(candidato.split()) >= 1 and
                candidato.split()[0][0].lower() == primeira_letra
            ]
        
        if candidatos_filtrados:
            melhor_match = process.extractOne(nome_jogador, candidatos_filtrados, scorer=fuzz.token_sort_ratio)
            return melhor_match[0] if melhor_match and melhor_match[1] >= pontuacao_minima else None
        
        return None
    except Exception as e:
        st.error(f"Erro na correspondência: {str(e)}")
        return None

# ===================================================
# CONFIGURAÇÃO DA PÁGINA
# ===================================================

st.set_page_config(
    page_title="Sistema de Integração de Dados Esportivos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================================================
# GERENCIAMENTO DE ESTADO DA SESSÃO
# ===================================================

if 'correspondencias_confirmadas' not in st.session_state:
    st.session_state.correspondencias_confirmadas = {}

if 'jogadores_rejeitados' not in st.session_state:
    st.session_state.jogadores_rejeitados = set()

if 'historico_acoes' not in st.session_state:
    st.session_state.historico_acoes = []

if 'jogadores_processados' not in st.session_state:
    st.session_state.jogadores_processados = set()

# ===================================================
# COMPONENTES DE INTERFACE
# ===================================================

st.title("📊 Integrador de Bases de Dados Esportivos")

# Seção de upload de arquivos
with st.expander("📤 Carregamento de Arquivos", expanded=True):
    coluna_esquerda, coluna_direita = st.columns(2)
    
    with coluna_esquerda:
        arquivo_wyscout = st.file_uploader(
            "Selecione o arquivo WyScout (CSV ou Excel)",
            type=['csv', 'xlsx', 'xls']
        )
    
    with coluna_direita:
        arquivos_skillcorner = st.file_uploader(
            "Selecione os arquivos SkillCorner (Physical/Overcome)",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True
        )

# ===================================================
# PROCESSAMENTO PRINCIPAL
# ===================================================

if arquivo_wyscout and arquivos_skillcorner:
    try:
        # Carregar dados WyScout
        if arquivo_wyscout.name.endswith('.csv'):
            df_wyscout = pd.read_csv(arquivo_wyscout)
        else:
            df_wyscout = pd.read_excel(arquivo_wyscout, engine='openpyxl' if arquivo_wyscout.name.endswith('.xlsx') else 'xlrd')
        
        # Verificar estrutura do arquivo WyScout
        if 'Player' not in df_wyscout.columns:
            st.error("Erro: O arquivo WyScout não contém a coluna 'Player'")
            st.stop()
        
        # Carregar dados SkillCorner
        df_physical = None
        df_overcome = None
        
        for arquivo in arquivos_skillcorner:
            if 'physical' in arquivo.name.lower():
                if arquivo.name.endswith('.csv'):
                    df_physical = pd.read_csv(arquivo)
                else:
                    df_physical = pd.read_excel(arquivo, engine='openpyxl' if arquivo.name.endswith('.xlsx') else 'xlrd')
            
            elif 'overcome' in arquivo.name.lower():
                if arquivo.name.endswith('.csv'):
                    df_overcome = pd.read_csv(arquivo)
                else:
                    df_overcome = pd.read_excel(arquivo, engine='openpyxl' if arquivo.name.endswith('.xlsx') else 'xlrd')
        
        # Validar arquivos SkillCorner
        for df, nome in zip([df_physical, df_overcome], ['Physical', 'Overcome']):
            if df is not None and 'Player' not in df.columns:
                st.error(f"Erro: O arquivo {nome} não contém a coluna 'Player'")
                st.stop()
        
        # Combinar jogadores SkillCorner
        jogadores_skillcorner = []
        if df_physical is not None:
            jogadores_skillcorner.extend(df_physical['Player'].dropna().unique().tolist())
        if df_overcome is not None:
            jogadores_skillcorner.extend(df_overcome['Player'].dropna().unique().tolist())
        jogadores_skillcorner = list(set(jogadores_skillcorner))
        
        # Obter lista de jogadores para processar
        jogadores_wyscout = [
            jogador for jogador in df_wyscout['Player'].unique()
            if jogador not in st.session_state.jogadores_rejeitados
            and jogador not in st.session_state.correspondencias_confirmadas
        ]
        
        # Seção de correspondência
        if jogadores_wyscout:
            jogador_atual = jogadores_wyscout[0]
            
            with st.container():
                st.subheader(f"🔍 Correspondência para: {jogador_atual}")
                
                # Encontrar correspondência sugerida
                correspondencia_sugerida = encontrar_melhor_correspondencia(
                    jogador_atual,
                    [j for j in jogadores_skillcorner if j not in st.session_state.jogadores_processados]
                )
                
                # Interface de seleção
                coluna_selecao, coluna_controles = st.columns([3, 1])
                
                with coluna_selecao:
                    opcoes = [""] + [j for j in jogadores_skillcorner if j not in st.session_state.jogadores_processados]
                    indice_padrao = opcoes.index(correspondencia_sugerida) + 1 if correspondencia_sugerida in opcoes else 0
                    selecao = st.selectbox(
                        "Selecione o jogador correspondente:",
                        options=opcoes,
                        index=indice_padrao
                    )
                
                with coluna_controles:
                    # Botão de confirmação
                    if st.button("✅ Confirmar", help="Confirma a correspondência selecionada"):
                        if selecao:
                            st.session_state.correspondencias_confirmadas[jogador_atual] = selecao
                            st.session_state.jogadores_processados.add(selecao)
                            st.session_state.historico_acoes.append(('confirmacao', jogador_atual, selecao))
                            st.rerun()
                    
                    # Botão de rejeição
                    if st.button("❌ Rejeitar", help="Rejeita o jogador atual"):
                        st.session_state.jogadores_rejeitados.add(jogador_atual)
                        st.session_state.historico_acoes.append(('rejeicao', jogador_atual, None))
                        st.rerun()
                    
                    # Botão de desfazer
                    if st.button("↩️ Desfazer", disabled=not st.session_state.historico_acoes):
                        ultima_acao = st.session_state.historico_acoes.pop()
                        if ultima_acao[0] == 'confirmacao':
                            del st.session_state.correspondencias_confirmadas[ultima_acao[1]]
                            st.session_state.jogadores_processados.remove(ultima_acao[2])
                        elif ultima_acao[0] == 'rejeicao':
                            st.session_state.jogadores_rejeitados.remove(ultima_acao[1])
                        st.rerun()
                
                # Exibir progresso
                progresso = len(st.session_state.correspondencias_confirmadas) / len(df_wyscout['Player'].unique())
                st.progress(progresso)
                st.caption(f"Progresso: {len(st.session_state.correspondencias_confirmadas)} de {len(df_wyscout['Player'].unique())} jogadores processados")
        
        else:
            st.success("✅ Todos os jogadores foram processados com sucesso!")
        
        # Seção de exportação
        with st.expander("📥 Exportação de Dados", expanded=False):
            if st.button("Gerar Arquivo Final"):
                df_final = df_wyscout.copy()
                
                # Adicionar dados físicos
                if df_physical is not None:
                    df_fisico = df_physical.rename(columns={'Player': 'Correspondencia'})
                    df_final = pd.merge(
                        df_final,
                        df_fisico,
                        left_on='Player',
                        right_on='Correspondencia',
                        how='left'
                    ).drop(columns=['Correspondencia'])
                
                # Adicionar dados de pressão
                if df_overcome is not None:
                    df_pressao = df_overcome.rename(columns={'Player': 'Correspondencia'})
                    df_final = pd.merge(
                        df_final,
                        df_pressao,
                        left_on='Player',
                        right_on='Correspondencia',
                        how='left'
                    ).drop(columns=['Correspondencia'])
                
                # Filtrar apenas correspondências confirmadas
                df_final = df_final[df_final['Player'].isin(st.session_state.correspondencias_confirmadas.keys())]
                
                # Gerar link de download
                st.markdown(gerar_link_download(df_final, 'dados_integrados.xlsx', '⬇️ Baixar Arquivo Consolidado'), unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Erro crítico no processamento: {str(e)}")
        st.stop()

else:
    st.info("ℹ️ Por favor, carregue todos os arquivos necessários para iniciar o processamento.")

# ===================================================
# SEÇÃO DE DIAGNÓSTICO
# ===================================================

with st.expander("🔧 Ferramentas de Diagnóstico", expanded=False):
    if st.button("Exibir Estado Atual"):
        st.write("Correspondências Confirmadas:", st.session_state.correspondencias_confirmadas)
        st.write("Jogadores Rejeitados:", st.session_state.jogadores_rejeitados)
        st.write("Histórico de Ações:", st.session_state.historico_acoes)
    
    if st.button("🔄 Reiniciar Sistema", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
