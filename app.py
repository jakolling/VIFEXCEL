# Save the Streamlit app with three file uploads and data merging
with open('app_streamlit.py', 'w', encoding='utf-8') as f:
    f.write("""import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata
from difflib import SequenceMatcher

st.set_page_config(page_title="Merge WyScout & SkillCorner", layout="wide")

def clean_player_name(name):
    if not isinstance(name, str):
        return ''
    name = unicodedata.normalize('NFKD', str(name)).encode('ASCII', 'ignore').decode('ASCII')
    return name.lower().strip()

def find_best_match(name, names_list, threshold=0.85):
    name = clean_player_name(name)
    best_match = None
    best_score = 0
    
    for target in names_list:
        target = clean_player_name(target)
        score = SequenceMatcher(None, name, target).ratio()
        
        if score > best_score:
            best_score = score
            best_match = target
            
    return (best_match, best_score) if best_score >= threshold else (None, 0)

st.title("Merge WyScout & SkillCorner Data")

col1, col2, col3 = st.columns(3)

with col1:
    wyscout_file = st.file_uploader("WyScout Data", type=['xlsx', 'xls'])
    
with col2:
    physical_file = st.file_uploader("SkillCorner Physical Output", type=['xlsx', 'xls'])
    
with col3:
    pressure_file = st.file_uploader("SkillCorner Overcoming Pressure", type=['xlsx', 'xls'])

if wyscout_file and physical_file and pressure_file:
    try:
        df_wyscout = pd.read_excel(wyscout_file)
        df_physical = pd.read_excel(physical_file)
        df_pressure = pd.read_excel(pressure_file)
        
        st.success("✅ Files loaded successfully")
        
        wyscout_players = df_wyscout['Player'].unique()
        
        # Match Physical Output players
        physical_matches = {}
        physical_unmatched = []
        
        for player in df_physical['Player'].unique():
            match, score = find_best_match(player, wyscout_players)
            if match:
                physical_matches[player] = match
            else:
                physical_unmatched.append(player)
                
        # Match Pressure players
        pressure_matches = {}
        pressure_unmatched = []
        
        for player in df_pressure['Player'].unique():
            match, score = find_best_match(player, wyscout_players)
            if match:
                pressure_matches[player] = match
            else:
                pressure_unmatched.append(player)
        
        # Handle unmatched players
        if physical_unmatched or pressure_unmatched:
            st.warning("Some players need manual matching")
            
            if physical_unmatched:
                st.subheader("Physical Output - Manual Matching")
                for player in physical_unmatched:
                    match = st.selectbox(
                        f"Match for {player}",
                        ["Select..."] + list(wyscout_players),
                        key=f"physical_{player}"
                    )
                    if match != "Select...":
                        physical_matches[player] = match
                        
            if pressure_unmatched:
                st.subheader("Pressure - Manual Matching")
                for player in pressure_unmatched:
                    match = st.selectbox(
                        f"Match for {player}",
                        ["Select..."] + list(wyscout_players),
                        key=f"pressure_{player}"
                    )
                    if match != "Select...":
                        pressure_matches[player] = match
        
        if st.button("Merge Data"):
            # Apply matches
            df_physical_matched = df_physical.copy()
            df_physical_matched['Player'] = df_physical_matched['Player'].map(physical_matches)
            
            df_pressure_matched = df_pressure.copy()
            df_pressure_matched['Player'] = df_pressure_matched['Player'].map(pressure_matches)
            
            # Add suffixes to avoid column conflicts
            df_physical_matched = df_physical_matched.add_suffix('_physical')
            df_physical_matched = df_physical_matched.rename(columns={'Player_physical': 'Player'})
            
            df_pressure_matched = df_pressure_matched.add_suffix('_pressure')
            df_pressure_matched = df_pressure_matched.rename(columns={'Player_pressure': 'Player'})
            
            # Merge dataframes
            merged_df = pd.merge(df_wyscout, df_physical_matched, on='Player', how='inner')
            final_df = pd.merge(merged_df, df_pressure_matched, on='Player', how='inner')
            
            # Save to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False)
            
            st.download_button(
                "📥 Download Merged Data",
                data=output.getvalue(),
                file_name="merged_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.success(f"Merged data with {len(final_df)} players")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.write("Please check if the files are in the correct format")
else:
    st.info("👆 Please upload all three Excel files")
""")

print("Streamlit app saved to app_streamlit.py")
print("Run with: streamlit run app_streamlit.py")
