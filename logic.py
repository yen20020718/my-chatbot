import json
import os
import re
import difflib 
from datetime import datetime 

KNOWLEDGE_FILE = "psh_database.json"

def loadDatabase(file_path: str = KNOWLEDGE_FILE):
    """Load knowledge base from a JSON file."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except json.JSONDecodeError:
        return []

def saveDatabase(file_path: str, knowledge_base):
    """Save the knowledge base back to the JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

def textReorganization(text: str) -> str:
    """Lowercase and clean text."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def SearchKeyWord(text: str):
    """Extract keywords from text."""
    text = textReorganization(text)
    tokens = text.split()
    stopwords = {
        "the", "is", "at", "on", "in", "a", "an", "and", "for",
        "to", "of", "do", "i", "you", "how", "what", "where",
        "when", "why", "can", "are", "please", "help", "me"
    }
    keywords = [t for t in tokens if t not in stopwords]
    return keywords

def FindBestAnswer(user_input: str, knowledge_base):
    """
    Find the best answer using Exact Match > Substring (Length > 2) > Fuzzy Logic.
    """
    user_keywords = SearchKeyWord(user_input)
    if not user_keywords:
        return None, 0

    best_score = 0
    best_entry = None

    print(f"\n--- Debug: Analyzing '{user_input}' ---") 

    for entry in knowledge_base:
       
        entry_keywords = [k.lower() for k in entry.get("keywords", [])]
        
        current_match_count = 0
        
        for u_word in user_keywords:
            
            if u_word in entry_keywords:
                current_match_count += 1
                continue 

           
            for db_k in entry_keywords:
                if len(db_k) > 2 and (u_word in db_k or db_k in u_word):
                    current_match_count += 1
                   
                    break 
            matches = difflib.get_close_matches(u_word, entry_keywords, n=1, cutoff=0.8)
            if matches:
               
                if matches[0] != u_word:
                    current_match_count += 0.5 
                    print(f"   (Fuzzy match: '{u_word}' -> '{matches[0]}')")

       
        if current_match_count > best_score:
            best_score = current_match_count
            best_entry = entry

   
    if best_entry:
        print(f"Match Found! Score: {best_score}, Answer Keywords: {best_entry['keywords']}")
    else:
        print("No match found.")

    # --- Confidence Threshold ---
    if best_score > 0:
        return best_entry, best_score
    else:
        return None, 0

def UpdateNewTerms(user_question: str, user_answer: str, knowledge_base):
    """Update database with new user-taught knowledge."""
    new_keywords = SearchKeyWord(user_question)
    if not new_keywords:
        new_keywords = [user_question.lower()]

    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_entry = {
        "keywords": new_keywords,
        "answer": user_answer,
        "created_at": timestamp,
        "source": "user_learning"
    }

    knowledge_base.append(new_entry)
    saveDatabase(KNOWLEDGE_FILE, knowledge_base)
    return knowledge_base



