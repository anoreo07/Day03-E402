import streamlit as st
import pandas as pd
import os
from src.chatbot import Chatbot
from src.run_agent import load_products, build_tools
from src.agent.agent import ReActAgent
from src.core.provider_factory import build_provider
from src.ui import inject_minimart_style, render_minimart_banner


def build_shop_system_prompt(product_context: str) -> str:
    return (
        "You are a precise shopping assistant for a product catalog. "
        "Always use the exact catalog fields: product_id, name, category, price_usd, stock_qty, tax_rate, shipping_weight_kg, coupon_code. "
        "Do not invent prices or discount codes. "
        "When asked to calculate a final total, compute: subtotal, discount amount, shipping cost, tax amount, and final total. "
        "Choose the correct tax rate by destination state (e.g., NY for New York, CA for California) and use the shipping destination for shipping cost. "
        "If the question includes a coupon code, apply it exactly. "
        "Answer using the product data from the catalog and explain each numeric step clearly.\n\n"
        f"Product catalog:\n{product_context}"
    )


def compare_page():
    inject_minimart_style()
    render_minimart_banner(
        "Compare Smart Shopping Answers",
        "So sánh câu trả lời giữa Chatbot và ReAct Agent trong phong cách minimart.",
    )

    st.sidebar.header("Minimart Comparison")
    provider = st.sidebar.selectbox("LLM Provider", ["openai", "gemini", "ollama"], index=0)
    model = st.sidebar.text_input("Model (leave blank for default)")
    max_steps = st.sidebar.slider("ReAct Max Steps", 1, 10, 5)
    st.sidebar.markdown("_Chọn model và bước tối đa để so sánh phản hồi một cách linh hoạt._")

    st.markdown(
        "<div class='minimart-highlight'>So sánh hai luồng trả lời cùng một câu hỏi — Chatbot thuần text và ReAct Agent dùng công cụ.</div>",
        unsafe_allow_html=True,
    )

    prompt = st.text_area("Nhập câu hỏi để so sánh", height=120)
    run_compare = st.button("Chạy so sánh")

    if run_compare:
        if not prompt.strip():
            st.warning("Vui lòng nhập câu hỏi để so sánh.")
            return

        try:
            product_df = pd.read_csv("src/data/products.csv")
            product_context = product_df.to_string(index=False)
            system_prompt = build_shop_system_prompt(product_context)

            chatbot = Chatbot(provider=provider, model=model if model else None)
            chatbot_answer = chatbot.ask(prompt, system_prompt=system_prompt)

            products_path = "src/data/products.csv"
            if os.path.exists(products_path):
                products = load_products(products_path)
                tools = build_tools(products)
            else:
                tools = []

            if tools:
                st.sidebar.markdown("---")
                st.sidebar.subheader("Available ReAct Tools")
                for tool in tools:
                    st.sidebar.markdown(f"**{tool['name']}**: {tool['description']}")

            llm = build_provider(provider=provider, model=model if model else None)
            agent = ReActAgent(
                llm=llm,
                tools=tools,
                max_steps=max_steps,
                product_context=product_context,
            )
            react_answer = agent.run(prompt)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Chatbot")
                st.markdown("**Câu hỏi:**")
                st.write(prompt)
                st.markdown("**Trả lời:**")
                st.write(chatbot_answer)

            with col2:
                st.subheader("ReAct Agent")
                st.markdown("**Câu hỏi:**")
                st.write(prompt)
                st.markdown("**Trả lời:**")
                st.write(react_answer)
                if agent.history:
                    st.markdown("**Lịch sử tác vụ ReAct:**")
                    for step in agent.history:
                        if step.startswith("User:"):
                            continue
                        st.code(step, language="text")

            st.markdown("---")
            st.subheader("Context dữ liệu sản phẩm được sử dụng cho Chatbot")
            st.code(product_context, language="text")

        except Exception as e:
            st.error(f"Lỗi khi so sánh: {e}")


def chat_page():
    inject_minimart_style()
    render_minimart_banner(
        "Minimart Shopping Assistant",
        "Nhập câu hỏi của bạn về sản phẩm, giảm giá, giao hàng và thuế để nhận câu trả lời chính xác.",
    )

    st.sidebar.header("Shop Settings")
    mode = st.sidebar.radio("Select Mode", ["Chatbot", "ReAct Agent"])
    provider = st.sidebar.selectbox("LLM Provider", ["openai", "gemini", "ollama"], index=0)
    model = st.sidebar.text_input("Model (leave blank for default)")

    if mode == "ReAct Agent":
        max_steps = st.sidebar.slider("Max Steps", 1, 10, 5)
        products_path = "src/data/products.csv"
        if os.path.exists(products_path):
            products = load_products(products_path)
            tools = build_tools(products)
        else:
            st.sidebar.error(f"Products file not found at {products_path}")
            tools = []

        if tools:
            st.sidebar.markdown("---")
            st.sidebar.subheader("Available ReAct Tools")
            for tool in tools:
                st.sidebar.markdown(f"**{tool['name']}**: {tool['description']}")

    # Initialize Session State
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if st.sidebar.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        "<div class='minimart-highlight'>Hãy nhập câu hỏi mua sắm rõ ràng, gồm product_id, số lượng, mã giảm giá và địa chỉ giao hàng. Chatbot và ReAct Agent sẽ sử dụng toàn bộ dữ liệu sản phẩm và tính toán subtotal, discount, shipping, tax, final total một cách chính xác.</div>",
        unsafe_allow_html=True,
    )

    with st.expander("How to use"):
        st.write(
            "Nhập câu hỏi dạng: 'I want to buy two P007 headsets, applying their discount code. "
            "I'm in California (CA) and want them shipped to New York. Please calculate the final total amount I will have to pay.'"
        )

    # Display Chat History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User Input
    if prompt := st.chat_input("What would you like to buy today?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            try:
                if mode == "Chatbot":
                    product_df = pd.read_csv("src/data/products.csv")
                    product_context = product_df.to_string(index=False)
                    system_prompt = build_shop_system_prompt(product_context)
                    
                    chatbot = Chatbot(provider=provider, model=model if model else None)
                    answer = chatbot.ask(prompt, system_prompt=system_prompt)
                    response_placeholder.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                
                else:
                    product_df = pd.read_csv("src/data/products.csv")
                    product_context = product_df.to_string(index=False)
                    llm = build_provider(provider=provider, model=model if model else None)
                    agent = ReActAgent(
                        llm=llm,
                        tools=tools,
                        max_steps=max_steps,
                        product_context=product_context,
                    )
                    
                    with st.status("Agent is thinking...", expanded=True) as status:
                        answer = agent.run(prompt)
                        for step in agent.history:
                            if step.startswith("User:"): continue
                            st.markdown(step)
                        status.update(label="Planning complete!", state="complete", expanded=False)
                    
                    response_placeholder.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

            except Exception as e:
                st.error(f"Error: {e}")
