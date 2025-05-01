import streamlit as st  
import pandas as pd  
from io import BytesIO  
import hashlib  
import unicodedata  
from difflib import SequenceMatcher  
 
st.set_page_config(page_title="Merge WyScout & SkillCorner", layout="wide")  
 
def preprocess_name(name):  
   if not isinstance(name, str):  
       return {'full': '', 'parts': [], 'last_name': '', 'initials': ''}  
   name = unicodedata.normalize('NFKD', str(name)).encode('ASCII', 'ignore').decode('ASCII')  
   name = name.lower().strip()  
   parts = name.replace('.', ' ').split()  
   last_name = parts[-1] if parts else ''  
   initials = ''.join(p[0] for p in parts[:-1]) if len(parts) > 1 else ''  
   return {  
       'full': name,  
       'parts': parts,  
       'last_name': last_name,  
       'initials': initials  
   }  
 
def improved_match_score(name1, name2):  
   n1 = preprocess_name(str(name1))  
   n2 = preprocess_name(str(name2))  
     
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
   unique_string = str(player_name) + '_' + str(idx) + '_' + prefix  
   return hashlib.md5(unique_string.encode()).hexdigest()  
 
def manual_link_interface(mismatched_players, wyscout_players):  
   st.subheader("Resolver Mismatches")  
   manual_links = {}  
     
   for idx, skill_player in enumerate(mismatched_players):  
       col1, col2 = st.columns([2,2])  
       with col1:  
           st.write("SkillCorner: " + str(skill_player))  
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
 
st.title("Merge WyScout & SkillCorner")  
 
uploaded_files = st.file_uploader(  
   "Upload dos arquivos Excel (WyScout e SkillCorner)",   
   type=["xlsx", "xls"],  
   accept_multiple_files=True  
)  
 
if len(uploaded_files) == 2:  
   try:  
       with st.spinner("Processando arquivos..."):  
           df_wyscout = pd.read_excel(uploaded_files[0])  
           df_skillcorner = pd.read_excel(uploaded_files[1])  
             
           st.success("✅ Arquivos carregados com sucesso!")  
           st.write("WyScout:", df_wyscout.shape)  
           st.write("SkillCorner:", df_skillcorner.shape)  
             
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
                     
                   st.download_button(  
                       "📥 Download Excel Mesclado",  
                       data=output.getvalue(),  
                       file_name="wyScout_skillcorner_merged.xlsx",  
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
                   )  
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
else:  
   st.info("👆 Por favor, faça upload dos 2 arquivos Excel (WyScout e SkillCorner)")  
