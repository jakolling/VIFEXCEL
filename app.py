import streamlit as st  
import pandas as pd  
from io import BytesIO  
import hashlib  
import unicodedata  
from difflib import SequenceMatcher  
  
def preprocess_name(name):  
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')  
    name = name.lower().strip()  
    parts = name.replace('.', ' ').split()  
    last_name = parts[-1] if parts else ''  
    initials = ''.join(p[0] for p in parts[:-1]) if len(parts) > 1 else ''  
    return {'full': name, 'parts': parts, 'last_name': last_name, 'initials': initials}  
  
def improved_match_score(name1, name2):  
    n1 = preprocess_name(name1)  
    n2 = preprocess_name(name2)  
    if n1['full'] == n2['full']:  
        return 1.0  
    if n1['last_name'] == n2['last_name']:  
        if (n1['initials'] and n1['initials'] in n2['full']) or (n2['initials'] and n2['initials'] in n1['full']):  
            return 0.9  
    return SequenceMatcher(None, n1['full'], n2['full']).ratio()  
  
def find_best_match(skill_player, wyscout_players, threshold=0.7):  
    matches = [(wp, improved_match_score(skill_player, wp)) for wp in wyscout_players]  
    best_match = max(matches, key=lambda x: x[1])  
    return best_match if best_match[1] >= threshold else (None, 0)  
  
def process_matches(df_wyscout, df_skillcorner):  
    automatic_matches = {}  
    mismatches = []  
    wyscout_players = df_wyscout["Player"].tolist()  
    for skill_player in df_skillcorner["Player"].unique():  
        best_match, score = find_best_match(skill_player, wyscout_players)  
        if best_match:  
            automatic_matches[skill_player] = best_match  
        else:  
            mismatches.append(skill_player)  
    return automatic_matches, mismatches  
  
def generate_unique_key(player_name, idx, prefix):  
    unique_string = player_name + "_" + str(idx) + "_" + prefix  
    return hashlib.md5(unique_string.encode()).hexdigest()  
  
def manual_link_interface(mismatched_players, wyscout_players):  
    st.subheader("Resolver Mismatches")  
    manual_links = {}  
    for idx, skill_player in enumerate(mismatched_players):  
        col1, col2 = st.columns([2,2])  
        with col1:  
            st.write("SkillCorner: " + skill_player)  
        with col2:  
            manual_match = st.selectbox("Match para " + skill_player, options=wyscout_players, key=generate_unique_key(skill_player, idx, "select"))  
            manual_links[skill_player] = (manual_match, 1.0)  
    return manual_links  
  
