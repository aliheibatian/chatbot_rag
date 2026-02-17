import streamlit as st
import base64
from pathlib import Path
from bson import ObjectId
import ollama
import html
import re
import time
import datetime
from dateutil.relativedelta import relativedelta
import jdatetime
from streamlit_nej_datepicker import datepicker_component, Config
from model_logic import (
    get_admin_mongo_collection,
    get_mongo_collection,
    get_milvus_retrievers_and_mongo_collections,
    ask_llm,
    update_conversation_cache,
    find_similar_liked_questions, 
    get_answer_from_admin_cache
)

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if st.session_state["authenticated"]:
        return True
    st.markdown("<h1 style='text-align: center;'>🔐 پنل دسترسی ادمین</h1>", unsafe_allow_html=True)
    st.markdown("---")
    _, form_col, _ = st.columns([2, 6, 2])
    with form_col:
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; font-family: Vazirmatn, sans-serif;'>ورود به پنل</h3>", unsafe_allow_html=True)
            username = st.text_input("نام کاربری")
            password = st.text_input("رمز عبور", type="password", autocomplete="off")
            _, btn_col, __ = st.columns([2, 2, 2])
            with btn_col:
                submitted = st.form_submit_button("ورود", use_container_width=True)
            if submitted:
                CORRECT_USERNAME = "admin"
                CORRECT_PASSWORD = "123"
                if username == CORRECT_USERNAME and password == CORRECT_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("نام کاربری یا رمز عبور اشتباه است!")
    return False

def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

