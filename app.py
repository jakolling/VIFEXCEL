import streamlit as st  
import pandas as pd  
import numpy as np  
from io import BytesIO  
import re  
from unidecode import unidecode  
  
st.set_page_config(page_title="Data Merger", layout="wide")  
  
# Utility functions for normalization and matching of names  
  
def normalize_name(name):  
    if not isinstance(name, str):  
        return ''  
    name = unidecode(str(name)).lower()  
    name = re.sub(r'[^a-z0-9\s]', '', name)  
    name = re.sub(r'\b(jr|sr|i|ii|iii)\b', '', name)  
    name = re.sub(r'\s+', ' ', name)  
    return name.strip()  
  
def get_key_name(name):  
    """  
    Extracts the key component for matching.  
    Here we use the last name.  
    """  
    normalized = normalize_name(name)  
    parts = normalized.split()  
    if len(parts) == 0:  
        return ''  
    if len(parts) == 1:  
        return parts[0]  
    return parts[-1]  
  
def find_matches(source_df, target_df):  
    """  
    Create matching indices by comparing key names.  
    Uses the last name as key.  
    """  
    matches = {}  
    unmatched = []  
      
    source_dict = {get_key_name(name): name for name in source_df['Player'].dropna()}  
    target_dict = {get_key_name(name): name for name in target_df['Player'].dropna()}  
      
    for key, source_name in source_dict.items():  
        if key in target_dict:  
            matches[source_name] = target_dict[key]  
        else:  
            unmatched.append(source_name)  
      
    return matches, unmatched  
  
def add_suffix(df, suffix):  
    df.columns = [col if col == 'Player' else col + '_' + suffix for col in df.columns]  
    return df  
  
# Main App  
st.title('Data Merger')  
  
uploaded_wyscout = st.file_uploader("Upload Wyscout Excel", type=["xlsx"])  
uploaded_physical = st.file_uploader("Upload Physical Data Excel", type=["xlsx"])  
uploaded_pressure = st.file_uploader("Upload Pressure Data Excel", type=["xlsx"])  
  
if uploaded_wyscout is not None and uploaded_physical is not None and uploaded_pressure is not None:  
    df_wyscout = pd.read_excel(uploaded_wyscout)  
    df_physical = pd.read_excel(uploaded_physical)  
    df_pressure = pd.read_excel(uploaded_pressure)  
      
    st.sidebar.write("Preview Wyscout")  
    st.sidebar.dataframe(df_wyscout.head())  
    st.sidebar.write("Preview Physical")  
    st.sidebar.dataframe(df_physical.head())  
    st.sidebar.write("Preview Pressure")  
    st.sidebar.dataframe(df_pressure.head())  
      
    tab1, tab2 = st.tabs(["Physical vs Wyscout", "Pressure vs Wyscout"])  
      
    with tab1:  
        physical_matches, physical_unmatched = find_matches(df_physical, df_wyscout)  
        st.write("Matches encontrados:")  
        st.write(physical_matches)  
          
        if physical_unmatched:  
            st.write("Jogadores não encontrados:")  
            physical_manual = {}  
            for player in physical_unmatched:  
                st.write("Jogador: " + player)  
                choose = st.selectbox(  
                    "Selecione o match correto",  
                    ["Select..."] + sorted(df_wyscout["Player"].unique().tolist()),  
                    key="physical_" + player  
                )  
                if choose != "Select...":  
                    physical_manual[player] = choose  
            physical_matches.update(physical_manual)  
      
    with tab2:  
        pressure_matches, pressure_unmatched = find_matches(df_pressure, df_wyscout)  
        st.write("Matches encontrados:")  
        st.write(pressure_matches)  
          
        if pressure_unmatched:  
            st.write("Jogadores não encontrados:")  
            pressure_manual = {}  
            for player in pressure_unmatched:  
                st.write("Jogador: " + player)  
                choose = st.selectbox(  
                    "Selecione o match correto",  
                    ["Select..."] + sorted(df_wyscout["Player"].unique().tolist()),  
                    key="pressure_" + player  
                )  
                if choose != "Select...":  
                    pressure_manual[player] = choose  
            pressure_matches.update(pressure_manual)  
      
    if st.button("Merge Data"):  
        df_physical_matched = df_physical.copy()  
        df_pressure_matched = df_pressure.copy()  
          
        df_physical_matched["Player"] = df_physical_matched["Player"].map(physical_matches)  
        df_pressure_matched["Player"] = df_pressure_matched["Player"].map(pressure_matches)  
          
        df_physical_matched = add_suffix(df_physical_matched, "physical")  
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
else:  
    st.info("👆 Faça upload dos três arquivos Excel")  
