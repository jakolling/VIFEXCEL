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
        # First + Last  
        variations.add(parts[0] + " " + parts[-1])  
        # Last + First  
        variations.add(parts[-1] + " " + parts[0])  
        # Initial + Last  
        variations.add(parts[0][0] + " " + parts[-1])  
        # Last + Initial  
        variations.add(parts[-1] + " " + parts[0][0])  
        # Just Last  
        variations.add(parts[-1])  
        # First Initial + ... + Last (all initials except last and last name appended)  
        if len(parts) > 2:  
            initials = ''.join(p[0] for p in parts[:-1])  
            variations.add(initials + " " + parts[-1])  
    return variations  
  
def calculate_match_score(name1, name2):  
    n1_variations = get_name_variations(name1)  
    n2_variations = get_name_variations(name2)  
    if n1_variations.intersection(n2_variations):  
        return 1.0  
    max_score = 0  
    for v1 in n1_variations:  
        for v2 in n2_variations:  
            token_score = fuzz.token_sort_ratio(v1, v2) / 100  
            partial_score = fuzz.partial_ratio(v1, v2) / 100  
            ratio_score = fuzz.ratio(v1, v2) / 100  
            score = max(token_score, partial_score, ratio_score)  
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
  
def process_dataframe(df):  
    df = df.dropna(how='all').dropna(axis=1, how='all')  
    if 'Player' not in df.columns:  
        st.error("Column 'Player' not found")  
        return None  
    df = df.dropna(subset=['Player'])  
    df['Player'] = df['Player'].astype(str).apply(lambda x: x.strip())  
    return df  
  
def add_suffix(df, suffix):  
    return df.rename(columns={col: col + "_" + suffix for col in df.columns if col != 'Player'})  
  
st.title("WyScout & SkillCorner Data Merger")  
  
col1, col2, col3 = st.columns(3)  
  
with col1:  
    wyscout_file = st.file_uploader("WyScout Data", type=['xlsx', 'xls'], key='wyscout')  
with col2:  
    physical_file = st.file_uploader("SkillCorner Physical", type=['xlsx', 'xls'], key='physical')  
with col3:  
    pressure_file = st.file_uploader("SkillCorner Pressure", type=['xlsx', 'xls'], key='pressure')  
  
if all([wyscout_file, physical_file, pressure_file]):  
    try:  
        df_wyscout = process_dataframe(pd.read_excel(wyscout_file))  
        df_physical = process_dataframe(pd.read_excel(physical_file))  
        df_pressure = process_dataframe(pd.read_excel(pressure_file))  
        if all([df_wyscout is not None, df_physical is not None, df_pressure is not None]):  
            st.success("✅ Files loaded successfully")  
              
            physical_matches, physical_unmatched, physical_details = find_matches(df_physical, df_wyscout)  
            pressure_matches, pressure_unmatched, pressure_details = find_matches(df_pressure, df_wyscout)  
              
            if physical_unmatched or pressure_unmatched:  
                st.warning("Manual matching required")  
                tab1, tab2 = st.tabs(["Physical Output", "Pressure"])  
                with tab1:  
                    if physical_unmatched:  
                        for unmatch in physical_unmatched:  
                            player = unmatch['player']  
                            st.write("Player: " + player)  
                            st.write("Best matches found:")  
                            for match, score in unmatch['best_matches']:  
                                st.write("- " + match + " (Score: " + str(round(score,2)) + ")")  
                            choose = st.selectbox("Select correct match", ["Select..."] + sorted(df_wyscout['Player'].unique().tolist()), key="physical_" + player)  
                            if choose != "Select...":  
                                physical_matches[player] = choose  
                with tab2:  
                    if pressure_unmatched:  
                        for unmatch in pressure_unmatched:  
                            player = unmatch['player']  
                            st.write("Player: " + player)  
                            st.write("Best matches found:")  
                            for match, score in unmatch['best_matches']:  
                                st.write("- " + match + " (Score: " + str(round(score,2)) + ")")  
                            choose = st.selectbox("Select correct match", ["Select..."] + sorted(df_wyscout['Player'].unique().tolist()), key="pressure_" + player)  
                            if choose != "Select...":  
                                pressure_matches[player] = choose  
            if st.button("Merge Data"):  
                df_physical_matched = df_physical.copy()  
                df_physical_matched['Player'] = df_physical_matched['Player'].map(physical_matches)  
                df_physical_matched = add_suffix(df_physical_matched, "physical")  
                  
                df_pressure_matched = df_pressure.copy()  
                df_pressure_matched['Player'] = df_pressure_matched['Player'].map(pressure_matches)  
                df_pressure_matched = add_suffix(df_pressure_matched, "pressure")  
                  
                merged_df = pd.merge(df_wyscout, df_physical_matched, on="Player", how="inner")  
                final_df = pd.merge(merged_df, df_pressure_matched, on="Player", how="inner")  
                  
                output = BytesIO()  
                with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                    final_df.to_excel(writer, index=False)  
                st.download_button("📥 Download Merged Data", data=output.getvalue(), file_name="merged_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
                st.success("✅ Merged " + str(len(final_df)) + " players")  
                st.dataframe(final_df.head())  
                  
                col1, col2, col3 = st.columns(3)  
                with col1:  
                    st.metric("Total Players", len(final_df))  
                with col2:  
                    st.metric("Auto Matches", str(len(physical_matches) - len(physical_unmatched)))  
                with col3:  
                    st.metric("Manual Matches", str(len(physical_unmatched)))  
    except Exception as e:  
        st.error("Error: " + str(e))  
else:  
    st.info("👆 Upload all three Excel files")  
