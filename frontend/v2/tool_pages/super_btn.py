import streamlit as st
import requests
from api_config import API_BASE

# 页面配置（每页含多个步骤，每步定义接口及默认参数）
lift = [
    {
        "title": "1楼",
        "api": "/control/lift",
        "method": "POST",
        "params": {
            "layer": 1
            }
    },
    {
        "title": "2楼",
        "api": "/control/lift",
        "method": "POST",
        "params": {
            "layer": 2
            }
    },
    {
        "title": "3楼",
        "api": "/control/lift",
        "method": "POST",
        "params": {
            "layer": 3
            }
    },
    {
        "title": "4楼",
        "api": "/control/lift",
        "method": "POST",
        "params": {
            "layer": 4
            }
    }
]

outband_task_in_lift = [
    {
        "title": "1楼开始出层",
        "api": "/control/task_in_lift",
        "method": "POST",
        "params": {
            "layer": 1
            }
    },
    {
        "title": "2楼开始出层",
        "api": "/control/task_in_lift",
        "method": "POST",
        "params": {
            "layer": 2
            }
    },
    {
        "title": "3楼开始出层",
        "api": "/control/task_in_lift",
        "method": "POST",
        "params": {
            "layer": 3
            }
    },
    {
        "title": "4楼开始出层",
        "api": "/control/task_in_lift",
        "method": "POST",
        "params": {
            "layer": 4
            }
    },
]

outband_task_feed_complete = [
    {
        "title": "1楼出层完成",
        "api": "/control/task_feed_complete",
        "method": "POST",
        "params": {
            "layer": 1
            }
    },
    {
        "title": "2楼出层完成",
        "api": "/control/task_feed_complete",
        "method": "POST",
        "params": {
            "layer": 2
            }
    },
    {
        "title": "3楼出层完成",
        "api": "/control/task_feed_complete",
        "method": "POST",
        "params": {
            "layer": 3
            }
    },
    {
        "title": "4楼出层完成",
        "api": "/control/task_feed_complete",
        "method": "POST",
        "params": {
            "layer": 4
            }
    },
]

outband = [
    {
        "title": "电梯 ➡️ 出口",
        "api": "/control/task_lift_outband",
        "method": "GET",
        "params": {}
    }
]

inband_task_out_lift = [
    {
        "title": "1楼开始入层",
        "api": "/control/task_out_lift",
        "method": "POST",
        "params": {
            "layer": 1
            },
    },
    {
        "title": "2楼开始入层",
        "api": "/control/task_out_lift",
        "method": "POST",
        "params": {
            "layer": 2
            },
    },
    {
        "title": "3楼开始入层",
        "api": "/control/task_out_lift",
        "method": "POST",
        "params": {
            "layer": 3
            },
    },
    {
        "title": "4楼开始入层",
        "api": "/control/task_out_lift",
        "method": "POST",
        "params": {
            "layer": 4
            },
    },
]

inband_task_pick_complete = [
    {
        "title": "1楼入库完成",
        "api": "/control/task_pick_complete",
        "method": "POST",
        "params": {
            "layer": 1
            },
    },
    {
        "title": "2楼入库完成",
        "api": "/control/task_pick_complete",
        "method": "POST",
        "params": {
            "layer": 2
            },
    },
    {
        "title": "3楼入库完成",
        "api": "/control/task_pick_complete",
        "method": "POST",
        "params": {
            "layer": 3
            },
    },
    {
        "title": "4楼入库完成",
        "api": "/control/task_pick_complete",
        "method": "POST",
        "params": {
            "layer": 4
            },
    },
]

inband = [
    {
        "title": "入口 ➡️ 电梯",
        "api": "/control/task_lift_inband",
        "method": "GET",
        "params": {},
    }
]

def super_btn(step, key_name):
    # 动态输入区域
        user_inputs = step['params']

        # 执行按钮（key 唯一）
        if st.button(f"🚀 {step['title']}", use_container_width=True, key=key_name):
            try:
                # 构建请求体
                payload = {}
                for k, v in user_inputs.items():
                    if isinstance(step["params"][k], list):
                        payload[k] = [item.strip() for item in v.split(",") if item.strip()]
                    else:
                        try:
                            payload[k] = int(v)
                        except:
                            payload[k] = v

                url = API_BASE + step["api"]
                method = step["method"].upper()

                if method == "POST":
                    resp = requests.post(url, json=payload)
                elif method == "GET":
                    resp = requests.get(url, params=payload)
                else:
                    st.error("❌ 不支持的请求方法")

                st.success(f"✅ 状态码：{resp.status_code}")
                # try:
                #     st.json(resp.json())
                # except:
                #     st.text(resp.text)
            except Exception as e:
                st.error(f"🚨 请求失败：{e}")

st.subheader("⬅️ 出库")

with st.expander("出库步骤", expanded=True):
    a1, a2, a3 = st.columns(3)
    with a1:
        with st.expander("🥅 出口", expanded=True):
            # st.markdown("载物台二维码")
            super_btn(outband[0], "task_lift_outband")
    with a2:
        with st.expander("↕️ 电梯", expanded=True):
            super_btn(lift[3], "out_lift_4")
            super_btn(lift[2], "out_lift_3")
            super_btn(lift[1], "out_lift_2")
            super_btn(lift[0], "out_lift_1")

    with a3:
        with st.expander("⬅️ 楼层出库", expanded=True):

            c1, c2 = st.columns(2)
            with c1:
                super_btn(outband_task_feed_complete[3], "task_feed_complete_4")
                super_btn(outband_task_feed_complete[2], "task_feed_complete_3")
                super_btn(outband_task_feed_complete[1], "task_feed_complete_2")
                super_btn(outband_task_feed_complete[0], "task_feed_complete_1")
                
            with c2:
                super_btn(outband_task_in_lift[3], "task_in_lift_4")
                super_btn(outband_task_in_lift[2], "task_in_lift_3")
                super_btn(outband_task_in_lift[1], "task_in_lift_2")
                super_btn(outband_task_in_lift[0], "task_in_lift_1")


st.subheader("➡️ 入库")

with st.expander("入库步骤", expanded=True):

    a1, a2, a3 = st.columns(3)
    with a1:
        with st.expander("🥅 入口", expanded=True):
            super_btn(inband[0], "task_lift_inband")
            # st.markdown("载物台二维码")
    
    with a2:
        with st.expander("↕️ 电梯", expanded=True):
            super_btn(lift[3], "in_lift_4")
            super_btn(lift[2], "in_lift_3")
            super_btn(lift[1], "in_lift_2")
            super_btn(lift[0], "in_lift_1")

    with a3:
        with st.expander("➡️ 楼层入库", expanded=True):
        
            b1, b2 = st.columns(2)
            with b1:
                super_btn(inband_task_out_lift[3], "task_out_lift_4")
                super_btn(inband_task_out_lift[2], "task_out_lift_3")
                super_btn(inband_task_out_lift[1], "task_out_lift_2")
                super_btn(inband_task_out_lift[0], "task_out_lift_1")
                
            with b2:
                super_btn(inband_task_pick_complete[3], "task_pick_complete_4")
                super_btn(inband_task_pick_complete[2], "task_pick_complete_3")
                super_btn(inband_task_pick_complete[1], "task_pick_complete_2")
                super_btn(inband_task_pick_complete[0], "task_pick_complete_1")
