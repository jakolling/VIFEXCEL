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
  
def merge_dataframes(df1, df2, df3, matches1, matches2, selected_physical_cols, selected_pressure_cols):  
    df2_matched = df2.copy()  
    df3_matched = df3.copy()  
      
    df2_matched["Player"] = df2_matched["Player"].map(matches1)  
    df3_matched["Player"] = df3_matched["Player"].map(matches2)  
      
    if selected_physical_cols:  
        physical_cols = ["Player"] + selected_physical_cols  
        df2_matched = df2_matched[physical_cols]  
      
    if selected_pressure_cols:  
        pressure_cols = ["Player"] + selected_pressure_cols  
        df3_matched = df3_matched[pressure_cols]  
      
    merged = pd.merge(df1, df2_matched, on="Player", how="inner")  
    final = pd.merge(merged, df3_matched, on="Player", how="inner")  
      
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
  
if 'selected_physical_cols' not in st.session_state:  
    st.session_state.selected_physical_cols = []  
if 'selected_pressure_cols' not in st.session_state:  
    st.session_state.selected_pressure_cols = []  
if 'show_physical_popup' not in st.session_state:  
    st.session_state.show_physical_popup = False  
if 'show_pressure_popup' not in st.session_state:  
    st.session_state.show_pressure_popup = False  
  
uploaded_wyscout = st.file_uploader("Upload WyScout Excel", type=["xlsx"])  
uploaded_physical = st.file_uploader("Upload SkillCorner Physical Output Excel", type=["xlsx"])  
uploaded_pressure = st.file_uploader("Upload SkillCorner Overcome Pressure Excel", type=["xlsx"])  
  
if all([uploaded_wyscout, uploaded_physical, uploaded_pressure]):  
    df_wyscout = pd.read_excel(uploaded_wyscout)  
    df_physical = pd.read_excel(uploaded_physical)  
    df_pressure = pd.read_excel(uploaded_pressure)  
  
    col1, col2 = st.columns(2)  
    with col1:  
        if st.button("Select Physical Columns"):  
            st.session_state.show_physical_popup = True  
    with col2:  
        if st.button("Select Pressure Columns"):  
            st.session_state.show_pressure_popup = True  
  
    if st.session_state.show_physical_popup:  
        with st.container():  
            st.subheader("Select Physical Data Columns")  
            physical_columns = [col for col in df_physical.columns if col != "Player"]  
            cols = st.columns(3)  
            columns_per_col = len(physical_columns) // 3 + 1  
            temp_selected = st.session_state.selected_physical_cols.copy()  
            if st.checkbox("Select All Physical", value=len(st.session_state.selected_physical_cols) == len(physical_columns)):  
                temp_selected = physical_columns.copy()  
            for i, col in enumerate(physical_columns):  
                col_idx = i // columns_per_col  
                with cols[col_idx]:  
                    if st.checkbox(col, value=col in temp_selected, key="phys_" + col):  
                        if col not in temp_selected:  
                            temp_selected.append(col)  
                    elif col in temp_selected:  
                        temp_selected.remove(col)  
            col1, col2 = st.columns(2)  
            with col1:  
                if st.button("Apply Physical"):  
                    st.session_state.selected_physical_cols = temp_selected  
                    st.session_state.show_physical_popup = False  
                    st.experimental_rerun()  
            with col2:  
                if st.button("Cancel Physical"):  
                    st.session_state.show_physical_popup = False  
                    st.experimental_rerun()  
  
    if st.session_state.show_pressure_popup:  
        with st.container():  
            st.subheader("Select Pressure Data Columns")  
            pressure_columns = [col for col in df_pressure.columns if col != "Player"]  
            cols = st.columns(3)  
            columns_per_col = len(pressure_columns) // 3 + 1  
            temp_selected = st.session_state.selected_pressure_cols.copy()  
            if st.checkbox("Select All Pressure", value=len(st.session_state.selected_pressure_cols) == len(pressure_columns)):  
                temp_selected = pressure_columns.copy()  
            for i, col in enumerate(pressure_columns):  
                col_idx = i // columns_per_col  
                with cols[col_idx]:  
                    if st.checkbox(col, value=col in temp_selected, key="pres_" + col):  
                        if col not in temp_selected:  
                            temp_selected.append(col)  
                    elif col in temp_selected:  
                        temp_selected.remove(col)  
            col1, col2 = st.columns(2)  
            with col1:  
                if st.button("Apply Pressure"):  
                    st.session_state.selected_pressure_cols = temp_selected  
                    st.session_state.show_pressure_popup = False  
                    st.experimental_rerun()  
            with col2:  
                if st.button("Cancel Pressure"):  
                    st.session_state.show_pressure_popup = False  
                    st.experimental_rerun()  
  
    st.write("Selected Physical Columns:", st.session_state.selected_physical_cols)  
    st.write("Selected Pressure Columns:", st.session_state.selected_pressure_cols)  
      
    st.sidebar.write("WyScout Preview")  
    st.sidebar.dataframe(df_wyscout.head())  
    st.sidebar.write("Physical Preview")  
    st.sidebar.dataframe(df_physical.head())  
    st.sidebar.write("Pressure Preview")  
    st.sidebar.dataframe(df_pressure.head())  
  
    tab1, tab2 = st.tabs(["Physical vs WyScout", "Pressure vs WyScout"])  
      
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
        if not st.session_state.selected_physical_cols or not st.session_state.selected_pressure_cols:  
            st.warning("Please select columns from both Physical and Pressure data")  
        else:  
            final_df = merge_dataframes(df_wyscout, df_physical, df_pressure,  
                                        physical_matches, pressure_matches,  
                                        st.session_state.selected_physical_cols,  
                                        st.session_state.selected_pressure_cols)  
            output = BytesIO()  
            with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                final_df.to_excel(writer, index=False)  
            st.download_button("📥 Download Merged Data", data=output.getvalue(),  
                               file_name="merged_data.xlsx",  
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
            st.success("✅ Merged " + str(len(final_df)) + " players")  
            st.dataframe(final_df.head())  
else:  
    st.info("👆 Please upload all three Excel files")  
