# 🚚 小车跨层页面文件，如 pages/🚚 小车跨层.py
import streamlit as st
import requests
import pandas as pd

from api_config import API_BASE

st.subheader("⚠️⚠️ 此页面为设备自动化联动页面，请使用前确保所有设备正常 ⚠️⚠️")

st.image("img/locations.png")

a1, a2 = st.columns(2)
with a1:
    st.subheader("🚧 电梯操作 🚧")
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
    st.subheader("👓 获取入口处托盘码 👓")
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
        "title": "⬇️ **入库操作** (无遮挡货物检测)",
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
        "title": "⬆️ **出库操作** (无遮挡货物检测)",
        "api": "/control/task_outband",
        "method": "POST",
        "params": {"target": "5,3,1"},
    },
    {
        "step": 4,
        "title": "⬇️ **入库操作**",
        "api": "/control/task_inband_with_solve_blocking",
        "method": "POST",
        "params": {
            "location": "1,1,4",
            "new_pallet_id": "P1001"
            }
    },
    {
        "step": 5,
        "title": "⬆️ **出库操作**",
        "api": "/control/task_outband_with_solve_blocking",
        "method": "POST",
        "params": {
            "location": "1,1,4",
            "new_pallet_id": "P1001"
            }
    },
]

read_db = [
    {
        "step": 1,
        "title": "**楼层信息查询**",
        "api": "/read/floor_info",
        "method": "POST",
        "params": {
            "start_id": 1,
            "end_id": 1
            },
    },
    {
        "step": 2,
        "title": "**库内托盘查询**",
        "api": "/read/location_by_pallet_id",
        "method": "POST",
        "params": {
            "pallet_id": "P1001"
            }
    },
]


################################################
# ----------------- 高级入库操作 -----------------
################################################

st.subheader("🚧 高级入库操作 🚧")

# 楼层信息查询
step = read_db[0]
with st.expander(step["title"]):
            
    user_inputs = {}
    floor_id = st.selectbox(f"选择楼层", list(range(1, 5)),key=f"floor_id_box_db_1")
    if floor_id == 1:
        user_inputs['start_id'] = 124
        user_inputs['end_id'] = 164
    elif floor_id == 2:
        user_inputs['start_id'] = 83
        user_inputs['end_id'] = 123
    elif floor_id == 3:
        user_inputs['start_id'] = 42
        user_inputs['end_id'] = 82
    elif floor_id == 4:
        user_inputs['start_id'] = 1
        user_inputs['end_id'] = 41
    else:
        st.error("❌ 输入楼层错误")

    if st.button(f"🔍 {step['title']}", key=f"btn_db_1"):
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
                        sql_infos = resp.json()['data']
                        # st.json(sql_infos)
                        if sql_infos:
                            table_data = []
                            for sql_info in sql_infos:
                                table_data.append([
                                    sql_info['id'],
                                    sql_info['location'],
                                    sql_info['pallet_id'],
                                    sql_info['status']
                                    ])
                            with st.expander(f"{floor_id}层库位信息", expanded=True):
                                df = pd.DataFrame(table_data, columns=['id', '库位', '托盘ID', '状态'])
                                st.dataframe(df)
                        else:
                            st.warning("没有找到库位信息")
                except:
                    st.text(resp.text)
            else:
                st.error(f"请求失败，状态码：{resp.status_code}")
                st.text(resp.text)

        except Exception as e:
            st.error(f"请求失败：{e}")

# --- 创建水平布局 ---
b1, b2 = st.columns(2)  # 创建两列水平布局
# 入库操作 (带障碍货物处理) -> 放在第一列
with b1:
    step = steps[3]
    with st.expander(step["title"], expanded=True):

        body = {}
        st.markdown("📌 **设置入库目标**")
        
        new_pallet_id = st.text_input("请输入托盘号, 如 A10001", value="A10001", key=f"input_3")
        if new_pallet_id:
            body["new_pallet_id"] = f"{new_pallet_id}"
        else:
            st.warning("请输入托盘号")

        col_x_3, col_y_3, col_z_3 = st.columns(3)
        with col_x_3:
            x_3 = st.selectbox("请选择行 (x)", list(range(1, 9)), key=f"x_3")
        with col_y_3:
            y_3 = st.selectbox("请选择列 (y)", list(range(1, 8)), key=f"y_3")
        with col_z_3:
            z_3 = st.selectbox("请选择层 (z)", list(range(1, 5)), key=f"z_3")
        location = f"{x_3},{y_3},{z_3}"
        
        body["location"] = location

        if st.button(f"🚀 [执行] {step['title']}", key=f"btn_step_4"):
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


