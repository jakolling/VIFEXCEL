import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import unicodedata
from difflib import SequenceMatcher
import re

st.set_page_config(page_title="Data Merger", layout="wide")

st.markdown("""
<style>
    .stButton>button { width: 100%; margin-top: 10px; }
    .upload-text { font-size: 16px; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

def clean_name(name):
    if not isinstance(name, str):
        return ''
    name = unicodedata.normalize('NFKD', str(name)).encode('ASCII', 'ignore').decode('ASCII').lower()
    name = re.sub(r'[^a-z0-9\s]', '', name)
    return ' '.join(name.split())

def calculate_match_score(name1, name2):
    n1 = clean_name(name1)
    n2 = clean_name(name2)
    
    if n1 == n2:
        return 1.0
    
    parts1 = n1.split()
    parts2 = n2.split()
    
    if parts1 and parts2 and parts1[-1] == parts2[-1]:
        initials1 = ''.join(p[0] for p in parts1[:-1])
        initials2 = ''.join(p[0] for p in parts2[:-1])
        if initials1 and initials2 and initials1 == initials2:
            return 0.95
        return 0.8
    
    return SequenceMatcher(None, n1, n2).ratio()

def find_matches(source_df, target_df, threshold=0.85):
    matches = {}
    unmatched = []
    
    source_players = source_df['Player'].dropna().unique()
    target_players = target_df['Player'].dropna().unique()
    
    for source_player in source_players:
        best_score = 0
        best_match = None
        
        for target_player in target_players:
            score = calculate_match_score(source_player, target_player)
            if score > best_score:
                best_score = score
                best_match = target_player
        
        if best_score >= threshold:
            matches[source_player] = best_match
        else:
            unmatched.append(source_player)
    
    return matches, unmatched

def process_dataframe(df):
    df = df.dropna(how='all').dropna(axis=1, how='all')
    if 'Player' not in df.columns:
        st.error("Column 'Player' not found")
        return None
    df = df.dropna(subset=['Player'])
    df['Player'] = df['Player'].astype(str).apply(lambda x: x.strip())
    return df

def add_suffix(df, suffix):
    return df.rename(columns={col: f"{col}_{suffix}" for col in df.columns if col != 'Player'})

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
            
            physical_matches, physical_unmatched = find_matches(df_physical, df_wyscout)
            pressure_matches, pressure_unmatched = find_matches(df_pressure, df_wyscout)
            
            if physical_unmatched or pressure_unmatched:
                st.warning("Manual matching required")
                
                tab1, tab2 = st.tabs(["Physical Output", "Pressure"])
                
                with tab1:
                    if physical_unmatched:
                        for player in physical_unmatched:
                            match = st.selectbox(
                                f"Match for {player}",
                                ["Select..."] + sorted(df_wyscout['Player'].unique().tolist()),
                                key=f"physical_{player}"
                            )
                            if match != "Select...":
                                physical_matches[player] = match
                
                with tab2:
                    if pressure_unmatched:
                        for player in pressure_unmatched:
                            match = st.selectbox(
                                f"Match for {player}",
                                ["Select..."] + sorted(df_wyscout['Player'].unique().tolist()),
                                key=f"pressure_{player}"
                            )
                            if match != "Select...":
                                pressure_matches[player] = match
            
            if st.button("Merge Data"):
                df_physical_matched = df_physical.copy()
                df_physical_matched['Player'] = df_physical_matched['Player'].map(physical_matches)
                df_physical_matched = add_suffix(df_physical_matched, 'physical')
                
                df_pressure_matched = df_pressure.copy()
                df_pressure_matched['Player'] = df_pressure_matched['Player'].map(pressure_matches)
                df_pressure_matched = add_suffix(df_pressure_matched, 'pressure')
                
                merged_df = pd.merge(df_wyscout, df_physical_matched, on='Player', how='inner')
                final_df = pd.merge(merged_df, df_pressure_matched, on='Player', how='inner')
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=False)
                
                st.download_button(
                    "📥 Download Merged Data",
                    data=output.getvalue(),
                    file_name="merged_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success(f"✅ Merged {len(final_df)} players")
                st.dataframe(final_df.head())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Players", len(final_df))
                with col2:
                    st.metric("Auto Matches", len(physical_matches) - len(physical_unmatched))
                with col3:
                    st.metric("Manual Matches", len(physical_unmatched))
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
else:
    st.info("👆 Upload all three Excel files")
