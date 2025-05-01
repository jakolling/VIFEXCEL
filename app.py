import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process

st.set_page_config(page_title="Player Matcher", layout="wide")

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='MatchedData')
    return output.getvalue()

def download_link(object_to_download, download_filename, download_link_text):
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = to_excel(object_to_download)
    b64 = base64.b64encode(object_to_download).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

def find_best_match(name, choices, min_score=65):
    '''
    Encontra a melhor correspondência para um nome de jogador entre as opções disponíveis.
    
    Estratégia de correspondência:
    1. Usa primeira letra do primeiro nome + último sobrenome
    2. Se não encontrar, tenta só a primeira letra do primeiro nome
    3. Se ainda não encontrar, usa correspondência fuzzy completa
    
    Args:
        name (str): Nome do jogador no formato WyScout
        choices (list): Lista de nomes de jogadores do SkillCorner
        min_score (int): Pontuação mínima para considerar uma correspondência (padrão: 65)
    
    Returns:
        str or None: Nome do jogador correspondente ou None se não encontrar
    '''
    name_parts = name.strip().split()
    if len(name_parts) < 2:
        return None
        
    first_letter = name_parts[0][0].lower()
    last_name = name_parts[-1].lower()
    
    # Tenta encontrar correspondência exata (primeira letra + último sobrenome)
    filtered_choices = [c for c in choices if 
                       c.split()[0][0].lower() == first_letter and 
                       c.lower().endswith(last_name)]
    
    # Se não encontrar, tenta só pela primeira letra
    if not filtered_choices:
        filtered_choices = [c for c in choices if c.split()[0][0].lower() == first_letter]
    
    # Aplica correspondência fuzzy nas opções filtradas ou em todas as opções
    if filtered_choices:
        best_match = process.extractOne(name, filtered_choices, scorer=fuzz.token_sort_ratio)
    else:
        best_match = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
        
    if best_match and best_match[1] >= min_score:
        return best_match[0]
    return None

# Initialize session state variables
if 'confirmed_matches' not in st.session_state:
    st.session_state.confirmed_matches = {}
if 'auto_matched' not in st.session_state:
    st.session_state.auto_matched = False
if 'rejected_players' not in st.session_state:
    st.session_state.rejected_players = set()
if 'match_history' not in st.session_state:
    st.session_state.match_history = []
if 'matched_skillcorner_players' not in st.session_state:
    st.session_state.matched_skillcorner_players = set()

st.title('⚽ Player Matcher')
st.write('Match players between WyScout and SkillCorner databases')

# File uploaders
col1, col2, col3 = st.columns(3)

with col1:
    st.write('### WyScout Data')
    wyscout_file = st.file_uploader('Upload WyScout file', type=['csv', 'xlsx'])

with col2:
    st.write('### Physical Data')
    physical_file = st.file_uploader('Upload Physical file', type=['csv', 'xlsx'])

with col3:
    st.write('### Overcome Data')
    overcome_file = st.file_uploader('Upload Overcome file', type=['csv', 'xlsx'])

