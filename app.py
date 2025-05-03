import streamlit as st
import pandas as pd
import base64
from io import BytesIO
from thefuzz import fuzz, process

# Função para converter DataFrame para Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='MatchedData')
    return output.getvalue()

# Função para gerar link de download
def download_link(object_to_download, download_filename, download_link_text):
    if isinstance(object_to_download, pd.DataFrame):
        object_to_download = to_excel(object_to_download)
    b64 = base64.b64encode(object_to_download).decode()
    return f'<a href="data:application/octet-stream;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

# Função para encontrar melhores correspondências
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

# Função para obter índice de seleção
def get_selection_index(current_selection, choices):
    try:
        if current_selection and current_selection != "-- None --" and current_selection in choices:
            return choices.index(current_selection) + 1
    except (ValueError, TypeError):
        pass
    return 0

# Configuração inicial da página
st.set_page_config(layout="wide")
st.title('Player Matching Tool')

# Inicialização do estado da sessão
session_state_defaults = {
    'temp_selections': {},
    'confirmed_matches': {},
    'rejected_players': set(),
    'match_history': [],
    'matched_skillcorner_players': set(),
    'auto_matched': False,
    'suggested_match': None
}

for key, value in session_state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Função de validação de arquivos
def validate_skillcorner_file(df, file_type):
    if 'Player' not in df.columns:
        st.error(f"❌ Erro crítico: O arquivo {file_type} não contém a coluna 'Player' obrigatória.")
        st.stop()

# Upload de arquivos
col1, col2 = st.columns(2)
with col1:
    wyscout_file = st.file_uploader("Carregar arquivo WyScout", type=['xlsx','xls','csv'])
with col2:
    skillcorner_files = st.file_uploader(
        "Carregar arquivos SkillCorner (Physical/Overcome)",
        type=['xlsx','xls','csv'],
        accept_multiple_files=True
    )

# Processamento principal
if wyscout_file and skillcorner_files:
    physical_df, overcome_df = None, None

    # Processar arquivos SkillCorner
    for file in skillcorner_files:
        file_name = file.name.lower()
        if 'physical' in file_name:
            physical_df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            validate_skillcorner_file(physical_df, "Physical Output")
        elif 'overcome' in file_name:
            overcome_df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
            validate_skillcorner_file(overcome_df, "Overcome Pressure")

    # Processar arquivo WyScout
    wyscout_df = pd.read_csv(wyscout_file) if wyscout_file.name.endswith('.csv') else pd.read_excel(wyscout_file)

    # Combinar jogadores SkillCorner
    skillcorner_players = []
    if physical_df is not None:
        skillcorner_players.extend(physical_df['Player'].dropna().tolist())
    if overcome_df is not None:
        skillcorner_players.extend(overcome_df['Player'].dropna().tolist())
    skillcorner_players = list(set(skillcorner_players))

    # Listas de jogadores disponíveis
    available_skillcorner_players = [p for p in skillcorner_players if p not in st.session_state.matched_skillcorner_players]
    wyscout_players = [p for p in wyscout_df['Player'].dropna().unique() 
                      if p not in st.session_state.rejected_players 
                      and p not in st.session_state.confirmed_matches]

    # Seção de seleção de métricas
    st.write("### Selecionar Métricas")
    col_metrics1, col_metrics2 = st.columns(2)

    selected_physical, selected_overcome = [], []
    with col_metrics1:
        if physical_df is not None:
            physical_cols = [col for col in physical_df.columns if col != 'Player']
            selected_physical = st.multiselect(
                "Métricas de Desempenho Físico:",
                physical_cols,
                default=physical_cols
            )

    with col_metrics2:
        if overcome_df is not None:
            overcome_cols = [col for col in overcome_df.columns if col != 'Player']
            selected_overcome = st.multiselect(
                "Métricas de Pressão:",
                overcome_cols,
                default=overcome_cols
            )

    # Interface de matching
    if wyscout_players:
        current_player = wyscout_players[0]
        st.subheader(f"🎯 Jogador Atual: {current_player}")

        if not st.session_state.auto_matched:
            st.session_state.suggested_match = find_best_match(current_player, available_skillcorner_players)
            st.session_state.auto_matched = True

        col_match, col_actions = st.columns([3, 2])
        with col_match:
            selection_index = get_selection_index(st.session_state.suggested_match, available_skillcorner_players)
            selection = st.selectbox(
                "Corresponder com:",
                [""] + available_skillcorner_players,
                index=selection_index
            )

        with col_actions:
            confirm_button = st.button("✅ Confirmar Correspondência", disabled=not selection)
            reject_button = st.button("❌ Rejeitar Jogador")
            undo_button = st.button("↩️ Desfazer Última Ação", disabled=len(st.session_state.match_history) == 0)

            if confirm_button:
                st.session_state.confirmed_matches[current_player] = selection
                st.session_state.matched_skillcorner_players.add(selection)
                st.session_state.match_history.append(('confirm', current_player, selection))
                st.session_state.auto_matched = False
                st.rerun()

            if reject_button:
                st.session_state.rejected_players.add(current_player)
                st.session_state.match_history.append(('reject', current_player, None))
                st.session_state.auto_matched = False
                st.rerun()

            if undo_button:
                action, player, match = st.session_state.match_history.pop()
                if action == 'confirm':
                    st.session_state.matched_skillcorner_players.remove(match)
                    del st.session_state.confirmed_matches[player]
                elif action == 'reject':
                    st.session_state.rejected_players.remove(player)
                st.session_state.auto_matched = False
                st.rerun()

        # Barra de progresso
        st.markdown("---")
        total_players = len(wyscout_df['Player'].dropna().unique())
        matched_count = len(st.session_state.confirmed_matches)
        st.progress(matched_count / total_players)
        st.write(f"**Progresso:** {matched_count} de {total_players} jogadores correspondidos")

    else:
        st.success("✅ Todos os jogadores foram processados!")

    # Seção de exportação
    st.markdown("---")
    if st.button("📤 Exportar Dados Consolidados"):
        wyscout_df['Jogador_Correspondente'] = wyscout_df['Player'].map(st.session_state.confirmed_matches)
        df_final = wyscout_df.dropna(subset=['Jogador_Correspondente'])

        # Merge com dados físicos
        if physical_df is not None:
            df_fisico = physical_df[['Player'] + selected_physical]
            df_final = pd.merge(
                df_final,
                df_fisico,
                left_on='Jogador_Correspondente',
                right_on='Player',
                how='left',
                suffixes=('', '_DROP')
            ).drop(columns=['Player', 'Player_DROP'], errors='ignore')

        # Merge com dados de pressão
        if overcome_df is not None:
            df_pressao = overcome_df[['Player'] + selected_overcome]
            df_final = pd.merge(
                df_final,
                df_pressao,
                left_on='Jogador_Correspondente',
                right_on='Player',
                how='left',
                suffixes=('', '_DROP')
            ).drop(columns=['Player', 'Player_DROP'], errors='ignore')

        # Gerar link de download
        download = download_link(df_final, 'dados_consolidados.xlsx', '⬇️ Baixar Arquivo Excel')
        st.markdown(download, unsafe_allow_html=True)

else:
    st.info("⚠️ Por favor, carregue o arquivo WyScout e pelo menos um arquivo SkillCorner para iniciar")
