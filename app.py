import streamlit as st  
import pandas as pd  
import numpy as np  
import base64  
from io import BytesIO  
  
def exact_match_only(source_df, target_df):  
    """  
    Realiza a correspondência exata 100% entre jogadores   
    dos dois dataframes, sem realizar nenhuma normalização adicional.  
    """  
    matches = {}  
    unmatched = []  
      
    source_players = source_df['Player'].dropna().unique()  
    target_players = set(target_df['Player'].dropna().unique())  
      
    for source_player in source_players:  
        if source_player in target_players:  
            matches[source_player] = source_player  
        else:  
            unmatched.append(source_player)  
              
    # Grava os resultados em um arquivo CSV para consulta  
    with open('player_matching_report.csv', 'w', encoding='utf-8') as f:  
        f.write('Source Player,Status\n')  
        for player in matches:  
            f.write(f'{player},Matched\n')  
        for player in unmatched:  
            f.write(f'{player},Unmatched\n')  
              
    return matches, unmatched  
  
def apply_matches(df, matches):  
    """  
    Aplica as correspondências encontradas ao dataframe original,  
    adicionando uma nova coluna 'Matched_Player'.  
    """  
    df['Matched_Player'] = df['Player'].map(matches)  
    return df  
  
def to_excel(df):  
    """  
    Converte o dataframe para um arquivo Excel em memória.  
    """  
    output = BytesIO()  
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:  
        df.to_excel(writer, index=False, sheet_name='Sheet1')  
    processed_data = output.getvalue()  
    return processed_data  
  
def download_link(object_to_download, download_filename, download_link_text):  
    """  
    Gera um link para download do objeto (arquivo Excel ou CSV) convertido para base64.  
    """  
    if isinstance(object_to_download, pd.DataFrame):  
        object_to_download = to_excel(object_to_download)  
      
    b64 = base64.b64encode(object_to_download).decode()  
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{download_filename}">{download_link_text}</a>'  
  
st.title('Player Matching App')  
st.write('Faça upload dos arquivos WyScout e SkillCorner para realizar o matching exato dos jogadores')  
  
# Upload dos arquivos  
wyscout_file = st.file_uploader("Carregar arquivo WyScout", type=['xlsx', 'xls', 'csv'])  
skillcorner_file = st.file_uploader("Carregar arquivo SkillCorner", type=['xlsx', 'xls', 'csv'])  
  
if wyscout_file and skillcorner_file:  
    try:  
        # Leitura dos arquivos  
        if wyscout_file.name.endswith('.csv'):  
            wyscout_df = pd.read_csv(wyscout_file)  
        else:  
            wyscout_df = pd.read_excel(wyscout_file)  
          
        if skillcorner_file.name.endswith('.csv'):  
            skillcorner_df = pd.read_csv(skillcorner_file)  
        else:  
            skillcorner_df = pd.read_excel(skillcorner_file)  
          
        # Seleção de colunas de interesse  
        st.write("Colunas disponíveis no WyScout:")  
        wyscout_cols = st.multiselect('Selecione as colunas que deseja manter do WyScout:', wyscout_df.columns.tolist())  
          
        st.write("Colunas disponíveis no SkillCorner:")  
        skillcorner_cols = st.multiselect('Selecione as colunas que deseja manter do SkillCorner:', skillcorner_df.columns.tolist())  
          
        if wyscout_cols and skillcorner_cols:  
            wyscout_subset = wyscout_df[wyscout_cols]  
            skillcorner_subset = skillcorner_df[skillcorner_cols]  
              
            # Realiza o matching exato entre jogadores  
            matches, unmatched = exact_match_only(wyscout_subset, skillcorner_subset)  
              
            matched_df = apply_matches(wyscout_subset.copy(), matches)  
              
            if len(matches) > 0:  
                st.success(f"Foram encontrados {len(matches)} matches exatos!")  
                st.write("Exemplo dos dados matched:")  
                st.dataframe(matched_df.head())  
                  
                if st.button("Download dos Dados Matched"):  
                    tmp_download_link = download_link(matched_df, 'matched_players.xlsx', 'Clique aqui para baixar os dados matched!')  
                    st.markdown(tmp_download_link, unsafe_allow_html=True)  
              
            if len(unmatched) > 0:  
                st.warning(f"Foram encontrados {len(unmatched)} jogadores sem match exato")  
                unmatched_df = pd.DataFrame({'Unmatched_Players': unmatched})  
                st.write("Jogadores sem match:")  
                st.dataframe(unmatched_df)  
                  
                if st.button("Download dos Jogadores Não Correspondidos"):  
                    tmp_download_link = download_link(unmatched_df, 'unmatched_players.xlsx', 'Clique aqui para baixar os jogadores não correspondidos!')  
                    st.markdown(tmp_download_link, unsafe_allow_html=True)  
      
    except Exception as e:  
        st.error(f"Ocorreu um erro: {str(e)}")  
else:  
    st.info("Por favor, carregue ambos os arquivos para iniciar o matching")  
