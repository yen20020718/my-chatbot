import json
import os
import re
import threading
import tkinter as tk
from tkinter import scrolledtext
from difflib import SequenceMatcher
from datetime import datetime

# --- 新增：AI 相關套件 ---
try:
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    from langchain_community.vectorstores import Chroma
    from langchain.docstore.document import Document
    from langchain.prompts import ChatPromptTemplate
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: AI packages not found. Running in Heuristic-Only mode.")

# --- 設定 API KEY (請換成你的 Key) ---
# 如果沒有 Key，程式會自動降級回原本的關鍵字模式
os.environ["OPENAI_API_KEY"] = "sk-proj-你的OpenAI_API_Key_填在這裡"

KNOWLEDGE_FILE = "psh_database.json"

# ==========================================
# 1. 資料庫與基礎處理 (原本的邏輯)
# ==========================================

def loadDatabase(file_path: str):
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
    stopwords = {"the", "is", "at", "on", "in", "a", "an", "and", "for", "to", "of", "do", "i", "you", "how", "what", "where", "when", "why", "can", "are"}
    keywords = [t for t in tokens if t not in stopwords]
    return keywords

# ==========================================
# 2. Heuristic RAG (符號式/啟發式檢索) - 代表 "Enhanced Domain Accuracy"
# ==========================================

def matchkey(user_keywords, entry_keywords):
    set_user = set(user_keywords)
    set_entry = set(k.lower() for k in entry_keywords)
    return len(set_user & set_entry)

