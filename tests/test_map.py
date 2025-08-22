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
        
    # 设置起点和终点
    source = "5,3,1"
    target = "2,1,1"
    
    # found_path = my_path.find_path(source, target)
    # print(f"路径: {found_path}")
    
    # cuted_path = my_path.cut_path(found_path)
    # print(f"切分之后的路径: {cuted_path}")

    # task_path = my_path.task_path(cuted_path)
    # print(f"任务路径: {task_path}")

    # task_segments = my_path.generate_point_list(task_path)
    # print(f"任务分段: {task_segments}")

    # my_path.draw_path(found_path)

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

    blocking_nodes = my_path.find_blocking_nodes(source, target, node_status)
    if blocking_nodes:
        print(f"路径上的阻塞点: {blocking_nodes}")
    free_nodes_excluding_path = my_path.find_free_nodes_excluding_path(source, target, node_status)
    print(f"不在路径上的空闲点: {free_nodes_excluding_path}")

    if blocking_nodes is None:
        print("没有找到可访问的点")
        return None
    
        
    nearest_highway_node = my_path.find_nearest_highway_node(blocking_nodes)
    print(f"最近的高速公路点: {nearest_highway_node}")
    
    short_free_node = my_path.find_nearest_free_node(
        source,
        target,
        nearest_highway_node,
        node_status
        )
    print(f"{nearest_highway_node} 最接近空闲点: {short_free_node}")
    
    if short_free_node is None:
        print("无法找到最近空闲点")
        return
    
    path_1 = my_path.find_path(nearest_highway_node, short_free_node)
    print(f"从{nearest_highway_node}到{short_free_node}的最短路径: {path_1}")
    
    if nearest_highway_node is None:
        print("无法找到最接近高速公路的点")
        return
    
    path_1_blocking_node = my_path.find_blocking_nodes(
        nearest_highway_node,
        short_free_node,
        node_status)
    print(f"路径1的阻塞点: {path_1_blocking_node}")

    # segments = my_path.build_segments(source, target)
    # print(f"找到的路径分段:{segments}")

    # task_segments = my_path.build_pick_task(source, target)
    # print(f"取货任务分段: {task_segments}")

if __name__ == "__main__":
    main()
