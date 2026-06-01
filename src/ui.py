import streamlit as st


def inject_minimart_style() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eff6ff 45%, #fdf2f8 100%);
            color: #111827;
            font-family: 'Inter', sans-serif;
        }
        .main .block-container {
            padding-top: 1.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
            padding-bottom: 2rem;
            max-width: 1800px;
        }
        .stSidebar {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border-right: 1px solid rgba(15, 23, 42, 0.06);
        }
        .minimart-header {
            font-size: 2.4rem;
            font-weight: 800;
            color: #1f2937;
            margin-bottom: 0.1rem;
        }
        .minimart-subtitle {
            font-size: 1.05rem;
            color: #4b5563;
            margin-top: 0;
            margin-bottom: 1rem;
        }
        .minimart-card {
            background: #ffffff;
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
            padding: 1.4rem;
        }
        .minimart-badge {
            display: inline-block;
            background: #f97316;
            color: #ffffff;
            border-radius: 999px;
            padding: 0.35rem 0.9rem;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }
        .minimart-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 24px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
            padding: 1.6rem;
        }
        .minimart-summary-card {
            background: #ffffff;
            border-radius: 24px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            box-shadow: 0 16px 30px rgba(15, 23, 42, 0.05);
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        .minimart-summary-card h3 {
            margin: 0;
            color: #111827;
            font-size: 1rem;
            font-weight: 600;
        }
        .minimart-summary-card p {
            margin: 0.6rem 0 0 0;
            font-size: 1.6rem;
            font-weight: 700;
            color: #0f172a;
        }
        .minimart-highlight {
            background: #eef2ff;
            border-radius: 18px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(99, 102, 241, 0.16);
        }
        .minimart-box {
            background: #f8fafc;
            border-radius: 14px;
            border: 1px solid rgba(148, 163, 184, 0.2);
            padding: 1rem;
        }
        .stButton>button {
            background: #0ea5e9;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.85rem 1.2rem;
            font-weight: 700;
        }
        .stButton>button:hover {
            background: #059669;
            color: white;
        }
        .stSlider>div>div>div>div {
            background: #f97316;
        }
        .stTextInput>div>div>input,
        .stTextArea>div>div>textarea {
            border-radius: 16px;
            border: 1px solid rgba(15, 23, 42, 0.15);
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.06);
        }
        .stDataFrame div[data-testid='stHorizontalBlock'] {
            border-radius: 16px;
        }
        .css-1d391kg {
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_minimart_banner(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class='minimart-card'>
            <div class='minimart-badge'>MiniMart Shop</div>
            <div class='minimart-header'>{title}</div>
            <div class='minimart-subtitle'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
