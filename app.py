import streamlit as st  
import pandas as pd  
from io import BytesIO  
  
def main():  
    st.title("Merge de Métricas de Performance - Eliminando Colunas Redundantes")  
  
    wyscout_file = st.file_uploader("Arquivo WyScout", type=['csv', 'xlsx'])  
    skillcorner_file = st.file_uploader("Arquivo SkillCorner", type=['csv', 'xlsx'])  
      
    if not wyscout_file and not skillcorner_file:  
        st.info("Usando conjuntos de dados de exemplo")  
        data_wyscout = {  
            "Player": ["João", "Maria", "Carlos"],  
            "Goals": [2, 1, 0],  
            "Assists": [0, 1, 0],  
            "player_id": [101, 102, 103],  
            "Minutes": [90, 85, 80]  
        }  
        data_skillcorner = {  
            "Player": ["João", "Maria", "Pedro"],  
            "Passes": [30, 20, 25],  
            "Tackles": [5, 2, 3],  
            "Minutes": [90, 85, 80],  
            "player_id": [101, 102, 104]  
        }  
        df_wyscout = pd.DataFrame(data_wyscout)  
        df_skillcorner = pd.DataFrame(data_skillcorner)  
    else:  
        try:  
            df_wyscout = pd.read_csv(wyscout_file) if wyscout_file and wyscout_file.name.endswith('.csv') else pd.read_excel(wyscout_file)  
            df_skillcorner = pd.read_csv(skillcorner_file) if skillcorner_file and skillcorner_file.name.endswith('.csv') else pd.read_excel(skillcorner_file)  
        except Exception as e:  
            st.error("Erro ao carregar os arquivos: " + str(e))  
            return  
  
    merged_df = pd.merge(df_wyscout, df_skillcorner, on="Player", how="outer")  
      
    redundant_cols = ['Player', 'player_id', 'ID', 'Name', 'player_name', 'Minutes', 'minutes', 'played_id']  
    final_df = merged_df.drop(columns=[col for col in redundant_cols if col in merged_df.columns])  
      
    st.subheader("Tabela Mesclada (Apenas Métricas)")  
    st.dataframe(final_df)  
      
    output = BytesIO()  
    with pd.ExcelWriter(output, engine="openpyxl") as writer:  
        final_df.to_excel(writer, index=False)  
      
    st.download_button(  
        "📥 Download Excel",  
        data=output.getvalue(),  
        file_name="metrics.xlsx",  
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
    )  
  
if __name__ == "__main__":  
    main()  
