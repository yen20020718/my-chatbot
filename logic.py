import json
import os
import re
import difflib  # 用於模糊比對
from datetime import datetime  # 用於紀錄時間

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
    Find the best answer using Keyword Matching + Fuzzy Logic.
    """
    user_keywords = SearchKeyWord(user_input)
    if not user_keywords:
        return None, 0

    best_score = 0
    best_entry = None

    for entry in knowledge_base:
        entry_keywords = entry.get("keywords", [])
        
        # --- Fuzzy Matching Logic ---
        current_match_count = 0
        for u_word in user_keywords:
            # 檢查是否有完全相同 或 高度相似 (相似度 > 0.8) 的字
            # n=1 代表只找最像的那一個
            matches = difflib.get_close_matches(u_word, entry_keywords, n=1, cutoff=0.8)
            if matches:
                current_match_count += 1
        
        if current_match_count > best_score:
            best_score = current_match_count
            best_entry = entry

    # --- Confidence Threshold ---
    # 如果關鍵字完全沒對中，或是匹配數量太少，就視為不知道
    if best_score > 0:
        return best_entry, best_score
    else:
        return None, 0

def UpdateNewTerms(user_question: str, user_answer: str, knowledge_base):
    """Update database with new user-taught knowledge."""
    new_keywords = SearchKeyWord(user_question)
    if not new_keywords:
        new_keywords = [user_question.lower()]

    # 加入時間戳記
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
