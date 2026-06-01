import streamlit as st
import pandas as pd
import json
import os
from glob import glob
from src.ui import inject_minimart_style, render_minimart_banner

def metrics_page():
    inject_minimart_style()
    render_minimart_banner(
        "MiniMart Analytics",
        "Theo dõi token, độ trễ và hiệu suất của chatbot trong cửa hàng.",
    )
    
    log_dir = "logs"
    if not os.path.exists(log_dir):
        st.warning("No logs found. Start chatting to generate metrics!")
        return

    log_files = glob(os.path.join(log_dir, "*.log"))
    if not log_files:
        st.warning("No log files found in the logs directory.")
        return

    # Parse logs
    all_events = []
    for file in log_files:
        with open(file, "r") as f:
            for line in f:
                try:
                    all_events.append(json.loads(line))
                except:
                    continue

    if not all_events:
        st.info("No data available yet.")
        return

    # Filter for usage data
    usage_data = []
    for event in all_events:
        data = event.get("data", {})
        usage = data.get("usage", {})
        if usage:
            usage_data.append({
                "Timestamp": event.get("timestamp"),
                "Event": event.get("event"),
                "Model": data.get("model", "unknown"),
                "Prompt Tokens": usage.get("prompt_tokens", 0),
                "Completion Tokens": usage.get("completion_tokens", 0),
                "Total Tokens": usage.get("total_tokens", 0),
                "Latency (ms)": data.get("latency_ms", 0)
            })

    if not usage_data:
        st.info("No token usage data found in logs.")
        return

    df = pd.DataFrame(usage_data)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])

    # Summary Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tokens", f"{df['Total Tokens'].sum():,}")
    col2.metric("Avg Latency", f"{df['Latency (ms)'].mean():.0f} ms")
    col3.metric("Total Requests", len(df))

    # Charts
    st.subheader("Tokens per Request")
    st.bar_chart(df, x="Timestamp", y="Total Tokens")

    st.subheader("Latency Trend")
    st.line_chart(df, x="Timestamp", y="Latency (ms)")

    # Raw Data
    st.subheader("Detailed Logs")
    st.dataframe(df.sort_values("Timestamp", ascending=False))
