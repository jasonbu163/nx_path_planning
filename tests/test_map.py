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
    source = "1,1,1"
    target = "6,3,1"
    
    # found_path = my_path.find_path(source, target)
    # print(f"路径: {found_path}")
    
    # cuted_path = my_path.cut_path(found_path)
    # print(f"切分之后的路径: {cuted_path}")

    # task_path = my_path.task_path(cuted_path)
    # print(f"任务路径: {task_path}")

    # task_segments = my_path.generate_point_list(task_path)
    # print(f"任务分段: {task_segments}")

    segments = my_path.build_segments(source, target)
    print(f"找到的路径分段:{segments}")

    task_segments = my_path.build_pick_task(source, target)
    print(f"取货任务分段: {task_segments}")


    # my_path.draw_path(found_path, G, pos)

    # 模拟节点状态，后续会使用sqlite来存储和更新节点状态
    # 这里的节点状态可以是从数据库中查询得到的
    # node_status = {
    #     "1,2,4": "occupied",
    #     "2,2,4": "occupied",
    #     "3,2,4": "free",
    #     "4,2,4": "free",
    #     "4,3,4": "free",
    #     "4,4,4": "free",
    #     "4,5,4": "free",
    #     "4,6,4": "free",
    #     "4,7,4": "free",
    #     "5,7,4": "free",
    #     "6,7,4": "free",
    #     "7,7,4": "free",
    #     "5,2,4": "free",
    #     "1,1,4": "free",
    #     "8,7,4": "free"
    #     }

    # 检查路径上的阻塞点
    # blocking_nodes = [node for node in found_path[1:-1] if node_status.get(node) == "occupied"]

    # from queue import PriorityQueue
    # if blocking_nodes:
    #     print(f"路径上的阻塞点: {blocking_nodes}")

if __name__ == "__main__":
    main()
