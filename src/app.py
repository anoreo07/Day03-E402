import streamlit as st
import os
import sys

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from dotenv import load_dotenv
load_dotenv()

from src.app_chat import chat_page, compare_page
from src.app_metrics import metrics_page
from src.app_inventory import warehouse_page
from src.ui import inject_minimart_style

st.set_page_config(page_title="MiniMart AI Shop", layout="wide", page_icon="🛒")

inject_minimart_style()

st.sidebar.title("MiniMart AI Lab")
page = st.sidebar.selectbox(
    "Go to",
    ["Shop Assistant", "Warehouse", "Answer Comparison", "Analytics"],
)

if page == "Shop Assistant":
    chat_page()
elif page == "Warehouse":
    warehouse_page()
elif page == "Answer Comparison":
    compare_page()
else:
    metrics_page()