def similarquery(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def heuristic_retrieval(user_input: str, knowledge_base):
    """
    原本的演算法：使用關鍵字重疊 + 模糊比對
    """
    user_keywords = SearchKeyWord(user_input)
    if not user_keywords:
        return None, 0

    best_entry = None
    best_score = 0.0
    user_joined = " ".join(user_keywords)

    for entry in knowledge_base:
        entry_keywords = entry.get("keywords", [])
        if not entry_keywords:
            continue
        entry_joined = " ".join(entry_keywords)
        
        overlap = matchkey(user_keywords, entry_keywords)
        
        token_pair_scores = [similarquery(uk, ek) for uk in user_keywords for ek in entry_keywords] or [0.0]
        max_token_pair = max(token_pair_scores)
        similar_score = max(similarquery(user_joined, entry_joined), max_token_pair)
        
        total_score = overlap + similar_score

        if total_score > best_score:
            best_score = total_score
            best_entry = entry

    if best_score <= 0.5: # 稍微提高門檻，讓低分轉給 AI 處理
        return None, 0

    return best_entry, best_score

# ==========================================
# 3. Real AI RAG (向量嵌入 + LLM) - 代表 "Embedded Technique" & "LLM Evaluation"
# ==========================================

class AI_RAG_System:
    def __init__(self, knowledge_base):
        self.vector_db = None
        self.llm = None
        if AI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
            try:
                self.initialize_vector_db(knowledge_base)
                self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
                print("AI System Initialized Successfully.")
            except Exception as e:
                print(f"AI Init Failed: {e}")

    def initialize_vector_db(self, knowledge_base):
        documents = []
        for entry in knowledge_base:
            # 將關鍵字與答案結合成語意文本
            text = f"Keywords: {', '.join(entry['keywords'])}\nAnswer: {entry['answer']}"
            doc = Document(page_content=text, metadata={"answer": entry["answer"]})
            documents.append(doc)
        
        # 建立向量資料庫 (Chroma)
        self.vector_db = Chroma.from_documents(
            documents, 
            OpenAIEmbeddings(),
            collection_name="psh_knowledge_hybrid"
        )

    def ask_llm(self, question):
        if not self.vector_db or not self.llm:
            return None
        
        # 1. 檢索 (Retrieval)
        results = self.vector_db.similarity_search(question, k=1)
        if not results:
            return None
        context = results[0].page_content

        # 2. 生成 (Generation)
        prompt = ChatPromptTemplate.from_template("""
        You are a helpful assistant for Penn State Harrisburg.
        Answer the question based ONLY on the following context:
        {context}
        
        Question: {question}
        """)
        msg = prompt.format_messages(context=context, question=question)
        response = self.llm.invoke(msg)
        return response.content

# ==========================================
# 4. GUI 介面
# ==========================================

class LearningState:
    def __init__(self):
        self.awaiting_answer = False
        self.last_question = ""

class ChatbotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Penn State Harrisburg Chatbot (Hybrid RAG)")

        self.knowledge_base = loadDatabase(KNOWLEDGE_FILE)
        self.learning_state = LearningState()
        
        # 初始化 AI (在背景執行以免卡住介面)
        self.ai_system = None
        threading.Thread(target=self.init_ai).start()

        # UI Components
        self.chat_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=70, height=22, state="disabled")
        self.chat_box.pack(padx=10, pady=10)

        bottom_frame = tk.Frame(root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.entry = tk.Entry(bottom_frame, width=60)
        self.entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.entry.bind("<Return>", self.Checkmessage)

        send_button = tk.Button(bottom_frame, text="Send", width=10, command=self.Checkmessage)
        send_button.pack(side=tk.LEFT, padx=(5, 0))

        self.AddChat("System", "Initializing... (Hybrid Mode: Heuristic + AI)")
        self.AddChat("Chatbot", "Hi! Ask me about Penn State Harrisburg.")

    def init_ai(self):
        self.ai_system = AI_RAG_System(self.knowledge_base)
        print("AI Ready")

    def AddChat(self, speaker, text):
        self.chat_box.config(state="normal")
        self.chat_box.insert(tk.END, f"{speaker}: {text}\n\n")
        self.chat_box.config(state="disabled")
        self.chat_box.see(tk.END)

    def Checkmessage(self, event=None):
        user_text = self.entry.get().strip()
        if self.learning_state.awaiting_answer and user_text == "":
            self.entry.delete(0, tk.END)
            self.CheckUserAnswer("")
            return
        if not user_text:
            return

        self.AddChat("You", user_text)
        self.entry.delete(0, tk.END)

        if self.learning_state.awaiting_answer:
            self.CheckUserAnswer(user_text)
        else:
            # 使用 threading 避免介面卡頓
            threading.Thread(target=self.ProcessResponse, args=(user_text,)).start()

    def ProcessResponse(self, user_text):
        """
        核心邏輯：先試本地演算法，失敗則試 AI
        """
        # 1. 嘗試 Heuristic (本地演算法)
        entry, score = heuristic_retrieval(user_text, self.knowledge_base)

        if entry and score > 2: # 如果分數夠高 (信心度高)
            self.AddChat("Chatbot (Local)", entry['answer'])
            return

        # 2. 嘗試 AI RAG (LLM + Embedding)
        if self.ai_system and self.ai_system.llm:
            self.AddChat("System", "Local match low. Asking AI...")
            ai_response = self.ai_system.ask_llm(user_text)
            if ai_response:
                self.AddChat("Chatbot (AI)", ai_response)
                return

        # 3. 都失敗，進入學習模式
        self.learning_state.awaiting_answer = True
        self.learning_state.last_question = user_text
        self.AddChat("Chatbot", "I’m not sure. Can you teach me?")

    def CheckUserAnswer(self, user_answer: str):
        question = self.learning_state.last_question
        self.learning_state.awaiting_answer = False
        self.learning_state.last_question = ""

        if not user_answer:
            self.AddChat("Chatbot", "Skipped learning.")
            return

        # 更新資料庫
        self.knowledge_base.append({"keywords": SearchKeyWord(question), "answer": user_answer})
        saveDatabase(KNOWLEDGE_FILE, self.knowledge_base)
        
        # 如果有 AI，也要更新 AI 的向量庫 (簡單起見，這裡只更新本地 JSON，重啟後 AI 才會讀到)
        self.AddChat("Chatbot", "Thanks! Learned.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatbotGUI(root)
    root.mainloop()
