import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process

# ===================================================
# FUNÇÕES AUXILIARES (ATUALIZADAS)
# ===================================================

def ler_arquivo_excel_com_verificacao(arquivo):
    """Função robusta para ler arquivos Excel com tratamento de erros"""
    try:
        if arquivo.name.endswith('.xlsx'):
            df = pd.read_excel(arquivo, engine='openpyxl')
        elif arquivo.name.endswith('.xls'):
            df = pd.read_excel(arquivo, engine='xlrd')
        else:
            st.error("Formato de arquivo não suportado")
            return None

        # Verificação avançada de estrutura
        df.columns = df.columns.str.strip().str.lower()
        if 'player' not in df.columns:
            st.error("ERRO: Coluna 'Player' não encontrada após normalização")
            st.write("Colunas detectadas:", df.columns.tolist())
            return None
            
        return df

    except Exception as e:
        st.error(f"Falha crítica na leitura do arquivo: {str(e)}")
        return None

# ===================================================
# MELHORIAS ADICIONADAS PARA TRATAMENTO DE DADOS
# ===================================================

def normalizar_nomes(nome):
    """Padroniza nomes para comparação segura"""
    return str(nome).strip().lower()

def verificar_duplicatas(df, coluna='player'):
    """Identifica valores duplicados problemáticos"""
    duplicatas = df[coluna][df[coluna].duplicated()].unique()
    if len(duplicatas) > 0:
        st.warning(f"Valores duplicados encontrados na coluna {coluna}: {duplicatas}")

# ===================================================
# INTERFACE E LÓGICA PRINCIPAL (ATUALIZADA)
# ===================================================

def main():
    st.set_page_config(page_title="Integrador de Dados Esportivos", layout="wide")
    st.title("📊 Sistema Integrado de Análise")

    # Upload de arquivos com verificação estendida
    with st.expander("🔽 Carregar Arquivos", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            wyscout_file = st.file_uploader("Arquivo WyScout", type=['xlsx', 'xls', 'csv'])
        with col2:
            skillcorner_files = st.file_uploader("Arquivos SkillCorner", type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)

    # Processamento principal com tratamento de erros
    if wyscout_file and skillcorner_files:
        try:
            # Leitura e verificação do arquivo WyScout
            if wyscout_file.name.endswith('.csv'):
                df_wyscout = pd.read_csv(wyscout_file, encoding_errors='replace')
            else:
                df_wyscout = ler_arquivo_excel_com_verificacao(wyscout_file)
            
            if df_wyscout is None:
                st.error("Falha ao ler arquivo WyScout")
                return

            df_wyscout['player'] = df_wyscout['player'].apply(normalizar_nomes)
            verificar_duplicatas(df_wyscout)

            # Leitura dos arquivos SkillCorner
            dfs_skillcorner = []
            for file in skillcorner_files:
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file, encoding_errors='replace')
                else:
                    df = ler_arquivo_excel_com_verificacao(file)
                
                if df is not None:
                    df['player'] = df['player'].apply(normalizar_nomes)
                    verificar_duplicatas(df)
                    dfs_skillcorner.append(df)

            if not dfs_skillcorner:
                st.error("Nenhum arquivo SkillCorner válido foi carregado")
                return

            # DEBUG: Exibir estrutura dos dados
            with st.expander("🔍 Visualização dos Dados Carregados"):
                st.write("WyScout Head:", df_wyscout.head())
                for i, df in enumerate(dfs_skillcorner):
                    st.write(f"SkillCorner {i+1} Head:", df.head())

            # Restante da lógica de correspondência...

        except Exception as e:
            st.error(f"Erro no processamento: {str(e)}")
            st.write("Dica: Verifique a consistência dos formatos de dados entre os arquivos")

    # Seção de diagnóstico avançado
    with st.expander("⚙️ Ferramentas de Diagnóstico"):
        if st.button("Executar Verificação Completa"):
            # Verificação de versões de bibliotecas
            st.write("Versões críticas:")
            st.write(f"- Pandas: {pd.__version__}")
            st.write(f"- Openpyxl: {pd.util._get_version('openpyxl')}")
            st.write(f"- Xlrd: {pd.util._get_version('xlrd')}")

if __name__ == "__main__":
    main()
