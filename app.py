import streamlit as st  
import pandas as pd  
import numpy as np  
from io import BytesIO  
import re  
from unidecode import unidecode  
  
st.set_page_config(page_title="Data Merger", layout="wide")  
  
def normalize_name(name):  
    if not isinstance(name, str):  
        return ''  
    name = unidecode(str(name)).lower()  
    name = re.sub(r'[^a-z0-9\s]', '', name)  
    name = re.sub(r'\s+', ' ', name)  
    return name.strip()  
  
def get_key_name(name):  
    normalized = normalize_name(name)  
    parts = normalized.split()  
    if len(parts) == 0:  
        return ''  
    if len(parts) == 1:  
        return parts[0]  
    return parts[-1]  
  
def find_matches(source_df, target_df):  
    matches = {}  
    unmatched = []  
      
    source_dict = {get_key_name(name): name for name in source_df['Player'].dropna()}  
    target_dict = {get_key_name(name): name for name in target_df['Player'].dropna()}  
      
    for source_name, original_source in source_dict.items():  
        if source_name in target_dict:  
            matches[original_source] = target_dict[source_name]  
        else:  
            unmatched.append(original_source)  
              
    return matches, unmatched  
  
def merge_dataframes(df1, df2, df3, df_skill, matches1, matches2, selected_skill_cols):  
    df2_matched = df2.copy()  
    df3_matched = df3.copy()  
    df_skill_matched = df_skill.copy()  
      
    df2_matched["Player"] = df2_matched["Player"].map(matches1)  
    df3_matched["Player"] = df3_matched["Player"].map(matches2)  
      
    # Keep only selected Skillcorner columns  
    if selected_skill_cols:  
        skill_cols = ["Player"] + selected_skill_cols  
        df_skill_matched = df_skill_matched[skill_cols]  
      
    merged = pd.merge(df1, df2_matched, on="Player", how="inner")  
    merged2 = pd.merge(merged, df3_matched, on="Player", how="inner")  
    final = pd.merge(merged2, df_skill_matched, on="Player", how="inner")  
      
    columns_to_drop = [  
        'Short Name',  
        'Player ID',  
        'Birthdate',  
        'Minutes',  
        'Count Performances (Physical Check passed)',  
        'Count Performances (Physical Check failed)',  
        'third',  
        'channel',  
        'Minutes played per match'  
    ]  
    final = final.drop(columns=[col for col in columns_to_drop if col in final.columns])  
      
    return final  
  
st.title('Data Merger')  
  
uploaded_wyscout = st.file_uploader("Upload Wyscout Excel", type=["xlsx"])  
uploaded_physical = st.file_uploader("Upload Physical Data Excel", type=["xlsx"])  
uploaded_pressure = st.file_uploader("Upload Pressure Data Excel", type=["xlsx"])  
uploaded_skill = st.file_uploader("Upload Skillcorner Database Excel", type=["xlsx"])  
  
if all([uploaded_wyscout, uploaded_physical, uploaded_pressure, uploaded_skill]):  
    df_wyscout = pd.read_excel(uploaded_wyscout)  
    df_physical = pd.read_excel(uploaded_physical)  
    df_pressure = pd.read_excel(uploaded_pressure)  
    df_skill = pd.read_excel(uploaded_skill)  
      
    # Skillcorner column selection popup state setup  
    if 'selected_skill_cols' not in st.session_state:  
        st.session_state.selected_skill_cols = []  
    if 'show_skill_popup' not in st.session_state:  
        st.session_state.show_skill_popup = False  
      
    if st.button("Select Skillcorner Columns"):  
        st.session_state.show_skill_popup = True  
  
    if st.session_state.show_skill_popup:  
        with st.container():  
            st.subheader("Select Columns from Skillcorner Database")  
            skill_columns = [col for col in df_skill.columns if col != "Player"]  
              
            # Display checkboxes in three columns layout  
            cols = st.columns(3)  
            columns_per_col = len(skill_columns) // 3 + 1  
            temp_selected = st.session_state.selected_skill_cols.copy()  
              
            if st.checkbox("Select All Skillcorner Columns", value=len(temp_selected) == len(skill_columns)):  
                temp_selected = skill_columns.copy()  
            for i, col in enumerate(skill_columns):  
                col_idx = i // columns_per_col  
                with cols[col_idx]:  
                    if st.checkbox(col, value=col in temp_selected, key="skill_" + col):  
                        if col not in temp_selected:  
                            temp_selected.append(col)  
                    elif col in temp_selected:  
                        temp_selected.remove(col)  
              
            col_a, col_b = st.columns(2)  
            with col_a:  
                if st.button("Apply Skillcorner Selection"):  
                    st.session_state.selected_skill_cols = temp_selected  
                    st.session_state.show_skill_popup = False  
                    st.experimental_rerun()  
            with col_b:  
                if st.button("Cancel Skillcorner Selection"):  
                    st.session_state.show_skill_popup = False  
                    st.experimental_rerun()  
      
    st.sidebar.write("Wyscout Preview")  
    st.sidebar.dataframe(df_wyscout.head())  
    st.sidebar.write("Physical Preview")  
    st.sidebar.dataframe(df_physical.head())  
    st.sidebar.write("Pressure Preview")  
    st.sidebar.dataframe(df_pressure.head())  
    st.sidebar.write("Skillcorner Preview")  
    st.sidebar.dataframe(df_skill.head())  
      
    tab1, tab2 = st.tabs(["Physical vs Wyscout", "Pressure vs Wyscout"])  
      
    with tab1:  
        physical_matches, physical_unmatched = find_matches(df_physical, df_wyscout)  
        st.write("Matches Found:")  
        st.write(physical_matches)  
          
        if physical_unmatched:  
            st.write("Unmatched Players:")  
            physical_manual = {}  
            for player in physical_unmatched:  
                st.write("Player: " + player)  
                choose = st.selectbox("Select correct match", ["Select..."] + sorted(df_wyscout["Player"].unique().tolist()),  
                                        key="physical_" + player)  
                if choose != "Select...":  
                    physical_manual[player] = choose  
            physical_matches.update(physical_manual)  
      
    with tab2:  
        pressure_matches, pressure_unmatched = find_matches(df_pressure, df_wyscout)  
        st.write("Matches Found:")  
        st.write(pressure_matches)  
          
        if pressure_unmatched:  
            st.write("Unmatched Players:")  
            pressure_manual = {}  
            for player in pressure_unmatched:  
                st.write("Player: " + player)  
                choose = st.selectbox("Select correct match", ["Select..."] + sorted(df_wyscout["Player"].unique().tolist()),  
                                        key="pressure_" + player)  
                if choose != "Select...":  
                    pressure_manual[player] = choose  
            pressure_matches.update(pressure_manual)  
      
    if st.button("Merge Data"):  
        if not st.session_state.selected_skill_cols:  
            st.warning("Please select at least one column from Skillcorner Database")  
        else:  
            final_df = merge_dataframes(df_wyscout, df_physical, df_pressure, df_skill,  
                                        physical_matches, pressure_matches,  
                                        st.session_state.selected_skill_cols)  
            output = BytesIO()  
            with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                final_df.to_excel(writer, index=False)  
            st.download_button("📥 Download Merged Data", data=output.getvalue(),  
                               file_name="merged_data.xlsx",  
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
            st.success("✅ Merged " + str(len(final_df)) + " players")  
            st.dataframe(final_df.head())  
else:  
    st.info("👆 Please upload all four Excel files")  
