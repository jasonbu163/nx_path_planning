import streamlit as st
import json
import pandas as pd
import numpy as np
from datetime import datetime
import requests

# 状态颜色映射 - 根据实际状态配置
STATUS_COLORS = {
    "free": "#90EE90",  # 浅绿色 - 空闲
    "occupied": "#FF6B6B",  # 红色 - 占用
    "highway": "#87CEEB",  # 天蓝色 - 通道
    "lift": "#FFD700",  # 金色 - 提升机
    "reserved": "#FFA500",  # 橙色 - 预留
    "maintenance": "#808080",  # 灰色 - 维护中
    "unavailable": "#E8E8E8"  # 浅灰色 - 不可用/无数据
}

# 状态显示文本（中文）
STATUS_TEXT = {
    "free": "空闲",
    "occupied": "占用",
    "highway": "通道",
    "lift": "提升机",
    "reserved": "预留",
    "maintenance": "维护",
    "unavailable": "无数据"
}

# 楼层ID范围映射
FLOOR_ID_MAPPING = {
    1: {"start_id": 124, "end_id": 164},
    2: {"start_id": 83, "end_id": 123},
    3: {"start_id": 42, "end_id": 82},
    4: {"start_id": 1, "end_id": 41}
}

def parse_location_data(data_list, target_layer=1):
    """
    解析返回的数据列表，根据坐标构建表格
    data_list: API返回的数据列表
    target_layer: 目标层数
    """
    # 确定表格尺寸
    max_row = 8
    max_col = 7
    
    # 初始化空表格 - 所有位置默认为"无数据"状态
    grid_data = []
    for row in range(1, max_row + 1):
        row_data = []
        for col in range(1, max_col + 1):
            row_data.append({
                "location": f"{row},{col},{target_layer}",
                "row": row,
                "col": col,
                "layer": target_layer,
                "status": "unavailable",
                "pallet_id": None,
                "id": None,
                "color": STATUS_COLORS["unavailable"]
            })
        grid_data.append(row_data)
    
    # 填充实际数据
    data_count = 0
    status_summary = {}
    
    for item in data_list:
        location = item.get("location")
        if not location:
            continue
        
        try:
            # 解析位置：格式 "行,列,层"
            parts = location.split(",")
            if len(parts) != 3:
                st.warning(f"⚠️ 位置格式错误: {location}")
                continue
            
            row, col, layer = int(parts[0]), int(parts[1]), int(parts[2])
            
            # 只处理目标层的数据
            if layer != target_layer:
                continue
            
            # 检查坐标是否在有效范围内
            if not (1 <= row <= max_row and 1 <= col <= max_col):
                st.warning(f"⚠️ 坐标超出范围: {location}")
                continue
            
            # 获取状态信息
            status = item.get("status", "unavailable")
            pallet_id = item.get("pallet_id")
            item_id = item.get("id")
            
            # 更新表格数据
            grid_data[row-1][col-1] = {
                "location": location,
                "row": row,
                "col": col,
                "layer": layer,
                "status": status,
                "pallet_id": pallet_id,
                "id": item_id,
                "color": STATUS_COLORS.get(status, STATUS_COLORS["unavailable"])
            }
            
            data_count += 1
            status_summary[status] = status_summary.get(status, 0) + 1
            
        except (ValueError, IndexError) as e:
            st.warning(f"⚠️ 解析位置失败: {location} - {str(e)}")
            continue
    
    return grid_data, data_count, status_summary

