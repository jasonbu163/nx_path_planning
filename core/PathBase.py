# /core/PathBase.py
# 用于路径规划
import networkx as nx
import matplotlib.pyplot as plt
from .MapBase import MapBase

class PathBase:
    """
    路径基类，提供路径规划的基本功能
    """

    def __init__(self):
        # 创建地图
        self.map_base = MapBase()
        self.G, self.pos = self.map_base.create_map()

    def draw_path(self, path=None, G=None, pos=None):
        """
        绘制地图和路径
        通过 NetworkX 和 Matplotlib 绘制地图
        """
        plt.figure(figsize=(10, 10))
        # 在draw命令后添加
        path = nx.shortest_path(G, source=path[0], target=path[-1]) if path else None
        # 高亮显示路径
        path_edges = list(zip(path, path[1:]))  # 获取路径的边列表 (path为路径列表 path[1:]为路径列表的后半部分)
        nx.draw_networkx_edges(G, pos, edgelist=path_edges, width=2, edge_color="r")
        nx.draw(
            self.G,
            pos=self.pos,
            with_labels=True,
            node_size=500,
            node_color="lightblue",
            font_size=10,
        )
        plt.title("Map with Shortest Path")
        plt.show()

    def find_shortest_path(self, source, target):
        """
        查找最短路径
        :param source: 起点
        :param target: 终点
        :return: 最短路径列表
        """
        try:
            path = nx.shortest_path(self.G, source=source, target=target)
            return path
        except nx.NetworkXNoPath:
            print(f"从 {source} 到 {target} 没有可达路径")
            return None

if __name__ == "__main__":
    # 创建路径基类实例
    pathbase = PathBase()
    # print(pathbase.G.number_of_edges())
    # print(pathbase.G.number_of_nodes())

    # 绘制地图和路径
    source = "1,3,1"
    target = "8,7,1"
    path = pathbase.find_shortest_path(source, target)
    print("最短路径:", path)  # 输出: ['1,2,1', '1,3,1', '2,3,1', '2,4,1', '2,5,1']
    print("最短路径长度:", len(path)-1)  # 输出: 12
    source2target = [path[0], path[-1]]
    print("起点和终点:", source2target)  # 输出: ['1,2,1', '2,5,1']
    G = pathbase.G  # 获取图对象
    pos = pathbase.pos  # 获取节点位置
    print("连通性检查:")
    print(f"{source} 和 {target} 是否连通:", nx.has_path(G, source, target))  # 输出: True
    print("最短路径数量:", len(list(nx.all_shortest_paths(G, source, target))))  # 输出: 1

    # 绘制地图和路径
    pathbase.draw_path(path, G, pos)