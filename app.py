with open('app.py', 'w') as f:
    f.write('''import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process
from collections import deque

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='MatchedData')
    return output.getvalue()

def download_link(object_to_download, download_filename, download_link_text):
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = to_excel(object_to_download)
    b64 = base64.b64encode(object_to_download).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

def find_best_match(name, choices, min_score=65):
    best_match = process.extractOne(name, choices, scorer=fuzz.token_sort_ratio)
    if best_match and best_match[1] >= min_score:
        return best_match[0]
    return None

def get_selection_index(current_selection, choices):
    try:
        if current_selection and current_selection != "-- None --" and current_selection in choices:
            return choices.index(current_selection) + 1
    except (ValueError, TypeError):
        pass
    return 0

st.set_page_config(layout="wide")
st.title('Player Matching Tool')

if 'temp_selections' not in st.session_state:
    st.session_state.temp_selections = {}
if 'confirmed_matches' not in st.session_state:
    st.session_state.confirmed_matches = {}
if 'rejected_players' not in st.session_state:
    st.session_state.rejected_players = set()
if 'page_number' not in st.session_state:
    st.session_state.page_number = 0
if 'auto_matched' not in st.session_state:
    st.session_state.auto_matched = False
if 'match_history' not in st.session_state:
    st.session_state.match_history = deque(maxlen=10)

col1, col2, col3 = st.columns(3)
with col1:
    wyscout_file = st.file_uploader("Upload WyScout file", type=['xlsx','xls','csv'])
with col2:
    physical_file = st.file_uploader("Upload SkillCorner Physical Output file", type=['xlsx','xls','csv'])
with col3:
    overcome_file = st.file_uploader("Upload SkillCorner Overcome Pressure file", type=['xlsx','xls','csv'])

if all([wyscout_file, physical_file, overcome_file]):
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

    skillcorner_players = pd.concat([
        physical_df['Player'].dropna(),
        overcome_df['Player'].dropna()
    ]).unique().tolist()
    
    wyscout_players = [p for p in wyscout_df['Player'].dropna().unique() 
                      if p not in st.session_state.rejected_players and 
                      p not in st.session_state.confirmed_matches]

    if not st.session_state.auto_matched:
        for player in wyscout_players:
            if player not in st.session_state.temp_selections:
                best_match = find_best_match(player, skillcorner_players)
                st.session_state.temp_selections[player] = best_match
        st.session_state.auto_matched = True

    col1, col2 = st.columns([2,1])
    
    with col1:
        st.write("### Select Metrics")
        col_metrics1, col_metrics2 = st.columns(2)
        
        with col_metrics1:
            physical_cols = [col for col in physical_df.columns if col != 'Player']
            selected_physical = st.multiselect(
                "Physical Output metrics:",
                physical_cols,
                default=physical_cols
            )
        
        with col_metrics2:
            overcome_cols = [col for col in overcome_df.columns if col != 'Player']
            selected_overcome = st.multiselect(
                "Overcome Pressure metrics:",
                overcome_cols,
                default=overcome_cols
            )

    with col2:
        st.write("### Navigation")
        players_per_page = 10
        total_pages = len(wyscout_players) // players_per_page + (1 if len(wyscout_players) % players_per_page > 0 else 0)
        
        col_nav1, col_nav2, col_nav3 = st.columns([1,3,1])
        with col_nav1:
            if st.button('◀ Previous') and st.session_state.page_number > 0:
                st.session_state.page_number -= 1
                st.rerun()
        with col_nav2:
            st.write(f"Page {st.session_state.page_number + 1} of {max(1, total_pages)}")
        with col_nav3:
            if st.button('Next ▶') and st.session_state.page_number < total_pages - 1:
                st.session_state.page_number += 1
                st.rerun()

    st.markdown("---")
    st.write("### Match Players")
    
    start_idx = st.session_state.page_number * players_per_page
    end_idx = min(start_idx + players_per_page, len(wyscout_players))
    
    for idx in range(start_idx, end_idx):
        if idx < len(wyscout_players):
            player = wyscout_players[idx]
            cols = st.columns([3,4,1,1])
            
            with cols[0]:
                st.markdown(f"**{player}**")
            
            with cols[1]:
                current_selection = st.session_state.temp_selections.get(player)
                selection_index = get_selection_index(current_selection, skillcorner_players)
                selection = st.selectbox(
                    "Match with:",
                    ["-- None --"] + skillcorner_players,
                    index=selection_index,
                    key=f"select_{player}"
                )
                st.session_state.temp_selections[player] = selection if selection != "-- None --" else None
            
            with cols[2]:
                if st.button("✓", key=f"confirm_{player}", help="Confirm match"):
                    if selection and selection != "-- None --":
                        st.session_state.match_history.append(('confirm', player, selection))
                        st.session_state.confirmed_matches[player] = selection
                        st.rerun()
            
            with cols[3]:
                if st.button("✗", key=f"reject_{player}", help="Reject player"):
                    if player in st.session_state.confirmed_matches:
                        del st.session_state.confirmed_matches[player]
                    if player in st.session_state.temp_selections:
                        del st.session_state.temp_selections[player]
                    st.session_state.match_history.append(('reject', player, None))
                    st.session_state.rejected_players.add(player)
                    st.rerun()

    st.markdown("---")
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.write("### Confirmed Matches")
        if st.session_state.confirmed_matches:
            confirmed_df = pd.DataFrame(
                list(st.session_state.confirmed_matches.items()),
                columns=['WyScout Player', 'SkillCorner Player']
            )
            st.dataframe(confirmed_df, use_container_width=True)
        else:
            st.info("No matches confirmed yet")
    
    with col2:
        st.write("### Actions")
        col_actions1, col_actions2 = st.columns(2)
        
        with col_actions1:
            if st.button("🔄 Reset All", help="Clear all matches and start over"):
                st.session_state.temp_selections = {}
                st.session_state.confirmed_matches = {}
                st.session_state.auto_matched = False
                st.session_state.rejected_players = set()
                st.session_state.match_history.clear()
                st.rerun()
        
        with col_actions2:
            if st.button("↩️ Undo Last", help="Undo last match", disabled=len(st.session_state.match_history) == 0):
                if st.session_state.match_history:
                    action, player, match = st.session_state.match_history.pop()
                    if action == 'confirm':
                        del st.session_state.confirmed_matches[player]
                    elif action == 'reject':
                        st.session_state.rejected_players.remove(player)
                    st.rerun()
        
        if st.button("📥 Export Data", help="Download matched data as Excel"):
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
        
        st.write("### Progress")
        progress = len(st.session_state.confirmed_matches) / len(wyscout_df['Player'].dropna().unique())
        st.progress(progress)
        st.write(f"Matched: {len(st.session_state.confirmed_matches)} of {len(wyscout_df['Player'].dropna().unique())} players")

        st.write("### Rejected Players")
        if st.session_state.rejected_players:
            st.write(f"Total rejected: {len(st.session_state.rejected_players)}")
            if st.button("Show Rejected"):
                st.write(sorted(list(st.session_state.rejected_players)))
else:
    st.info("Please upload all required files to begin matching")
''')
