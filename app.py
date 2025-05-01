import streamlit as st  
import pandas as pd  
import numpy as np  
from io import BytesIO  
import re  
import unicodedata  
from fuzzywuzzy import fuzz  
from unidecode import unidecode  
  
st.set_page_config(page_title="Data Merger", layout="wide")  
  
st.markdown("""  
<style>  
    .stButton>button { width: 100%; margin-top: 10px; }  
    .upload-text { font-size: 16px; margin-bottom: 5px; }  
</style>  
""", unsafe_allow_html=True)  
  
# Novo algoritmo de matching aprimorado  
def normalize_name(name):  
    if not isinstance(name, str):  
        return ''  
    name = unidecode(str(name)).lower()  
    name = re.sub(r'[^a-z0-9\s]', '', name)  
    name = re.sub(r'\b(jr|sr|i|ii|iii)\b', '', name)  
    name = re.sub(r'\s+', ' ', name)  
    return name.strip()  
  
def get_name_variations(name):  
    normalized = normalize_name(name)  
    parts = normalized.split()  
    variations = {normalized}  
    if len(parts) > 1:  
        variations.add(parts[0] + " " + parts[-1])  
        variations.add(parts[-1] + " " + parts[0])  
        variations.add(parts[0][0] + " " + parts[-1])  
        variations.add(parts[-1] + " " + parts[0][0])  
        variations.add(parts[-1])  
        if len(parts) > 2:  
            initials = ''.join([p[0] for p in parts[:-1]])  
            variations.add(initials + " " + parts[-1])  
    return variations  
  
def calculate_match_score(name1, name2):  
    variations1 = get_name_variations(name1)  
    variations2 = get_name_variations(name2)  
    if variations1.intersection(variations2):  
        return 1.0  
    max_score = 0  
    for v1 in variations1:  
        for v2 in variations2:  
            score = max(  
                fuzz.token_sort_ratio(v1, v2) / 100,  
                fuzz.partial_ratio(v1, v2) / 100,  
                fuzz.ratio(v1, v2) / 100  
            )  
            if score > max_score:  
                max_score = score  
    return max_score  
  
def find_matches(source_df, target_df, threshold=0.85):  
    matches = {}  
    unmatched = []  
    match_details = {}  
    source_players = source_df['Player'].dropna().unique()  
    target_players = target_df['Player'].dropna().unique()  
    for source_player in source_players:  
        best_match = None  
        best_score = 0  
        potential_matches = []  
        for target_player in target_players:  
            score = calculate_match_score(source_player, target_player)  
            if score >= threshold:  
                potential_matches.append((target_player, score))  
            if score > best_score:  
                best_score = score  
                best_match = target_player  
        if best_score >= threshold:  
            matches[source_player] = best_match  
            match_details[source_player] = {  
                'match': best_match,  
                'score': best_score,  
                'alternatives': [ (m, s) for m, s in potential_matches if m != best_match ][:2]  
            }  
        else:  
            unmatched.append({  
                'player': source_player,  
                'best_matches': potential_matches[:3],  
                'best_score': best_score  
            })  
    return matches, unmatched, match_details  
  
def add_suffix(df, suffix):  
    cols = df.columns.tolist()  
    new_cols = [col if col=='Player' else col + "_" + suffix for col in cols]  
    df.columns = new_cols  
    return df  
  
# Upload de arquivos  
st.sidebar.header("Upload de Arquivos")  
wyscout_file = st.sidebar.file_uploader("Escolha o arquivo Wyscout (Excel)", type=["xlsx"])  
physical_file = st.sidebar.file_uploader("Escolha o arquivo de dados físicos (Excel)", type=["xlsx"])  
pressure_file = st.sidebar.file_uploader("Escolha o arquivo de dados de pressão (Excel)", type=["xlsx"])  
  
