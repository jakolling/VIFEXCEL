import streamlit as st  
import pandas as pd  
from io import BytesIO  
  
def process_mismatches(df_wyscout, df_skillcorner):  
    merged = pd.merge(df_wyscout, df_skillcorner, on="Player", how="outer", indicator=True)  
    wyscout_only = merged[merged["_merge"] == "left_only"]["Player"].tolist()  
    skill_only = merged[merged["_merge"] == "right_only"]["Player"].tolist()  
    return wyscout_only, skill_only  
  
def manual_link_interface(wyscout_players, skillcorner_players):  
    st.subheader("Resolver Mismatches")  
    links = {}  
    players_to_exclude = []  
      
    for wyscout_player in wyscout_players:  
        col1, col2, col3 = st.columns([2, 2, 1])  
          
        with col1:  
            st.write(f"WyScout: {wyscout_player}")  
              
        with col2:  
            skill_player = st.selectbox(  
                "Linkar com jogador do SkillCorner",  
                ["Selecione um jogador"] + skillcorner_players,  
                key=f"link_{wyscout_player}"  
            )  
              
        with col3:  
            exclude = st.checkbox("Excluir", key=f"exclude_{wyscout_player}")  
          
        if skill_player != "Selecione um jogador":  
            links[wyscout_player] = skill_player  
        if exclude:  
            players_to_exclude.append(wyscout_player)  
              
    return links, players_to_exclude  
  
def main():  
    st.set_page_config(page_title="Merge WyScout & SkillCorner", layout="wide")  
    st.title("Mesclador WyScout & SkillCorner com Resolução Manual")  
      
    st.sidebar.title("Instruções")  
    st.sidebar.write("""  
    1. Faça upload dos arquivos Excel do WyScout e SkillCorner.  
    2. O app identificará automaticamente os mismatches.  
    3. Resolva os mismatches manualmente usando a interface.  
    4. Baixe o arquivo Excel mesclado final.  
    """)  
      
    wyscout_file = st.file_uploader("Database WyScout", type=["xlsx"])  
    physical_file = st.file_uploader("SkillCorner Physical Output", type=["xlsx"])  
    pressure_file = st.file_uploader("SkillCorner Overcome Pressure", type=["xlsx"])  
  
    if all([wyscout_file, physical_file, pressure_file]):  
        try:  
            df_wyscout = pd.read_excel(wyscout_file)  
            df_physical = pd.read_excel(physical_file)  
            df_pressure = pd.read_excel(pressure_file)  
  
            st.write("### Preview dos dados:")  
            col1, col2, col3 = st.columns(3)  
            with col1:  
                st.write("WyScout Data:")  
                st.write(df_wyscout.head())  
            with col2:  
                st.write("Physical Output Data:")  
                st.write(df_physical.head())  
            with col3:  
                st.write("Pressure Data:")  
                st.write(df_pressure.head())  
  
            df_skillcorner = pd.merge(df_physical, df_pressure, on="Player", how="outer")  
            wyscout_only, skill_only = process_mismatches(df_wyscout, df_skillcorner)  
              
            if wyscout_only or skill_only:  
                st.warning(f"Encontrados {len(wyscout_only)} jogadores apenas no WyScout e {len(skill_only)} apenas no SkillCorner")  
                  
                links, exclusions = manual_link_interface(wyscout_only, skill_only)  
                  
                if st.button("Aplicar Links e Gerar Excel"):  
                    df_skillcorner_copy = df_skillcorner.copy()  
                    for wyscout_name, skill_name in links.items():  
                        df_skillcorner_copy.loc[df_skillcorner_copy["Player"] == skill_name, "Player"] = wyscout_name  
                      
                    df_wyscout = df_wyscout[~df_wyscout["Player"].isin(exclusions)]  
                    final_df = pd.merge(df_wyscout, df_skillcorner_copy, on="Player", how="inner")  
                      
                    output = BytesIO()  
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                        final_df.to_excel(writer, index=False)  
                      
                    st.download_button(  
                        "📥 Download Excel Mesclado",  
                        data=output.getvalue(),  
                        file_name="wyScout_skillcorner_merged.xlsx",  
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
                    )  
                    st.success(f"Arquivo gerado com {len(final_df)} jogadores após resolução de mismatches")  
            else:  
                st.success("Nenhum mismatch encontrado!")  
                final_df = pd.merge(df_wyscout, df_skillcorner, on="Player", how="inner")  
                  
                output = BytesIO()  
                with pd.ExcelWriter(output, engine="openpyxl") as writer:  
                    final_df.to_excel(writer, index=False)  
                  
                st.download_button(  
                    "📥 Download Excel Mesclado",  
                    data=output.getvalue(),  
                    file_name="wyScout_skillcorner_merged.xlsx",  
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
                )  
        except Exception as e:  
            st.error(f"Erro ao processar os arquivos: {str(e)}")  
            st.write("Por favor, verifique se os arquivos estão no formato correto e tente novamente.")  
  
if __name__ == "__main__":  
    main()  
