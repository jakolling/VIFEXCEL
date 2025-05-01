import streamlit as st
import pandas as pd
import base64
from io import BytesIO

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='MatchedData')
    return output.getvalue()

def download_link(object_to_download, download_filename, download_link_text):
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = to_excel(object_to_download)
    b64 = base64.b64encode(object_to_download).decode()
    return '<a href="data:application/octet-stream;base64,' + b64 + '" download="' + download_filename + '">' + download_link_text + '</a>'

st.title('Player Matching Tool')

# File uploaders
wyscout_file = st.file_uploader("Upload WyScout file", type=['xlsx','xls','csv'])
physical_file = st.file_uploader("Upload SkillCorner Physical Output file", type=['xlsx','xls','csv'])
overcome_file = st.file_uploader("Upload SkillCorner Overcome Pressure file", type=['xlsx','xls','csv'])

# Initialize session states
if 'temp_selections' not in st.session_state:
    st.session_state.temp_selections = {}
if 'confirmed_matches' not in st.session_state:
    st.session_state.confirmed_matches = {}
if 'page_number' not in st.session_state:
    st.session_state.page_number = 0

if all([wyscout_file, physical_file, overcome_file]):
    # Load dataframes
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

    # Get unique players
    skillcorner_players = pd.concat([
        physical_df['Player'].dropna(),
        overcome_df['Player'].dropna()
    ]).unique().tolist()
    
    # Get unmatched WyScout players
    matched_players = list(st.session_state.confirmed_matches.keys())
    wyscout_players = [p for p in wyscout_df['Player'].dropna().unique() if p not in matched_players]

    # Metric selection
    st.write("### Select Metrics")
    physical_cols = [col for col in physical_df.columns if col != 'Player']
    overcome_cols = [col for col in overcome_df.columns if col != 'Player']
    
    selected_physical = st.multiselect(
        "Select Physical Output metrics:",
        physical_cols,
        default=physical_cols
    )
    
    selected_overcome = st.multiselect(
        "Select Overcome Pressure metrics:",
        overcome_cols,
        default=overcome_cols
    )

    # Pagination
    players_per_page = 10
    total_pages = len(wyscout_players) // players_per_page + (1 if len(wyscout_players) % players_per_page > 0 else 0)
    
    col1, col2, col3 = st.columns([1,3,1])
    with col1:
        if st.button('Previous') and st.session_state.page_number > 0:
            st.session_state.page_number -= 1
    with col2:
        st.write(f"Page {st.session_state.page_number + 1} of {total_pages}")
    with col3:
        if st.button('Next') and st.session_state.page_number < total_pages - 1:
            st.session_state.page_number += 1

    start_idx = st.session_state.page_number * players_per_page
    end_idx = min(start_idx + players_per_page, len(wyscout_players))
    
    # Player matching interface
    st.write("### Match Players")
    for idx in range(start_idx, end_idx):
        player = wyscout_players[idx]
        cols = st.columns([3,4,1,1])
        
        with cols[0]:
            st.write(f"**{player}**")
        
        with cols[1]:
            current_selection = st.session_state.temp_selections.get(player, "-- None --")
            selection = st.selectbox(
                "Match with:",
                ["-- None --"] + skillcorner_players,
                index=0 if current_selection == "-- None --" else skillcorner_players.index(current_selection) + 1,
                key=f"select_{player}"
            )
            st.session_state.temp_selections[player] = selection
        
        with cols[2]:
            if st.button("✓", key=f"confirm_{player}"):
                if selection != "-- None --":
                    st.session_state.confirmed_matches[player] = selection
                    st.experimental_rerun()
        
        with cols[3]:
            if st.button("✗", key=f"reject_{player}"):
                if player in st.session_state.confirmed_matches:
                    del st.session_state.confirmed_matches[player]
                st.session_state.temp_selections[player] = "-- None --"
                st.experimental_rerun()

    # Display confirmed matches
    st.write("### Confirmed Matches")
    if st.session_state.confirmed_matches:
        confirmed_df = pd.DataFrame(
            list(st.session_state.confirmed_matches.items()),
            columns=['WyScout Player', 'SkillCorner Player']
        )
        st.dataframe(confirmed_df)
    else:
        st.write("No matches confirmed yet")

    # Export and clear buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear All"):
            st.session_state.temp_selections = {}
            st.session_state.confirmed_matches = {}
            st.experimental_rerun()
    
    with col2:
        if st.button("Export Data"):
            # Filter WyScout data to only confirmed matches
            wyscout_df['Matched_Player'] = wyscout_df['Player'].map(st.session_state.confirmed_matches)
            wyscout_matched = wyscout_df.dropna(subset=['Matched_Player'])
            
            # Select and merge data
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
            
            download = download_link(final_df, 'matched_players.xlsx', 'Download Matched Data')
            st.markdown(download, unsafe_allow_html=True)

    # Progress bar
    progress = len(st.session_state.confirmed_matches) / len(wyscout_df['Player'].dropna().unique())
    st.progress(progress)
    st.write(f"Matched: {len(st.session_state.confirmed_matches)} of {len(wyscout_df['Player'].dropna().unique())} players")

else:
    st.info("Please upload all required files to begin matching")
