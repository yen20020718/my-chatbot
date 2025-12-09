# --- Streamlit Cloud SQLite Fix ---
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass  # 如果沒有 pysqlite3 就跳過，使用系統預設的
# ----------------------------------

import streamlit as st
import json
import os
import re
import difflib
from datetime import datetime

# --- AI 套件 ---
try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import Chroma
    from langchain.docstore.document import Document
    from langchain.prompts import ChatPromptTemplate
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# --- 設定頁面 ---
st.set_page_config(page_title="PSH Hybrid Chatbot", page_icon="🦁")
st.title("🦁 Penn State Harrisburg Hybrid AI")
st.caption("Architecture: Heuristic Retrieval + Embedded AI Technique")

# --- 設定 API Key (從 Streamlit Secrets 讀取，或測試用直接寫) ---
# 建議在 Streamlit Cloud 後台設定 Secrets，這裡先預留位置
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
else:
    # 如果你不想設定 secrets，就把 key 填在下面引號內 (小心不要外洩)
    os.environ["OPENAI_API_KEY"] = "" 

KNOWLEDGE_FILE = "psh_database.json"

# ==========================================
# 核心邏輯 A: 本地啟發式演算法 (Heuristic)
# 對應 PPT: "Enhanced Domain Accuracy"
# ==========================================
@st.cache_data
def loadDatabase():
    if not os.path.exists(KNOWLEDGE_FILE):
        return []
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def saveDatabase(knowledge_base):
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

def SearchKeyWord(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    stopwords = {"the", "is", "at", "on", "in", "a", "an", "and", "for", "to", "of", "do", "i", "you", "how", "what", "where", "when", "why", "can", "are"}
    return [t for t in tokens if t not in stopwords]

def heuristic_retrieval(user_input, knowledge_base):
    user_keywords = SearchKeyWord(user_input)
    if not user_keywords:
        return None, 0

    best_entry = None
    best_score = 0.0
    user_joined = " ".join(user_keywords)

    for entry in knowledge_base:
        entry_keywords = entry.get("keywords", [])
        entry_joined = " ".join(entry_keywords)
        
        # 1. 離散重疊 (Discrete Overlap)
        set_user = set(user_keywords)
        set_entry = set(k.lower() for k in entry_keywords)
        overlap = len(set_user & set_entry)
        
        # 2. 連續相似度 (Continuous Similarity)
        matcher = difflib.SequenceMatcher(None, user_joined, entry_joined)
        similar_score = matcher.ratio()
        
        total_score = overlap + similar_score

        if total_score > best_score:
            best_score = total_score
            best_entry = entry

    return best_entry, best_score

# ==========================================
# 核心邏輯 B: AI 嵌入技術 (Embedded Technique)
# 對應 PPT: "Embedded Technique Exploration"
# ==========================================
@st.cache_resource
def init_ai_system(knowledge_base):
    if not AI_AVAILABLE or not os.environ.get("OPENAI_API_KEY"):
        return None, None
    
    # 準備文件
    documents = []
    for entry in knowledge_base:
        text = f"Keywords: {', '.join(entry['keywords'])}\nAnswer: {entry['answer']}"
        doc = Document(page_content=text, metadata={"answer": entry["answer"]})
        documents.append(doc)
    
    # 建立向量資料庫
    vector_db = Chroma.from_documents(
        documents, 
        OpenAIEmbeddings(),
        collection_name="psh_hybrid_web"
    )
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    return vector_db, llm

def ask_llm(vector_db, llm, question):
    if not vector_db or not llm:
        return None
    
    results = vector_db.similarity_search(question, k=1)
    if not results:
        return None
    
    context = results[0].page_content
    prompt = ChatPromptTemplate.from_template("""
    You are a PSH Campus Assistant. Answer based ONLY on context:
    {context}
    Question: {question}
    """)
    response = llm.invoke(prompt.format_messages(context=context, question=question))
    return response.content

# ==========================================
# 介面與流程控制
# ==========================================

# 1. 初始化
if "knowledge_base" not in st.session_state:
    st.session_state["knowledge_base"] = loadDatabase()

# 初始化 AI (只跑一次)
vector_db, llm = init_ai_system(st.session_state["knowledge_base"])

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Hi! I am ready. (Mode: Hybrid RAG)"}]

if "awaiting_answer" not in st.session_state:
    st.session_state["awaiting_answer"] = False
    st.session_state["last_question"] = ""

# 2. 顯示對話
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 3. 處理輸入
if user_input := st.chat_input("Ask about PSH..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    response = ""

    # A. 學習模式
    if st.session_state["awaiting_answer"]:
        if user_input.strip():
            new_entry = {
                "keywords": SearchKeyWord(st.session_state["last_question"]),
                "answer": user_input,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.session_state["knowledge_base"].append(new_entry)
            saveDatabase(st.session_state["knowledge_base"])
            response = "Thanks! I've learned that and saved it to the database."
        else:
            response = "Skipped learning."
        
        st.session_state["awaiting_answer"] = False
        st.session_state["last_question"] = ""

    # B. 混合搜尋模式 (Hybrid Search)
    else:
        # Step 1: Heuristic (本地)
        entry, score = heuristic_retrieval(user_input, st.session_state["knowledge_base"])
        
        # 信心門檻 (Threshold)
        if entry and score > 1.5:
            response = entry["answer"] + " (Source: Local Heuristic)"
        
        # Step 2: AI Fallback (嵌入技術)
        elif vector_db and llm:
            with st.spinner("Local confidence low. Using Embedded Technique (AI)..."):
                ai_response = ask_llm(vector_db, llm, user_input)
                if ai_response:
                    response = ai_response + " (Source: AI Embedding)"
                else:
                    response = None
        
        # Step 3: 都失敗 -> 觸發學習
        if not response:
            st.session_state["awaiting_answer"] = True
            st.session_state["last_question"] = user_input
            response = "I'm not sure. Can you teach me the answer?"

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)

