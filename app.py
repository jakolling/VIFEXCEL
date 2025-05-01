# Save the corrected app.py
with open('app.py', 'w') as f:
    f.write("""import streamlit as st
import pandas as pd
from thefuzz import fuzz, process
import base64
from io import BytesIO

def init_session_state():
    defaults = {
        'confirmed_matches': {},
        'auto_matched': False,
        'rejected_players': set(),
        'match_history': [],
        'matched_skillcorner_players': set(),
        'suggested_match': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def find_best_match(name, choices, min_score=65):
    if not isinstance(name, str) or not choices:
        return None
    name_parts = name.strip().split()
    if len(name_parts) < 2:
        return None
    first_letter = name_parts[0][0].lower()
    last_name = name_parts[-1].lower()
    filtered_choices = [c for c in choices if isinstance(c, str) and 
                       len(c.split()) > 0 and
                       c.split()[0][0].lower() == first_letter and 
                       c.lower().endswith(last_name)]
    if not filtered_choices:
        filtered_choices = [c for c in choices if isinstance(c, str) and
                          len(c.split()) > 0 and
                          c.split()[0][0].lower() == first_letter]
    if filtered_choices:
        best_match = process.extractOne(name, filtered_choices, scorer=fuzz.token_sort_ratio)
        return best_match[0] if best_match and best_match[1] >= min_score else None
    return None

def main():
    st.set_page_config(page_title="Player Matcher", layout="wide")
    init_session_state()
    
    st.title('Player Matcher')
    st.write('Match players between databases')
    
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
        try:
            wyscout_df = pd.read_csv(wyscout_file) if wyscout_file.name.endswith('.csv') else pd.read_excel(wyscout_file)
            physical_df = pd.read_csv(physical_file) if physical_file.name.endswith('.csv') else pd.read_excel(physical_file)
            overcome_df = pd.read_csv(overcome_file) if overcome_file.name.endswith('.csv') else pd.read_excel(overcome_file)
            
            unmatched_players = [p for p in wyscout_df['Player'].dropna().unique() 
                               if p not in st.session_state.confirmed_matches 
                               and p not in st.session_state.rejected_players]
            
            if unmatched_players:
                current_player = unmatched_players[0]
                st.write(f'Current player: **{current_player}**')
                
                available_skillcorner = [p for p in physical_df['Player'].dropna().unique() 
                                       if p not in st.session_state.matched_skillcorner_players]
                
                if not st.session_state.auto_matched:
                    suggested_match = find_best_match(current_player, available_skillcorner)
                    if suggested_match:
                        st.session_state.suggested_match = suggested_match
                        st.session_state.auto_matched = True
                
                col_match, col_actions1, col_actions2 = st.columns([2,1,1])
                
                with col_match:
                    select_index = 0
                    if st.session_state.suggested_match in available_skillcorner:
                        select_index = available_skillcorner.index(st.session_state.suggested_match) + 1
                    selected_match = st.selectbox('Select matching player', options=[''] + available_skillcorner, index=select_index)
                
                with col_actions1:
                    if st.button('✅ Confirm Match', disabled=not selected_match):
                        st.session_state.confirmed_matches[current_player] = selected_match
                        st.session_state.matched_skillcorner_players.add(selected_match)
                        st.session_state.match_history.append(('confirm', current_player, selected_match))
                        st.session_state.auto_matched = False
                        st.session_state.suggested_match = None
                        st.experimental_rerun()
                    
                    if st.button('❌ Reject Player'):
                        st.session_state.rejected_players.add(current_player)
                        st.session_state.match_history.append(('reject', current_player, None))
                        st.session_state.auto_matched = False
                        st.session_state.suggested_match = None
                        st.experimental_rerun()
                
                with col_actions2:
                    if st.button('↩️ Undo Last', disabled=len(st.session_state.match_history) == 0):
                        if st.session_state.match_history:
                            action, player, match = st.session_state.match_history.pop()
                            if action == 'confirm':
                                matched_player = st.session_state.confirmed_matches[player]
                                st.session_state.matched_skillcorner_players.remove(matched_player)
                                del st.session_state.confirmed_matches[player]
                            elif action == 'reject':
                                st.session_state.rejected_players.remove(player)
                            st.session_state.auto_matched = False
                            st.session_state.suggested_match = None
                            st.experimental_rerun()
                
                st.write('### Progress')
                progress = len(st.session_state.confirmed_matches) / len(wyscout_df['Player'].dropna().unique())
                st.progress(progress)
                st.write(f"Matched: {len(st.session_state.confirmed_matches)} of {len(wyscout_df['Player'].dropna().unique())} players")
            else:
                st.success('All players have been matched or rejected!')
        except Exception as e:
            st.error(f'Error processing files: {str(e)}')
    else:
        st.info('Please upload all required files to begin')

if __name__ == '__main__':
    main()""")

print("Updated app.py saved without syntax errors. Run with: streamlit run app.py")
