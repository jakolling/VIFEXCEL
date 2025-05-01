import streamlit as st  
import pandas as pd  
import base64  
from io import BytesIO  
  
# Helper functions  
def to_excel(df):  
    output = BytesIO()  
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:  
        df.to_excel(writer, index=False, sheet_name='MatchedData')  
    return output.getvalue()  
  
def download_link(object_to_download, download_filename, download_link_text):  
    if isinstance(object_to_download, pd.DataFrame):  
        object_to_download = to_excel(object_to_download)  
    b64 = base64.b64encode(object_to_download).decode()  
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{download_filename}">{download_link_text}</a>'  
  
st.title('Player Matching - WyScout & SkillCorner Integration')  
  
# Upload files  
wyscout_file = st.file_uploader("Upload WyScout file", type=['xlsx', 'xls', 'csv'])  
physical_file = st.file_uploader("Upload SkillCorner Physical Output file", type=['xlsx', 'xls', 'csv'])  
overcome_file = st.file_uploader("Upload SkillCorner Overcome Pressure file", type=['xlsx', 'xls', 'csv'])  
  
# Initialize session state variables  
if 'manual_matches' not in st.session_state:  
    st.session_state.manual_matches = {}  
if 'matched_players' not in st.session_state:  
    st.session_state.matched_players = set()  
  
if wyscout_file and physical_file and overcome_file:  
    # Load files  
    if wyscout_file.name.endswith('.csv'):  
        wyscout_df = pd.read_csv(wyscout_file)  
    else:  
        wyscout_df = pd.read_excel(wyscout_file)  
          
    if physical_file.name.endswith('.csv'):  
        physical_df = pd.read_csv(physical_file)  
    else:  
        physical_df = pd.read_excel(physical_file)  
          
    if overcome_file.name.endswith('.csv'):  
        overcome_df = pd.read_csv(overcome_file)  
    else:  
        overcome_df = pd.read_excel(overcome_file)  
          
    # Combine SkillCorner files  
    skillcorner_players = pd.concat([  
        physical_df['Player'].dropna(),  
        overcome_df['Player'].dropna()  
    ]).unique().tolist()  
  
    # Get WyScout players  
    wyscout_players = wyscout_df['Player'].dropna().unique().tolist()  
      
    st.write("### Manual Player Matching")  
      
    # Iterate through WyScout players for manual matching  
    for player in wyscout_players:  
        if player not in st.session_state.matched_players:  
            col1, col2 = st.columns([3,4])  
            with col1:  
                st.write(f"**WyScout Player:** {player}")  
            with col2:  
                selected_skillcorner = st.selectbox(  
                    "Select matching SkillCorner player:",  
                    ["-- None --"] + skillcorner_players,  
                    key="match_" + player  
                )  
                if selected_skillcorner != "-- None --":  
                    st.session_state.manual_matches[player] = selected_skillcorner  
                    st.session_state.matched_players.add(player)  
      
    # Display current matches  
    st.write("### Current Matches")  
    if st.session_state.manual_matches:  
        matches_df = pd.DataFrame(list(st.session_state.manual_matches.items()),  
                                  columns=['WyScout Player', 'SkillCorner Player'])  
        st.dataframe(matches_df)  
    else:  
        st.write("No matches made yet.")  
      
    # Options to clear matches and export final data  
    col1, col2 = st.columns(2)  
    with col1:  
        if st.button("Clear All Matches"):  
            st.session_state.manual_matches = {}  
            st.session_state.matched_players = set()  
            st.experimental_rerun()  
    with col2:  
        if st.button("Export Matched Data"):  
            # Map the matches to the WyScout data  
            wyscout_df['Matched_Player'] = wyscout_df['Player'].map(st.session_state.manual_matches)  
            # Merge with Physical Output data  
            merged_physical = pd.merge(  
                wyscout_df,  
                physical_df,  
                left_on='Matched_Player',  
                right_on='Player',  
                how='left',  
                suffixes=('_WyScout', '_Physical')  
            )  
            # Merge with Overcome Pressure data  
            final_df = pd.merge(  
                merged_physical,  
                overcome_df,  
                left_on='Matched_Player',  
                right_on='Player',  
                how='left',  
                suffixes=('', '_Overcome')  
            )  
            tmp_download_link = download_link(final_df, 'matched_players_complete.xlsx', 'Download Complete Matched Data')  
            st.markdown(tmp_download_link, unsafe_allow_html=True)  
      
    progress = len(st.session_state.matched_players) / len(wyscout_players)  
    st.progress(progress)  
    st.write(f"Players matched: {len(st.session_state.matched_players)} / {len(wyscout_players)}")  
else:  
    st.info("Please upload all three files to begin matching.")  
