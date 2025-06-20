import networkx as nx
from core import PathCustom

def main():
    # 创建路径基类实例
    my_path = PathCustom()
    G = my_path.G
    pos = my_path.pos
    assert nx.is_tree(G), "图不是树结构，无法进行路径规划"

    # 设置起点和终点
    source = "1,2,1"
    target = "8,7,1"
    path = my_path.find_shortest_path(source, target)
    print(f"找到的路径: {path}")
    my_path.draw_path(path, G, pos)

    # 模拟节点状态，后续会使用sqlite来存储和更新节点状态
    # 这里的节点状态可以是从数据库中查询得到的
    node_status = {
        "1,2,1": "occupied",
        "2,2,1": "occupied",
        "3,2,1": "free",
        "4,2,1": "free",
        "4,3,1": "free",
        "4,4,1": "free",
        "4,5,1": "free",
        "4,6,1": "free",
        "4,7,1": "free",
        "5,7,1": "free",
        "6,7,1": "free",
        "7,7,1": "free",
        "5,2,1": "free",
        "1,1,1": "free",
        "8,7,1": "free"
        }

    # 检查路径上的阻塞点
    blocking_nodes = [node for node in path[1:-1] if node_status.get(node) == "occupied"]

    from queue import PriorityQueue
    if blocking_nodes:
        print(f"路径上的阻塞点: {blocking_nodes}")

if __name__ == "__main__":
    main()