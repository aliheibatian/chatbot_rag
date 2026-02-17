import streamlit as st
import base64
from pathlib import Path
from bson import ObjectId
import ollama
import re
import html
import time
from typing import List, Dict, Tuple, Optional, Any
from st_keyup import st_keyup
from model_logic import (
    get_mongo_collection,
    get_milvus_retrievers_and_mongo_collections,
    ask_llm,
    update_conversation_cache,
    find_similar_liked_questions,
    get_answer_from_admin_cache,
    sync_admin_liked_to_milvus
)
import streamlit as st



def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        st.error(f"❌ فایل تصویر {file_path} یافت نشد. لطفاً مسیر فایل را بررسی کنید.")
        return None


def filter_think_section(response: str) -> str:
    pattern = r'<think>.*?</think>\s*'
    filtered_response = re.sub(pattern, '', response, flags=re.DOTALL)
    return filtered_response.strip()


def create_consolidated_source_tooltip(sources_data: list) -> str:
    if not sources_data or not isinstance(sources_data, list):
        return ""
    all_sources_html = []
    processed_filenames = set()
    for source_info in sources_data:
        filename = source_info.get('filename')
        if filename not in processed_filenames:
            processed_filenames.add(filename)
            all_quotes_for_file = []
            for s_info in sources_data:
                if s_info.get('filename') == filename and s_info.get('quotes'):
                    for q in s_info.get('quotes'):
                        if q not in all_quotes_for_file:
                            all_quotes_for_file.append(q)
            file_html = f'<div class="source-entry"><div class="source-filename"><b>فایل:</b> {html.escape(str(filename))}</div>'
            if all_quotes_for_file:
                file_html += '<div class="quote-header">نقل قول‌های یافت شده:</div>'
                for quote in all_quotes_for_file:
                    file_html += f'<div class="quote">"{html.escape(str(quote))}"</div>'
            else:
                file_html += '<div class="quote-header" style="opacity: 0.7;">نقل قول دقیقی برای این فایل یافت نشد.</div>'
            file_html += '</div>'
            all_sources_html.append(file_html)
    if not all_sources_html:
        return ""
    combined_details = '<hr style="margin: 10px 0; border-color: #888; border-style: dashed;">'.join(all_sources_html)
    tooltip_html = f"""
    <div style="text-align: right; margin-top: 15px; margin-right: 5px;">
        <div class="tooltip" tabindex="0" aria-label="مشاهده منابع">
            <span style="font-size: 24px; cursor: help;">📄</span>
            <div class="tooltiptext" role="tooltip">
                <div style="font-weight: bold; margin-bottom: 10px; text-align: center; border-bottom: 1px solid #555; padding-bottom: 5px;">منابع استفاده شده</div>
                {combined_details}
            </div>
        </div>
    </div>
    """
    return tooltip_html


# --- تنظیمات صفحه و استایل‌ها ---
st.set_page_config(
    page_title="دستیار هوشمند",
    page_icon="anacav-logo.webp",
    layout="centered",
)

logo_image_path = Path(__file__).parent / "logo_no_extra_white.webp"
logo_image_base64 = get_image_as_base64(logo_image_path)

image_path = Path(__file__).parent / "20240815_032319.jpg"
image_base64 = get_image_as_base64(image_path)
font_path = Path(__file__).parent / "Vazirmatn-Regular.woff2"
font_base64 = get_image_as_base64(font_path)


