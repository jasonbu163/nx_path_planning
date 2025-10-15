# 📤 出库操作页面文件，如 pages/task_outbound.py
import streamlit as st
import requests
from api_config import API_BASE

st.subheader("⚠️ 确保小车在需要出库的楼层 ⚠️")
st.subheader("⚠️ 如果小车不在任务楼层 ⚠️")
st.subheader("⚠️ 先去把🚗小车移到出库楼层 ⚠️")
st.link_button("🚗 前往小车跨层页面", url="/car_cross_layer_by_step")
st.subheader("⚠️ 小车在出库楼层，就不需要小车跨层了 ⚠️")

st.image("img/locations.png")

# 统一设置任务层号
st.subheader("📌 先设置出库物料的楼层")
with st.expander("📋 楼层层号选择", expanded=True):
    location_id = st.selectbox("请选择任务所在层 (z)", list(range(1, 5)), index=0)

st.subheader("🚧 电梯要先到要出库的物料楼层！！🚧")
st.subheader("🚧 不管上一次任务去了哪里！！🚧")
with st.expander("📋 电梯到位操作", expanded=True):
    # floor_id = st.selectbox(f"请输入电梯层", list(range(1, 5)))

    if st.button(f"🚀 [执行] 操作电梯到物料层"):
        try:
            body = {"layer": location_id}
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

st.subheader("🚗 操作小车到达需要出库的货物位置")
with st.expander("🚗 到达货物位置操作", expanded=True):
    user_inputs = {}

    st.markdown("**小车目标坐标**（x=行, y=列, z=层）")
    col1, col2 = st.columns(2)
    with col1:
        x = st.selectbox("📦 行号 (x)", list(range(1, 9)), key=f"car_x")
    with col2:
        y = st.selectbox("📦 列号 (y)", list(range(1, 8)), key=f"car_y")
    user_inputs["target"] = f"{x},{y},{location_id}"

    if st.button(f"🚗 [执行] 操作小车"):
        try:
            body = {}
            for k, v in user_inputs.items():
                try:
                    body[k] = int(v)
                except:
                    body[k] = v
            url = API_BASE + "/control/car_move"
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

st.subheader("🚦 出库操作开始！")

# 出库任务步骤配置
steps = [
    {
        "step": 1,
        "title": "步骤 1：启动输送线确认",
        "api": "/control/task_in_lift",
        "method": "POST",
        "params": {"layer": location_id}
    },
    {
        "step": 2,
        "title": "步骤 2：操作小车取/放料，移动货物",
        "api": "/control/good_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        }
    },
    {
        "step": 3,
        "title": "步骤 3：确认在对应楼层，小车放料完成✅",
        "api": "/control/task_feed_complete",
        "method": "POST",
        "params": {"layer": location_id}
    },
    {
        "step": 4,
        "title": "步骤 4：电梯移动到1楼",
        "api": "/control/lift",
        "method": "POST",
        "params": {"layer": 1}
    },
    {
        "step": 5,
        "title": "步骤 5：提升机物料 ➡️ 库口 出库",
        "api": "/control/task_lift_outband",
        "method": "GET",
        "params": {}
    }
]

# 每步执行逻辑
for i, step in enumerate(steps):
    with st.expander(step["title"], expanded=True):
        user_inputs = {}

        if step["step"] == 1:
            user_inputs["layer"] = location_id
                    
        elif step["step"] == 2:
            user_inputs["target"] = f"5,3,{location_id}"

        elif step["step"] == 3:
            user_inputs["layer"] = location_id
                    
        elif step["step"] == 4:
            user_inputs["layer"] = 1
                    
        elif step["step"] == 5:
            user_inputs = {}

        if st.button(f"🚀 [执行] 步骤{step['title']}", key=f"exec_{i}"):
            try:
                body = {}
                for k, v in user_inputs.items():
                    try:
                        body[k] = int(v)
                    except:
                        body[k] = v
                # st.write(f"请求：{step['api']} - {body}")

                url = API_BASE + step["api"]
                resp = (
                    requests.post(url, json=body)
                    if step["method"] == "POST"
                    else requests.get(url, params=body)
                )

                # st.success(f"✅ 状态码：{resp.status_code}")

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
