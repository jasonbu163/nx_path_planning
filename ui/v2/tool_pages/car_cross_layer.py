# 🚚 小车跨层页面文件，如 pages/🚚 小车跨层.py
import streamlit as st
import requests
import time

from api_config import API_BASE

st.image("img/locations.png")

st.subheader("🚧 此功能为测试功能，请谨慎使用。")

steps = [
    {
        "step": 0,
        "title": "准备：📋 电梯到达🚗层操作",
        "api": "/control/lift",
        "method": "POST",
        "params": {"layer": 1},
    },
    {
        "step": 1,
        "title": "步骤 1：🚚 操作小车",
        "api": "/control/car_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        },
    },
    {
        "step": 2,
        "title": "步骤 2：🚚 操作小车",
        "api": "/control/car_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        },
    },
    {
        "step": 3,
        "title": "步骤 3：🚀 电梯移动",
        "api": "/control/lift",
        "method": "POST",
        "params": {"layer": 1},
    },
    {
        "step": 4,
        "title": "步骤 4：🚚 确认小车到位",
        "api": "/control/change_car_location",
        "method": "POST",
        "params": {"target": "5,3,1"},
    },
    {
        "step": 5,
        "title": "步骤 5：🚚 操作小车",
        "api": "/control/car_move",
        "method": "POST",
        "params": {
            "target": "5,3,1",
        },
    },
    {
        "step": 6,
        "title": "步骤 6：🚚 确认完成小车跨层所有操作",
        "api": "/control/lift",
        "method": "POST",
        "params": {"layer": 1},
    },
]


# 楼层选择区
st.subheader("📌 设置小车移动楼层")
col1, col2 = st.columns(2)
with col1:
    floor_a = st.selectbox("🚩 小车起始楼层（步骤 1-2）", [1, 2, 3, 4], key="floor_a")
with col2:
    floor_b = st.selectbox("🏁 小车目标楼层（步骤 3-6）", [1, 2, 3, 4], key="floor_b")

# 创建取消执行的状态
if "cancel_execution" not in st.session_state:
    st.session_state.cancel_execution = False

# 动态参数生成函数（保持原始字典结构，仅替换特定值）
def generate_dynamic_params(step, floor_a, floor_b):
    # 创建参数的深拷贝，避免修改原始字典
    params = step["params"].copy()
    
    if step["step"] == 0:
        params["layer"] = floor_a
    
    elif step["step"] == 1:
        params["target"] = f"5,3,{floor_a}"
    
    elif step["step"] == 2:
        params["target"] = f"6,3,{floor_a}"
    
    elif step["step"] == 3:
        params["layer"] = floor_b
    
    elif step["step"] == 4:
        params["target"] = f"6,3,{floor_b}"
    
    elif step["step"] == 5:
        params["target"] = f"5,3,{floor_b}"
    
    elif step["step"] == 6:
        params["layer"] = floor_b
        
    return params

# 操作执行函数
def execute_cross_layer_steps(floor_a, floor_b):
    # 重置取消状态
    st.session_state.cancel_execution = False

    process_bar = st.progress(0, text="准备开始操作...")
    status_area = st.empty()
    cancel_button = st.empty()
    results = {}
    
    for i, step in enumerate(steps):
        # 确保状态变量存在且检查是否取消
        if 'cancel_execution' in st.session_state and st.session_state.cancel_execution:
            status_area.warning("操作已取消")
            break
        
        # 更新进度条和状态
        progress_value = int((i + 1) / len(steps) * 100)
        process_bar.progress(progress_value, text=f"执行中: {step['title']}")
        status_area.info(f"正在执行: {step['title']}")
        
        # 获取动态参数（保持原始字典结构）
        dynamic_params = generate_dynamic_params(step, floor_a, floor_b)
        
        # 显示取消按钮（每次循环时刷新）
        if cancel_button.button("⛔ 取消操作", key=f"cancel_{i}"):
            st.session_state.cancel_execution = True
            status_area.warning("操作取消中...")
            break
        
        try:
            url = API_BASE + step["api"]
            method = step["method"]
            
            # 执行API请求
            if method == "POST":
                response = requests.post(url, json=dynamic_params, timeout=600)
            else:
                response = requests.get(url, params=dynamic_params, timeout=600)
            
            # 处理响应
            if response.status_code == 200:
                response_data = response.json()
                if response_data["code"] == 200 and response_data["data"] == True:
                    results[step["step"]] = "✅ 成功"
                else:
                    results[step["step"]] = f"❌ 错误: {response_data['message']}"
                    st.error(f"步骤 {step['step']} 失败: {response_data['message']}")
                    break
            else:
                results[step["step"]] = f"❌ HTTP错误: {response.status_code}"
                st.error(f"请求失败: {response.status_code}")
                break
                
        except Exception as e:
            results[step["step"]] = f"❌ 异常: {str(e)}"
            st.error(f"执行异常: {str(e)}")
            break
    
    # 完成后的处理
    process_bar.empty()
    
    if not st.session_state.cancel_execution and len(results) == len(steps):
        st.balloons()
        st.success("🎉 所有步骤已完成！")
    elif not st.session_state.cancel_execution:
        st.warning(f"⚠️ 操作在步骤 {step['step']} 中断")
    
    # 显示详细结果
    with st.expander("操作详情"):
        for step in steps:
            result = results.get(step["step"], "未执行")
            st.write(f"{step['title']}: {result}")

# 操作界面
st.subheader("🚦 小车跨层操作开始！")

with st.expander("穿梭车跨层操作", expanded=True):
    if st.button("🚀 执行任务", key="btn_car_cross_layer"):
        execute_cross_layer_steps(floor_a, floor_b)
    
    if st.button("🔄 清除结果", key="btn_clear"):
        st.rerun()