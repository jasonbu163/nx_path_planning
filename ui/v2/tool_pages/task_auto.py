# 🚚 小车跨层页面文件，如 pages/🚚 小车跨层.py
import streamlit as st
import requests
from api_config import API_BASE

st.image("img/locations.png")

st.subheader("🚧 电梯先到需要跨层🚗小车楼层！！")

with st.expander("📋 电梯操作", expanded=True):
    floor_id = st.selectbox(f"请输入电梯层", list(range(1, 5)), key="floor_id")

    if st.button(f"🚀 [执行] 操作电梯"):
        try:
            body = {"layer": floor_id}
            url = API_BASE + "/control/lift"
            # st.write(f"请求：{url}")
            resp = requests.post(url, json=body)

            if resp.status_code == 200:
                try:
                    if resp.json()["code"] == 404:
                        st.error(f"{resp.json()['message']}")
                    else:
                        st.success(f"✅ 动作发送成功")
                except:
                    st.text(resp.text)
            else:
                st.error(f"请求失败，状态码：{resp.status_code}")
                st.text(resp.text)

        except Exception as e:
            st.error(f"请求失败：{e}")

steps = [
    {
        "step": 1,
        "title": "⬇️ 入库操作",
        "api": "/control/task_inband",
        "method": "POST",
        "params": {"target": "5,3,1"}
    },
    {
        "step": 2,
        "title": "🚚 小车跨层操作",
        "api": "/control/car_cross_layer",
        "method": "POST",
        "params": {"layer": 1},
    },
    {
        "step": 3,
        "title": "⬆️ 出库操作",
        "api": "/control/task_outband",
        "method": "POST",
        "params": {"target": "5,3,1"}
    }
]

# 执行步骤
for i, step in enumerate(steps):
    with st.expander(step["title"], expanded=True):
        body = {}

        if step["step"] == 1:
            st.subheader("📌 设置任务入库目标")
            col1, col2, col3 = st.columns(3)
            with col1:
                x_1 = st.selectbox("目标行(x)", list(range(1, 9)), key="x_1")
            with col2:
                y_1 = st.selectbox("目标列(y)", list(range(1, 8)), key="y_1")
            with col3:
                z_1 = st.selectbox("目标层(z)", list(range(1, 5)), key="z_1")
            body["target"] = f"{x_1},{y_1},{z_1}"

        elif step["step"] == 2:
            # 楼层选择区
            st.subheader("📌 设置小车目标楼层")
            layer = st.selectbox("🚩 小车目标层", list(range(1, 5)), key="layer")

            st.subheader("🚦 小车跨层操作开始！")
            body["layer"] = layer

        elif step["step"] == 3:
            st.subheader("📌 设置任务出库目标")
            col1, col2, col3 = st.columns(3)
            with col1:
                x_2 = st.selectbox("目标行(x)", list(range(1, 9)), key="x_2")
            with col2:
                y_2 = st.selectbox("目标列(y)", list(range(1, 8)), key="y_2")
            with col3:
                z_2 = st.selectbox("目标层(z)", list(range(1, 5)), key="z_2")
            body["target"] = f"{x_2},{y_2},{z_2}"


        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
            try:
                url = API_BASE + step["api"]
                resp = (
                    requests.post(url, json=body)
                    if step["method"] == "POST"
                    else requests.get(url, params=body)
                )
                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)
                
            except Exception as e:
                st.error(f"请求失败：{e}")
