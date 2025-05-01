import streamlit as st  
import pandas as pd  
import numpy as np  
from difflib import SequenceMatcher  
from io import BytesIO  
import unicodedata  
  
# Função para pré-processar nomes  
def preprocess_name(name):  
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')  
    name = name.lower().strip()  
    return name  
  
# Função para calcular a similaridade entre dois nomes usando SequenceMatcher  
def name_similarity(a, b):  
    return SequenceMatcher(None, a, b).ratio()  
  
# Função para encontrar o melhor match entre um nome e uma lista de candidatos  
def find_best_match(name, candidates, threshold=0.7):  
    norm_name = preprocess_name(name)  
    matches = [(cand, name_similarity(norm_name, preprocess_name(cand))) for cand in candidates]  
    best_match = max(matches, key=lambda x: x[1])  
    return best_match[0] if best_match[1] >= threshold else None  
  
# Função para carregar os datasets via upload  
def load_data():  
    wyscout_file = st.file_uploader("Carregar arquivo WyScout (CSV ou Excel)", type=["csv", "xlsx"], key="wyscout")  
    skillcorner_file = st.file_uploader("Carregar arquivo SkillCorner (CSV ou Excel)", type=["csv", "xlsx"], key="skillcorner")  
      
    df_wyscout = None  
    df_skillcorner = None  
      
    try:  
        if wyscout_file is not None:  
            if wyscout_file.name.endswith('.csv'):  
                df_wyscout = pd.read_csv(wyscout_file)  
            else:  
                df_wyscout = pd.read_excel(wyscout_file)  
                  
        if skillcorner_file is not None:  
            if skillcorner_file.name.endswith('.csv'):  
                df_skillcorner = pd.read_csv(skillcorner_file)  
            else:  
                df_skillcorner = pd.read_excel(skillcorner_file)  
    except Exception as e:  
        st.error("Erro ao ler os arquivos: " + str(e))  
      
    return df_wyscout, df_skillcorner  
  
# Função para renomear colunas dos dados SkillCorner com prefixos  
def rename_skillcorner_columns(df):  
    # Preserva a coluna de 'Player'  
    new_names = {}  
    for col in df.columns:  
        if col != "Player":  
            if "Physical" in col or "Output" in col:  
                new_names[col] = "Physical_Output_" + col  
            elif "Pressure" in col or "Overcome" in col:  
                new_names[col] = "Overcome_Pressure_" + col  
            else:  
                new_names[col] = col  
    df.rename(columns=new_names, inplace=True)  
    return df  
  
# Função para realizar a união dos dados  
def merge_data(df_wyscout, df_skillcorner):  
    wyscout_players = df_wyscout["Player"].tolist()  
    skillcorner_players = df_skillcorner["Player"].tolist()  
      
    # Cria mapa de matching utilizando a função find_best_match  
    mapping = {}  
    for player in skillcorner_players:  
        match = find_best_match(player, wyscout_players)  
        if match:  
            mapping[player] = match  
        else:  
            mapping[player] = None  
  
    df_skillcorner_matched = df_skillcorner.copy()  
    df_skillcorner_matched["Matched_Player"] = df_skillcorner["Player"].map(mapping)  
      
    # Realiza merge outer para que os jogadores não casados fiquem com campos em branco  
    merged_df = pd.merge(df_wyscout,   
                         df_skillcorner_matched,  
                         left_on="Player",   
                         right_on="Matched_Player",  
                         how="outer")  
      
    # Organiza as colunas e remove chaves auxiliares  
    if "Matched_Player" in merged_df.columns:  
        merged_df.drop("Matched_Player", axis=1, inplace=True)  
      
    # Caso ocorram duplicatas de coluna "Player", renomeia  
    if "Player_x" in merged_df.columns and "Player_y" in merged_df.columns:  
        merged_df = merged_df.rename(columns={"Player_x": "Player"}).drop("Player_y", axis=1)  
      
    return merged_df  
  
def main():  
    st.title("App de Merge entre WyScout e SkillCorner")  
      
    st.markdown("### Carregue os arquivos de dados")  
    df_wyscout, df_skillcorner = load_data()  
  
    if df_wyscout is not None and df_skillcorner is not None:  
        st.success("Arquivos carregados com sucesso!")  
          
        # Exibe head dos dataframes carregados  
        st.subheader("Primeiras linhas do WyScout Data")  
        st.dataframe(df_wyscout.head())  
        st.subheader("Primeiras linhas do SkillCorner Data")  
        st.dataframe(df_skillcorner.head())  
          
        # Renomeia colunas do SkillCorner para identificação clara  
        df_skillcorner = rename_skillcorner_columns(df_skillcorner)  
          
        # Casos de seleção de métricas através de checkbox  
        include_physical = st.checkbox("Incluir Métricas de Physical Output", value=True)  
        include_pressure = st.checkbox("Incluir Métricas de Overcome Pressure", value=True)  
          
        # Filtra as colunas a partir dos prefixos, mantendo a coluna "Player"  
        physical_cols = [col for col in df_skillcorner.columns if col.startswith("Physical_Output_")] if include_physical else []  
        pressure_cols = [col for col in df_skillcorner.columns if col.startswith("Overcome_Pressure_")] if include_pressure else []  
        selected_cols = ["Player"] + physical_cols + pressure_cols  
          
        # Limita o dataframe SkillCorner às colunas selecionadas  
        df_skillcorner = df_skillcorner[selected_cols]  
          
        st.markdown("### Executar Merge dos Dados")  
        if st.button("Gerar Excel Mesclado"):  
            try:  
                merged_df = merge_data(df_wyscout, df_skillcorner)  
                  
                # Gerar arquivo Excel para download  
                output = BytesIO()  
                with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                    merged_df.to_excel(writer, index=False)  
                st.download_button("📥 Download Excel Mesclado",   
                                   data=output.getvalue(),  
                                   file_name="wyScout_skillcorner_merged.xlsx",  
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
                st.success("Merge realizado com sucesso! Confira o Excel baixado.")  
            except Exception as e:  
                st.error("Erro durante o merge: " + str(e))  
                  
if __name__ == "__main__":  
    main()  