def display_liked_admin_messages():
    st.header("📝 پیام‌های ذخیره شده توسط ادمین")
    st.markdown("---")
    admin_collection = get_admin_mongo_collection()
    query = {'liked_by_admin': True}
    if admin_collection is None:
        st.error("خطا در اتصال به دیتابیس.")
        return
    liked_admin_messages = list(admin_collection.find(query).sort("timestamp", -1))
    if not liked_admin_messages:
        st.info("هنوز هیچ پیامی در این بخش ذخیره نشده است.")
        return
    now_jalali_str = jdatetime.datetime.now().strftime('%Y-%m-%d')
    for msg in liked_admin_messages:
        msg_id = msg.get('_id')
        end_date = msg.get('end_date')
        is_expired = False
        if end_date:
            if isinstance(end_date, datetime.datetime):
                end_date_str_for_comparison = jdatetime.datetime.fromgregorian(datetime=end_date).strftime('%Y-%m-%d')
                is_expired = end_date_str_for_comparison < now_jalali_str
            elif isinstance(end_date, str):
                is_expired = end_date < now_jalali_str
        with st.container(border=True):
            st.markdown(f"**سوال:**\n> {msg.get('user_question', 'N/A')}")
            st.markdown(f"**پاسخ ذخیره شده:**\n> {msg.get('llm_answer', 'N/A')}")
            if msg.get("sources_data"):
                tooltip_html = create_consolidated_source_tooltip(msg["sources_data"])
                st.markdown(tooltip_html, unsafe_allow_html=True)
            if is_expired:
                if st.session_state.renewing_message_id == msg_id:
                    st.warning("در حال تمدید اعتبار...")
                    renew_col2, renew_col1 = st.columns(2)
                    with renew_col1:
                        st.markdown("**: از تاریخ**")
                        new_start_date_obj = datepicker_component(config=Config(dark_mode=True, locale="fa", selection_mode="single"), key=f"renew_start_date_{msg_id}")
                    with renew_col2:
                        st.markdown("**: تا تاریخ**")
                        new_end_date_obj = datepicker_component(config=Config(dark_mode=True, locale="fa", selection_mode="single"), key=f"renew_end_date_{msg_id}")
                    _, confirm_col, cancel_col = st.columns([5, 2, 1])
                    with confirm_col:
                        if st.button("✅ تایید تمدید", key=f"confirm_renew_{msg_id}", use_container_width=True):
                            if new_start_date_obj and new_end_date_obj:
                                jalali_start_dt = jdatetime.datetime(
                                    year=new_start_date_obj.year,
                                    month=new_start_date_obj.month,
                                    day=new_start_date_obj.day,
                                    hour=0,
                                    minute=0
                                )
                                jalali_end_dt = jdatetime.datetime(
                                    year=new_end_date_obj.year,
                                    month=new_end_date_obj.month,
                                    day=new_end_date_obj.day,
                                    hour=23,
                                    minute=59
                                )
                                start_date_str_to_save = jalali_start_dt.strftime('%Y-%m-%d')
                                end_date_str_to_save = jalali_end_dt.strftime('%Y-%m-%d')
                                admin_collection.update_one(
                                    {'_id': ObjectId(msg_id)},
                                    {'$set': {'start_date': start_date_str_to_save, 'end_date': end_date_str_to_save, 'timestamp': jdatetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}
                                )
                                st.session_state.renewing_message_id = None
                                st.success("اعتبار با موفقیت تمدید شد!")
                                st.rerun()
                            else:
                                st.error("لطفا تاریخ شروع و پایان را برای تمدید مشخص کنید.")
                    with cancel_col:
                        if st.button("لغو", key=f"cancel_renew_{msg_id}", use_container_width=True):
                            st.session_state.renewing_message_id = None
                            st.rerun()
                else:
                    st.error(" اعتبار این پیام به پایان رسیده است.")
                    b_col1, b_col2, _ = st.columns([1, 2, 4])
                    with b_col1:
                        if st.button("🗑️ حذف", key=f"delete_{msg_id}", help="حذف کامل از دیتابیس"):
                            admin_collection.delete_one({'_id': ObjectId(msg_id)})
                            st.toast("پیام با موفقیت حذف شد.")
                            st.rerun()
                    with b_col2:
                        if st.button("🔄 تمدید اعتبار", key=f"renew_{msg_id}"):
                            st.session_state.renewing_message_id = msg_id
                            st.rerun()
            else:
                if st.session_state.editing_validity_id == msg_id:
                    st.warning("در حال ویرایش اعتبار...")
                    renew_col1, renew_col2 = st.columns(2)
                    with renew_col1:
                        st.markdown("**از تاریخ جدید:**")
                        new_start_date_obj = datepicker_component(config=Config(dark_mode=True, locale="fa", selection_mode="single"), key=f"edit_start_date_{msg_id}")
                    with renew_col2:
                        st.markdown("**تا تاریخ جدید:**")
                        new_end_date_obj = datepicker_component(config=Config(dark_mode=True, locale="fa", selection_mode="single"), key=f"edit_end_date_{msg_id}")
                    _, confirm_col, cancel_col = st.columns([4, 2, 2])
                    with confirm_col:
                        if st.button("✅ ذخیره تغییرات", key=f"confirm_edit_{msg_id}", use_container_width=True):
                            if new_start_date_obj and new_end_date_obj:
                                jalali_start_dt = jdatetime.datetime(
                                    year=new_start_date_obj.year, month=new_start_date_obj.month, day=new_start_date_obj.day,
                                    hour=0, minute=0
                                )
                                jalali_end_dt = jdatetime.datetime(
                                    year=new_end_date_obj.year, month=new_end_date_obj.month, day=new_end_date_obj.day,
                                    hour=23, minute=59
                                )
                                start_date_str_to_save = jalali_start_dt.strftime('%Y-%m-%d')
                                end_date_str_to_save = jalali_end_dt.strftime('%Y-%m-%d')
                                admin_collection.update_one(
                                    {'_id': ObjectId(msg_id)},
                                    {'$set': {'start_date': start_date_str_to_save, 'end_date': end_date_str_to_save}}
                                )
                                st.session_state.editing_validity_id = None
                                st.success("اعتبار با موفقیت به‌روزرسانی شد!")
                                st.rerun()
                            else:
                                st.error("لطفا تاریخ شروع و پایان جدید را مشخص کنید.")
                    with cancel_col:
                        if st.button("لغو ویرایش", key=f"cancel_edit_{msg_id}", use_container_width=True):
                            st.session_state.editing_validity_id = None
                            st.rerun()
                else:
                    start_date_val = msg.get('start_date', 'N/A')
                    end_date_val = msg.get('end_date', 'بدون انقضا')
                    start_display, end_display = 'N/A', 'بدون انقضا'
                    try:
                        if isinstance(start_date_val, str):
                            start_display = jdatetime.datetime.strptime(start_date_val, '%Y-%m-%d').strftime('%Y/%m/%d')
                        elif isinstance(start_date_val, datetime.datetime):
                            start_display = jdatetime.datetime.fromgregorian(datetime=start_date_val).strftime('%Y/%m/%d')
                    except (ValueError, TypeError):
                        start_display = f" {start_date_val}"
                    try:
                        if isinstance(end_date_val, str):
                            end_display = jdatetime.datetime.strptime(end_date_val, '%Y-%m-%d').strftime('%Y/%m/%d')
                        elif isinstance(end_date_val, datetime.datetime):
                            end_display = jdatetime.datetime.fromgregorian(datetime=end_date_val).strftime('%Y/%m/%d')
                    except (ValueError, TypeError):
                        end_display = f" {end_date_val}"
                    info_col, btn_col = st.columns([4, 1.5])
                    with info_col:
                        st.info(f"معتبر از: {start_display}  |  تا: {end_display}")
                    with btn_col:
                        if st.button("📝 ویرایش اعتبار", key=f"edit_validity_{msg_id}"):
                            st.session_state.editing_validity_id = msg_id
                            st.rerun()

def create_consolidated_source_tooltip(sources_data: list) -> str:
    if not sources_data or not isinstance(sources_data, list):
        return ""
    all_sources_html = []
    processed_filenames = set()
    for source_info in sources_data:
        filename = source_info.get('filename')
        if not filename or filename in processed_filenames:
            continue
        processed_filenames.add(filename)
        all_quotes_for_file = []
        for s_info in sources_data:
            if s_info.get('filename') == filename and s_info.get('quotes'):
                for q in s_info.get('quotes'):
                    if q not in all_quotes_for_file:
                        all_quotes_for_file.append(q)
        file_html = f'<div class="source-entry"><div class="source-filename"><b>فایل:</b> {html.escape(filename)}</div>'
        if all_quotes_for_file:
            file_html += '<div class="quote-header">نقل قول‌های یافت شده:</div>'
            for quote in all_quotes_for_file:
                file_html += f'<div class="quote">"{html.escape(quote)}"</div>'
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

st.set_page_config(
    page_title="🔐 پنل دسترسی ادمین",
    page_icon="anacav-logo.webp",
    layout="centered",
)

st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            order: 2;
        }
        [data-testid="stMain"] {
            order: 1;
        }
    </style>
    """,
    unsafe_allow_html=True
)

image_path = Path(__file__).parent / "20240815_032319.jpg"
logo_image_path = Path(__file__).parent / "/home/ali/Anacav/ChatBot/test2_shahrestan/logo_no_extra_white.webp"
logo_image_base64 = get_image_as_base64(logo_image_path)
image_base64 = get_image_as_base64(image_path)
font_path = Path(__file__).parent / "Vazirmatn-Regular.woff2"
font_base64 = get_image_as_base64(font_path)

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
    [data-testid="stChatInput"] textarea {{
        font-family: 'Vazirmatn', sans-serif !important;
        text-align: right !important;
        direction: rtl !important;
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
    .tooltiptext * {{
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
    [class="stVerticalBlock st-emotion-cache-1gz5zxc e52wr8w2"]{{
        background-color: rgba(25, 30, 40, 0.95);
    }}
    [data-testid="stCustomComponentV1"]{{
        background-color: #333333;
        border: 1px solid #4A4A4A;
        border-radius: 10px;
        padding: 5px 10px;
    }}
</style>
"""
if image_base64:
    st.markdown(page_bg_style, unsafe_allow_html=True)