st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            order: 2;
        }
        [data-testid="stMain"] {
            order: 1;
        }
        .stKeyUpInput > div > input {
            font-family: 'Vazirmatn', sans-serif !important;
            text-align: right !important;
            direction: rtl !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

page_bg_style = f"""
<style>
    @font-face {{
        font-family: 'Vazirmatn';
        src: url(data:font/woff2;base64,{font_base64}) format('woff2');
    }}
    html, body, [data-testid="stAppViewContainer"] {{
        height: 100%;
        margin: 0;
        background-image: url("data:image/jpeg;base64,{image_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        
    }}
    [data-testid="stSidebar"]::before {{
        content: "";
        display: block;
        margin: 2rem auto -2rem auto;
        width: 180px;
        height: 180px;
        background-image: url("data:image/png;base64,{logo_image_base64}");
        background-size: 180px 150px;
        background-repeat: no-repeat;
        background-position: center 2rem;
        border-radius: 30px;
    }}
    div[data-testid="stChatMessage"]:has(div.e1ypd8m72) {{
        flex-direction: row-reverse;
        border-radius: 1em;
        border: 1px solid rgb(250 250 250 / 0%);
    }}
    div[data-testid="stChatMessage"]:has(div.e1ypd8m72) div.e1ypd8m72 {{
        margin-right: 8px;
        margin-left: 8px;
        background-color: rgb(250 250 250 / 17%);
        border-radius: 2rem;
        border: 1px solid rgb(250 250 250 / 0%);
    }}
    .st-emotion-cache-z8vbw2 {{
        background-color: rgb(250 250 250 / 17%);
        border: 1px solid rgba(250 250 250 / 0%);
        border-radius: 2rem;
    }}
    [data-testid="stChatMessage"] {{
        background-color: rgba(45, 45, 45, 0.85);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    div[data-testid="stHorizontalBlock"]:has(div[data-testid="stChatMessage"]) > div[style*="justify-content: flex-end"] [data-testid="stChatMessage"] {{
        background-color: rgba(0, 85, 153, 0.85);
    }}
    [data-testid="stChatMessage"] p {{
        font-family: 'Vazirmatn', sans-serif !important;
        font-size: 15px !important;
        text-align: right;
        direction: rtl;
    }}
    [data-testid="stSidebarNavLink"] {{
        font-family: 'Vazirmatn', sans-serif !important;
    }}
    [data-testid="stAppViewContainer"] h1 {{
        font-family: 'Vazirmatn', sans-serif !important;
    }}
    button[data-testid="stBaseButton-headerNoPadding"] {{
        display: none !important;
    }}
    [data-testid="stSidebar"] {{
        text-align: right;
        direction: rtl;
        background: transparent !important;
        border: none !important;
        backdrop-filter: none !important;
        position: fixed;
        right: 0;
        top: 0;
        width: 300px;
        height: 100%;
        z-index: 999;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        background: transparent !important;
    }}
    .st-emotion-cache-hzygls {{
        position: relative;
        bottom: 0px;
        width: 100%;
        min-width: 100%;
        background-color: rgb(0 0 0 / 0%);
        display: flex;
        flex-direction: column;
        -webkit-box-align: center;
        align-items: center;
    }}
    .st-emotion-cache-gquqoo {{
        position: absolute;
        top: 0px;
        left: 0px;
        right: 0px;
        display: flex;
        -webkit-box-align: center;
        align-items: center;
        height: 3.75rem;
        min-height: 3.75rem;
        width: 100%;
        background: rgb(0 0 0 / 0%);
        outline: none;
        z-index: 999990;
        pointer-events: auto;
        font-size: 0.875rem;
    }}
    [data-testid="stSpinner"] > div,
    [data-testid="stStyledFullScreenFrame"],
    [data-testid="stButton"] p {{
        font-family: 'Vazirmatn', sans-serif !important;
    }}
    .st-bx {{
        background-color: rgba(0,0,0,0);
        border: none;
        border-bottom: 2px solid rgba(105, 118, 132, 255);
        color: rgba(255, 255, 255, 230);
        padding-bottom: 7px;
    }}
    .tooltip {{
        position: relative;
        display: inline-block;
        cursor: pointer;
    }}
    .tooltip .tooltiptext {{
        visibility: hidden;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
        width: 450px;
        max-width: 70vw;
        background-color: rgba(10,20,30,0.95);
        color: #fff;

text-align: right;
        direction: rtl;
        border-radius: 8px;
        padding: 12px;
        position: absolute;
        z-index: 999999;
        bottom: 130%;
        left: 50%;
        transform: translateX(-50%);
        box-shadow: 0 8px 20px rgba(0,0,0,0.5);
        font-size: 14px;
        line-height: 1.6;
        word-break: break-word;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .tooltip:hover .tooltiptext,
    .tooltip:focus-within .tooltiptext {{
        visibility: visible;
        opacity: 1;
    }}
    .tooltiptext {{
        font-family: 'Vazirmatn', sans-serif !important;
    }}
    .tooltip .quote-header {{
        font-style: normal;
        color: #ddd;
        margin-top: 8px;
        margin-bottom: 4px;
        font-size: 13px !important;
    }}
    .tooltip .quote {{
        border-right: 3px solid #87CEEB;
        padding-right: 10px;
        margin: 10px 0;
    }}
    .st-emotion-cache-gx6i9d ul, .st-emotion-cache-gx6i9d dl, .st-emotion-cache-gx6i9d li {{
        font-size: inherit;
        text-align: center;
    }}
    
    div[data-testid="stButton"] button[key="send_button"] {{
        height: 40px;
        margin-top: -10px;
    }}
    /* --- استایل برای دکمه‌های پیشنهادی افقی (Chips) --- */
.suggestion-chips {{
    display: flex;
    flex-direction: column; /* چیدمان را عمودی (ستونی) می‌کند */
    align-items: flex-end;   /* دکمه‌ها را در ستون به سمت راست می‌چسباند */
    gap: 10px;               /* فاصله بین دکمه‌ها */
    padding: 10px 0;
}}

.suggestion-chips .stButton button {{
    background-color: rgba(60, 60, 60, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 20px !important; /* گرد کردن کامل گوشه‌ها */
    color: #f0f0f0 !important;
    padding: 6px 16px !important;
    transition: all 0.2s ease-in-out;
    font-size: 14px !important;
    font-weight: 500;
}}

.suggestion-chips .stButton button:hover {{
    background-color: rgba(85, 85, 85, 0.9);
    border-color: #87CEEB !important;
    color: #ffffff !important;
    transform: translateY(-2px); /* افکت شناور شدنเล็กน้อย */
}}

.st-emotion-cache-1anq8dj {{
    display: inline-flex;
    -webkit-box-align: center;
    align-items: center;
    -webkit-box-pack: center;
    justify-content: center;
    font-weight: 400;
    padding: 0.6rem 0.85rem;
    border-radius: 0.5rem;
    min-height: 2.5rem;
    margin: 0px;
    line-height: 1.6;
    text-transform: none;
    font-size: inherit;
    font-family: inherit;
    color: inherit;
    width: 100%;
    cursor: pointer;
    user-select: none;
    background-color: rgb(19, 23, 32);
    border: 1px solid rgba(250, 250, 250, 0.2);
}}
    
</style>
"""
if image_base64:
    st.markdown(page_bg_style, unsafe_allow_html=True)

# -- عنوان اصلی --
st.markdown(
    """
    <h1 style='text-align: center; direction: rtl; font-size: 31px;'>
        💡 دستیار هوشمند شرکت توزیع برق شهرستان اصفهان
    </h1>
    """,
    unsafe_allow_html=True
)


# --- مقداردهی اولیه به session_state ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "سلام! چطور می‌توانم کمکتان کنم؟", "interaction_id": None}]
if "history_for_llm" not in st.session_state:
    st.session_state["history_for_llm"] = []
if "rated_interactions" not in st.session_state:
    st.session_state.rated_interactions = set()
if "reply_to_index" not in st.session_state:
    st.session_state.reply_to_index = None
if "suggestions" not in st.session_state:
    st.session_state["suggestions"] = []
if "input_text" not in st.session_state:
    st.session_state.input_text = ""
if "last_query" not in st.session_state:
    st.session_state.last_query = ""
if "suggestion_was_clicked" not in st.session_state:
    st.session_state.suggestion_was_clicked = False
if "just_responded" not in st.session_state:
    st.session_state.just_responded = False


@st.cache_resource
def initialize_connections_and_clients():
    mongo_collection = get_mongo_collection()
    knowledge_collection, conversation_vectorstore, mongo_collection, admin_collection, ef, admin_liked_collection = get_milvus_retrievers_and_mongo_collections()
    ollama_client = ollama.Client(host='http://localhost:11434')
    return mongo_collection, admin_collection, knowledge_collection, conversation_vectorstore, ollama_client, ef, admin_liked_collection


mongo_collection, admin_collection, knowledge_collection, conversation_vectorstore, ollama_client, ef, admin_liked_collection = initialize_connections_and_clients()

if mongo_collection is None or knowledge_collection is None or conversation_vectorstore is None or ollama_client is None:
    st.error("❌ خطای اساسی در اتصال به سرویس‌ها. لطفاً از اجرای صحیح Ollama و دیتابیس‌ها اطمینان حاصل کنید.")
    st.stop()


def sync_admin_liked_data():
    try:
        sync_admin_liked_to_milvus(admin_collection, admin_liked_collection, ef)
        return True
    except Exception as e:
        st.error(f"خطا در همگام‌سازی داده‌های ادمین: {str(e)}")
        return False


# نمایش تاریخچه مکالمات
for i, msg in enumerate(st.session_state.messages):
    avatar = "🧠" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            if msg["role"] == "assistant" and msg.get("interaction_id"):
                if st.button("↪️", key=f"reply_{i}", help="پاسخ به این پیام"):
                    st.session_state.reply_to_index = i
                    st.rerun()
        with col2:
            display_content = filter_think_section(msg["content"]) if msg["role"] == "assistant" else msg["content"]
            citation_pattern = r'\[Source:\s*[\d\s,]+\]'
            cleaned_content = re.sub(citation_pattern, '', display_content).strip()
            st.markdown(cleaned_content)
            if msg.get("sources_data"):
                tooltip_html = create_consolidated_source_tooltip(msg["sources_data"])
                st.markdown(tooltip_html, unsafe_allow_html=True)


# مدیریت پاسخ به پیام خاص
if st.session_state.reply_to_index is not None:
    replied_message = st.session_state.messages[st.session_state.reply_to_index]
    author = "دستیار" if replied_message['role'] == 'assistant' else "شما"
    with st.container(border=True):
        st.markdown(f"**در حال پاسخ به {author}:**")
        st.markdown(f"> {replied_message['content'][:80]}...")
        if st.button("لغو پاسخ", key=f"cancel_reply_{len(st.session_state.messages)}"):
            st.session_state.reply_to_index = None
            st.rerun()




input_col, button_col = st.columns([0.85, 0.103])
with input_col:
    user_input = st_keyup(
        label=" ",
        placeholder="پیام خود را بنویسید...",
        value=st.session_state.input_text,
        key="user_input_widget",
    )
    if user_input != st.session_state.input_text:
        st.session_state.input_text = user_input

with button_col:
    st.markdown("<br>", unsafe_allow_html=True)
    send_clicked = st.button("ارسال", key="send_button", use_container_width=True)


# --- منطق دریافت پیشنهادات ---
# تغییر ۱: شرط جدید به اینجا اضافه شده است
if user_input and user_input.endswith(" ") and not st.session_state.suggestion_was_clicked and not st.session_state.just_responded:
    query = user_input.strip()
    if query and query != st.session_state.last_query:
        st.session_state.last_query = query
        sync_admin_liked_data()
        try:
            suggestions = find_similar_liked_questions(query, admin_liked_collection, ef)[:5]
            st.session_state.suggestions = suggestions
        except Exception as e:
            st.error(f"خطا در دریافت پیشنهادات: {str(e)}")
            st.session_state.suggestions = []

# --- ریست کردن پرچم‌ها ---
st.session_state.suggestion_was_clicked = False
# تغییر ۲: پرچم جدید در اینجا ریست می‌شود
st.session_state.just_responded = False


# --- منطق نمایش پیشنهادات ---
if st.session_state.suggestions and not send_clicked:
    st.markdown('<div class="suggestion-chips">', unsafe_allow_html=True)
    for i, suggestion in enumerate(st.session_state.suggestions):
            if st.button(key=f"sugg_{i}", label=suggestion['question'], use_container_width=True):
                # ... (منطق داخلی دکمه شما بدون تغییر باقی می‌ماند) ...
                question = suggestion["question"]
                doc_id = suggestion["id"]
                cached_data = get_answer_from_admin_cache(doc_id, admin_collection)
                if cached_data:
                    user_message_content = question
                    if st.session_state.reply_to_index is not None:
                        replied_text = st.session_state.messages[st.session_state.reply_to_index]['content']
                        citation_pattern = r'\[Source:\s*[\d\s,]+\]'
                        replied_text_clean = re.sub(citation_pattern, '', replied_text).strip()
                        user_message_content = f"در پاسخ به پیام «{replied_text_clean}»:\n\n{question}"
                        st.session_state.reply_to_index = None
                    st.session_state.messages.append({"role": "user", "content": user_message_content, "interaction_id": "suggestion_selected"})
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": cached_data["answer"],
                        "interaction_id": "cached_admin_answer",
                        "sources_data": cached_data["sources_data"]
                    })
                    st.session_state.input_text = ""
                    st.session_state.suggestions = []
                    st.session_state.last_query = ""
                    st.session_state.suggestion_was_clicked = True
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# --- منطق دکمه ارسال ---
if send_clicked:
    prompt = st.session_state.input_text.strip()
    if prompt:
        user_message_content = prompt
        if st.session_state.reply_to_index is not None:
            replied_text = st.session_state.messages[st.session_state.reply_to_index]['content']
            citation_pattern = r'\[Source:\s*[\d\s,]+\]'
            replied_text_clean = re.sub(citation_pattern, '', replied_text).strip()
            user_message_content = f"در پاسخ به پیام «{replied_text_clean}»:\n\n{prompt}"
            st.session_state.reply_to_index = None
        st.session_state.messages.append({"role": "user", "content": user_message_content, "interaction_id": None})
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("در حال فکر کردن..."):
                answer, interaction_id, source, sources_data = ask_llm(
                    user_message_content, [], ollama_client, mongo_collection, admin_collection, knowledge_collection, conversation_vectorstore, ef, admin_liked_collection
                )
                source_emoji_map = {
                    "smart_cache_exact_match": "⚡️ از کش هوشمند",
                    "rag_langgraph_avoiding_dislike": "🤔 تولید جدید (با یادگیری از بازخورد)",
                    "rag_langgraph_generation": "📚 از پایگاه دانش (RAG)",
                }
                source_text = source_emoji_map.get(source, "")
                full_response = filter_think_section(answer)
                if source == "smart_cache_exact_match":
                    full_response += f"\n\n*منبع: {source_text}*"
                st.markdown(full_response)
                if sources_data:
                    tooltip_html = create_consolidated_source_tooltip(sources_data)
                    st.markdown(tooltip_html, unsafe_allow_html=True)
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "interaction_id": interaction_id,
            "is_rated": False,
            "sources_data": sources_data
        })
        st.session_state.history_for_llm = [
            {"role": "user", "content": user_message_content},
            {"role": "assistant", "content": answer}
        ]
        st.session_state.input_text = ""
        st.session_state.suggestions = []
        st.session_state.last_query = ""
        # تغییر ۳: پرچم جدید را قبل از اجرای مجدد فعال می‌کنیم
        st.session_state.just_responded = True
        st.rerun()