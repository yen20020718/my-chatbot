import streamlit as st
import logic  # 匯入剛剛建立的 logic.py

# 設定網頁標題
st.set_page_config(page_title="PSH Chatbot", page_icon="🦁")
st.title("Penn State Harrisburg Chatbot")

# 初始化 Session State (用來記住對話紀錄和學習狀態)
if "knowledge_base" not in st.session_state:
    st.session_state["knowledge_base"] = logic.loadDatabase()

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Hi! Ask me about Penn State Harrisburg (admissions, tuition, housing, etc.)."}]

if "awaiting_answer" not in st.session_state:
    st.session_state["awaiting_answer"] = False

if "last_question" not in st.session_state:
    st.session_state["last_question"] = ""

# 顯示對話歷史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 處理使用者輸入
if user_input := st.chat_input("Type your message here..."):
    # 1. 顯示使用者訊息
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # 2. 判斷機器人邏輯
    response = ""
    
    # 如果機器人正在等待學習 (使用者正在輸入答案)
    if st.session_state["awaiting_answer"]:
        if user_input.strip() == "":
            response = "No worries, maybe I’ll learn it later."
        else:
            # 更新資料庫
            st.session_state["knowledge_base"] = logic.UpdateNewTerms(
                st.session_state["last_question"], 
                user_input, 
                st.session_state["knowledge_base"]
            )
            response = "Got it! I’ve learned something new about Penn State Harrisburg."
        
        # 重置學習狀態
        st.session_state["awaiting_answer"] = False
        st.session_state["last_question"] = ""

    else:
        # 正常問答模式
        entry, score = logic.FindBestAnswer(user_input, st.session_state["knowledge_base"])
        
        if entry:
            response = entry["answer"]
        else:
            # 找不到答案，進入學習模式
            st.session_state["awaiting_answer"] = True
            st.session_state["last_question"] = user_input
            response = "I’m not sure about that yet. Can you teach me the answer? (Type the answer below, or hit enter to skip.)"

    # 3. 顯示機器人回應
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.write(response)