with st.sidebar:
    st.markdown("# 💡 توضیحات ادمین ")
    st.markdown(
        "ادمین باید سوالات را دقیق بپرسد تا مدل به درستی آموزش ببیند درصورتی که ادمین سوال ناقص یا نا مفهوم بپرسد در جواب مدل تاثیر منفی میگذارد"
    )

if not check_password():
    st.stop()

if "admin_messages" not in st.session_state:
    st.session_state["admin_messages"] = [{"role": "assistant", "content": "سلام! چطور می‌توانم کمکتان کنم؟", "interaction_id": None}]
if "admin_history_for_llm" not in st.session_state:
    st.session_state["admin_history_for_llm"] = []
if "rated_interactions" not in st.session_state:
    st.session_state.rated_interactions = set()
if "reply_to_index" not in st.session_state:
    st.session_state.reply_to_index = None
if "editing_index" not in st.session_state:
    st.session_state.editing_index = None
if 'admin_view' not in st.session_state:
    st.session_state.admin_view = 'chat'
if 'renewing_message_id' not in st.session_state:
    st.session_state.renewing_message_id = None
if 'regenerating_index' not in st.session_state:
    st.session_state.regenerating_index = None
if 'active_validity_setter' not in st.session_state:
    st.session_state.active_validity_setter = None
