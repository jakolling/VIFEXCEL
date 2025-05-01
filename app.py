import streamlit as st  
import pandas as pd  
from io import BytesIO  
  
def main():  
    st.title("Merge Performance Metrics")  
      
    wyscout_file = st.file_uploader("WyScout File", type=["csv", "xlsx"])  
    skillcorner_file = st.file_uploader("SkillCorner File", type=["csv", "xlsx"])  
  
    if wyscout_file and skillcorner_file:  
        try:  
            df_wyscout = pd.read_csv(wyscout_file) if wyscout_file.name.endswith('.csv') else pd.read_excel(wyscout_file)  
            df_skillcorner = pd.read_csv(skillcorner_file) if skillcorner_file.name.endswith('.csv') else pd.read_excel(skillcorner_file)  
  
            # Remove colunas redundantes  
            redundant_cols = ['Player', 'player_id', 'ID', 'Name', 'player_name', 'Minutes', 'minutes']  
            metrics_wyscout = df_wyscout.drop(columns=[col for col in redundant_cols if col in df_wyscout.columns])  
            metrics_skillcorner = df_skillcorner.drop(columns=[col for col in redundant_cols if col in df_skillcorner.columns])  
              
            # Remove prefixos das colunas do SkillCorner  
            metrics_skillcorner.columns = metrics_skillcorner.columns.str.replace('Physical_Output_', '')  
            metrics_skillcorner.columns = metrics_skillcorner.columns.str.replace('Overcome_Pressure_', '')  
              
            # Merge horizontal dos dataframes  
            final_df = pd.concat([metrics_wyscout, metrics_skillcorner], axis=1)  
              
            # Remove colunas duplicadas  
            final_df = final_df.loc[:,~final_df.columns.duplicated()]  
              
            output = BytesIO()  
            with pd.ExcelWriter(output, engine='openpyxl') as writer:  
                final_df.to_excel(writer, index=False)  
              
            st.download_button(  
                "Download Excel",  
                data=output.getvalue(),  
                file_name="metrics.xlsx",  
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
            )  
  
        except Exception as e:  
            st.error(f"Error: {str(e)}")  
  
if __name__ == "__main__":  
    main()  
