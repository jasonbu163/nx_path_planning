import streamlit as st
import requests

API_BASE = "http://localhost:8765"

# 页面配置（每页含多个步骤，每步定义接口及默认参数）
page_steps = {
    "📥 入库操作": [
        {
            "title": "步骤 1：库口物料 ➡️ 电梯 入库",
            "api": "/control/task_lift_inband",
            "method": "GET",
            "params": {}
        },
        {
            "title": "步骤 2：电梯移动",
            "api": "/control/lift",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 3：提升机物料 ➡️ 库内",
            "api": "/control/task_out_lift",
            "method": "POST",
            "params": {
                "layer": 1
            }
        },
        {
            "title": "步骤 4：操作小车取料，移动货物",
            "api":"/control/good_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "points": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 5：入库完成确认",
            "api": "/control/task_pick_complete",
            "method": "POST",
            "params": {
                "layer": 1
            }
        }
    ],
    "📤 出库操作": [
        {
            "title": "步骤 1：启动PLC确认，小车去放料",
            "api":"/control/task_in_lift",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 2：操作小车放料，移动货物",
            "api": "/control/good_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "points": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 3：确认在对应楼层，小车放料完成✅",
            "api":  "/control/task_feed_complete",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 4：电梯移动",
            "api": "/control/lift",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 5：提升机物料 ➡️ 库口 出库",
            "api": "/control/task_lift_outband",
            "method": "GET",
            "params": {}
        }
    ],
    "🚚 小车跨层": [
        {
            "title": "步骤 1：操作小车移动",
            "api": "/control/car_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "path": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 2：电梯移动",
            "api": "/control/lift",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 1：操作小车移动",
            "api": "/control/car_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "path": ["1,1,1", "3,2,1", "6,3,1"]
            }
        }
    ],
    "📦 货物跨层": [
        {
            "title": "步骤 1：启动PLC确认，小车去放料",
            "api":"/control/task_in_lift",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 2：操作小车放货",
            "api": "/control/good_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "points": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 3：确认在对应楼层，小车放料完成✅",
            "api":  "/control/task_feed_complete",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 4：电梯移动",
            "api": "/control/lift",
            "method": "POST",
            "params": {"layer": 1}
        },
        {
            "title": "步骤 5：提升机物料 ➡️ 库内",
            "api": "/control/task_out_lift",
            "method": "POST",
            "params": {
                "layer": 1
            }
        },
        {
            "title": "步骤 5：操作小车取货",
            "api": "/control/good_move_segments",
            "method": "POST",
            "params": {
                "source": "1,1,1",
                "target": "6,3,1",
                "points": ["1,1,1", "3,2,1", "6,3,1"]
            }
        },
        {
            "title": "步骤 6：入库完成确认",
            "api": "/control/task_pick_complete",
            "method": "POST",
            "params": {
                "layer": 1
            }
        }
    ]
}

# 页面导航栏
st.sidebar.title("页面导航")
page = st.sidebar.radio("选择操作页面", list(page_steps.keys()))
st.title(page)

# 每个页面包含若干步骤
for i, step in enumerate(page_steps[page]):
    with st.expander(step["title"], expanded=True):
        st.markdown(f"**接口：** `{step['method']} {step['api']}`")

        # 动态输入区域
        user_inputs = {}
        for key, default in step["params"].items():
            if isinstance(default, list):
                user_inputs[key] = st.text_area(f"{key}（多个值用英文逗号分隔）", value=", ".join(default), key=f"{key}_{i}")
            else:
                user_inputs[key] = st.text_input(key, value=str(default), key=f"{key}_{i}")

        # 执行按钮（key 唯一）
        if st.button(f"🚀 执行 {step['title']}", key=f"send_{i}"):
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
                    continue

                st.success(f"✅ 状态码：{resp.status_code}")
                try:
                    st.json(resp.json())
                except:
                    st.text(resp.text)
            except Exception as e:
                st.error(f"🚨 请求失败：{e}")