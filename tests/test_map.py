# tests/test_map.py
# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from map_core import PathCustom

def main():
    # 创建路径基类实例
    my_path = PathCustom()
    G = my_path.G
    pos = my_path.pos
    assert nx.is_tree(G), "图不是树结构，无法进行路径规划"
    
    # 模拟节点状态，后续会使用sqlite来存储和更新节点状态
    # 这里的节点状态可以是从数据库中查询得到的
    node_status = {
        "1,1,1": "occupied",
        "2,1,1": "free",
        "3,1,1": "occupied",
        "4,1,1": "highway",
        "5,1,1": "free",

        "1,2,1": "free",
        "2,2,1": "occupied",
        "3,2,1": "occupied",
        "4,2,1": "highway",
        "5,2,1": "occupied",

        "1,3,1": "free",
        "2,3,1": "free",
        "3,3,1": "occupied",
        "4,3,1": "highway",
        "5,3,1": "free",

        "1,4,1": "free",
        "2,4,1": "free",
        "3,4,1": "occupied",
        "4,4,1": "highway",
        "5,4,1": "occupied",

        "1,5,1": "free",
        "2,5,1": "free",
        "3,5,1": "occupied",
        "4,5,1": "highway",
        "5,5,1": "occupied",

        "1,6,1": "free",
        "2,6,1": "free",
        "3,6,1": "occupied",
        "4,6,1": "highway",
        "5,6,1": "occupied",
        "6,6,1": "free",
        "7,6,1": "free",
        "8,6,1": "free",

        "1,7,1": "free",
        "2,7,1": "free",
        "3,7,1": "occupied",
        "4,7,1": "highway",
        "5,7,1": "occupied",
        "6,7,1": "free",
        "7,7,1": "occupied",
        "8,7,1": "free",
        }
    
    ####################################
    # 模拟出入库任务 "5,3,z" 是出入口
    ####################################
    # step 0 (初始化)
    # 穿梭车跨层等步骤

    # step 1 (穿梭车完成跨层后，剩下就是单层的移动任务)
    # 设置起点和终点
    car_location = "4,3,1"
    source = "3,1,1"
    target = "5,3,1"
    
    # step 2 判断阻塞节点，并处理阻塞
    # step 2.1 找到阻塞节点
    blocking_nodes = my_path.find_blocking_nodes(source, target, node_status)
    if blocking_nodes:
        print(f"路径上的阻塞点: {blocking_nodes}")
    
        # step 2.2 找到最接近 highway 的阻塞节点
        nearest_highway_node = my_path.find_nearest_highway_node(blocking_nodes)
        print(f"最近的高速公路点: {nearest_highway_node}")
        
        # step 2.3 找到最接近higihway阻塞点的free节点
        nearest_free_node = my_path.find_nearest_free_node(
            source,
            target,
            nearest_highway_node,
            node_status
            )
        print(f"{nearest_highway_node} 最接近空闲点: {nearest_free_node}")
    
        if nearest_free_node is None:
            print("无法找到最近空闲点")
            return
        
        if nearest_highway_node is None:
            print("无法找到最接近高速公路的点")
            return
        
        # step 2.4 检查处理阻塞点的路径是否存在阻塞
        blocking_node_1 = my_path.find_blocking_nodes(
            nearest_highway_node,
            nearest_free_node,
            node_status)
        if blocking_node_1:
            print(f"路径1存在阻塞点 {blocking_node_1}")
            return
        
        # step 2.5 穿梭车移动处理阻塞点
        segments = my_path.build_segments(car_location, nearest_highway_node)
        print(f"穿梭车前往货物处:{segments}")
        task_segments = my_path.build_pick_task(nearest_highway_node, nearest_free_node)
        print(f"取货到目标处: {task_segments}")
        # step 2.6 更新穿梭车坐标
        car_location = nearest_free_node

    segments = my_path.build_segments(car_location, source)
    print(f"穿梭车前往货物处:{segments}")
    source_x, source_y, source_z = my_path.get_point(source)
    if source_x != 5 and source_y != 3:
        node_status[source] = "free"
    task_segments = my_path.build_pick_task(source, target)
    print(f"取货到目标处: {task_segments}")
    target_x, target_y, target_z = my_path.get_point(target)
    if target_x != 5 and target_y != 3:
        node_status[source] = "occupied"

    car_location = target
    print(f"穿梭车最后位置: {car_location}")
    print(f"{node_status}")
if __name__ == "__main__":
    main()
