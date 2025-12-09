import os
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
# --- 修正 Streamlit Cloud 上 SQLite 版本過舊的問題 ---
import sys
import pysqlite3
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
# ------------------------------------------------

import os
from langchain_community.document_loaders import WebBaseLoader
# ... (下面維持你原本的程式碼)
# 設定 API Key (Streamlit Cloud 建議用 secrets 管理，這裡先寫死測試，請小心不要外洩)
os.environ["OPENAI_API_KEY"] = "sk-..." # 記得填入你的 Key

# 定義要爬取的網址
URLS = [
    "https://harrisburg.psu.edu/admissions",
    "https://harrisburg.psu.edu/tuition-and-financial-aid",
    "https://harrisburg.psu.edu/housing",
    "https://harrisburg.psu.edu/library",
    "https://harrisburg.psu.edu/its"
]

def build_web_knowledge_base():
    """建立向量資料庫"""
    print("Loading web data...")
    loader = WebBaseLoader(URLS)
    data = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(data)
    
    vector_db = Chroma.from_documents(
        documents=all_splits, 
        embedding=OpenAIEmbeddings(),
        collection_name="psh_web_data"
    )
    return vector_db

# 初始化
# 注意：這會消耗 API 額度並花時間下載，建議在本機測試好再上傳
# 如果在雲端不想每次都重跑，可以加 try-except 或是使用 st.cache_resource
try:
    db = build_web_knowledge_base()
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=db.as_retriever())
except Exception as e:
    print(f"Error initializing AI: {e}")
    qa_chain = None

def ask_website(question: str):
    if not qa_chain:
        return "AI Service is not available right now (Init Failed)."
    try:
        response = qa_chain.invoke(question)
        return response['result']
    except Exception as e:
        return f"Error: {e}"
