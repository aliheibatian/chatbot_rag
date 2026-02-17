import streamlit as st
from pathlib import Path
import base64
from form import show_page as show_assignment_form 
from billing import show_page as show_billing_protest_form

# تابع برای تبدیل تصویر به base64
def get_image_as_base64(file_path):
    try:
        full_path = Path(file_path)
        if not full_path.exists():
            # ارور نمایش داده می‌شود اما برنامه ادامه پیدا می‌کند
            # در صورت عدم وجود فایل، مقدار None برمی‌گرداند
            # st.error(f"فایل تصویر در مسیر '{file_path}' پیدا نشد.") 
            return None
        with open(full_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e:
        # st.error(f"خطا در تبدیل فایل به base64: {e}")
        return None

# مسیر فایل‌ها
logo_image_path = Path(__file__).parent / "logo_no_extra_white.webp"
logo_image_base64 = get_image_as_base64(logo_image_path)
image_path = Path(__file__).parent / "20240815_032319.jpg"
image_base64 = get_image_as_base64(image_path)
font_path = Path(__file__).parent / "Vazirmatn-Regular.woff2"
font_base64 = get_image_as_base64(font_path)



if 'info_text' not in st.session_state:
        st.session_state.info_text = ""
        
page_bg_style = f"""
<style>    
    @font-face {{
        font-family: 'Vazirmatn';
        src: url(data:font/woff2;base64,{font_base64}) format('woff2');
    }}
    body, .stApp, [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/jpeg;base64,{image_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        direction: rtl;
        text-align: center;
        font-family: 'Vazirmatn', sans-serif !important;
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


    /* 2. Hide the sidebar menu button */
    button[data-testid="stBaseButton-headerNoPadding"] {{
        display: none !important;
    }}

    /* ** 🚀 بخش حیاتی برای تیره کردن باکس‌های محتوا، از جمله کانتینر اصلی **
    ** این سلکتورها بالاترین اولویت را برای پس‌زمینه بلاک‌ها اعمال می‌کنند. **
    */
    
    [data-testid="stVerticalBlockBorderWrapper"], /* هدف قرار دادن st.container(border=True) */
    [data-testid="stVerticalBlock"],              /* هدف قرار دادن کانتینرهای والد و ستون‌ها */
    .stForm {{
        /* تنظیم رنگ بسیار تیره و مات (98% تیرگی) */
        # background-color: rgba(15, 15, 15, 0.5) !important; 
        # border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 15px !important;
        # padding: 2em !important;
        backdrop-filter: blur(10px) !important;
    }}

    # /* برای ستون‌ها (Columns) و expanderها */
    # .st-emotion-cache-1wmy9hl, .st-emotion-cache-1r6slb0, .st-emotion-cache-1cypcdb {{
    #     background-color: rgba(15, 15, 15, 0.98) !important;
    #     border-radius: 15px !important;
    #     padding: 1em !important;
    # }}
    
    
    /* 4. Force all text elements to be white for readability */
    h1, h2, h3, p, label,.st-emotion-cache-1o77jex, .st-emotion-cache-1r6slb0, .st-emotion-cache-183lzff, .st-emotion-cache-ue6h4q, .st-emotion-cache-1cypcdb, .st-emotion-cache-1y4p8pa, .st-emotion-cache-16cq8s3 {{
         color: #FFFFFF !important;
         font-family: 'Vazirmatn', sans-serif !important;
    }}

    /* 5. Specific overrides for input/text area fields */
    .stTextInput > div > input, .stTextArea > div > textarea, .stSelectbox > div > select, .stRadio > div, .stDateInput > div > div {{
        text-align: right;
        background-color: #333333;
        color: #FFFFFF;
        font-family: 'Vazirmatn', sans-serif !important;
    }}
    
    .stButton > button {{
        float: right;
    }}
    
    [data-testid="stSidebar"] {{
        text-align: right;
        direction: rtl;
        background: transparent !important;
        border: none !important;
        backdrop-filter: none !important;
        margin-right: 0 !important; /* برای قرارگیری صحیح در RTL */
        left: unset !important;
        right: 0 !important;
    }}

    /* این بخش برای اطمینان از شفافیت محتوای داخلی باقی می‌ماند */
    [data-testid="stSidebar"] > div:first-child {{
        background: transparent !important;
    }}
    
    /* حذف استایل برای stLayoutWrapper که ممکن است پس‌زمینه را بپوشاند */
    /* [data-testid="stLayoutWrapper"]{{
        direction: rtl !important;
        background-color: rgba(45, 45, 45, 0.9) !important;
        border-radius: 15px !important;
        padding: 2em !important;
        backdrop-filter: blur(10px) !important;
    }} */

    [data-testid="stCustomComponentV1"]{{
        background-color: #1E1E1E;
        border: 1px solid #4A4A4A;
        border-radius: 10px;
        padding: 5px 10px;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }}
    
    /* استایل دهی به نوار بالای صفحه (header) */
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
        background: rgb(0 0 0 / 0%); /* مطمئن شوید که کاملاً شفاف است */
        outline: none;
        z-index: 999990;
        pointer-events: auto;
        font-size: 0.875rem;
    }}
    .button-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        flex-wrap: wrap;
        gap: 2rem;
        padding-top: 3rem;
    }}
    .stButton > button:hover {{
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-color: #FFFFFF !important;
    }}

    div[class*="st-key-circ_"] .stButton > button {{
        border-radius: 50% !important;
        width: 180px !important;
        height: 180px !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        border: 3px solid rgba(255, 255, 255, 0.7) !important;
        background-color: rgba(0, 0, 0, 0.4) !important;
        transition: all 0.3s ease !important;
        display: flex;
        justify-content: center;
        align-items: center;
        text-align: center;
        line-height: 1.4; /* برای شکستن خط در صورت نیاز */
    }}
    
   
</style>
"""


def main_page():



    st.set_page_config(
    page_title="دستیار خدمات هوشمند",
    page_icon="anacav-logo.webp",
    layout="wide"
)

    if image_base64 and font_base64 and logo_image_base64:
        st.markdown(page_bg_style, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            body, .stApp {
                background-color: #111111;
                direction: rtl;
            }
        </style>
        """, unsafe_allow_html=True)

    if 'view_state' not in st.session_state:
        st.session_state.view_state = 'main_menu'

    def set_view(view):
        st.session_state.view_state = view
        
    st.title("سامانه هوشمند خدمات شرکت توزیع برق شهرستان اصفهان")

    if st.session_state.view_state == 'main_menu':
        st.write("به سامانه هوشمند خدمات شرکت توزیع برق شهرستان اصفهان خوش امدید.")
        st.write("در این سامانه می توانید تمام خدمات مربوط به برق را بصورت غیرحضوری از جمله : تبت و پیگیری درخواست ها ،مشاهده ی سوابق درخواست های قبلی ، مشاهده و مدیریت انشعاب های برق و بسازی خدمات دیگر به صورت ساده و سریع انجام دهید ")
        st.write("ما اینجا هستیم تا تجربه ی هوشمند، دقیق و راحت برای شما فراهم کنیم .")
        
        st.divider()
        with st.container():
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.button("ثبت درخواست خدمات", on_click=set_view, args=('services',), key="circ_btn_sabt")
            with col2:
                st.button("پیگیری درخواست", on_click=set_view, args=('tracking',),key="circ_btn_peigir")
            with col3:
                st.button("خدمات صورتحساب", on_click=set_view, args=('billing',), key="circ_btn_bill")
            with col4:
                st.button("مشاوره تخصصی", on_click=set_view, args=('consulting',), key="circ_btn_mosh")
            with col5:
                st.button("پروفایل من", on_click=set_view, args=('profile',), key="circ_btn_prof")
            
    elif st.session_state.view_state == 'services':
        
        
        st.divider()
        with st.container():
        
            col1,col2,col3, col4 = st.columns(4)
            with col3:
                st.button("واگذاری انشعاب",on_click=set_view, args=('donate',), key="circ_btn_subscription")
            with col2:
                st.button("خدمات پس از فروش", on_click=set_view, args=('after_sales',),key="circ_btn_aft")
                
        st.divider()

        col1, col2, col3= st.columns([5,7,0.05])
        with col2:
            back_col, _ = st.columns([1, 4])  
            with back_col:
                if st.button(" بازگشت", key="back_to_main_menu"):
                    set_view('main_menu')
                    st.rerun()
           

    elif st.session_state.view_state == 'after_sales':
             
        st.divider()
        with st.container():
            
            st.subheader("خدمات پس از فروش")
            msg = "این بخش در حال توسعه است."
            col1, col2, col3, col4, col5 , col6 = st.columns(6)
            with col1:
                if st.button("جابجایی کنتور (در داخل)", key="circ_btn_jabejaei_kontor"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("تغییر قدرت", key="circ_change_power"):
                    st.session_state.info_text = ""
                    set_view('change_power')
                    st.rerun()
            with col2:
                if st.button("تغییر نام", key="circ_btn_taghir_nam"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("تست کنتور", key="circ_btn_test_kontor"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col3:
                if st.button("جمع آوری و نصب مجدد انشعاب", key="circ_install"):
                    st.session_state.info_text = "" # پاک کردن متن قبل از رفتن به صفحه جدید
                    set_view('insatall_again')
                    st.rerun()
                if st.button("تعویض کنتور", key="circ_change_kontor"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col4:
                if st.button("درخواست تقسیط هزینه انشعاب", key="circ_btn_darkhast_taghsit_hazine"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("استعلام", key="circ_btn_esteelam"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col5:
                if st.button("تغییر تعرفه", key="circ_btn_taghir_tarifeh"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("رفع اشکال لوازم اندازه گیری", key="circ_btn_raf_eshkal_lavazem"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col6:
                if st.button("قطع موقت و وصل جریان", key="circ_ghat_jaryan"):
                    st.session_state.info_text = "" # پاک کردن متن قبل از رفتن به صفحه جدید
                    set_view('dis_connect')
                    st.rerun()
                if st.button("تمدید تاریخ مجوز تعرفه", key="circ_btn_tamdid_tarikh_mojavaz"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                                    
        if 'info_text' in st.session_state and st.session_state.info_text:
            st.info(st.session_state.info_text)
                
        st.divider()
        col1, col2, col3= st.columns([6,7,0.05])
        with col2:
            back_col, _ = st.columns([1, 4])  
            with back_col:
                if st.button(" بازگشت", key="back_to_serv"):
                    st.session_state.info_text = ""
                    set_view('services')
                    st.rerun()

        
    elif st.session_state.view_state == 'donate': 
        st.divider()
        
        if st.button("واگذاری انشعاب", key="circ_btn_raf_eshkal_lavazem"):
                set_view('assignment_form')
                st.rerun()
        st.divider()
        col1, col2, col3= st.columns([6,7,0.05])
        with col2:
            back_col, _ = st.columns([1, 4])  
            with back_col:
                if st.button(" بازگشت", key="back_to_serv"):
                    st.session_state.info_text = ""
                    set_view('services')
                    st.rerun()
    
    elif st.session_state.view_state == 'change_power': 
        st.subheader("خدمات پس از فروش")

        msg = "این بخش در حال توسعه است."    
        st.divider()   
        with st.container():

            col1, col2, col3, col4 = st.columns(4)
            with col3:
                if st.button("کاهش قدرت", key="circ_decrease_power"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("افزایش قدرت", key="circ_increase_power"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()      
            if st.session_state.info_text:
                st.info(st.session_state.info_text)
            
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_aft"):
                        st.session_state.info_text = ""
                        set_view('after_sales')
                        st.rerun()
        
                
    elif st.session_state.view_state == 'insatall_again': 
        st.divider()   
        msg = "این بخش در حال توسعه است."
        with st.container():

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if st.button("جمع آوری برق موقت غیر کارگاهی", key="circ_sum_elec"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("جمع آوری موقت انشعاب", key="circ_sum_elec2"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col3:
                if st.button("جمع آوری دائم", key="circ_sum_elec_all"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col4:
                if st.button("نصب مجدد", key="circ_install_again"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            if st.session_state.info_text:
                st.info(st.session_state.info_text)
            
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_aft2"):
                        st.session_state.info_text = ""
                        set_view('after_sales')
                        st.rerun()
     
    elif st.session_state.view_state == 'dis_connect':   
        st.divider() 
        msg = "این بخش در حال توسعه است."
        with st.container():
                
            col1, col2, col3, col4 = st.columns(4)
            with col3:
                if st.button("قطع موقت جریان", key="circ_disconnect"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("وصل جریان", key="circ_connect"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()  

            if st.session_state.info_text:
                st.info(st.session_state.info_text)
                
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_aft3"):
                        st.session_state.info_text = ""
                        set_view('after_sales')
                        st.rerun()
                        
    elif st.session_state.view_state == 'tracking':
        st.subheader("پیگیری درخواست")
        st.divider()
        msg = "این بخش در حال توسعه است."
        with st.container():

            col1, col2, col3= st.columns([6,7,3])
            with col2:
                if st.button("ثبت پیگیری درخواست", key="circ_btn_pigiri_darkhast"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()         
            if st.session_state.info_text:
                st.info(st.session_state.info_text)
                
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_men"):
                        st.session_state.info_text = ""
                        set_view('main_menu')
                        st.rerun()
        
    elif st.session_state.view_state == 'billing':
        st.divider()
        with st.container():
            
            st.subheader("خدمات صورتحساب")
            msg = "این بخش در حال توسعه است."
            col1, col2, col3, col4, col5 , col6 = st.columns(6)
            with col1:
                if st.button("اعتراض به صورت حساب", key="circ_protest"):
                    set_view('billing_protest_form') # state جدید برای فرم اعتراض
                    st.rerun()
                if st.button("تقسیط انرژی", key="circ_divide"):
                    st.session_state.info_text = ""
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("تسویه حساب", key="circ_pay_bill2"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("اصلاح اطلاعات", key="circ_edit"):
                    st.session_state.info_text = "" # پاک کردن متن قبل از رفتن به صفحه جدید
                    set_view('edit')
                    st.rerun()
            with col3:
                if st.button("کد خانوار", key="circ_family_code"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("خود اظهاری", key="circ_self_ez"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col4:
                if st.button("ثبت کیلووات دربسته", key="circ_kw_bast"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("اعلام درخواست وصول مطالبات", key="circ_vosool"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col5:
                if st.button("اعلام پرداخت پس از موعود", key="circ_pay_after"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
                if st.button("مشاهده ی آخرین صورتحساب", key="circ_see_pay"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col6:
                if st.button("سوابق", key="circ_sava"):
                    st.session_state.info_text = "" # پاک کردن متن قبل از رفتن به صفحه جدید
                    set_view('savavbegh')
                    st.rerun()
                if st.button("پرداخت آخرین صورتحساب", key="circ_pay_bill3"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()    
        if 'info_text' in st.session_state and st.session_state.info_text:
            st.info(st.session_state.info_text)
                
        st.divider()
        col1, col2, col3= st.columns([6,7,0.05])
        with col2:
            back_col, _ = st.columns([1, 4])  
            with back_col:
                if st.button(" بازگشت", key="back_to_serv"):
                    st.session_state.info_text = ""
                    set_view('main_menu')
                    st.rerun()
                    
                    
    elif st.session_state.view_state == 'edit':
        st.divider() 
        msg = "این بخش در حال توسعه است."
        with st.container():   
            col1, col2, col3, col4 = st.columns(4)
            with col3:
                if st.button("درج کد پستی", key="circ_post_code_en"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("اصلاح شماره موبایل مصرف کننده", key="circ_edit_phone"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()  
            if st.session_state.info_text:
                st.info(st.session_state.info_text)
                
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_bill"):
                        st.session_state.info_text = ""
                        set_view('billing')
                        st.rerun()
                        
     
    elif st.session_state.view_state == 'savavbegh':   
        st.divider() 
        msg = "این بخش در حال توسعه است."
        with st.container():  
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("صورتحساب", key="circ_billl"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("مصرف", key="circ_use"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()  
            with col3:
                if st.button("پرداخت", key="circ_payy"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()          
            if st.session_state.info_text:
                st.info(st.session_state.info_text)
                
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_bill2"):
                        st.session_state.info_text = ""
                        set_view('billing')
                        st.rerun()
          
    elif st.session_state.view_state == 'consulting':
        st.divider()
        msg = "این بخش در حال توسعه است."
        col1, col2, col3= st.columns([6,7,1])
        with col2:
             if st.button("مشاوره های تخصصی", key="circ_mosh"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()     
               
        if st.session_state.info_text:
                st.info(st.session_state.info_text)
        st.divider()
        
        col1, col2, col3= st.columns([6,7,0.05])
        with col2:
            back_col, _ = st.columns([1, 4])  
            with back_col:
                if st.button(" بازگشت", key="back_to_serv2"):
                    st.session_state.info_text = ""
                    set_view('main_menu')
                    st.rerun()
    
        
        
                
    elif st.session_state.view_state == 'profile':
        st.divider() 
        msg = "این بخش در حال توسعه است."
        with st.container():
                
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("درخواست های من", key="circ_request"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()
            with col2:
                if st.button("انشعابهای برق من", key="circ_my_elec"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()  
            with col3:
                if st.button("اطلاعات شخصی", key="circ_personal_info"):
                    st.session_state.info_text = "" if st.session_state.info_text == msg else msg
                    st.rerun()  
       
            if st.session_state.info_text:
                st.info(st.session_state.info_text)
                
            st.divider()
            col1, col2, col3= st.columns([6,7,1])
            with col2:
                back_col, _ = st.columns([1, 4])  
                with back_col:
                    if st.button(" بازگشت", key="back_to_main3"):
                        st.session_state.info_text = ""
                        set_view('main_menu')
                        st.rerun()
        
    elif st.session_state.view_state == 'assignment_form':
        show_assignment_form()
    elif st.session_state.view_state == 'billing_protest_form':
        show_billing_protest_form()
        
pages = st.navigation([
    st.Page(main_page, title="صفحه اصلی", icon="🏠"),
    st.Page("app.py", title="دستیار هوشمند", icon="💡"),
    st.Page("admin_page.py", title="دسترسی ادمین", icon="🔐")
    # st.Page("pages/form.py", title="ثبت واگذاری", icon="📝"),
    # st.Page("billing.py", title="اعتراض به مبلغ صورتحساب", icon="❗")
])


pages.run()








# import streamlit as st
# from pathlib import Path
# import base64
# from form import show_page as show_assignment_form 
# from billing import show_page as show_billing_protest_form



# def get_image_as_base64(file_path):
#     try:
#         full_path = Path(file_path)
#         if not full_path.exists():
#             return None
#         with open(full_path, "rb") as f:
#             data = f.read()
#         return base64.b64encode(data).decode()
#     except Exception as e:
#         return None

# logo_image_path = Path(__file__).parent / "logo_no_extra_white.webp"
# logo_image_base64 = get_image_as_base64(logo_image_path)
# image_path = Path(__file__).parent / "20240815_032319.jpg"
# image_base64 = get_image_as_base64(image_path)
# font_path = Path(__file__).parent / "Vazirmatn-Regular.woff2"
# font_base64 = get_image_as_base64(font_path)

# if 'info_text' not in st.session_state:
#         st.session_state.info_text = ""

# page_style = f"""
# <style>

#     @font-face {{
#         font-family: 'Vazirmatn';
#         src: url(data:font/woff2;base64,{font_base64}) format('woff2');
#     }}
#     body, .stApp, [data-testid="stAppViewContainer"] {{
#         background-image: url("data:image/jpeg;base64,{image_base64}");
#         background-size: cover; background-position: center;
#         background-repeat: no-repeat; background-attachment: fixed;
#         direction: rtl; text-align: center;
#         font-family: 'Vazirmatn', sans-serif !important;
#     }}
#      [data-testid="stSidebar"] > div:first-child::before {{
#         content: "";
#         display: block;
#         margin: 2rem auto 0rem auto;
#         width: 180px;              
#         height: 180px;     
#         background-image: url("data:image/png;base64,{logo_image_base64}");
#         background-size: 180px 150px; 
#         background-repeat: no-repeat;
#         background-position: center 2rem; 
#         border-radius: 30px; 
#         position: relative; /* <-- این خط را اضافه کنید */
#         z-index: 10;        /* <-- این خط را اضافه کنید */
#     }}

#     /* این قانون جدید، متن‌های منو را روی پس‌زمینه می‌آورد */
#     [data-testid="stSidebar"] > div:first-child > div {{
#         position: relative; /* <-- این خط را اضافه کنید */
#         z-index: 10;        /* <-- این خط را اضافه کنید */
#     }}
#     [data-testid="stSidebar"] {{
#         text-align: right;
#         direction: rtl;
#         background: transparent !important;
#         border: none !important;
#         backdrop-filter: none !important;
#     }}
#     /* این بخش برای اطمینان از شفافیت محتوای داخلی باقی می‌ماند */
#     [data-testid="stSidebar"] > div:first-child {{
#         background-color: rgba(100, 100, 100 / 17%) !important; /* <-- پس‌زمینه نیمه-شفاف (85%) */
#         backdrop-filter: blur(10px) !important;             /* <-- افکت شیشه مات (بلور) */
#         position: relative;
#         /* (اختیاری) اضافه کردن حاشیه و فاصله برای زیبایی بیشتر */
#         border-radius: 15px;
#         border: 1px solid rgba(255, 255, 255, 0.1);
#         margin: 1rem;
#     }}
#     .st-emotion-cache-gquqoo {{
#         position: absolute;
#         top: 0px;
#         left: 0px;
#         right: 0px;
#         display: flex;
#         -webkit-box-align: center;
#         align-items: center;
#         height: 3.75rem;
#         min-height: 3.75rem;
#         width: 100%;
#         background: rgb(0 0 0 / 0%); 
#         outline: none;
#         z-index: 999990;
#         pointer-events: auto;
#         font-size: 0.875rem;
#      }}
#      [data-testid="stVerticalBlockBorderWrapper"], 
#      [data-testid="stVerticalBlock"],             
#      .stForm {{
#          /* تنظیم رنگ بسیار تیره و مات (98% تیرگی) */
#          # background-color: rgba(15, 15, 15, 0.5) !important; 
#          # border: 1px solid rgba(255, 255, 255, 0.2) !important;
#          border-radius: 15px !important;
#          # padding: 2em !important;
#          backdrop-filter: blur(10px) !important;
#      }}

#      /* 2. Hide the sidebar menu button */
#      button[data-testid="stBaseButton-headerNoPadding"] {{
#          display: none !important;
#      }}

#     h1, h2, h3, p, label, div {{
#         color: #FFFFFF !important;
#         font-family: 'Vazirmatn', sans-serif !important;
#     }}
#     .stButton > button {{ color: #FFFFFF !important; }}
#     button[data-testid="stBaseButton-headerNoPadding"] {{ display: none !important; }}


#     /* --- استایل اصلی ساختار درختی --- */
#     .tree-container {{
#         width: 100%; display: flex; flex-direction: column;
#         align-items: center; padding: 2rem 0;
#     }}
#     .tree-level {{
#         display: flex; justify-content: center;
#         position: relative; padding: 2.5rem 0; gap: 2rem;
#     }}
#     .tree-node {{
#         position: relative;
#     }}
#     .tree-node .stButton > button {{
#         width: 220px !important; height: 80px !important;
#         font-size: 1.1rem !important; font-weight: bold !important;
#         text-align: center; line-height: 1.5;
#         background: rgba(255, 255, 255, 0.1) !important;
#         backdrop-filter: blur(12px) !important;
#         border: 1px solid rgba(255, 255, 255, 0.2) !important;
#         border-radius: 15px !important;
#         box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
#         transition: all 0.3s ease !important;
#     }}
#     .tree-node .stButton > button:hover {{
#         transform: scale(1.08);
#         background: rgba(255, 255, 255, 0.25) !important;
#         box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
#     }}
#     .tree-node.active .stButton > button {{
#         border: 2px solid #FFFFFF !important;
#         background: rgba(90, 150, 255, 0.25) !important;
#     }}

#     /* --- رسم خطوط اتصال --- */
#     /* خط عمودی که از فرزند به سمت والد (بالا) می‌رود */
#     .tree-node::before {{
#         content: ''; position: absolute;
#         top: -2.5rem; left: 50%;
#         transform: translateX(-50%);
#         width: 2px; height: 2.5rem;
#         background-color: rgba(255, 255, 255, 0.5);
#     }}
#     /* خط عمودی که از والد به سمت فرزندان (پایین) می‌رود */
#     .tree-node.parent-node::after {{
#         content: ''; position: absolute;
#         bottom: -2.5rem; left: 50%;
#         transform: translateX(-50%);
#         width: 2px; height: 2.5rem;
#         background-color: rgba(255, 255, 255, 0.5);
#         gap: 1rem;
#     }}
#     /* خط افقی که فرزندان یک سطح را به هم متصل می‌کند */
#     .tree-level::before {{
#         content: ''; position: absolute; top: 0;
#         height: 2px; background-color: rgba(255, 255, 255, 0.5);
#         /* عرض خط افقی بر اساس تعداد فرزندان تنظیم می‌شود */
#     }}
#     /* تنظیم عرض خط افقی برای سطوح مختلف */
#     .level-2-children::before {{ left: 25%; right: 25%; }}
#     .level-3-children::before {{ left: 16.66%; right: 16.66%; }}
#     .level-4-children::before {{ left: 12.5%; right: 12.5%; }}
#     .level-5-children::before {{ left: 10%; right: 10%; }}

#     /* حذف خطوط اضافی */
#     .tree-level.root .tree-node::before {{ display: none; }}
#     .tree-level:has(.tree-node:only-child)::before {{ display: none; }}
    
#     .tree-level-vertical {{
#     display: flex;
#     flex-direction: column; /* چیدمان عمودی */
#     align-items: center;   /* همه آیتم‌ها در مرکز قرار می‌گیرند */
#     position: relative;
#     padding: 2rem 0;
#     gap: 2rem !important; /* فاصله بین دکمه‌ها */
# }}

# /* استایل هر دکمه در لیست عمودی */
# .vertical-node .stButton > button {{
#     width: 400px !important;  /* عرض ثابت و مناسب */
#     max-width: 90% !important;
#     height: 65px !important;  /* ارتفاع کمتر از حالت افقی */
#     font-size: 1.1rem !important;
#     text-align: right !important; /* چینش متن از راست */
#     display: flex;
#     align-items: center;
#     justify-content: flex-start; /* متن از سمت راست شروع شود */
#     padding-right: 2rem !important;
# }}

# /* خط اتصال از والد به لیست عمودی */
# .tree-level-vertical::before {{
#     content: '';
#     position: absolute;
#     top: 0rem; /* به اندازه padding والد */
#     left: 50%;
#     transform: translateX(-50%);
#     width: 2px;
#     height: 2.5rem; /* طول خط اتصال */
#     background-color: rgba(255, 255, 255, 0.5);
# }}

# /* حذف خطوط اتصال اضافی برای آیتم‌های لیست عمودی */
# .vertical-node::before, .vertical-node::after {{
#     display: none !important;
# }}

# .vertical-node {{
#         margin-top: 0.15rem !important;
#         margin-bottom: 0.15rem !important;
#         padding: 0 !important;
#     }}
    
# [data-testid="stVerticalBlock"]{{
#     gap: 0.25rem;
# }}

# .vertical-content-display {{
#         width: 400px; /* هم‌عرض با دکمه‌های عمودی */
#         max-width: 90%;
#         margin: 0.5rem auto 0 auto; /* 0.5rem فاصله از دکمه بالا */
#         padding: 1.5rem;
#         background: rgba(30, 30, 30, 0.7); /* پس‌زمینه نیمه‌شفاف */
#         backdrop-filter: blur(10px);
#         border: 1px solid rgba(255, 255, 255, 0.2);
#         border-radius: 10px;
#         text-align: right; /* متن راست‌چین */
#     }}
    
#     /* حذف پس‌زمینه و حاشیه st.info در داخل کادر جدید */
#     .vertical-content-display .stAlert {{
#         background-color: transparent !important;
#         border: none !important;
#         padding: 0 !important;
#         text-align: right !important;
#     }}

#     /* اطمینان از سفید بودن و راست‌چین بودن متن پیام */
#     .vertical-content-display .stAlert p {{
#             text-align: right !important;
#             color: #FFFFFF !important;
#     }}
# </style>
# """

# st.set_page_config(
#     page_title="دستیار خدمات هوشمند",
#     page_icon="anacav-logo.webp",
#     layout="wide"
#     )

# def main_page():
#     SERVICE_TREE = {
#         "ثبت درخواست خدمات": {
#             "واگذاری انشعاب": {
#                 "واگذاری انشعاب":"content"
#                 },
#             "خدمات پس از فروش": {
#                 "تغییر قدرت":{
#                     "کاهش قدرت":"content",
#                     "افزایش قدرت":"content"
#                 },
#                 "تغییر نام":"content",
#                 "جابجایی کنتور(در داخل)":"content",
#                 "تعویض کنتور":"content",
#                 "جمع آوری و نصب مجدد انشعاب":{
#                 "جمع آوری برق موقت غیر کارگاهی":"content",
#                 "جمع آوری موقت انشعاب":"content",
#                 "جمع آوری دائم":"content",
#                 "نصب مجدد":"content"                     
#                 },
#                 "تست کنتور":"content",
#                 "رفع اشکال لوازم اندازه گیری":"content",
#                 "تغییر تعرفه":"content",
#                 "تمدید تاریخ مجوز تعرفه":"content",
#                 "قطع موقت و وصل جریان":{
#                     "قطع موقت جریان":"content",
#                     "وصل جریان":"content"    
#                 },
#                 "درخواست تقسیط هزینه انشعاب":"content",
#                 "استعلام":"content",            
#                 }},
#         "پیگیری درخواست":"content",
#         "خدمات صورتحساب":{
#                 "پرداخت آخرین صورتحساب":"content",
#                 "مشاهده ی آخرین صورتحساب":"content",
#                 "سوابق":{
#                     "صورتحساب":"content",
#                     "مصرف":"content",
#                     "پرداخت":"content"
#                 },
#                 "تسویه حساب":"content" ,
#                 "اعتراض به صورت حساب":"content",
#                 "اصلاح اطلاعات":{
#                     "درج کد پستی":"content",
#                     "اصلاح شماره موبایل مصرف کننده":"content"
#                 },
#                 "تقسیط انرژی":"content",
#                 "خود اظهاری":"content",
#                 "کد خانوار":"content",
#                 "ثبت کیلووات دربسته":"content",
#                 "اعلام درخواست وصول مطالبات":"content",
#                 "اعلام پرداخت پس از موعود":"content"
#                 },
#         "مشاوره های تخصصی":"content",
#         "پروفایل من":{
#             "درخواستهای من":"content",
#             "انشعابهای برق من":"content",
#             "اطلاعات شخصی":"content"
#         } 
#         }

#     st.markdown(page_style, unsafe_allow_html=True)
#     st.markdown("""
#          <style>
#              body, .stApp {
#                  background-color: #111111;
#                  direction: rtl;
#              }
#          </style>
#          """, unsafe_allow_html=True)

#     if 'view_state' not in st.session_state:
#         st.session_state.view_state = 'main_tree'
#     if 'active_path' not in st.session_state:
#         st.session_state.active_path = []
#     if 'final_content_key' not in st.session_state:
#         st.session_state.final_content_key = None 

# ##################################### توابع ##############################       
#     def set_view(view):
#         st.session_state.view_state = view
        
#     def handle_node_click(path_list):
#         clicked_path_key = "/".join(path_list)

#         if st.session_state.active_path == path_list:
#             st.session_state.active_path.pop()
#             st.session_state.final_content_key = None
#             return

#         if clicked_path_key == "ثبت درخواست خدمات/واگذاری انشعاب/واگذاری انشعاب":
#             set_view('assignment_form')
#             return 
#         elif clicked_path_key == "خدمات صورتحساب/اعتراض به صورت حساب":
#             set_view('billing_protest_form')
#             return 

#         st.session_state.active_path = path_list
#         current_level_data = SERVICE_TREE
#         for step in path_list:
#             current_level_data = current_level_data[step]
        
#         if current_level_data == "content":
#             st.session_state.final_content_key = clicked_path_key
#         else:
#             st.session_state.final_content_key = None
            
# ############################################# main tree ##################################            
            
#     if st.session_state.view_state == 'main_tree':

#         st.title("سامانه هوشمند خدمات شرکت توزیع برق شهرستان اصفهان")
#         st.write("به سامانه هوشمند خدمات شرکت توزیع برق شهرستان اصفهان خوش امدید.")
#         st.write("در این سامانه می توانید تمام خدمات مربوط به برق را بصورت غیرحضوری از جمله : ثبت و پیگیری درخواست ها ،مشاهده ی سوابق درخواست های قبلی ، مشاهده و مدیریت انشعاب های برق و بسیاری خدمات دیگر به صورت ساده و سریع انجام دهید ")
#         st.write("ما اینجا هستیم تا تجربه ی هوشمند، دقیق و راحت برای شما فراهم کنیم .")
            
#         st.divider()
        
#         st.write("مشترک گرامی در انتخاب درخواست دقت کافی داشته باشید تا عنوان آن را اشتباها انتخاب نکنید. همچنین به سوالاتی که پرسیده می شود اعم از مشخصات فردی , نشانی, نوع درخواست ,مشخصات انشعاب و.. بطور کامل و با دقت پاسخ دهید چون مسئولیت صحت اطلاعاتی که اعلام می نمایید بعهده شما می باشد.")
#         st.write("خاطر نشان می سازد اطلاع رسانی به شما متقاضی گرامی از طریق نرم افزار بله با شماره ای که ثبت درخواست می نمایید انجام می گردد.")
#         st.write("نکته 1: در صورتی که فرآیند ثبت درخواست بمدت 72 ساعت ناتمام بماند پس از آن فرآیند ثبت درخواست بایستی ار ابتدا انجام گردد.")
#         st.write("نکته 2: جهت احراز هویت لازم است مالکیت قانونی شماره همراه با شخص درخواست دهنده همخوانی داشته باشد.")
        
#         st.divider()
        
#         with st.container(border=True):
#             st.markdown('<div class="tree-container">', unsafe_allow_html=True)
#             st.markdown("### شروع فرایند")

#             # ----- رندر سطح ۱ (شاخه‌های اصلی) -----
#             current_level_data = SERVICE_TREE
#             num_nodes = len(current_level_data)
#             st.markdown(f'<div class="tree-level root level-{num_nodes}-children">', unsafe_allow_html=True)
#             active_node_in_this_level = None
#             if len(st.session_state.active_path) > 0:
#                 active_node_in_this_level = st.session_state.active_path[0]

#             if active_node_in_this_level:
#                 if active_node_in_this_level in current_level_data:
#                     node_name = active_node_in_this_level
#                     node_content = current_level_data[node_name]
#                     new_path = [node_name]
                    
#                     col1, col2, col3 = st.columns([1, 1, 1])
#                     with col2:
#                         is_parent = len(st.session_state.active_path) > 1 and node_content != "content"
#                         node_class = "parent-node active" if is_parent else "active"
                        
#                         st.markdown(f'<div class="tree-node {node_class}">', unsafe_allow_html=True)
#                         st.button(node_name, key=node_name, use_container_width=True, on_click=handle_node_click, args=(new_path,))
#                         st.markdown('</div>', unsafe_allow_html=True)
                        
#                         if len(st.session_state.active_path) == 1 and node_content == "content":
#                             st.info("این بخش در حال توسعه است.")
#                 else:

#                     st.session_state.active_path = []
#                     cols = st.columns(num_nodes)
#                     for i, (node_name, node_content) in enumerate(current_level_data.items()):
#                         with cols[i]:
#                             st.markdown(f'<div class="tree-node">', unsafe_allow_html=True)
#                             st.button(node_name, key=node_name, use_container_width=True, on_click=handle_node_click, args=([node_name],))
#                             st.markdown('</div>', unsafe_allow_html=True)

#             else:
#                 cols = st.columns(num_nodes)
#                 for i, (node_name, node_content) in enumerate(current_level_data.items()):
#                     with cols[i]:
#                         node_class = "" 
#                         st.markdown(f'<div class="tree-node {node_class}">', unsafe_allow_html=True)
#                         st.button(node_name, key=node_name, use_container_width=True, on_click=handle_node_click, args=([node_name],))
#                         st.markdown('</div>', unsafe_allow_html=True)

#             st.markdown('</div>', unsafe_allow_html=True)

#             # ----- رندر سطوح بعدی بر اساس مسیر فعال کاربر -----
#             THRESHOLD = 6
#             current_path = []
#             for i, step in enumerate(st.session_state.active_path):
#                 current_path.append(step)
#                 try:
#                     current_level_data = SERVICE_TREE
#                     for s in current_path:
#                         current_level_data = current_level_data[s]
                        
#                     if isinstance(current_level_data, dict) and current_level_data:
#                         num_nodes = len(current_level_data)
#                         if num_nodes > THRESHOLD:
#                             col1, col2, col3 = st.columns([1, 2, 1])
#                             with col2:
#                                 st.markdown('<div class="tree-level-vertical">', unsafe_allow_html=True)
                                
#                                 # --- [منطق جدید رندر عمودی] ---
#                                 active_node_in_this_level = None
#                                 next_step_index = i + 1
#                                 if len(st.session_state.active_path) > next_step_index:
#                                     active_node_in_this_level = st.session_state.active_path[next_step_index]
                                
#                                 if active_node_in_this_level:
#                                     # --- حالت ۱: یک گزینه فعال است ---
#                                     # فقط دکمه فعال را نمایش بده
#                                     node_name = active_node_in_this_level
#                                     node_content = current_level_data[node_name]
#                                     new_path = current_path + [node_name]

#                                     is_parent = len(st.session_state.active_path) > len(new_path) and node_content != "content"
#                                     node_class = "parent-node active" if is_parent else "active"

#                                     st.markdown(f'<div class="tree-node vertical-node {node_class}">', unsafe_allow_html=True)
#                                     st.button(node_name, key="/".join(new_path), use_container_width=True, on_click=handle_node_click, args=(new_path,))
#                                     st.markdown('</div>', unsafe_allow_html=True)

#                                     # اگر این دکمه خودش برگ نهایی بود، محتوایش را نشان بده
#                                     if len(st.session_state.active_path) == len(new_path) and node_content == "content":
#                                         st.info("این بخش در حال توسعه است.")

#                                 else:
#                                     # --- حالت ۲: هیچ گزینه‌ای فعال نیست ---
#                                     # همه دکمه‌های این سطح را نمایش بده
#                                     for node_name, node_content in current_level_data.items():
#                                         new_path = current_path + [node_name]
#                                         st.markdown(f'<div class="tree-node vertical-node">', unsafe_allow_html=True)
#                                         st.button(node_name, key="/".join(new_path), use_container_width=True, on_click=handle_node_click, args=(new_path,))
#                                         st.markdown('</div>', unsafe_allow_html=True)
#                                 st.markdown('</div>', unsafe_allow_html=True)
#                         else:
#                             st.markdown(f'<div class="tree-level level-{num_nodes}-children">', unsafe_allow_html=True)

#                             # --- [منطق جدید رندر افقی] ---
#                             active_node_in_this_level = None
#                             next_step_index = i + 1
#                             if len(st.session_state.active_path) > next_step_index:
#                                 active_node_in_this_level = st.session_state.active_path[next_step_index]

#                             if active_node_in_this_level:
#                                 # --- حالت ۱: یک گزینه فعال است ---
#                                 # فقط دکمه فعال را در مرکز نمایش بده
#                                 node_name = active_node_in_this_level
#                                 node_content = current_level_data[node_name]
#                                 new_path = current_path + [node_name]

#                                 col1, col2, col3 = st.columns([1, 1, 1])
#                                 with col2:
#                                     is_parent = len(st.session_state.active_path) > len(new_path) and node_content != "content"
#                                     node_class = "parent-node active" if is_parent else "active"

#                                     st.markdown(f'<div class="tree-node {node_class}">', unsafe_allow_html=True)
#                                     st.button(node_name, key="/".join(new_path), use_container_width=True, on_click=handle_node_click, args=(new_path,))
#                                     st.markdown('</div>', unsafe_allow_html=True)
                                    
#                                     if len(st.session_state.active_path) == len(new_path) and node_content == "content":
#                                         st.info("این بخش در حال توسعه است.")
#                             else:
#                                 # --- حالت ۲: هیچ گزینه‌ای فعال نیست ---
#                                 # همه دکمه‌های این سطح را نمایش بده
#                                 cols = st.columns(num_nodes)
#                                 for j, (node_name, node_content) in enumerate(current_level_data.items()):
#                                     with cols[j]:
#                                         new_path = current_path + [node_name]
#                                         st.markdown(f'<div class="tree-node">', unsafe_allow_html=True)
#                                         st.button(node_name, key="/".join(new_path), use_container_width=True, on_click=handle_node_click, args=(new_path,))
#                                         st.markdown('</div>', unsafe_allow_html=True)             
#                             st.markdown('</div>', unsafe_allow_html=True)
#                 except (KeyError, TypeError):
#                     break

#             st.markdown('</div>', unsafe_allow_html=True) 


#     if st.session_state.view_state == 'assignment_form':
#         show_assignment_form()

#     if st.session_state.view_state == 'billing_protest_form':
#         show_billing_protest_form()
        
            
# pages = st.navigation([
#     st.Page(main_page, title="صفحه اصلی", icon="🏠"),
#     st.Page("app.py", title="دستیار هوشمند", icon="💡"),
#     st.Page("admin_page.py", title="دسترسی ادمین", icon="🔐")
# ])


# pages.run()