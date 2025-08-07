# 🚚 小车跨层页面文件，如 pages/🚚 小车跨层.py
import streamlit as st
import requests
from api_config import API_BASE

st.image("img/locations.png")

st.subheader("🚧 电梯先到需要跨层🚗小车楼层！！")
with st.expander("📋 电梯到达🚗层操作", expanded=True):
    floor_id = st.selectbox(f"请输入电梯层", list(range(1, 5)), key="floor_id")

    if st.button(f"🚀 [执行] 操作电梯"):
        try:
            body = {"location_id": f"{floor_id}"}
            url = API_BASE + "/api/v1/wcs/control/lift"
            # st.write(f"请求：{url}")
            resp = requests.post(url, json=body)

            if resp.status_code == 200:
                st.success(f"✅ 动作发送成功")
            else:
                st.error(f"请求失败，状态码：{resp.status_code}")
                st.text(resp.text)

            # try:
            #     st.json(resp.json())
            # except:
            #     st.text(resp.text)
        except Exception as e:
            st.error(f"请求失败：{e}")

steps = [
    {
        "step": 1,
        "title": "步骤 1：🚚 操作小车",
        "api": "/api/v1/wcs/control/car_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        },
    },
    {
        "step": 2,
        "title": "步骤 2：🚚 操作小车",
        "api": "/api/v1/wcs/control/car_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        },
    },
    {
        "step": 3,
        "title": "步骤 3：🚀 电梯移动",
        "api": "/api/v1/wcs/control/lift",
        "method": "POST",
        "params": {"location_id": 1},
    },
    {
        "step": 4,
        "title": "步骤 4：🚚 确认小车到位",
        "api": "/api/v1/wcs/control/change_car_location",
        "method": "POST",
        "params": {"target": "5,3,1"},
    },
    {
        "step": 5,
        "title": "步骤 5：🚚 操作小车",
        "api": "/api/v1/wcs/control/car_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        },
    },
    {
        "step": 6,
        "title": "步骤 6：🚚 确认完成小车跨层所有操作",
        "api": "/api/v1/wcs/control/lift",
        "method": "POST",
        "params": {"location_id": 1},
    },
]


# 楼层选择区
st.subheader("📌 设置小车移动楼层")
col1, col2 = st.columns(2)
with col1:
    floor_a = st.selectbox("🚩 小车起始楼层（步骤 1-2）", list(range(1, 5)), key="floor_a")
with col2:
    floor_b = st.selectbox("🏁 小车目标楼层（步骤 3-6）", list(range(1, 5)), key="floor_b")

st.subheader("🚦 小车跨层操作开始！")

# 执行步骤
for i, step in enumerate(steps):
    with st.expander(step["title"], expanded=True):
        body = {}

        if step["step"] == 1:
            st.markdown("**小车移动到电梯口输送线**")
            z = floor_a
            body["target"] = f"5,3,{z}"

        elif step["step"] == 2:
            st.markdown("**小车开始进入电梯**")
            z = floor_a
            body["target"] = f"6,3,{z}"

        elif step["step"] == 3 and "lift" in step["api"]:
            st.markdown("**操作电梯载车**")
            z = floor_b  # 跨层操作的电梯移动目标一定是楼层 B
            body["location_id"] = z

        elif step["step"] == 4:
            st.markdown("**确认电梯载车到达目标楼层**")
            z = floor_b
            body["target"] = f"6,3,{z}"

        elif step["step"] == 5:
            st.markdown("**小车从电梯进入库内输送线位置**")
            z = floor_b
            body["target"] = f"5,3,{z}"

        elif step["step"] == 6 and "lift" in step["api"]:
            st.markdown("**必须确认整个流程结束**")
            z = floor_b  # 跨层操作的电梯移动目标一定是楼层 B
            body["location_id"] = z


        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
            try:
                url = API_BASE + step["api"]
                resp = (
                    requests.post(url, json=body)
                    if step["method"] == "POST"
                    else requests.get(url, params=body)
                )
                if resp.status_code == 200:
                        st.success(f"✅ 动作发送成功")
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

                # try:
                #     st.json(resp.json())
                # except:
                #     st.text(resp.text)
                
            except Exception as e:
                st.error(f"请求失败：{e}")