def create_table_html(grid_data, floor_id):
    """
    生成可视化HTML表格
    """
    html = f"""
    <style>
    .location-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: 'Microsoft YaHei', Arial, sans-serif;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}
    .location-table th, .location-table td {{
        border: 2px solid #2E8B57;
        padding: 12px;
        text-align: center;
        font-size: 13px;
    }}
    .location-table th {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        font-size: 14px;
    }}
    .location-table td {{
        min-height: 70px;
        vertical-align: middle;
        transition: all 0.3s ease;
    }}
    .location-table td:hover {{
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10;
    }}
    .row-header {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
    }}
    .cell-content {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 50px;
    }}
    .cell-location {{
        font-weight: bold;
        font-size: 12px;
        margin-bottom: 4px;
    }}
    .cell-pallet {{
        font-size: 11px;
        color: #333;
        background-color: rgba(255,255,255,0.7);
        padding: 2px 6px;
        border-radius: 3px;
        margin-top: 4px;
    }}
    .cell-status {{
        font-size: 10px;
        color: #666;
        margin-top: 2px;
    }}
    </style>
    <table class="location-table">
    <tr>
        <th>第{floor_id}层</th>
        <th>第1列</th>
        <th>第2列</th>
        <th>第3列</th>
        <th>第4列</th>
        <th>第5列</th>
        <th>第6列</th>
        <th>第7列</th>
    </tr>
    """
    
    for i, row_data in enumerate(grid_data):
        html += f'<tr><td class="row-header">第{i+1}行</td>'
        for cell in row_data:
            # 构建单元格内容
            cell_html = f'<div class="cell-content">'
            cell_html += f'<div class="cell-location">({cell["row"]},{cell["col"]})</div>'
            
            if cell["pallet_id"]:
                cell_html += f'<div class="cell-pallet">🎯 {cell["pallet_id"]}</div>'
            
            if cell["status"] != "unavailable":
                status_text = STATUS_TEXT.get(cell["status"], cell["status"])
                cell_html += f'<div class="cell-status">{status_text}</div>'
            
            cell_html += '</div>'
            
            html += f'<td style="background-color: {cell["color"]};">{cell_html}</td>'
        html += '</tr>'
    
    html += '</table>'
    return html

def create_legend():
    """
    创建状态图例
    """
    st.subheader("📊 状态图例")
    
    # 动态生成图例（排除unavailable）
    active_statuses = {k: v for k, v in STATUS_COLORS.items() if k != "unavailable"}
    cols = st.columns(len(active_statuses))
    
    for i, (status, color) in enumerate(active_statuses.items()):
        with cols[i]:
            st.markdown(
                f'<div style="background-color: {color}; '
                f'padding: 12px; border: 2px solid #2E8B57; '
                f'text-align: center; border-radius: 8px; '
                f'box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
                f'<b>{STATUS_TEXT.get(status, status)}</b></div>', 
                unsafe_allow_html=True
            )

def fetch_floor_data(floor_id, api_url):
    """
    根据楼层ID获取数据
    """
    if floor_id not in FLOOR_ID_MAPPING:
        return None, "无效的楼层ID"
    
    floor_range = FLOOR_ID_MAPPING[floor_id]
    body = {
        "start_id": floor_range["start_id"],
        "end_id": floor_range["end_id"]
    }
    
    try:
        resp = requests.post(api_url, json=body, timeout=10)
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 404:
                return None, result.get("message", "数据未找到")
            elif result.get("code") == 500:
                return None, f"{result.get('message', '服务器错误')}, {result.get('data', '')}"
            else:
                return result.get("data", []), None
        else:
            return None, f"请求失败，状态码：{resp.status_code}"
    
    except requests.exceptions.RequestException as e:
        return None, f"网络请求失败：{str(e)}"
    except Exception as e:
        return None, f"处理失败：{str(e)}"

