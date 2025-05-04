import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process

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
    if not isinstance(name, str) or not choices:
        return None
    name_parts = name.strip().split()
    if len(name_parts) < 2:
        return None
    first_letter = name_parts[0][0].lower()
    last_name = name_parts[-1].lower()
    filtered_choices = [c for c in choices if isinstance(c, str) and len(c.split()) > 0 and
                        c.split()[0][0].lower() == first_letter and c.lower().endswith(last_name)]
    if not filtered_choices:
        filtered_choices = [c for c in choices if isinstance(c, str) and len(c.split()) > 0 and
                            c.split()[0][0].lower() == first_letter]
    if filtered_choices:
        best_match = process.extractOne(name, filtered_choices, scorer=fuzz.token_sort_ratio)
        return best_match[0] if best_match and best_match[1] >= min_score else None
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

# Session state setup
if 'temp_selections' not in st.session_state:
    st.session_state.temp_selections = {}
if 'confirmed_matches' not in st.session_state:
    st.session_state.confirmed_matches = {}
if 'rejected_players' not in st.session_state:
    st.session_state.rejected_players = set()
if 'match_history' not in st.session_state:
    st.session_state.match_history = []
if 'matched_skillcorner_players' not in st.session_state:
    st.session_state.matched_skillcorner_players = set()
if 'auto_matched' not in st.session_state:
    st.session_state.auto_matched = False
if 'suggested_match' not in st.session_state:
    st.session_state.suggested_match = None

# File upload (apenas 2 arquivos)
col1, col2 = st.columns(2)
with col1:
    wyscout_file = st.file_uploader("Upload WyScout file", type=['xlsx','xls','csv'])
with col2:
    physical_file = st.file_uploader("Upload SkillCorner Physical Output file", type=['xlsx','xls','csv'])

if all([wyscout_file, physical_file]):
    if wyscout_file.name.endswith('.csv'):
        wyscout_df = pd.read_csv(wyscout_file)
    else:
        wyscout_df = pd.read_excel(wyscout_file)

    if physical_file.name.endswith('.csv'):
        physical_df = pd.read_csv(physical_file)
    else:
        physical_df = pd.read_excel(physical_file)

    all_skillcorner_players = physical_df['Player'].dropna().unique().tolist()  # Removido overcome_df

    available_skillcorner_players = [p for p in all_skillcorner_players 
                                     if p not in st.session_state.matched_skillcorner_players]

    wyscout_players = [p for p in wyscout_df['Player'].dropna().unique()
                       if p not in st.session_state.rejected_players and
                       p not in st.session_state.confirmed_matches]

    st.write("### Select Metrics")
    selected_physical = st.multiselect(  # Removido seção Overcome
        "Physical Output metrics:",
        [col for col in physical_df.columns if col != 'Player'],
        default=[col for col in physical_df.columns if col != 'Player']
    )

    if wyscout_players:
        current_player = wyscout_players[0]
        st.subheader(f"🎯 Match Player: {current_player}")

        if not st.session_state.auto_matched:
            best_match = find_best_match(current_player, available_skillcorner_players)
            st.session_state.suggested_match = best_match
            st.session_state.auto_matched = True

        col_match, col_c1, col_c2 = st.columns([2, 1, 1])
        with col_match:
            selection_index = get_selection_index(st.session_state.suggested_match, available_skillcorner_players)
            selection = st.selectbox(
                "Match with:",
                [""] + available_skillcorner_players,
                index=selection_index
            )

        with col_c1:
            if st.button("✅ Confirm Match", disabled=not selection):
                st.session_state.confirmed_matches[current_player] = selection
                st.session_state.matched_skillcorner_players.add(selection)
                st.session_state.match_history.append(('confirm', current_player, selection))
                st.session_state.auto_matched = False
                st.session_state.suggested_match = None
                st.rerun()

            if st.button("❌ Reject Player"):
                st.session_state.rejected_players.add(current_player)
                st.session_state.match_history.append(('reject', current_player, None))
                st.session_state.auto_matched = False
                st.session_state.suggested_match = None
                st.rerun()

        with col_c2:
            if st.button("↩️ Undo Last", disabled=len(st.session_state.match_history) == 0):
                action, player, match = st.session_state.match_history.pop()
                if action == 'confirm':
                    st.session_state.matched_skillcorner_players.remove(match)
                    del st.session_state.confirmed_matches[player]
                elif action == 'reject':
                    st.session_state.rejected_players.remove(player)
                st.session_state.auto_matched = False
                st.session_state.suggested_match = None
                st.rerun()

        st.markdown("---")
        progress = len(st.session_state.confirmed_matches) / len(wyscout_df['Player'].dropna().unique())
        st.progress(progress)
        st.write(f"Matched: {len(st.session_state.confirmed_matches)} of {len(wyscout_df['Player'].dropna().unique())} players")
    else:
        st.success("✅ All players have been matched or rejected!")

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
        if st.button("🔄 Reset All", help="Clear all matches and start over"):
            st.session_state.temp_selections = {}
            st.session_state.confirmed_matches = {}
            st.session_state.auto_matched = False
            st.session_state.rejected_players = set()
            st.session_state.match_history = []
            st.session_state.matched_skillcorner_players = set()
            st.session_state.suggested_match = None
            st.rerun()

        if st.button("📥 Export Data", help="Download matched data as Excel"):
            wyscout_df['Matched_Player'] = wyscout_df['Player'].map(st.session_state.confirmed_matches)
            wyscout_matched = wyscout_df.dropna(subset=['Matched_Player'])

            physical_subset = physical_df[['Player'] + selected_physical]

            # Merge apenas com physical_df (removido overcome_df)
            final_df = pd.merge(
                wyscout_matched,
                physical_subset,
                left_on='Matched_Player',
                right_on='Player',
                how='left',
                suffixes=('_WyScout', '_Physical')
            ).dropna(subset=['Player_Physical'])

            download = download_link(final_df, 'matched_players.xlsx', '📥 Download Excel File')
            st.markdown(download, unsafe_allow_html=True)

        st.write("### Rejected Players")
        if st.session_state.rejected_players:
            st.write(f"Total rejected: {len(st.session_state.rejected_players)}")
            if st.button("Show Rejected"):
                st.write(sorted(list(st.session_state.rejected_players)))

else:
    st.info("Please upload both files to begin matching")
