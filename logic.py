import os
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA

# 1. 設定你的 OpenAI API Key (必須要有這個才能讓 AI 讀懂網頁)
os.environ["OPENAI_API_KEY"] = "你的_sk_開頭的_API_Key"

# 2. 定義你要讓機器人「學習」的網址清單
# 這裡我放了幾個 Penn State Harrisburg 重要的頁面
URLS = [
    "https://harrisburg.psu.edu/admissions",           # 招生
    "https://harrisburg.psu.edu/tuition-and-financial-aid", # 學費
    "https://harrisburg.psu.edu/housing",              # 住宿
    "https://harrisburg.psu.edu/library",              # 圖書館
    "https://harrisburg.psu.edu/its"                   # IT 部門
]

def build_web_knowledge_base():
    """
    這是一次性的：去爬取網頁、切割文字、存入向量資料庫
    """
    print("正在讀取學校網站資料，請稍等...")
    
    # A. 爬取網頁 (Load)
    loader = WebBaseLoader(URLS)
    data = loader.load()
    
    # B. 切割文字 (Split)
    # 網頁內容很長，必須切成小塊，每塊 1000 字，重疊 200 字以便保持語意連貫
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_splits = text_splitter.split_documents(data)
    
    # C. 存入向量資料庫 (Vector Store)
    # 這一步會把文字變成數學向量
    vector_db = Chroma.from_documents(
        documents=all_splits, 
        embedding=OpenAIEmbeddings(),
        collection_name="psh_web_data"
    )
    
    print("資料庫建立完成！")
    return vector_db

# 初始化系統 (全域變數)
# 注意：第一次執行會花幾秒鐘爬網頁
db = build_web_knowledge_base()
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# 設定檢索鍊 (Retrieval Chain)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm, 
    chain_type="stuff", 
    retriever=db.as_retriever()
)

def ask_website(question: str):
    """
    接收使用者問題，從網頁資料找答案
    """
    try:
        response = qa_chain.invoke(question)
        return response['result']
    except Exception as e:
        return f"發生錯誤: {e}"

# --- 測試區 ---
if __name__ == "__main__":
    # 測試一個原本 JSON 裡很難回答的複雜問題
    user_q = "What are the housing options for first-year students?"
    print(f"問: {user_q}")
    print(f"答: {ask_website(user_q)}")
