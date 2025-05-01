import streamlit as st  
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
        'suggested_match': None,  
        'selected_metrics': [],  
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
  
def export_to_excel(wyscout_df, physical_df, overcome_df):  
    output = BytesIO()  
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:  
        # Create merged dataframe based on confirmed matches  
        merged_df = pd.DataFrame(list(st.session_state.confirmed_matches.items()),   
                                columns=['WyScout_Player', 'Physical_Player'])  
          
        # Add selected metrics from the three dfs if available  
        if st.session_state.selected_metrics:  
            for metric in st.session_state.selected_metrics:  
                if metric in wyscout_df.columns:  
                    merged_df = merged_df.merge(  
                        wyscout_df[['Player', metric]],   
                        left_on='WyScout_Player',   
                        right_on='Player',   
                        how='left'  
                    ).drop('Player', axis=1)  
                if metric in physical_df.columns:  
                    merged_df = merged_df.merge(  
                        physical_df[['Player', metric]],   
                        left_on='Physical_Player',   
                        right_on='Player',   
                        how='left'  
                    ).drop('Player', axis=1)  
                if metric in overcome_df.columns:  
                    merged_df = merged_df.merge(  
                        overcome_df[['Player', metric]],   
                        left_on='Physical_Player',   
                        right_on='Player',   
                        how='left'  
                    ).drop('Player', axis=1)  
        merged_df.to_excel(writer, sheet_name='Matched_Players', index=False)  
        # Export rejected players  
        rejected_df = pd.DataFrame(list(st.session_state.rejected_players), columns=['Rejected_Players'])  
        rejected_df.to_excel(writer, sheet_name='Rejected_Players', index=False)  
    return output.getvalue()  
  
def main():  
    st.set_page_config(page_title="Player Matcher", layout="wide")  
    init_session_state()  
      
    st.title('Player Matcher')  
      
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
              
            # Metrics selector in sidebar  
            st.sidebar.write('### Select Metrics')  
            all_metrics = (set(wyscout_df.columns) | set(physical_df.columns) | set(overcome_df.columns)) - {'Player'}  
            st.session_state.selected_metrics = st.sidebar.multiselect(  
                'Choose metrics to include in export',  
                options=sorted(list(all_metrics)),  
                default=st.session_state.selected_metrics  
            )  
              
            # List of confirmed matches in sidebar  
            st.sidebar.write('### Matched Players')  
            if st.session_state.confirmed_matches:  
                for ws_player, ph_player in st.session_state.confirmed_matches.items():  
                    st.sidebar.text(f"{ws_player} \u2794 {ph_player}")  
            else:  
                st.sidebar.text("No matches yet")  
              
            # Excel export functionality  
            if st.sidebar.button('Export to Excel'):  
                excel_data = export_to_excel(wyscout_df, physical_df, overcome_df)  
                b64 = base64.b64encode(excel_data).decode()  
                href = f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'  
                st.sidebar.markdown(f'<a href="{href}" download="matched_players.xlsx">Download Excel File</a>', unsafe_allow_html=True)  
              
            unmatched_players = [p for p in wyscout_df['Player'].dropna().unique()   
                                if p not in st.session_state.confirmed_matches   
                                and p not in st.session_state.rejected_players]  
              
            if unmatched_players:  
                current_player = unmatched_players[0]  
                st.write(f'Current player: **{current_player}**')  
                  
                # Display current player's metrics from WyScout  
                if st.session_state.selected_metrics:  
                    st.write("### WyScout Metrics")  
                    player_metrics = wyscout_df[wyscout_df['Player'] == current_player]  
                    if not player_metrics.empty:  
                        for metric in st.session_state.selected_metrics:  
                            if metric in player_metrics.columns:  
                                st.write(f"{metric}: {player_metrics[metric].iloc[0]}")  
                  
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
                    selected_match = st.selectbox('Select matching player',   
                                                options=[''] + available_skillcorner,  
                                                index=select_index)  
                    # Display selected player's metrics from Physical data  
                    if selected_match and st.session_state.selected_metrics:  
                        st.write("### Physical Metrics")  
                        player_metrics = physical_df[physical_df['Player'] == selected_match]  
                        if not player_metrics.empty:  
                            for metric in st.session_state.selected_metrics:  
                                if metric in player_metrics.columns:  
                                    st.write(f"{metric}: {player_metrics[metric].iloc[0]}")  
                  
                with col_actions1:  
                    if st.button('✅ Confirm Match', disabled=not selected_match):  
                        st.session_state.confirmed_matches[current_player] = selected_match  
                        st.session_state.matched_skillcorner_players.add(selected_match)  
                        st.session_state.match_history.append(('confirm', current_player, selected_match))  
                        st.session_state.auto_matched = False  
                        st.session_state.suggested_match = None  
                        st.rerun()  
                      
                    if st.button('❌ Reject Player'):  
                        st.session_state.rejected_players.add(current_player)  
                        st.session_state.match_history.append(('reject', current_player, None))  
                        st.session_state.auto_matched = False  
                        st.session_state.suggested_match = None  
                        st.rerun()  
                  
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
                            st.rerun()  
                  
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
    main()  
