# tool_pages/location_set.py
import streamlit as st
import requests
import pandas as pd

from api_config import API_BASE

st.image("img/locations.png")    

steps = [
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
        "title": "**新增位置托盘信息**",
        "api": "/write/update_pallet_by_loc",
        "method": "POST",
        "params": {
            "location": "1,1,4",
            "new_pallet_id": "P1001"
            },
    },
    {
        "step": 3,
        "title": "**删除位置托盘信息**",
        "api": "/write/delete_pallet_by_loc",
        "method": "POST",
        "params": {
            "location": "1,1,4"
            },
    }
]

for i, step in enumerate(steps):

    if step["step"] == 1:
        with st.expander(step["title"], expanded=True):
            
            user_inputs = {}
            floor_id = st.selectbox(f"选择楼层", list(range(1, 5)),key=f"floor_id_box_{i}")
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

            if st.button(f"🔍 {step['title']}", key=f"btn_{i}"):
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

    elif step["step"] == 2:
        with st.expander(step["title"], expanded=True):
            
            user_inputs = {}

            new_pallet_id = st.text_input("请输入托盘号, 如 A10001", value="A10001", key=f"input_{i}")
            if new_pallet_id:
                user_inputs["new_pallet_id"] = f"{new_pallet_id}"
            else:
                st.warning("请输入托盘号")

            col_x_1, col_y_1, col_z_1 = st.columns(3)
            with col_x_1:
                x_1 = st.selectbox("请选择行 (x)", list(range(1, 9)), key=f"x_{i}")
            with col_y_1:
                y_1 = st.selectbox("请选择列 (y)", list(range(1, 8)), key=f"y_{i}")
            with col_z_1:
                z_1 = st.selectbox("请选择层 (z)", list(range(1, 5)), key=f"z_{i}")

            location = f"{x_1},{y_1},{z_1}"
            user_inputs["location"] = location

            if st.button(f"🔍 {step['title']}", key=f"btn_{i}"):
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

    elif step["step"] == 3:
        with st.expander(step["title"], expanded=True):
            
            user_inputs = {}

            col_x_1, col_y_1, col_z_1 = st.columns(3)
            with col_x_1:
                x_1 = st.selectbox("请选择行 (x)", list(range(1, 9)), key=f"x_{i}")
            with col_y_1:
                y_1 = st.selectbox("请选择列 (y)", list(range(1, 8)), key=f"y_{i}")
            with col_z_1:
                z_1 = st.selectbox("请选择层 (z)", list(range(1, 5)), key=f"z_{i}")

            location = f"{x_1},{y_1},{z_1}"
            user_inputs["location"] = location

            if st.button(f"🔍 {step['title']}", key=f"btn_{i}"):
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