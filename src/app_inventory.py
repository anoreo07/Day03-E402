import os
import streamlit as st
import pandas as pd
from src.ui import inject_minimart_style, render_minimart_banner


def warehouse_page():
    inject_minimart_style()
    render_minimart_banner(
        "Warehouse Dashboard",
        "Xem kho sản phẩm, tồn kho và xu hướng hàng hóa nhanh chóng.",
    )

    data_path = "src/data/products.csv"
    if not os.path.exists(data_path):
        st.error("Không tìm thấy dữ liệu kho hàng. Vui lòng kiểm tra file products.csv.")
        return

    product_df = pd.read_csv(data_path)
    product_df["stock_qty"] = product_df["stock_qty"].astype(int)
    product_df["price_usd"] = product_df["price_usd"].astype(float)

    categories = sorted(product_df["category"].unique().tolist())
    selected_categories = st.sidebar.multiselect("Chọn danh mục", categories, default=categories)
    low_stock_threshold = st.sidebar.slider("Ngưỡng tồn kho thấp", 0, 100, 30)

    filtered = product_df[product_df["category"].isin(selected_categories)]
    total_products = len(filtered)
    total_stock = int(filtered["stock_qty"].sum())
    avg_price = filtered["price_usd"].mean() if total_products else 0
    low_stock = filtered[filtered["stock_qty"] <= low_stock_threshold]

    stat_col1, stat_col2, stat_col3 = st.columns(3)
    stat_col1.markdown("### 🛍️ Total SKUs")
    stat_col1.markdown(f"**{total_products}**")
    stat_col2.markdown("### 📦 Total Stock")
    stat_col2.markdown(f"**{total_stock:,}**")
    stat_col3.markdown("### 💵 Avg. Price")
    stat_col3.markdown(f"**${avg_price:,.2f}**")

    st.markdown("---")
    st.markdown("### Inventory Table")
    st.dataframe(filtered.style.format({"price_usd": "${:,.2f}"}), use_container_width=True)

    st.markdown("---")
    st.markdown("### Low Stock Alerts")
    if low_stock.empty:
        st.success("Không có sản phẩm nào dưới ngưỡng tồn kho hiện tại.")
    else:
        st.table(low_stock.sort_values("stock_qty").head(10).loc[:, ["product_id", "name", "category", "stock_qty", "price_usd", "coupon_code"]])