def location_display():
    st.markdown("---")
    
    # 侧边栏设置
    st.sidebar.header("⚙️ 系统设置")
    
    # API配置
    api_url = st.sidebar.text_input(
        "API地址", 
        value="http://localhost:8765/api/v2/wcs/read/floor_info",
        help="楼层信息查询API"
    )
    
    # 楼层选择
    floor_id = st.sidebar.selectbox(
        "选择楼层", 
        list(range(1, 5)), 
        format_func=lambda x: f"🏢 第{x}层"
    )
    
    # 显示楼层ID范围信息
    if floor_id in FLOOR_ID_MAPPING:
        floor_range = FLOOR_ID_MAPPING[floor_id]
        st.sidebar.info(
            f"📍 第{floor_id}层\n\n"
            f"ID范围：{floor_range['start_id']} - {floor_range['end_id']}\n\n"
            f"共 {floor_range['end_id'] - floor_range['start_id'] + 1} 个库位"
        )
    
    st.sidebar.markdown("---")
    
    # 显示选项
    st.sidebar.subheader("📋 显示选项")
    show_table = st.sidebar.checkbox("显示详细数据表", value=True)
    show_raw_data = st.sidebar.checkbox("显示原始JSON", value=False)
    
    # 显示图例
    create_legend()
    st.markdown("---")
    
    # 查询按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        query_button = st.button(
            f"🔍 查询第{floor_id}层库位信息", 
            type="primary", 
            use_container_width=True
        )
    
    if query_button:
        with st.spinner(f"⏳ 正在查询第{floor_id}层数据..."):
            data, error = fetch_floor_data(floor_id, api_url)
            
            if error:
                st.error(f"❌ 查询失败：{error}")
            elif data:
                st.success(f"✅ 查询成功！共获取 {len(data)} 条记录")
                
                # 解析并显示可视化表格
                try:
                    grid_data, data_count, status_summary = parse_location_data(data, target_layer=floor_id)
                    table_html = create_table_html(grid_data, floor_id)
                    
                    st.subheader(f"🗺️ 第{floor_id}层库位分布图")
                    st.info(f"✨ 已映射 {data_count} 个库位到表格中")
                    st.markdown(table_html, unsafe_allow_html=True)
                    
                    # 显示统计信息
                    st.markdown("---")
                    st.subheader("📈 统计信息")
                    
                    # 计算所有状态（包括无数据的格子）
                    # total_cells = 8 * 7  # 8行 x 7列
                    # occupied_cells = data_count
                    total_cells = 32
                    # 计算cells中，status为occupied的数量
                    occupied_cells = sum(1 for item in data if item['status'] == 'occupied')
                    empty_cells = total_cells - occupied_cells
                    
                    # 显示统计指标
                    metric_cols = st.columns(4)
                    with metric_cols[0]:
                        st.metric("总库位数", total_cells)
                    with metric_cols[1]:
                        st.metric("已使用", occupied_cells)
                    with metric_cols[2]:
                        st.metric("未使用", empty_cells)
                    with metric_cols[3]:
                        utilization = (occupied_cells / total_cells * 100) if total_cells > 0 else 0
                        st.metric("使用率", f"{utilization:.1f}%")
                    
                    # 按状态分类统计
                    if status_summary:
                        st.markdown("##### 状态分布")
                        status_cols = st.columns(len(status_summary))
                        for i, (status, count) in enumerate(status_summary.items()):
                            with status_cols[i]:
                                st.metric(
                                    label=STATUS_TEXT.get(status, status),
                                    value=count,
                                    delta=f"{count/data_count*100:.1f}%" if data_count > 0 else "0%"
                                )
                    
                except Exception as e:
                    st.error(f"❌ 处理数据时出错：{str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                
                # 显示详细数据表
                if show_table and data:
                    with st.expander(f"📋 第{floor_id}层库位详细信息", expanded=False):
                        table_data = []
                        for item in data:
                            table_data.append({
                                'ID': item.get('id'),
                                '库位坐标': item.get('location'),
                                '托盘ID': item.get('pallet_id') if item.get('pallet_id') else '-',
                                '状态': STATUS_TEXT.get(item.get('status'), item.get('status')),
                                '更新时间': item.get('update_time', '-')
                            })
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True, height=400)
                
                # 显示原始JSON
                if show_raw_data:
                    with st.expander("🔍 原始JSON数据", expanded=False):
                        st.json(data)
            else:
                st.warning("⚠️ 没有找到库位信息")
    
    # 底部按钮
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 刷新页面", use_container_width=True):
        st.rerun()
    
    # 显示时间戳
    st.sidebar.markdown("---")
    st.sidebar.caption(f"⏰ 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 帮助信息
    with st.sidebar.expander("ℹ️ 使用说明"):
        st.markdown("""
        **操作步骤：**
        1. 选择要查询的楼层
        2. 点击"查询"按钮
        3. 查看可视化表格和统计信息
        
        **表格说明：**
        - 不同颜色代表不同状态
        - 显示库位坐标 (行,列)
        - 显示托盘ID（如有）
        - 鼠标悬停可放大查看
        """)

location_display()