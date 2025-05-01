import streamlit as st
import pandas as pd
from io import BytesIO
import hashlib
import unicodedata
from difflib import SequenceMatcher

streamlit run app.py

def preprocess_name(name):
    name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
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
    n1 = preprocess_name(name1)
    n2 = preprocess_name(name2)
    
    if n1['full'] == n2['full']:
        return 1.0
    
    if n1['last_name'] == n2['last_name']:
        if (n1['initials'] and n1['initials'] in n2['full']) or \
           (n2['initials'] and n2['initials'] in n1['full']):
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
    st.sidebar.write(\"\"\"
    1. Faça upload dos arquivos Excel
    2. O sistema fará o match automático dos jogadores
    3. Resolva manualmente apenas os mismatches identificados
    4. Baixe o arquivo Excel mesclado final
    \"\"\")
    
    wyscout_file = st.file_uploader("Database WyScout", type=["xlsx"])
    physical_file = st.file_uploader("SkillCorner Physical Output", type=["xlsx"])
    pressure_file = st.file_uploader("SkillCorner Overcome Pressure", type=["xlsx"])

    if all([wyscout_file, physical_file, pressure_file]):
        try:
            df_wyscout = pd.read_excel(wyscout_file)
            df_physical = pd.read_excel(physical_file)
            df_pressure = pd.read_excel(pressure_file)

            df_skillcorner = pd.merge(df_physical, df_pressure, on="Player", how="outer")
            
            automatic_matches, mismatches = process_matches(df_wyscout, df_skillcorner)
            
            st.write("### Resumo do Processamento:")
            st.write("- Matches automáticos encontrados: " + str(len(automatic_matches)))
            st.write("- Mismatches para resolução manual: " + str(len(mismatches)))
            
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

if __name__ == "__main__":
    main()"""

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_content)

print("Updated app.py created with improved name matching")
