import streamlit as st  
import pandas as pd  
import base64  
from io import BytesIO  
  
def to_excel(df):  
    output = BytesIO()  
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:  
        df.to_excel(writer, index=False, sheet_name='MatchedData')  
    processed_data = output.getvalue()  
    return processed_data  
  
def download_link(object_to_download, download_filename, download_link_text):  
    if isinstance(object_to_download, pd.DataFrame):  
        object_to_download = to_excel(object_to_download)  
    b64 = base64.b64encode(object_to_download).decode()  
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{download_filename}">{download_link_text}</a>'  
  
st.title('Manual Player Matching')  
  
wyscout_file = st.file_uploader("Upload WyScout file", type=['xlsx', 'xls', 'csv'])  
skillcorner_file = st.file_uploader("Upload SkillCorner file", type=['xlsx', 'xls', 'csv'])  
  
if 'manual_matches' not in st.session_state:  
    st.session_state.manual_matches = {}  
  
if wyscout_file and skillcorner_file:  
    if wyscout_file.name.endswith('.csv'):  
        wyscout_df = pd.read_csv(wyscout_file)  
    else:  
        wyscout_df = pd.read_excel(wyscout_file)  
          
    if skillcorner_file.name.endswith('.csv'):  
        skillcorner_df = pd.read_csv(skillcorner_file)  
    else:  
        skillcorner_df = pd.read_excel(skillcorner_file)  
  
    st.write("### Manual Player Matching")  
      
    wyscout_players = wyscout_df['Player'].dropna().unique().tolist()  
    skillcorner_players = [""] + list(skillcorner_df['Player'].dropna().unique())  
      
    col1, col2 = st.columns(2)  
      
    with col1:  
        st.write("WyScout Players")  
        selected_wyscout = st.selectbox("Select WyScout player:", wyscout_players)  
      
    with col2:  
        st.write("SkillCorner Players")   
        if selected_wyscout:  
            selected_skillcorner = st.selectbox("Select matching SkillCorner player:", skillcorner_players)  
            if st.button("Match Players"):  
                st.session_state.manual_matches[selected_wyscout] = selected_skillcorner  
      
    st.write("### Current Matches")  
    matches_df = pd.DataFrame(list(st.session_state.manual_matches.items()), columns=['WyScout Player', 'SkillCorner Player'])  
    st.dataframe(matches_df)  
      
    if st.button("Clear All Matches"):  
        st.session_state.manual_matches = {}  
        st.experimental_rerun()  
          
    if st.button("Apply Matches"):  
        wyscout_df['Matched_Player'] = wyscout_df['Player'].map(st.session_state.manual_matches)  
        st.write("### Final Matched Data")  
        st.dataframe(wyscout_df)  
          
        if st.button("Download Matched Data"):  
            tmp_download_link = download_link(wyscout_df, 'manual_matched_players.xlsx', 'Download Matched Data')  
            st.markdown(tmp_download_link, unsafe_allow_html=True)  