# 托盘号查询 -> 放在第二列
with b2:
    step = read_db[1]
    with st.expander(step["title"], expanded=True):
            
        user_inputs = {}

        pallet_id = st.text_input("请输入托盘号, 如 A10001", value="A10001", key=f"input_db_2")
        if pallet_id:
            user_inputs["pallet_id"] = f"{pallet_id}"
        else:
            st.warning("请输入托盘号")

        if st.button(f"🔍 {step['title']}", key=f"btn__db_2"):
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
                            sql_infos = resp.json()['data']
                            # st.write(sql_infos)
                            if sql_infos:
                                table_data = []
                                table_data.append([
                                    sql_infos['id'],
                                    sql_infos['location'],
                                    sql_infos['pallet_id'],
                                    sql_infos['status']
                                    ])
                                with st.expander(f"{floor_id}层库位信息", expanded=True):
                                    df = pd.DataFrame(table_data, columns=['id', '库位', '托盘ID', '状态'])
                                    st.dataframe(df)
                            else:
                                st.warning("没有找到库位信息")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")


################################################
# ----------------- 高级出库操作 -----------------
################################################

st.subheader("🚧 高级出库操作 🚧")

# 楼层信息查询
step = read_db[0]
with st.expander(step["title"]):
            
    user_inputs = {}
    floor_id = st.selectbox(f"选择楼层", list(range(1, 5)),key=f"floor_id_box_db_3")
    if floor_id == 1:
        user_inputs['start_id'] = 124
        user_inputs['end_id'] = 164
    elif floor_id == 2:
        user_inputs['start_id'] = 83
        user_inputs['end_id'] = 123
    elif floor_id == 3:
        user_inputs['start_id'] = 42
        user_inputs['end_id'] = 82
    elif floor_id == 4:
        user_inputs['start_id'] = 1
        user_inputs['end_id'] = 41
    else:
        st.error("❌ 输入楼层错误")

    if st.button(f"🔍 {step['title']}", key=f"btn_db_3"):
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
                        sql_infos = resp.json()['data']
                        # st.json(sql_infos)
                        if sql_infos:
                            table_data = []
                            for sql_info in sql_infos:
                                table_data.append([
                                    sql_info['id'],
                                    sql_info['location'],
                                    sql_info['pallet_id'],
                                    sql_info['status']
                                    ])
                            with st.expander(f"{floor_id}层库位信息", expanded=True):
                                df = pd.DataFrame(table_data, columns=['id', '库位', '托盘ID', '状态'])
                                st.dataframe(df)
                        else:
                            st.warning("没有找到库位信息")
                except:
                    st.text(resp.text)
            else:
                st.error(f"请求失败，状态码：{resp.status_code}")
                st.text(resp.text)

        except Exception as e:
            st.error(f"请求失败：{e}")

# --- 创建水平布局 ---
d1, d2 = st.columns(2)  # 创建两列水平布局

# 出库操作 -> 放在第一列
with d1:
    step = steps[4]
    with st.expander(step["title"], expanded=True):
        body = {}

        st.markdown("📌 **设置出库目标**")

        
        new_pallet_id = st.text_input("请输入托盘号, 如 A10001", value="A10001", key=f"input_4")
        if new_pallet_id:
            body["new_pallet_id"] = f"{new_pallet_id}"
        else:
            st.warning("请输入托盘号")

        col_x_4, col_y_4, col_z_4 = st.columns(3)
        with col_x_4:
            x_4 = st.selectbox("请选择行 (x)", list(range(1, 9)), key="x_4")
        with col_y_4:
            y_4 = st.selectbox("请选择列 (y)", list(range(1, 8)), key="y_4")
        with col_z_4:
            z_4 = st.selectbox("请选择层 (z)", list(range(1, 5)), key="z_4")
        location = f"{x_4},{y_4},{z_4}"
        body["location"] = location

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

# 托盘号查询 -> 放在第二列
with d2:
    step = read_db[1]
    with st.expander(step["title"], expanded=True):
            
        user_inputs = {}

        pallet_id = st.text_input("请输入托盘号, 如 A10001", value="A10001", key=f"input_db_4")
        if pallet_id:
            user_inputs["pallet_id"] = f"{pallet_id}"
        else:
            st.warning("请输入托盘号")

        if st.button(f"🔍 {step['title']}", key=f"btn__db_4"):
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
                            sql_infos = resp.json()['data']
                            # st.write(sql_infos)
                            if sql_infos:
                                table_data = []
                                table_data.append([
                                    sql_infos['id'],
                                    sql_infos['location'],
                                    sql_infos['pallet_id'],
                                    sql_infos['status']
                                    ])
                                with st.expander(f"{floor_id}层库位信息", expanded=True):
                                    df = pd.DataFrame(table_data, columns=['id', '库位', '托盘ID', '状态'])
                                    st.dataframe(df)
                            else:
                                st.warning("没有找到库位信息")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")


################################################
# ----------------- 设备基础联动操作 -----------------
################################################

st.subheader("🚧 设备基础联动操作 🚧")
# --- 创建水平布局 ---
c1, c2, c3 = st.columns(3)  # 创建三列水平布局

# 入库操作 -> 放在第一列
with c1:
    step = steps[0]
    with st.expander(step["title"]):
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
    with st.expander(step["title"]):
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
    with st.expander(step["title"]):
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