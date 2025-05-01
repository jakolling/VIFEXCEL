import streamlit as st  
import pandas as pd  
from io import BytesIO  
from difflib import SequenceMatcher  
  
# Função para calcular similaridade entre nomes  
def name_similarity(a, b):  
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()  
  
# Função para encontrar o melhor match, com threshold default de 0.7  
def find_best_match(name, candidates, threshold=0.7):  
    matches = [(c, name_similarity(name, c)) for c in candidates]  
    best_match = max(matches, key=lambda x: x[1])  
    return best_match[0] if best_match[1] >= threshold else None  
  
# Interface para selecção manual dos matches que não foram encontrados automaticamente  
def manual_link_interface(mismatched_players, wyscout_players):  
    st.subheader("Resolver Mismatches")  
    manual_links = {}  
    options = [""] + wyscout_players  
    for idx, skill_player in enumerate(mismatched_players):  
        manual_choice = st.selectbox(  
            f"Match para {skill_player}",  
            options=options,  
            key=f"match_{idx}"  
        )  
        if manual_choice != "":  
            manual_links[skill_player] = manual_choice  
    return manual_links  
  
def main():  
    st.title("Merge de Métricas de Performance")  
      
    # Upload dos arquivos  
    wyscout_file = st.file_uploader("Arquivo WyScout", type=['csv', 'xlsx'])  
    skillcorner_file = st.file_uploader("Arquivo SkillCorner", type=['csv', 'xlsx'])  
      
    if not wyscout_file and not skillcorner_file:  
        st.info("Utilizando conjuntos de dados de exemplo")  
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
            df_wyscout = pd.read_csv(wyscout_file) if wyscout_file.name.endswith('.csv') else pd.read_excel(wyscout_file)  
            df_skillcorner = pd.read_csv(skillcorner_file) if skillcorner_file.name.endswith('.csv') else pd.read_excel(skillcorner_file)  
        except Exception as e:  
            st.error("Erro ao carregar os arquivos: " + str(e))  
            return  
  
    # Processo de matching dos jogadores  
    wyscout_players = df_wyscout["Player"].tolist()  
    skillcorner_players = df_skillcorner["Player"].unique().tolist()  
      
    automatic_matches = {}  
    mismatches = []  
    for skill_player in skillcorner_players:  
        match = find_best_match(skill_player, wyscout_players)  
        if match:  
            automatic_matches[skill_player] = match  
        else:  
            mismatches.append(skill_player)  
      
    if mismatches:  
        manual_matches = manual_link_interface(mismatches, wyscout_players)  
        all_matches = {**automatic_matches, **manual_matches}  
    else:  
        all_matches = automatic_matches  
      
    if st.button("Gerar Excel"):  
        # Mapear os nomes do SkillCorner para os nomes encontrados no WyScout  
        df_skillcorner_matched = df_skillcorner.copy()  
        df_skillcorner_matched["Player"] = df_skillcorner_matched["Player"].map(lambda x: all_matches.get(x, x))  
          
        # Mesclar os dataframes com base na coluna "Player"  
        merged_df = pd.merge(df_wyscout, df_skillcorner_matched, on="Player", how="outer")  
          
        # Remover colunas redundantes: nome, minutos, IDs e outras colunas não relativas às métricas  
        redundant_cols = ['Player', 'player_id', 'ID', 'Name', 'player_name', 'Minutes', 'minutes', 'played_id', 'nome', 'minutos']  
        final_df = merged_df.drop(columns=[col for col in redundant_cols if col in merged_df.columns])  
          
        st.subheader("Tabela Mesclada (Somente Métricas)")  
        st.dataframe(final_df)  
          
        output = BytesIO()  
        with pd.ExcelWriter(output, engine='openpyxl') as writer:  
            final_df.to_excel(writer, index=False)  
          
        st.download_button(  
            "📥 Download Excel",  
            data=output.getvalue(),  
            file_name="metrics.xlsx",  
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
        )  
  
if __name__ == "__main__":  
    main()  
