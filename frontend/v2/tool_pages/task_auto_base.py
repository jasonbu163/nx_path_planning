# 🚚 小车跨层页面文件，如 pages/🚚 小车跨层.py
import streamlit as st
import requests
import pandas as pd

from api_config import API_BASE

st.markdown("⚠️ 此页面为设备自动化联动页面，请使用前**确保所有设备正常**")
st.markdown("⚠️ 此页面所有功能**不操作数据库**，如对货物位置进行操作，请自行记录货物位置变更")

st.image("img/locations.png")

a1, a2 = st.columns(2)
with a1:
    st.subheader("🚧 电梯操作")
    with st.expander("📋 电梯操作"):
        floor_id = st.selectbox(f"请设置电梯层", list(range(1, 5)), key="floor_id")

        if st.button(f"🚀 [执行] 电梯操作"):
            try:
                body = {"layer": floor_id}
                url = API_BASE + "/control/lift"
                # st.write(f"请求：{url}")
                resp = requests.post(url, json=body)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")

with a2:
    st.subheader("👓 获取入口处托盘码")
    with st.expander("🔘 请确保已按下输送线左下方🟢绿色按钮"):

        if st.button(f"🚀 [执行] 获取条码"):
            try:
                url = API_BASE + "/control/qrcode"
                # st.write(f"请求：{url}")
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 扫码成功, 托盘码为: {resp.json()['data']}")
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
        "title": "⬇️ **入库操作**",
        "api": "/control/task_inband",
        "method": "POST",
        "params": {"target": "5,3,1"},
    },
    {
        "step": 2,
        "title": "🚚 **穿梭车跨层操作**",
        "api": "/control/car_cross_layer",
        "method": "POST",
        "params": {"layer": 1},
    },
    {
        "step": 3,
        "title": "⬆️ **出库操作**",
        "api": "/control/task_outband",
        "method": "POST",
        "params": {"target": "5,3,1"},
    },
    {
        "step": 4,
        "title": "🗺️ **穿梭车位置**",
        "api": "/control/get_car_location",
        "method": "GET",
        "params": {}
    },
    {
        "step": 5,
        "title": "🚗 **穿梭车移动操作**",
        "api": "/control/car_move",
        "method": "POST",
        "params": {
            "target": "1,1,4"
            }
    },
    {
        "step": 6,
        "title": "📦 **货物移动操作**",
        "api": "/control/good_move_by_start_end_control",
        "method": "POST",
        "params": {
            "start_location": "4,3,1",
            "end_location": "4,3,1"
            }
    }
]

################################################
# ---------------- 基础穿梭车操作 ----------------
################################################

st.subheader("🚗 基础穿梭车操作(无遮挡货物处理)")
# --- 创建水平布局 ---
a1, a2 = st.columns(2)  # 创建二列水平布局
with a1:
    step = steps[3]
    with st.expander(step["title"], expanded=True):

        if st.button("🚀 [执行] 获取🚗当前位置", key=f"get_car_location"):
            try:
                url = API_BASE + step["api"]
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"{resp.json()['data']}")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)
                    
            except Exception as e:
                st.error(f"请求失败：{e}")
    
    step = steps[4]
    with st.expander(step["title"], expanded=True):
        body = {}

        st.markdown("🏁 **设置货物当前位置**")
        col_x_7, col_y_7, col_z_7 = st.columns(3)
        with col_x_7:
            x_7 = st.selectbox("请选择行 (x)", list(range(1, 9)), key="x_7")
        with col_y_7:
            y_7 = st.selectbox("请选择列 (y)", list(range(1, 8)), key="y_7")
        with col_z_7:
            z_7 = st.selectbox("请选择层 (z)", list(range(1, 5)), key="z_7")
        target = f"{x_7},{y_7},{z_7}"
        body["target"] = target

        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_step_5"):
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
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")

with a2:
    step = steps[5]
    with st.expander(step["title"], expanded=True):
        body = {}

        st.markdown("🏁 **设置货物当前位置**")
        col_x_5, col_y_5, col_z_5 = st.columns(3)
        with col_x_5:
            x_5 = st.selectbox("请选择开始行 (x)", list(range(1, 9)), key="x_5")
        with col_y_5:
            y_5 = st.selectbox("请选择开始列 (y)", list(range(1, 8)), key="y_5")
        with col_z_5:
            z_5 = st.selectbox("请选择开始层 (z)", list(range(1, 5)), key="z_5")
        start_location = f"{x_5},{y_5},{z_5}"
        body["start_location"] = start_location

        st.markdown("🎯 **设置货物目标位置**")
        col_x_6, col_y_6, col_z_6 = st.columns(3)
        with col_x_6:
            x_6 = st.selectbox("请选择目标行 (x)", list(range(1, 9)), key="x_6")
        with col_y_6:
            y_6 = st.selectbox("请选择目标列 (y)", list(range(1, 8)), key="y_6")
        with col_z_6:
            z_6 = st.selectbox("请选择目标层 (z)", list(range(1, 5)), key="z_6")
        end_location = f"{x_6},{y_6},{z_6}"
        body["end_location"] = end_location

        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_good"):
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
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")


################################################
# --------------- 设备基础联动操作 ---------------
################################################

st.subheader("🔗 设备基础联动操作(无遮挡货物处理)")
# --- 创建水平布局 ---
c1, c2, c3 = st.columns(3)  # 创建三列水平布局

# 入库操作 -> 放在第一列
with c1:
    step = steps[0]
    with st.expander(step["title"], expanded=True):
        body = {}

        st.markdown("📌 **设置入库目标**")
        col_x_1, col_y_1, col_z_1 = st.columns(3)
        with col_x_1:
            x_1 = st.selectbox("目标行(x)", list(range(1, 9)), key="x_1")
        with col_y_1:
            y_1 = st.selectbox("目标列(y)", list(range(1, 8)), key="y_1")
        with col_z_1:
            z_1 = st.selectbox("目标层(z)", list(range(1, 5)), key="z_1")
        body["target"] = f"{x_1},{y_1},{z_1}"


        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_step_1"):
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
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")

# 小车跨层 -> 放在第二列
with c2:
    step = steps[1]
    with st.expander(step["title"], expanded=True):
        body = {}

        # 楼层选择区
        st.markdown("📌 **设置目标楼层**")
        layer = st.selectbox("🚩 小车目标层", list(range(1, 5)), key="layer")
        body["layer"] = layer

        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_step_2"):
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
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")

# 出库操作 -> 放在第三列
with c3:
    step = steps[2]
    with st.expander(step["title"], expanded=True):
        body = {}

        st.markdown("📌 **设置出库目标**")
        col_x_2, col_y_2, col_z_2 = st.columns(3)
        with col_x_2:
            x_2 = st.selectbox("目标行(x)", list(range(1, 9)), key="x_2")
        with col_y_2:
            y_2 = st.selectbox("目标列(y)", list(range(1, 8)), key="y_2")
        with col_z_2:
            z_2 = st.selectbox("目标层(z)", list(range(1, 5)), key="z_2")
        body["target"] = f"{x_2},{y_2},{z_2}"

        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_step_3"):
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
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}, {resp.json()['data']}")
                        else:
                            st.success(f"✅ 动作发送成功")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")