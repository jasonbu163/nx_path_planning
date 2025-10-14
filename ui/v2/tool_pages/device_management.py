# tool_pages/device_management.py
import streamlit as st
import requests

from api_config import API_BASE

st.markdown("⚠️ 此页面为设备自动化联动页面，请使用前**确保所有设备正常**")

a1, a2 = st.columns(2)
with a1:
    
    with st.expander("🚧 穿梭车状态查询", expanded=True):

        if st.button(f"🔋 查询穿梭车电量", use_container_width=True):
            try:
                url = API_BASE + "/control/get_car_info_with_power"
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        else:
                            st.success(f"{resp.json()['message']}")
                            # st.json(resp.json())
                            st.markdown(f"电量：{resp.json()['data'].get('power')}")
                            st.markdown(f"位置：{resp.json()['data'].get('current_location')}")
                            st.markdown(f"状态：{resp.json()['data'].get('car_status')}")
                            st.markdown(f"描述：{resp.json()['data'].get('status_description')}")

                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")
        
        if st.button(f"📄 查询穿梭车信息", use_container_width=True):
            try:
                url = API_BASE + "/control/get_car_status"
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        else:
                            st.success(f"{resp.json()['message']}")
                            # st.json(resp.json())
                            st.markdown(f"状态码：{resp.json()['data'].get('car_status')}")
                            st.markdown(f"状态：{resp.json()['data'].get('name')}")
                            st.markdown(f"描述：{resp.json()['data'].get('description')}")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")

        if st.button(f"📍 查询穿梭车位置", use_container_width=True):
            try:
                url = API_BASE + "/control/get_car_location"
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        else:
                            st.success(f"{resp.json()['message']}")
                            # st.json(resp.json())
                            st.markdown(f"位置：{resp.json()['data']}")
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")

with a2:

    with st.expander("🔋 穿梭车电量管理", expanded=True):

        if st.button(f"🚗 前往充电口", use_container_width=True):
            try:
                url = API_BASE + "/control/car_move_to_charge"
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        else:
                            st.success(f"{resp.json()['message']}")
                            st.json(resp.json())
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")


        if st.button(f"▶️ 开始充电", use_container_width=True):
            try:
                url = API_BASE + "/control/start_car_charge"
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        else:
                            st.success(f"{resp.json()['message']}")
                            st.json(resp.json())
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")


        if st.button(f"⏸️ 停止充电", use_container_width=True):
            try:
                url = API_BASE + "/control/start_car_charge"
                resp = requests.get(url)

                if resp.status_code == 200:
                    try:
                        if resp.json()["code"] == 404:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        elif resp.json()["code"] == 500:
                            st.error(f"{resp.json()['message']}")
                            st.json(resp.json())
                        else:
                            st.success(f"{resp.json()['message']}")
                            st.json(resp.json())
                    except:
                        st.text(resp.text)
                else:
                    st.error(f"请求失败，状态码：{resp.status_code}")
                    st.text(resp.text)

            except Exception as e:
                st.error(f"请求失败：{e}")