if 'validity_period_cache' not in st.session_state:
    st.session_state.validity_period_cache = {}
if 'editing_validity_id' not in st.session_state:
    st.session_state.editing_validity_id = None


if 'autocomplete_suggestions' not in st.session_state:
    st.session_state.autocomplete_suggestions = []
if 'user_input_text' not in st.session_state:
    st.session_state.user_input_text = ""
if 'is_suggestion_selected' not in st.session_state:
    st.session_state.is_suggestion_selected = False


def handle_suggestion_click(question_id, question_text):
    """Callback function for when a suggestion is clicked."""
    st.session_state.is_suggestion_selected = True
    
    # Retrieve answer from cache
    cached_data = get_answer_from_admin_cache(question_id, admin_collection)
    
    if cached_data:
        # Add the user's question and the cached answer to the chat history
        st.session_state.admin_messages.append({"role": "user", "content": question_text, "source": "admin_cache_hit"})
        st.session_state.admin_messages.append({
            "role": "assistant",
            "content": cached_data['answer'],
            "sources_data": cached_data['sources_data'],
            "source": "admin_cache_hit"
        })
        st.session_state.user_input_text = ""  # Clear the input box
        st.session_state.autocomplete_suggestions = [] # Clear suggestions
    st.rerun()


    

@st.cache_resource
def initialize_connections_and_clients():
    mongo_collection = get_mongo_collection()
    admin_collection = get_admin_mongo_collection()
    knowledge_retriever, conversation_vectorstore, mongo_collection, admin_collection, ef,admin_liked_collection = get_milvus_retrievers_and_mongo_collections()
    ollama_client = ollama.Client(host='http://localhost:11434')
    return mongo_collection, admin_collection, knowledge_retriever, conversation_vectorstore, ollama_client, ef,admin_liked_collection

mongo_collection, admin_collection, knowledge_retriever, conversation_vectorstore, ollama_client, ef,admin_liked_collection = initialize_connections_and_clients()

if mongo_collection is None or admin_collection is None or knowledge_retriever is None or conversation_vectorstore is None or ollama_client is None:
    st.error("❌ خطای اساسی در اتصال به سرویس‌ها. لطفاً از اجرای صحیح Ollama و دیتابیس‌ها اطمینان حاصل کنید.")
    st.stop()

if st.session_state.regenerating_index is not None:
    with st.spinner("...در حال بازنویسی پاسخ"):
        idx = st.session_state.regenerating_index
        msg_to_regenerate = st.session_state.admin_messages[idx]
        original_question = msg_to_regenerate.get("user_question")
        history_for_regeneration = st.session_state.admin_history_for_llm[:-1]
        new_answer, _, _, sources_data = ask_llm(
            original_question,
            history_for_regeneration,
            ollama_client,
            mongo_collection,
            knowledge_retriever,
            conversation_vectorstore,
            ef
        )
        st.session_state.admin_messages[idx]['content'] = new_answer
        st.session_state.admin_messages[idx]['sources_data'] = sources_data
        st.session_state.admin_history_for_llm[-1]['content'] = new_answer
        st.session_state.regenerating_index = None
        st.rerun()

