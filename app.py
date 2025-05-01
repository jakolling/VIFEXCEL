import streamlit as st  
import pandas as pd  
from io import BytesIO  
import hashlib  
from difflib import SequenceMatcher  
  
def similar(a, b):  
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()  
  
def find_best_match(skill_player, wyscout_players, threshold=0.8):  
    matches = [(wp, similar(skill_player, wp)) for wp in wyscout_players]  
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
            select_key = generate_unique_key(skill_player, idx, "select")  
            wyscout_player = st.selectbox(  
                "Selecionar jogador do WyScout",  
                ["Selecione um jogador"] + wyscout_players,  
                key=select_key  
            )  
              
        if wyscout_player != "Selecione um jogador":  
            manual_links[skill_player] = wyscout_player  
              
    return manual_links  
  
def main():  
    st.set_page_config(page_title="Merge WyScout & SkillCorner", layout="wide")  
    st.title("Mesclador WyScout & SkillCorner")  
      
    st.sidebar.title("Instruções")  
    st.sidebar.write("""  
    1. Faça upload dos arquivos Excel  
    2. O sistema fará o match automático dos jogadores  
    3. Resolva manualmente apenas os mismatches identificados  
    4. Baixe o arquivo Excel mesclado final  
    """)  
      
    wyscout_file = st.file_uploader("Database WyScout", type=["xlsx"])  
    physical_file = st.file_uploader("SkillCorner Physical Output", type=["xlsx"])  
    pressure_file = st.file_uploader("SkillCorner Overcome Pressure", type=["xlsx"])  
  
    if all([wyscout_file, physical_file, pressure_file]):  
        try:  
            df_wyscout = pd.read_excel(wyscout_file)  
            df_physical = pd.read_excel(physical_file)  
            df_pressure = pd.read_excel(pressure_file)  
  
            # Merge SkillCorner data first  
            df_skillcorner = pd.merge(df_physical, df_pressure, on="Player", how="outer")  
              
            # Process automatic matches and mismatches  
            automatic_matches, mismatches = process_matches(df_wyscout, df_skillcorner)  
              
            # Display matching summary  
            st.write("### Resumo do Processamento:")  
            st.write("- Matches automáticos encontrados: " + str(len(automatic_matches)))  
            st.write("- Mismatches para resolução manual: " + str(len(mismatches)))  
              
            if mismatches:  
                st.warning("Encontrados " + str(len(mismatches)) + " jogadores que precisam de match manual")  
                manual_links = manual_link_interface(mismatches, df_wyscout["Player"].tolist())  
                  
                if st.button("Aplicar Links e Gerar Excel"):  
                    # Combine automatic and manual matches  
                    all_matches = {**automatic_matches, **manual_links}  
                      
                    # Create mapping dictionary for renaming  
                    rename_map = {skill: wyscout for skill, wyscout in all_matches.items()}  
                      
                    # Apply renaming to SkillCorner data  
                    df_skillcorner_matched = df_skillcorner.copy()  
                    df_skillcorner_matched["Player"] = df_skillcorner_matched["Player"].map(rename_map)  
                      
                    # Merge with WyScout data  
                    final_df = pd.merge(df_wyscout, df_skillcorner_matched, on="Player", how="inner")  
                      
                    output = BytesIO()  
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                        final_df.to_excel(writer, index=False)  
                      
                    st.download_button(  
                        "📥 Download Excel Mesclado",  
                        data=output.getvalue(),  
                        file_name="wyScout_skillcorner_merged.xlsx",  
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
                    )  
                    st.success("Arquivo gerado com " + str(len(final_df)) + " jogadores após resolução de mismatches")  
            else:  
                st.success("Todos os jogadores foram matched automaticamente!")  
                  
                # Apply automatic matches  
                rename_map = {skill: wyscout for skill, wyscout in automatic_matches.items()}  
                df_skillcorner_matched = df_skillcorner.copy()  
                df_skillcorner_matched["Player"] = df_skillcorner_matched["Player"].map(rename_map)  
                  
                # Merge with WyScout data  
                final_df = pd.merge(df_wyscout, df_skillcorner_matched, on="Player", how="inner")  
                  
                output = BytesIO()  
                with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                    final_df.to_excel(writer, index=False)  
                  
                st.download_button(  
                    "📥 Download Excel Mesclado",  
                    data=output.getvalue(),  
                    file_name="wyScout_skillcorner_merged.xlsx",  
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
                )  
                st.success("Arquivo gerado com " + str(len(final_df)) + " jogadores")  
                  
        except Exception as e:  
            st.error("Erro ao processar os arquivos: " + str(e))  
            st.write("Por favor, verifique se os arquivos estão no formato correto e tente novamente.")  
  
if __name__ == "__main__":  
    main()  
