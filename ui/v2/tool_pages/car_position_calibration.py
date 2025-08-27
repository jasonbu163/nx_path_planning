# 🚚 小车跨层页面文件，如 pages/⚙️ 校准小车位置.py
import streamlit as st
import requests
from api_config import API_BASE

st.image("img/locations.png")

# 统一设置任务层号
st.subheader("📌 小车启动或者重启后，请来这里校准小车位置")
with st.expander("📋 楼层选择", expanded=True):
    location_id = st.selectbox("请选择小车所在层 (z)", list(range(1, 5)), index=0)

steps = [
    {
        "step": 1,
        "title": "⚙️ 更改小车位置",
        "api": "/control/change_car_location",
        "method": "POST",
        "params": {"target": "1,1,1"}
    },
    {
        "step": 2,
        "title": "🚗 获取小车位置",
        "api": "/control/get_car_location",
        "method": "GET",
        "params": {}
    },
]

# 每步执行逻辑
for i, step in enumerate(steps):

    if step["step"] == 1:
        with st.expander(step["title"], expanded=True):
            user_inputs = {}
            if step["api"] == "/control/change_car_location":
                for key, default in step["params"].items():
                    st.markdown("**小车目标坐标**（x=行, y=列, z=层）")
                    col1, col2 = st.columns(2)
                    with col1:
                        x = st.selectbox("小车行号 (x)", list(range(1, 9)), key=f"{key}_x_{i}")
                    with col2:
                        y = st.selectbox("小车列号 (y)", list(range(1, 7)), key=f"{key}_y_{i}")
                    user_inputs["target"] = f"{x},{y},{location_id}"
            else:    
                user_inputs["target"] = f"5,3,{location_id}"

            if st.button(f"🚀 [执行] {step['title']}", key=f"exec_{i}"):
                try:
                    body = {}
                    for k, v in user_inputs.items():
                        try:
                            body[k] = int(v)
                        except:
                            body[k] = v

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
                                st.success(f"{resp.json()['data']}")
                        except:
                            st.text(resp.text)
                    else:
                        st.error(f"请求失败，状态码：{resp.status_code}")
                        st.text(resp.text)
                    
                except Exception as e:
                    st.error(f"请求失败：{e}")
    
    elif step["step"] == 2:
        with st.expander(step["title"], expanded=True):

            if st.button(f"🚀 [执行] {step['title']}", key=f"exec_{i}"):
                try:
                    body = {}
                    for k, v in user_inputs.items():
                        try:
                            body[k] = int(v)
                        except:
                            body[k] = v

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
                                st.success(f"{resp.json()['data']}")
                        except:
                            st.text(resp.text)
                    else:
                        st.error(f"请求失败，状态码：{resp.status_code}")
                        st.text(resp.text)
                    
                except Exception as e:
                    st.error(f"请求失败：{e}")