with st.sidebar:
    st.markdown("## منوی ادمین")
    if st.session_state.admin_view == 'chat':
        if st.button("مشاهده پیام‌های ذخیره شده", use_container_width=True):
            st.session_state.admin_view = 'liked_admin_messages'
            st.rerun()
    else:
        if st.button("بازگشت به چت", use_container_width=True):
            st.session_state.admin_view = 'chat'
            st.rerun()
    st.markdown("---")
    if st.button("خروج از حساب کاربری", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

if st.session_state.admin_view == 'chat':
    for i, msg in enumerate(st.session_state.admin_messages):
        avatar = "🧠" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            btn_col, content_col = st.columns([0.1, 0.9])
            with content_col:
                citation_pattern = r'\[Source:\s*[\d\s,]+\]'
                cleaned_content = re.sub(citation_pattern, '', msg["content"]).strip()
                st.markdown(cleaned_content)
                if msg.get("sources_data"):
                    tooltip_html = create_consolidated_source_tooltip(msg["sources_data"])
                    st.markdown(tooltip_html, unsafe_allow_html=True)
            with btn_col:
                if st.button("↪️", key=f"reply_{i}", help="پاسخ به این پیام"):
                    st.session_state.reply_to_index = i
                    st.rerun()
            if msg["role"] == "assistant":
                is_from_cache = msg.get("source") == "admin_cache_hit"
                if is_from_cache:
                    continue  # Skip like, edit, and validity buttons for cached messages
                if st.session_state.regenerating_index == i:
                    st.spinner("...در حال تولید پاسخ جدید")
                    st.markdown(" ")
                elif st.session_state.editing_index == i:
                    st.text_area(
                        "ویرایش پاسخ:",
                        value=msg['content'],
                        key=f"editor_{i}",
                        height=250
                    )
                    col1, col2, _ = st.columns([1, 1, 5])
                    with col1:
                        if st.button("ذخیره", key=f"save_{i}"):
                            edited_text = st.session_state[f"editor_{i}"]
                            st.session_state.admin_messages[i]['content'] = edited_text
                            st.session_state.editing_index = None
                            st.rerun()
                    with col2:
                        if st.button("لغو", key=f"cancel_{i}"):
                            st.session_state.editing_index = None
                            st.rerun()
                else:
                    if i > 0:
                        is_rated_key = f"rated_{i}"
                        is_rated = is_rated_key in st.session_state.get('rated_interactions', set())
                        validity_selected = i in st.session_state.validity_period_cache
                        is_regenerating = st.session_state.regenerating_index is not None
                        b_col_like, b_col_edit, b_col_validity, _ = st.columns([1.25, 1.25, 4.75, 5])
                        with b_col_validity:
                            if st.button("📅", key=f"toggle_validity_{i}", help="تنظیم مدت اعتبار", disabled=is_rated):
                                st.session_state.active_validity_setter = i if st.session_state.active_validity_setter != i else None
                                st.rerun()
                        with b_col_like:
                            if st.button("👍", key=f"like_{i}", help="ذخیره در کالکشن ادمین و کش", disabled=(is_rated or not validity_selected)):
                                interaction_id = msg.get("interaction_id")
                                if interaction_id:
                                    mongo_collection.update_one(
                                        {'_id': ObjectId(interaction_id)},
                                        {'$set': {'like_status': 'like'}}
                                    )
                                    question_to_save = msg.get("user_question")
                                    answer_to_save = msg.get("content")
                                    sources_data_to_save = msg.get("sources_data", [])
                                    text_for_embedding = f"Question: {question_to_save}\nAnswer: {answer_to_save}"
                                    try:
                                        embeddings = ef([text_for_embedding])
                                        dense_vector = embeddings["dense"][0].tolist()
                                        sparse_embedding = embeddings["sparse"].getrow(0)
                                        sparse_dict = {int(idx): float(val) for idx, val in zip(sparse_embedding.indices, sparse_embedding.data)}
                                        entities = [
                                            [str(ObjectId())],
                                            [text_for_embedding],
                                            ["admin_cache_entry"],
                                            [sparse_dict],
                                            [dense_vector]
                                        ]
                                        conversation_vectorstore.insert(entities)
                                        print("Inserted admin-liked interaction into conversation vector store.")
                                    except Exception as e:
                                        print(f"Error inserting into Milvus from admin page: {e}")
                                        st.error("خطا در ذخیره پاسخ در پایگاه داده برداری.")
                                    cached_dates = st.session_state.validity_period_cache[i]
                                    start_date_str_to_save = cached_dates['start']
                                    end_date_str_to_save = cached_dates['end']
                                    now = jdatetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    admin_collection.insert_one({
                                        'user_question': question_to_save,
                                        'llm_answer': answer_to_save,
                                        'sources_data': sources_data_to_save,
                                        'timestamp': now,
                                        'liked_by_admin': True,
                                        'start_date': start_date_str_to_save,
                                        'end_date': end_date_str_to_save
                                    })
                                    st.session_state.rated_interactions.add(is_rated_key)
                                    st.toast("✅ گفتگو با مدت اعتبار مشخص ذخیره شد!", icon="👍")
                                    st.session_state.active_validity_setter = None
                                    del st.session_state.validity_period_cache[i]
                                    st.rerun()
                        with b_col_edit:
                            if st.button("📝", key=f"edit_{i}", help="ویرایش این پاسخ", disabled=is_rated):
                                st.session_state.editing_index = i
                                st.rerun()
                        if st.session_state.active_validity_setter == i:
                            with st.container(border=True):
                                st.markdown("##### تعیین مدت اعتبار")
                                d_col2, d_col1 = st.columns(2)
                                with d_col1:
                                    st.markdown("**از تاریخ:**")
                                    start_date_obj = datepicker_component(config=Config(dark_mode=True, locale="fa", selection_mode="single"), key=f"start_date_{i}")
                                with d_col2:
                                    st.markdown("**تا تاریخ:**")
                                    end_date_obj = datepicker_component(config=Config(dark_mode=True, locale="fa", selection_mode="single"), key=f"end_date_{i}")
                                date_selected = start_date_obj and end_date_obj
                                st.markdown("---")
                                btn_confirm_col, btn_cancel_col, _ = st.columns([2, 1, 5])
                                with btn_confirm_col:
                                    if st.button("✅ تایید اعتبار", key=f"confirm_validity_{i}", disabled=(not date_selected)):
                                        jalali_start_dt = jdatetime.datetime(
                                            year=start_date_obj.year, month=start_date_obj.month, day=start_date_obj.day,
                                            hour=0, minute=0
                                        )
                                        jalali_end_dt = jdatetime.datetime(
                                            year=end_date_obj.year, month=end_date_obj.month, day=end_date_obj.day,
                                            hour=23, minute=59
                                        )
                                        st.session_state.validity_period_cache[i] = {
                                            'start': jalali_start_dt.strftime('%Y-%m-%d'),
                                            'end': jalali_end_dt.strftime('%Y-%m-%d')
                                        }
                                        st.toast("اعتبار تنظیم شد. اکنون می‌توانید پیام را ذخیره کنید.", icon="📅")
                                        st.session_state.active_validity_setter = None
                                        st.rerun()
                                with btn_cancel_col:
                                    if st.button("لغو", key=f"cancel_validity_{i}"):
                                        st.session_state.active_validity_setter = None
                                        st.rerun()

    if st.session_state.reply_to_index is not None:
        replied_message = st.session_state.admin_messages[st.session_state.reply_to_index]
        author = "دستیار" if replied_message['role'] == 'assistant' else "شما"
        with st.container(border=True):
            st.markdown(f"**در حال پاسخ به {author}:**")
            st.markdown(f"> *{replied_message['content'][:80]}...*")
            if st.button("لغو پاسخ", key="cancel_reply"):
                st.session_state.reply_to_index = None
                st.rerun()

    if prompt := st.chat_input("پیام خود را بنویسید...", key="chat_input"):
        user_message_content = prompt
        if st.session_state.reply_to_index is not None:
            replied_text = st.session_state.admin_messages[st.session_state.reply_to_index]['content']
            replied_text_clean = replied_text.split("\n\n*منبع:")[0]
            user_message_content = f"در پاسخ به پیام «{replied_text_clean}»:\n\n{prompt}"
        st.session_state.admin_messages.append({"role": "user", "content": user_message_content, "interaction_id": None})
        st.session_state.reply_to_index = None
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_message_content)
        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("در حال فکر کردن..."):
                llm_history = st.session_state.admin_history_for_llm[-2:]
                answer, interaction_id, source, sources_data = ask_llm(
                    user_message_content, llm_history, ollama_client, mongo_collection, admin_collection, knowledge_retriever, conversation_vectorstore, ef,admin_liked_collection
                )
                source_emoji_map = {
                    "smart_cache_majority_like": "⚡️ از کش هوشمند",
                    "rag_generation_avoiding_dislike": "🤔 تولید جدید (با یادگیری از بازخورد)",
                    "rag_langgraph_generation": "📚 از پایگاه دانش (با استناد)",
                }
                source_text = source_emoji_map.get(source, "")
                assistant_message = {
                    "role": "assistant",
                    "content": answer,
                    "interaction_id": interaction_id,
                    "user_question": user_message_content,
                    "sources_data": sources_data,
                    "source": source
                }
                st.session_state.admin_messages.append(assistant_message)
                st.session_state.admin_history_for_llm.append({"role": "user", "content": user_message_content})
                st.session_state.admin_history_for_llm.append({"role": "assistant", "content": answer})
        st.rerun()
elif st.session_state.admin_view == 'liked_admin_messages':
    display_liked_admin_messages()