if all([wyscout_file, physical_file, overcome_file]):
    # Load data
    if wyscout_file.name.endswith('.csv'):
        wyscout_df = pd.read_csv(wyscout_file)
    else:
        wyscout_df = pd.read_excel(wyscout_file)
    
    if physical_file.name.endswith('.csv'):
        physical_df = pd.read_csv(physical_file)
    else:
        physical_df = pd.read_excel(physical_file)
    
    if overcome_file.name.endswith('.csv'):
        overcome_df = pd.read_csv(overcome_file)
    else:
        overcome_df = pd.read_excel(overcome_file)
    
    # Column selection
    st.write('### Select Columns')
    col_physical, col_overcome = st.columns(2)
    
    with col_physical:
        st.write('Physical Metrics')
        selected_physical = st.multiselect(
            'Select physical metrics',
            [col for col in physical_df.columns if col != 'Player'],
            key='physical_metrics'
        )
    
    with col_overcome:
        st.write('Overcome Metrics')
        selected_overcome = st.multiselect(
            'Select overcome metrics',
            [col for col in overcome_df.columns if col != 'Player'],
            key='overcome_metrics'
        )
    
    # Player matching interface
    st.write('### Match Players')
    
    # Get unmatched players
    unmatched_players = [p for p in wyscout_df['Player'].dropna().unique() 
                        if p not in st.session_state.confirmed_matches 
                        and p not in st.session_state.rejected_players]
    
    if unmatched_players:
        current_player = unmatched_players[0]
        st.write(f'Current player: **{current_player}**')
        
        # Get available SkillCorner players (not already matched)
        available_skillcorner = [p for p in physical_df['Player'].unique() 
                               if p not in st.session_state.matched_skillcorner_players]
        
        # Find best match if not already auto-matched
        if not st.session_state.auto_matched:
            suggested_match = find_best_match(current_player, available_skillcorner)
            if suggested_match:
                st.session_state.suggested_match = suggested_match
                st.session_state.auto_matched = True
        
        col_match, col_actions1, col_actions2 = st.columns([2,1,1])
        
        with col_match:
            selected_match = st.selectbox(
                'Select matching player',
                options=[''] + available_skillcorner,
                index=0 if not hasattr(st.session_state, 'suggested_match') 
                      else available_skillcorner.index(st.session_state.suggested_match) + 1
            )
        
        with col_actions1:
            if st.button('✅ Confirm Match', disabled=not selected_match):
                st.session_state.confirmed_matches[current_player] = selected_match
                st.session_state.matched_skillcorner_players.add(selected_match)
                st.session_state.match_history.append(('confirm', current_player, selected_match))
                st.session_state.auto_matched = False
                st.rerun()
            
            if st.button('❌ Reject Player'):
                st.session_state.rejected_players.add(current_player)
                st.session_state.match_history.append(('reject', current_player, None))
                st.session_state.auto_matched = False
                st.rerun()
            
            if st.button('🔄 Reset All'):
                st.session_state.confirmed_matches = {}
                st.session_state.auto_matched = False
                st.session_state.rejected_players = set()
                st.session_state.match_history = []
                st.session_state.matched_skillcorner_players = set()
                st.rerun()
        
        with col_actions2:
            if st.button('↩️ Undo Last', help='Undo last match', disabled=len(st.session_state.match_history) == 0):
                if st.session_state.match_history:
                    action, player, match = st.session_state.match_history.pop()
                    if action == 'confirm':
                        matched_player = st.session_state.confirmed_matches[player]
                        st.session_state.matched_skillcorner_players.remove(matched_player)
                        del st.session_state.confirmed_matches[player]
                    elif action == 'reject':
                        st.session_state.rejected_players.remove(player)
                    st.rerun()
        
        if st.button('📥 Export Data', help='Download matched data as Excel'):
            wyscout_df['Matched_Player'] = wyscout_df['Player'].map(st.session_state.confirmed_matches)
            wyscout_matched = wyscout_df.dropna(subset=['Matched_Player'])
            
            physical_subset = physical_df[['Player'] + selected_physical]
            overcome_subset = overcome_df[['Player'] + selected_overcome]
            
            merged_df = pd.merge(
                wyscout_matched,
                physical_subset,
                left_on='Matched_Player',
                right_on='Player',
                how='left',
                suffixes=('_WyScout', '_Physical')
            )
            
            final_df = pd.merge(
                merged_df,
                overcome_subset,
                left_on='Matched_Player',
                right_on='Player',
                how='left',
                suffixes=('', '_Overcome')
            ).dropna(subset=['Player'])
            
            download = download_link(final_df, 'matched_players.xlsx', '📥 Download Excel File')
            st.markdown(download, unsafe_allow_html=True)
        
        st.write('### Progress')
        progress = len(st.session_state.confirmed_matches) / len(wyscout_df['Player'].dropna().unique())
        st.progress(progress)
        st.write(f"Matched: {len(st.session_state.confirmed_matches)} of {len(wyscout_df['Player'].dropna().unique())} players")

        st.write('### Rejected Players')
        if st.session_state.rejected_players:
            st.write(f"Total rejected: {len(st.session_state.rejected_players)}")
            if st.button('Show Rejected'):
                st.write(sorted(list(st.session_state.rejected_players)))
    else:
        st.success('All players have been matched or rejected!')
else:
    st.info('Please upload all required files to begin matching')
