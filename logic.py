import json
import os
import re

KNOWLEDGE_FILE = "psh_database.json"

def loadDatabase(file_path: str = KNOWLEDGE_FILE):
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
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

def textReorganization(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def SearchKeyWord(text: str):
    text = textReorganization(text)
    tokens = text.split()
    stopwords = {
        "the", "is", "at", "on", "in", "a", "an", "and", "for",
        "to", "of", "do", "i", "you", "how", "what", "where",
        "when", "why", "can", "are"
    }
    keywords = [t for t in tokens if t not in stopwords]
    return keywords

def matchkey(user_keywords, entry_keywords):
    set_user = set(user_keywords)
    set_entry = set(k.lower() for k in entry_keywords)
    return len(set_user & set_entry)

def FindBestAnswer(user_input: str, knowledge_base):
    user_keywords = SearchKeyWord(user_input)
    if not user_keywords:
        return None, 0

    best_score = 0
    best_entry = None

    for entry in knowledge_base:
        entry_keywords = entry.get("keywords", [])
        score = matchkey(user_keywords, entry_keywords)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_score > 0:
        return best_entry, best_score
    else:
        return None, 0

def UpdateNewTerms(user_question: str, user_answer: str, knowledge_base):
    new_keywords = SearchKeyWord(user_question)
    if not new_keywords:
        new_keywords = [user_question.lower()]

    new_entry = {
        "keywords": new_keywords,
        "answer": user_answer
    }

    knowledge_base.append(new_entry)
    saveDatabase(KNOWLEDGE_FILE, knowledge_base)
    return knowledge_base
