import pandas as pd  
import re  
from unidecode import unidecode  
from fuzzywuzzy import fuzz  
  
def normalize_name(name):  
    name = str(name)  
    name = unidecode(name)  
    name = re.sub(r'[^\w\s\-]', '', name)  
    parts = name.lower().strip().split()  
    return ' '.join(sorted(parts))  
  
def calculate_similarity(name1, name2):  
    name1_norm = normalize_name(name1)  
    name2_norm = normalize_name(name2)  
    return max(  
        fuzz.ratio(name1_norm, name2_norm),  
        fuzz.token_sort_ratio(name1_norm, name2_norm)  
    ) / 100  
  
# Dados de teste com variações mais complexas  
wyscout_data = {  
    'Player': [  
        'Kevin De Bruyne',  
        'Mohamed Salah',  
        'João Félix',  
        'Erling Haaland',  
        'Vinícius Júnior'  
    ]  
}  
  
skillcorner_data = {  
    'Player': [  
        'De Bruyne Kevin',  
        'Mo Salah',  
        'Joao Felix',  
        'Haaland, Erling',  
        'Vinicius Jr.'  
    ]  
}  
  
df_wyscout = pd.DataFrame(wyscout_data)  
df_skillcorner = pd.DataFrame(skillcorner_data)  
  
matches = {}  
unmatched = []  
potential_matches = {}  
  
for _, wyscout_row in df_wyscout.iterrows():  
    wyscout_name = wyscout_row['Player']  
    best_match = None  
    best_score = 0  
    potentials = []  
      
    for _, skill_row in df_skillcorner.iterrows():  
        skill_name = skill_row['Player']  
        score = calculate_similarity(wyscout_name, skill_name)  
        if score >= 0.85:  
            if score > best_score:  
                best_score = score  
                best_match = skill_name  
        elif score >= 0.70:  
            potentials.append((skill_name, score))  
      
    if best_match:  
        matches[wyscout_name] = (best_match, best_score)  
    else:  
        unmatched.append(wyscout_name)  
        if potentials:  
            potential_matches[wyscout_name] = sorted(potentials, key=lambda x: x[1], reverse=True)[:3]  
  
print('--- Matches Automáticos ---')  
for wyscout_name, (skill_name, score) in matches.items():  
    print(f'{wyscout_name} -> {skill_name} (score: {score:.2f})')  
  
print('\n--- Nomes sem Correspondência Automática (para revisão) ---')  
for name in unmatched:  
    print(f'\n{name}:')  
    if name in potential_matches:  
        for suggestion, score in potential_matches[name]:  
            print(f'  - {suggestion} (score: {score:.2f})')  
    else:  
        print('  Nenhuma sugestão próxima encontrada')  
