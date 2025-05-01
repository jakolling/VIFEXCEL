import streamlit as st  
import pandas as pd  
from difflib import SequenceMatcher  
from io import BytesIO  
  
def name_similarity(a, b):  
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()  
  
def find_best_match(name, candidates, threshold=0.7):  
    matches = [(c, name_similarity(name, c)) for c in candidates]  
    best_match = max(matches, key=lambda x: x[1])  
    return best_match[0] if best_match[1] >= threshold else None  
  
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
    st.title("Merge Métricas de Performance")  
      
    wyscout_file = st.file_uploader("WyScout", type=['csv', 'xlsx'])  
    skillcorner_file = st.file_uploader("SkillCorner", type=['csv', 'xlsx'])  
  
    if wyscout_file and skillcorner_file:  
        try:  
            df_wyscout = pd.read_csv(wyscout_file) if wyscout_file.name.endswith('.csv') else pd.read_excel(wyscout_file)  
            df_skillcorner = pd.read_csv(skillcorner_file) if skillcorner_file.name.endswith('.csv') else pd.read_excel(skillcorner_file)  
  
            redundant_cols = ['Player', 'player_id', 'ID', 'Name', 'player_name', 'Minutes', 'minutes', 'played_id']  
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
                df_skillcorner_matched = df_skillcorner.copy()  
                df_skillcorner_matched["Player"] = df_skillcorner_matched["Player"].map(lambda x: all_matches.get(x, None))  
                  
                merged_df = pd.merge(df_wyscout, df_skillcorner_matched, on="Player", how="outer")  
                final_df = merged_df.drop(columns=[col for col in redundant_cols if col in merged_df.columns])  
                  
                output = BytesIO()  
                with pd.ExcelWriter(output, engine='openpyxl') as writer:  
                    final_df.to_excel(writer, index=False)  
                  
                st.download_button(  
                    "📥 Download Excel",  
                    data=output.getvalue(),  
                    file_name="metrics.xlsx",  
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"  
                )  
  
        except Exception as e:  
            st.error(f"Erro: {str(e)}")  
  
if __name__ == "__main__":  
    main()  
