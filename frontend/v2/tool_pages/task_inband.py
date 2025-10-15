# 入库操作页面
# tool_pages/task_inband.py

import streamlit as st
import requests
from api_config import API_BASE

st.subheader("⚠️ 确保小车在需要入库的楼层 ⚠️")
st.subheader("⚠️ 如果小车不在任务楼层 ⚠️")
st.subheader("⚠️ 先去把🚗小车移到需要入库的楼层 ⚠️")
st.link_button("🚗 前往小车跨层页面", url="/car_cross_layer")
st.subheader("⚠️ 小车在入库楼层，就不需要小车跨层了 ⚠️")

st.image("img/locations.png")

st.subheader("🚧 此功能为测试功能，使用前请谨慎。")

# 在最上方统一选择任务层号
st.subheader("📌 设置物料需要入库的楼层和坐标")
with st.expander("📋 任务层号设置", expanded=True):
    layer = st.selectbox("请选择任务所在楼层 (z)", list(range(1, 5)), index=0)
    st.markdown(f"**目标点坐标**（x=行, y=列, z=层）")
    col1, col2 = st.columns(2)
    with col1:
        x = st.selectbox(
            f"起点 - 行号 (x)",
            list(range(1, 9)),
            key=f"target_x",
        )
    with col2:
        y = st.selectbox(
            f"起点 - 列号 (y)",
            list(range(1, 8)),
            key=f"target_y",
        )
    location = f"{x},{y},{layer}"


st.subheader("🚦 入库操作开始！")
steps = [
    {
        "step": 0,
        "title": "准备：📋 电梯到达1层操作",
        "api": "/control/lift",
        "method": "POST",
        "params": {"layer": 1},
    },
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
        "params": {"layer": layer},
    },
    {
        "step": 3,
        "title": "步骤 3：提升机物料 ➡️ 库内",
        "api": "/control/task_out_lift",
        "method": "POST",
        "params": {"layer": layer},
    },
    {
        "step": 4,
        "title": "步骤 4：操作小车移动到接驳位",
        "api": "/control/car_move",
        "method": "POST",
        "params": {
            "target": f"5,3,{layer}",
        },
    },
    {
        "step": 5,
        "title": "步骤 5：操作小车取料，移动货物",
        "api": "/control/good_move",
        "method": "POST",
        "params": {
            "target": location,
        },
    },
    {
        "step": 6,
        "title": "步骤 6：入库完成确认",
        "api": "/control/task_pick_complete",
        "method": "POST",
        "params": {"layer": layer},
    },
]

# 创建取消执行的状态
if "cancel_execution" not in st.session_state:
    st.session_state.cancel_execution = False

# 动态参数生成函数（保持原始字典结构，仅替换特定值）
def generate_dynamic_params(SETP, TARGET_LAYER, TARGET_LOCATION):
    # 创建参数的深拷贝，避免修改原始字典
    params = SETP["params"].copy()
    
    if SETP["step"] == 0:
        params["layer"] = 1
    
    elif SETP["step"] == 1:
        params["target"] = f"5,3,{TARGET_LAYER}"
    
    elif SETP["step"] == 2:
        params["target"] = {}
    
    elif SETP["step"] == 3:
        params["layer"] = TARGET_LAYER
    
    elif SETP["step"] == 4:
        params["layer"] = TARGET_LAYER
    
    elif SETP["step"] == 5:
        params["target"] = TARGET_LOCATION
    
    elif SETP["step"] == 6:
        params["layer"] = TARGET_LAYER
        
    return params

# 操作执行函数
def execute_cross_layer_steps(TARGET_LAYER, TARGET_LOCATION):
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
        dynamic_params = generate_dynamic_params(step, TARGET_LAYER, TARGET_LOCATION)
        
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

with st.expander("入库操作", expanded=True):
    if st.button("🚀 执行任务", key="btn_car_cross_layer"):
        execute_cross_layer_steps(layer, location)
    
    if st.button("🔄 清除结果", key="btn_clear"):
        st.rerun()