def main():  
    st.title("Merge de Dados com Checkboxes de Seleção de Métricas")  
      
    # Upload dos arquivos  
    uploaded_wyscout = st.file_uploader("Carregar arquivo Wyscout (Excel ou CSV)", type=['csv','xlsx'], key="wyscout")  
    uploaded_physical = st.file_uploader("Carregar Physical Output (CSV ou Excel)", type=['csv','xlsx'], key="physical")  
    uploaded_pressure = st.file_uploader("Carregar Overcome Pressure (CSV ou Excel)", type=['csv','xlsx'], key="pressure")  
      
    if uploaded_wyscout is not None:  
        try:  
            if uploaded_wyscout.name.endswith('.csv'):  
                df_wyscout = pd.read_csv(uploaded_wyscout)  
            else:  
                df_wyscout = pd.read_excel(uploaded_wyscout)  
        except Exception as e:  
            st.error("Erro ao carregar arquivo Wyscout: " + str(e))  
            return  
    else:  
        st.info("Aguardando carregamento do arquivo Wyscout.")  
        return  
  
    # Leitura dos dados de SkillCorner  
    if uploaded_physical is not None or uploaded_pressure is not None:  
        dfs_skillcorner = []  
        # Caso exista Physical Output: renomear colunas (exceto a coluna Player)  
        if uploaded_physical is not None:  
            try:  
                if uploaded_physical.name.endswith('.csv'):  
                    df_physical = pd.read_csv(uploaded_physical)  
                else:  
                    df_physical = pd.read_excel(uploaded_physical)  
                physical_cols = df_physical.columns.tolist()  
                physical_renamed = {col: (col if col == "Player" else "Physical_Output_" + col) for col in physical_cols}  
                df_physical.rename(columns=physical_renamed, inplace=True)  
                dfs_skillcorner.append(df_physical)  
            except Exception as e:  
                st.error("Erro ao carregar Physical Output: " + str(e))  
                return  
  
        # Caso exista Overcome Pressure: renomear colunas (exceto a coluna Player)  
        if uploaded_pressure is not None:  
            try:  
                if uploaded_pressure.name.endswith('.csv'):  
                    df_pressure = pd.read_csv(uploaded_pressure)  
                else:  
                    df_pressure = pd.read_excel(uploaded_pressure)  
                pressure_cols = df_pressure.columns.tolist()  
                pressure_renamed = {col: (col if col == "Player" else "Overcome_Pressure_" + col) for col in pressure_cols}  
                df_pressure.rename(columns=pressure_renamed, inplace=True)  
                dfs_skillcorner.append(df_pressure)  
            except Exception as e:  
                st.error("Erro ao carregar Overcome Pressure: " + str(e))  
                return  
          
        # Merge dos dataframes SkillCorner pela coluna "Player"  
        df_skillcorner = dfs_skillcorner[0]  
        if len(dfs_skillcorner) > 1:  
            for df_extra in dfs_skillcorner[1:]:  
                df_skillcorner = pd.merge(df_skillcorner, df_extra, on="Player", how="outer")  
    else:  
        st.error("É necessário carregar pelo menos um arquivo SkillCorner (Physical ou Overcome Pressure).")  
        return  
  
    st.subheader("Opções de Inclusão das Métricas")  
    incluir_physical = st.checkbox("Incluir dados de Physical Output", value=True)  
    incluir_pressure = st.checkbox("Incluir dados de Overcome Pressure", value=True)  
  
    # Filtrar colunas conforme checkboxes  
    colunas = ["Player"]  
    if incluir_physical:  
        colunas += [col for col in df_skillcorner.columns if col.startswith("Physical_Output_")]  
    if incluir_pressure:  
        colunas += [col for col in df_skillcorner.columns if col.startswith("Overcome_Pressure_")]  
    df_skillcorner = df_skillcorner[colunas]  
  
    st.write("Preview dos dados do SkillCorner ajustado:")  
    st.dataframe(df_skillcorner.head())  
  
    st.subheader("Match entre Wyscout e SkillCorner")  
    try:  
        automatic_matches, mismatches = process_matches(df_wyscout, df_skillcorner)  
        if mismatches:  
            st.warning("Encontrados " + str(len(mismatches)) + " jogadores que precisam de match manual")  
            manual_links = manual_link_interface(mismatches, df_wyscout["Player"].tolist())  
            if st.button("Aplicar Links e Gerar Excel"):  
                all_matches = {**automatic_matches, **manual_links}  
                rename_map = {skill: wyscout for skill, wyscout in all_matches.items()}  
                df_skillcorner_matched = df_skillcorner.copy()  
                df_skillcorner_matched["Player"] = df_skillcorner_matched["Player"].map(rename_map)  
                final_df = pd.merge(df_wyscout, df_skillcorner_matched, on="Player", how="inner")  
                output = BytesIO()  
                with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                    final_df.to_excel(writer, index=False)  
                st.download_button("📥 Download Excel Mesclado", data=output.getvalue(),  
                                   file_name="wyScout_skillcorner_merged.xlsx",  
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
                st.success("Arquivo gerado com " + str(len(final_df)) + " jogadores após resolução de mismatches")  
        else:  
            st.success("Todos os jogadores foram matched automaticamente!")  
            rename_map = {skill: wyscout for skill, wyscout in automatic_matches.items()}  
            df_skillcorner_matched = df_skillcorner.copy()  
            df_skillcorner_matched["Player"] = df_skillcorner_matched["Player"].map(rename_map)  
            final_df = pd.merge(df_wyscout, df_skillcorner_matched, on="Player", how="inner")  
            output = BytesIO()  
            with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                final_df.to_excel(writer, index=False)  
            st.download_button("📥 Download Excel Mesclado", data=output.getvalue(),  
                               file_name="wyScout_skillcorner_merged.xlsx",  
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")  
            st.success("Arquivo gerado com " + str(len(final_df)) + " jogadores")  
    except Exception as e:  
        st.error("Erro ao processar os arquivos: " + str(e))  
        st.write("Por favor, verifique se os arquivos estão no formato correto e tente novamente.")  
  
if __name__ == "__main__":  
    main()  
