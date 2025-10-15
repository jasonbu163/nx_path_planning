import streamlit as st
import requests
from api_config import API_BASE

st.subheader("⚠️ 确保小车在需要入库的楼层 ⚠️")
st.subheader("⚠️ 如果小车不在任务楼层 ⚠️")
st.subheader("⚠️ 先去把🚗小车移到需要入库的楼层 ⚠️")
st.link_button("🚗 前往小车跨层页面", url="/car_cross_layer_by_step")
st.subheader("⚠️ 小车在入库楼层，就不需要小车跨层了 ⚠️")

st.image("img/locations.png")

st.subheader("🚧 电梯要先到1楼！！不管上一次任务去了哪里！")
with st.expander("📋 电梯到位操作", expanded=True):
    # floor_id = st.selectbox(f"请输入电梯层", list(range(1, 5)))
    floor_id = 1

    if st.button(f"🚀 [执行] 操作电梯到1楼"):
        try:
            body = {"layer": floor_id}
            url = API_BASE + "/control/lift"
            # st.write(f"请求：{url} - 参数：{body}")
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

# 在最上方统一选择任务层号
st.subheader("📌 设置物料需要入库的楼层")
with st.expander("📋 任务层号设置", expanded=True):
    location_id = st.selectbox("请选择任务所在楼层 (z)", list(range(1, 5)), index=0)

st.subheader("🚗 操作小车到达目标输送线等待货物")
st.markdown("**⚠️ 小车如果在输送线，可以不用执行这个操作 ⚠️**")
with st.expander("🚗 到位操作", expanded=True):
    user_inputs = {}
    user_inputs["target"] = f"5,3,{location_id}"

    if st.button(f"🚗 [执行] 操作小车"):
        try:
            body = {}
            for k, v in user_inputs.items():
                try:
                    body[k] = int(v)
                except:
                    body[k] = v
            url = API_BASE + "/control/car_move"
            # st.write(f"请求：{url} - 参数：{body}")

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

st.subheader("🚦 入库操作开始！")
steps = [
    {
        "step": 1,
        "title": "步骤 1：库口物料 ➡️ 电梯 入库",
        "api": "/control/task_lift_inband",
        "method": "GET",
        "params": {},
    },
    {
        "step": 2,
        "title": "步骤 2：电梯移动",
        "api": "/control/lift",
        "method": "POST",
        "params": {"layer": location_id},
    },
    {
        "step": 3,
        "title": "步骤 3：提升机物料 ➡️ 库内",
        "api": "/control/task_out_lift",
        "method": "POST",
        "params": {"layer": location_id},
    },
    {
        "step": 4,
        "title": "步骤 4：操作小车取料，移动货物",
        "api": "/control/good_move",
        "method": "POST",
        "params": {
            "target": "6,3,1",
        },
    },
    {
        "step": 5,
        "title": "步骤 5：入库完成确认",
        "api": "/control/task_pick_complete",
        "method": "POST",
        "params": {"layer": location_id},
    },
]

for i, step in enumerate(steps):

    if step["step"] == 1:
        with st.expander(step["title"], expanded=True):
            # st.markdown(f"**接口：** `{step['method']} {step['api']}`")
            user_inputs = {}
            if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
                try:
                    body = {}
                    for k, v in user_inputs.items():
                        if isinstance(step["params"][k], list):
                            body[k] = v
                        else:
                            try:
                                body[k] = int(v)
                            except:
                                body[k] = v

                    url = API_BASE + step["api"]
                    
                    # st.write(f"请求：{url} - 参数：{body}")

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

    elif step["step"] == 2:
        with st.expander(step["title"], expanded=True):
            # st.markdown(f"**接口：** `{step['method']} {step['api']}`")
            # location_id = st.selectbox(f"请输入电梯层", list(range(1, 5)))

            if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
                try:
                    body = {"layer": location_id}
                    url = API_BASE + step["api"]
                    
                    # st.write(f"请求：{url} - 参数：{body}")

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

    elif step["step"] == 3:
        with st.expander(step["title"], expanded=True):
            # st.markdown(f"**接口：** `{step['method']} {step['api']}`")
            # location_id = st.selectbox(f"请输入任务层", list(range(1, 5)))

            if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
                try:
                    body = {"layer": location_id}
                    url = API_BASE + step["api"]

                    # st.write(f"请求：{url} - 参数：{body}")

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

    elif step["step"] == 4:
        with st.expander(step["title"], expanded=True):
            # st.markdown(f"**接口：** `{step['method']} {step['api']}`")
            user_inputs = {}
            for key, default in step["params"].items():
                # z = st.selectbox(f"层号 (z)", list(range(1, 5)), key=f"{key}_z_{i}")
                if key in ["source", "target"]:
                    if key == "source":
                        # st.markdown(f"**起点 坐标**（x=行, y=列, z=层）")
                        user_inputs[key] = f"5,3,{location_id}"

                    elif key == "target":
                        # st.markdown(f"**终点 坐标**（x=5, y=3, z={z}）")
                        st.markdown(f"**目标点坐标**（x=行, y=列, z=层）")
                        col1, col2 = st.columns(2)
                        with col1:
                            x = st.selectbox(
                                f"起点 - 行号 (x)",
                                list(range(1, 9)),
                                key=f"{key}_x_{i}",
                            )
                        with col2:
                            y = st.selectbox(
                                f"起点 - 列号 (y)",
                                list(range(1, 8)),
                                key=f"{key}_y_{i}",
                            )
                        user_inputs[key] = f"{x},{y},{location_id}"

                elif isinstance(default, list):
                    user_inputs[key] = default  # 固定默认值不编辑
                else:
                    user_inputs[key] = st.text_input(
                        key, value=str(default), key=f"{key}_{i}"
                    )

            if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
                try:
                    body = {}
                    for k, v in user_inputs.items():
                        if isinstance(step["params"][k], list):
                            body[k] = v
                        else:
                            try:
                                body[k] = int(v)
                            except:
                                body[k] = v

                    url = API_BASE + step["api"]
                    
                    # st.write(f"请求：{url} - 参数：{body}")

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

    elif step["step"] == 5:
        with st.expander(step["title"], expanded=True):
            # st.markdown(f"**接口：** `{step['method']} {step['api']}`")
            # location_id = st.selectbox(f"请输入任务层", list(range(1, 5)))

            if st.button(f"🚀 [执行] {step['title']}", key=f"btn_{i}"):
                try:
                    body = {"layer": location_id}
                    url = API_BASE + step["api"]

                    # st.write(f"请求：{url} - 参数：{body}")

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
