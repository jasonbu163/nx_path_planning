# 🚚 小车跨层页面文件，如 pages/📦 控制货物移动.py
import streamlit as st
import requests
from api_config import API_BASE

st.image("img/locations.png")

# 统一设置任务层号
st.subheader("📌 先设置物料的楼层")
with st.expander("📋 任务层号选择", expanded=True):
    location_id = st.selectbox("请选择任务所在层 (z)", list(range(1, 5)), index=0)

# 出库任务步骤配置
steps = [
    {
        "step": 1,
        "title": "步骤 1：🚗 控制小车，到达货物位置",
        "api": "/control/car_move",
        "method": "POST",
        "params": {"target": f"5,3,1"}
    },
    {
        "step": 2,
        "title": "步骤 2：📦 控制小车移动货物",
        "api": "/control/good_move",
        "method": "POST",
        "params": {"target": f"5,3,1"}
    },
]

# 每步执行逻辑
for i, step in enumerate(steps):
    with st.expander(step["title"], expanded=True):
        user_inputs = {}
        if step["step"] == 1:
            for key, default in step["params"].items():
                st.markdown("**移动🚗，到达需要移动的📦货物位置**（x=行, y=列, z=层）")
                col1, col2 = st.columns(2)
                with col1:
                    x = st.selectbox("📦 行号 (x)", list(range(1, 9)), key=f"{key}_x_{i}")
                with col2:
                    y = st.selectbox("📦 列号 (y)", list(range(1, 8)), key=f"{key}_y_{i}")
                user_inputs["target"] = f"{x},{y},{location_id}"
        elif step["step"] == 2:
            for key, default in step["params"].items():
                st.markdown("**🚗货物，去往目标位置**（x=行, y=列, z=层）")
                col1, col2 = st.columns(2)
                with col1:
                    x = st.selectbox("🏁 目标行号 (x)", list(range(1, 9)), key=f"{key}_x_{i}")
                with col2:
                    y = st.selectbox("🏁 目标列号 (y)", list(range(1, 8)), key=f"{key}_y_{i}")
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
                # st.write(f"请求：{step['api']} - {body}")

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
