import streamlit as st

st.set_page_config(page_title="立体库控制系统", page_icon="🤖", layout="wide")

st.title("🚀 欢迎使用立体库控制平台")

st.markdown("""
这里是你的调试首页，你可以从左侧导航栏进入不同操作模块：

- 📥 出库操作
- 📤 入库操作
- 🚚 小车跨层


每个模块都包含多个步骤，允许你逐个请求调试 API 响应。
""")