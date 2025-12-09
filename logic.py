import json
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document
from langchain.prompts import ChatPromptTemplate

# 1. 設定 API Key (去 OpenAI 申請，或者換成其他免費的 LLM)
os.environ["OPENAI_API_KEY"] = "sk-proj-xxxxxxxx..." 

# 載入你的資料庫
KNOWLEDGE_FILE = "psh_database.json"

def load_and_embed_data():
    """
    把 JSON 資料轉換成向量 (Vector) 並存入 ChromaDB
    """
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 把 JSON 轉成 LangChain 看得懂的 Document 格式
    documents = []
    for entry in data:
        # 我們把 "keywords" 和 "answer" 結合起來變成內容，讓 AI 理解整段話
        text_content = f"Keywords: {', '.join(entry['keywords'])}\nAnswer: {entry['answer']}"
        doc = Document(page_content=text_content, metadata={"answer": entry["answer"]})
        documents.append(doc)

    # 建立向量資料庫 (使用 OpenAI 的 Embedding 模型)
    # 這一步會把文字變成數字矩陣 (Vectors)
    db = Chroma.from_documents(
        documents, 
        OpenAIEmbeddings(),
        collection_name="psh_knowledge_base"
    )
    return db

# 初始化資料庫 (全域變數，避免每次問問題都重跑)
vector_db = load_and_embed_data()
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0) # 使用 GPT-3.5

def get_rag_response(user_question):
    """
    RAG 的核心流程
    """
    # 步驟 1: Retrieval (檢索)
    # 找出跟使用者問題「語意最接近」的 1 筆資料 (k=1)
    results = vector_db.similarity_search(user_question, k=1)
    
    if not results:
        return "I'm sorry, I don't have information about that."

    # 取得找到的「小抄」 (Context)
    retrieved_context = results[0].page_content
    
    # 步驟 2: Augmentation (增強 - 提示工程 Prompt Engineering)
    # 告訴 AI 你的角色，並限制它只能根據提供資料回答
    prompt_template = ChatPromptTemplate.from_template("""
    You are a helpful assistant for Penn State Harrisburg.
    
    Answer the user's question based ONLY on the following context:
    {context}
    
    If the answer is not in the context, say "I don't know the answer to that based on my database."
    
    User Question: {question}
    """)
    
    # 步驟 3: Generation (生成)
    prompt = prompt_template.format_messages(
        context=retrieved_context,
        question=user_question
    )
    
    response = llm.invoke(prompt)
    return response.content

# --- 測試區 ---
if __name__ == "__main__":
    # 測試語意理解 (注意：原本的程式會失敗，因為沒 tuition 這個字)
    print(get_rag_response("How much do I need to pay for school?"))