if wyscout_file and physical_file and pressure_file:  
    try:  
        df_wyscout = pd.read_excel(wyscout_file)  
        df_physical = pd.read_excel(physical_file)  
        df_pressure = pd.read_excel(pressure_file)  
    except Exception as e:  
        st.error("Erro ao ler os arquivos: " + str(e))  
    else:  
        st.success("Arquivos carregados com sucesso!")  
  
    st.subheader("Matching de Nomes")  
  
    physical_matches, physical_unmatched, physical_details = find_matches(df_physical, df_wyscout, threshold=0.85)  
    pressure_matches, pressure_unmatched, pressure_details = find_matches(df_pressure, df_wyscout, threshold=0.85)  
  
    st.write("##### Auto-matches Físicos")  
    st.write(physical_matches)  
    st.write("##### Auto-matches de Pressão")  
    st.write(pressure_matches)  
  
    tab1, tab2 = st.tabs(["Ajustar Físicos", "Ajustar Pressão"])  
    physical_manual = {}  
    pressure_manual = {}  
    with tab1:  
        if physical_unmatched:  
            st.write("Ajuste manual para os seguintes jogadores de dados físicos:")  
            for unmatch in physical_unmatched:  
                player = unmatch["player"]  
                st.write("Jogador:", player)  
                st.write("Melhores matches encontrados:")  
                for match, score in unmatch["best_matches"]:  
                    st.write("- " + match + " (Score: " + str(round(score,2)) + ")")  
                choose = st.selectbox("Selecione o match correto",  
                                        ["Select..."] + sorted(df_wyscout["Player"].unique().tolist()),  
                                        key="physical_" + player)  
                if choose != "Select...":  
                    physical_manual[player] = choose  
        else:  
            st.write("Todos os jogadores de dados físicos foram auto-matched.")  
    with tab2:  
        if pressure_unmatched:  
            st.write("Ajuste manual para os seguintes jogadores de dados de pressão:")  
            for unmatch in pressure_unmatched:  
                player = unmatch["player"]  
                st.write("Jogador:", player)  
                st.write("Melhores matches encontrados:")  
                for match, score in unmatch["best_matches"]:  
                    st.write("- " + match + " (Score: " + str(round(score,2)) + ")")  
                choose = st.selectbox("Selecione o match correto",  
                                        ["Select..."] + sorted(df_wyscout["Player"].unique().tolist()),  
                                        key="pressure_" + player)  
                if choose != "Select...":  
                    pressure_manual[player] = choose  
        else:  
            st.write("Todos os jogadores de dados de pressão foram auto-matched.")  
  
    # Atualiza os matches com correções manuais  
    for k, v in physical_manual.items():  
        physical_matches[k] = v  
    for k, v in pressure_manual.items():  
        pressure_matches[k] = v  
  
    if st.button("Merge Data"):  
        df_physical_matched = df_physical.copy()  
        df_physical_matched["Player"] = df_physical_matched["Player"].map(physical_matches)  
        df_physical_matched = add_suffix(df_physical_matched, "physical")  
          
        df_pressure_matched = df_pressure.copy()  
        df_pressure_matched["Player"] = df_pressure_matched["Player"].map(pressure_matches)  
        df_pressure_matched = add_suffix(df_pressure_matched, "pressure")  
          
        merged_df = pd.merge(df_wyscout, df_physical_matched, on="Player", how="inner")  
        final_df = pd.merge(merged_df, df_pressure_matched, on="Player", how="inner")  
          
        output = BytesIO()  
        with pd.ExcelWriter(output, engine="openpyxl") as writer:  
            final_df.to_excel(writer, index=False)  
          
        st.download_button("📥 Download Merged Data",   
                           data=output.getvalue(),   
                           file_name="merged_data.xlsx",   
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
          
        st.success("✅ Mesclados " + str(len(final_df)) + " jogadores")  
        st.dataframe(final_df.head())  
          
        col1, col2, col3 = st.columns(3)  
        with col1:  
            st.metric("Total Players", len(final_df))  
        with col2:  
            st.metric("Auto Matches (Físicos)", str(len(physical_matches) - len(physical_unmatched)))  
        with col3:  
            st.metric("Auto Matches (Pressão)", str(len(pressure_matches) - len(pressure_unmatched)))  
else:  
    st.info("👆 Faça upload dos três arquivos Excel")  
