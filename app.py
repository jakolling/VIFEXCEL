import pandas as pd  
import re  
from unidecode import unidecode  
from rapidfuzz import fuzz, process  
import logging  
from datetime import datetime  
  
logging.basicConfig(  
    filename=f'matching_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',  
    level=logging.INFO,  
    format='%(asctime)s:%(levelname)s:%(message)s'  
)  
  
def normalize_name(name):  
    if not isinstance(name, str):  
        return ''  
    name = unidecode(str(name)).lower()  
    name = re.sub(r'[^a-z0-9\s\-]', '', name)  
    name = re.sub(r'\s+', ' ', name)  
    name = name.replace('-', ' ')  
    return name.strip()  
  
def get_name_variations(name):  
    normalized = normalize_name(name)  
    parts = normalized.split()  
    variations = set()  
    if not parts:  
        return []  
    variations.add(normalized)  
    for i in range(len(parts)):  
        variations.add(parts[i])  
    if len(parts) >= 2:  
        variations.add(f"{parts[0]} {parts[-1]}")  
        variations.add(f"{parts[-1]} {parts[0]}")  
        variations.add(' '.join(parts[:2]))  
        variations.add(' '.join(parts[-2:]))  
    if len(parts) >= 3:  
        variations.add(' '.join(parts[:3]))  
        variations.add(' '.join(parts[-3:]))  
        variations.add(f"{parts[0]} {parts[1]} {parts[-1]}")  
    return list(variations)  
  
def find_matches_v2(source_df, target_df):  
    matches = {}  
    unmatched = []  
    match_scores = {}  
      
    source_players = source_df['Player'].dropna().unique()  
    target_players = target_df['Player'].dropna().unique()  
      
    target_dict = {}  
    for player in target_players:  
        variations = get_name_variations(player)  
        for var in variations:  
            target_dict[var] = player  
              
    target_variations = list(target_dict.keys())  
      
    for source_player in source_players:  
        source_variations = get_name_variations(source_player)  
        best_match = None  
        best_score = 0  
        match_found = False  
          
        for var in source_variations:  
            if var in target_dict:  
                matches[source_player] = target_dict[var]  
                match_scores[source_player] = 100  
                match_found = True  
                logging.info(f"Direct match: {source_player} -> {target_dict[var]}")  
                break  
          
        if not match_found:  
            for var in source_variations:  
                result = process.extractOne(  
                    var,  
                    target_variations,  
                    scorer=fuzz.token_sort_ratio,  
                    score_cutoff=70  
                )  
                if result is None:  
                    continue  
                match, score, _ = result  
                if score > best_score:  
                    best_score = score  
                    best_match = target_dict.get(match)  
            if best_match and best_score >= 85:  
                matches[source_player] = best_match  
                match_scores[source_player] = best_score  
                logging.info(f"Fuzzy match ({best_score}%): {source_player} -> {best_match}")  
            else:  
                unmatched.append(source_player)  
                logging.warning(f"No match found for: {source_player}")  
                if best_match:  
                    logging.warning(f"Best potential match ({best_score}%): {best_match}")  
      
    with open('matching_report.txt', 'w', encoding='utf-8') as f:  
        f.write("=== MATCHING REPORT ===\n\n")  
        f.write("MATCHED PLAYERS:\n")  
        for source, target in matches.items():  
            score = match_scores.get(source, 'N/A')  
            f.write(f"{source} -> {target} (Score: {score})\n")  
        f.write("\nUNMATCHED PLAYERS:\n")  
        for player in unmatched:  
            f.write(f"{player}\n")  
        f.write(f"\nTotal matched: {len(matches)}")  
        f.write(f"\nTotal unmatched: {len(unmatched)}")  
          
    return matches, unmatched, match_scores  
  
# Test com dados de exemplo  
if __name__ == '__main__':  
    test_source = pd.DataFrame({  
        'Player': [  
            'João Pedro Santos Silva',  
            'Roberto Carlos da Silva',  
            'Ronaldo Nazário de Lima',  
            'Neymar Jr',  
            'Gabriel Jesus',  
            'Vinicius Junior',  
            'Casemiro',  
            'Richarlison de Andrade',  
            'Raphinha',  
            'Lucas Paquetá'  
        ]  
    })  
      
    test_target = pd.DataFrame({  
        'Player': [  
            'Joao Pedro',  
            'Roberto Carlos',  
            'Ronaldo',  
            'Neymar',  
            'Gabriel Jesus Silva',  
            'Vini Jr',  
            'Carlos Casemiro',  
            'Richarlison',  
            'Raphinha Dias',  
            'Lucas Paqueta'  
        ]  
    })  
      
    matches, unmatched, scores = find_matches_v2(test_source, test_target)  
      
    print("\nMatches encontrados:")  
    for source, target in matches.items():  
        score = scores.get(source, 'N/A')  
        print(f"{source} -> {target} (Score: {score})")  
      
    print("\nJogadores não correspondidos:")  
    for player in unmatched:  
        print(player)  
