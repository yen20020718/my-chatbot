import streamlit as st
import logic             # 原本的本地資料庫邏輯
import web_search_logic  # 新的 AI 網頁搜尋邏輯

# 1. 設定網頁標題與圖示
st.set_page_config(page_title="PSH Chatbot", page_icon="🦁")
st.title("🦁 Penn State Harrisburg AI Assistant")

# 2. 初始化 Session State
if "knowledge_base" not in st.session_state:
    st.session_state["knowledge_base"] = logic.loadDatabase()

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Hi! Ask me about Penn State Harrisburg (Admissions, Housing, Tuition, etc.)."}]

if "awaiting_answer" not in st.session_state:
    st.session_state["awaiting_answer"] = False

if "last_question" not in st.session_state:
    st.session_state["last_question"] = ""

# 3. 顯示對話歷史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 4. 處理使用者輸入
if user_input := st.chat_input("Type your question here..."):
    # 顯示使用者輸入
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    response = ""
    
    # --- 情況 A: 機器人正在等待使用者教學 (Learning Mode) ---
    if st.session_state["awaiting_answer"]:
        if user_input.strip() == "":
            response = "No worries, maybe I’ll learn it later."
        else:
            st.session_state["knowledge_base"] = logic.UpdateNewTerms(
                st.session_state["last_question"], 
                user_input, 
                st.session_state["knowledge_base"]
            )
            response = "Got it! I’ve added this to my local database."
        
        st.session_state["awaiting_answer"] = False
        st.session_state["last_question"] = ""

    # --- 情況 B: 正常問答模式 (Hybrid Search) ---
    else:
        # 第一步：先檢查本地 JSON 資料庫 (速度快、答案固定)
        entry, score = logic.FindBestAnswer(user_input, st.session_state["knowledge_base"])
        
        if entry:
            # 找到了！直接使用本地答案
            response = entry["answer"]
            # (可選) 加上標註讓使用者知道這是本地資料
            # response += " (Source: Local DB)" 
        else:
            # 第二步：本地找不到，啟動 AI 網頁搜尋 (RAG)
            with st.chat_message("assistant"):
                with st.spinner("Searching PSH website for answers..."):
                    try:
                        # 呼叫 web_search_logic 進行搜尋
                        ai_response = web_search_logic.ask_website(user_input)
                        response = ai_response
                    except Exception as e:
                        response = "I'm having trouble connecting to the AI right now."

            # (可選) 只有當 AI 也回答不出來時，才進入「教學模式」
            # 這裡我們先假設 AI 總能回傳一些東西，所以直接顯示 AI 答案
            
    # 5. 顯示機器人回應
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)
