# tool_pages/location_set.py
import json

import streamlit as st
import requests
import pandas as pd

from api_config import API_BASE

steps = [
    {
        "step": 1,
        "title": "**数据库信息查询**",
        "api": "/read/locations",
        "method": "GET",
        "params": {},
    },
    {
        "step": 2,
        "title": "**更新数据库信息**",
        "api": "/write/bulk_sync_locations",
        "method": "POST",
        "params": {
            "data": []
            }
    },
    {
        "step": 3,
        "title": "**重置数据库信息**",
        "api": "/reset/locations",
        "method": "GET",
        "params": {}
    }
]

a1, a2 = st.columns(2)

for i, step in enumerate(steps):

    if step["step"] == 1:
        with a1:
            with st.expander(step["title"], expanded=True):

                if st.button(f"🔍 {step['title']}", key=f"btn_{i}"):
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
                                    st.success(f"✅ 数据库查询成功")
                                    sql_infos = resp.json()
                                    st.write(sql_infos)
                            except:
                                st.text(resp.text)
                        else:
                            st.error(f"请求失败，状态码：{resp.status_code}")
                            st.text(resp.text)

                    except Exception as e:
                        st.error(f"请求失败：{e}")
    
    elif step["step"] == 2:
        with a2:
            with st.expander(step["title"], expanded=True):  
                if f"input_{i}" not in st.session_state:
                    st.session_state[f"input_{i}"] = """
            {
                "success":true,
                "code":200,
                "status":"ok",
                "message":"操作成功",
                "data": [
                    {
                        "location": "1,1,1",
                        "status": "free"
                    },
                    {
                        "location": "1,1,2",
                        "pallet_id": "P1001",
                        "status": "occupied"
                    }
                ]
            }
                    """

                location_data_str = st.text_area(
                    "请输入数据",
                    value=st.session_state[f"input_{i}"],
                    key=f"text_area_{i}"
                    )
                if location_data_str:
                    location_data_obj = json.loads(location_data_str)
                    # st.write(location_data_obj)
                    location_data = location_data_obj["data"]
                    body = {"data": location_data}
                    # st.write(body)
                else:
                    st.warning("请输入数据")

                if st.button(f"🔍 {step['title']}", key=f"btn_{i}"):
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
                                    sql_infos = resp.json()['data']
                                    st.json(sql_infos)
                            except:
                                st.text(resp.text)
                        else:
                            st.error(f"请求失败，状态码：{resp.status_code}")
                            st.text(resp.text)

                    except Exception as e:
                        st.error(f"请求失败：{e}")

    elif step["step"] == 3:
        with st.expander(step["title"]):

            if st.button(f"🔍 {step['title']}", key=f"btn_{i}"):
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
                                st.success(f"✅ 数据库重置成功")
                                sql_infos = resp.json()
                                st.write(sql_infos)
                        except:
                            st.text(resp.text)
                    else:
                        st.error(f"请求失败，状态码：{resp.status_code}")
                        st.text(resp.text)

                except Exception as e:
                    st.error(f"请求失败：{e}")