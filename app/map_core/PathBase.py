# /core/PathBase.py
import logging
logger = logging.getLogger(__name__)

# 用于路径规划
import networkx as nx
import matplotlib.pyplot as plt
from .MapBase import MapBase

class PathBase:
    """路径基类，提供路径规划的基本功能。"""

    def __init__(self):
        # 创建地图
        self.map_base = MapBase()
        self.G, self.pos = self.map_base.create_map()

    def draw_path(self, PATH):
        """[绘制地图和路径] 通过 NetworkX 和 Matplotlib 绘制地图。"""
        plt.figure(figsize=(10, 10))
        # 高亮显示路径
        path_edges = list(zip(PATH, PATH[1:]))  # 获取路径的边列表 (path为路径列表 path[1:]为路径列表的后半部分)
        print(f"path_edges - {path_edges}")
        nx.draw_networkx_edges(self.G, self.pos, edgelist=path_edges, width=2, edge_color="r")
        nx.draw(
            G=self.G,
            pos=self.pos,
            with_labels=True,
            node_size=500,
            node_color="lightblue",
            font_size=10,
        )
        plt.title("Map with Shortest Path")
        plt.show()

    def find_shortest_path(self, SOURCE, TARGET):
        """查找最短路径

        Args:
            SOURCE: 起点
            TARGET: 终点

        Returns:
            PATH: 最短路径列表
        """
        # 检查节点是否在图中
        if SOURCE not in self.G.nodes():
            raise ValueError(f"起点 {SOURCE} 不在地图节点中")
        
        if TARGET not in self.G.nodes():
            raise ValueError(f"终点 {TARGET} 不在地图节点中")
            
        try:
            path = nx.shortest_path(self.G, source=SOURCE, target=TARGET)
            return path
        except nx.NetworkXNoPath:
            logger.warning(f"从 {SOURCE} 到 {TARGET} 没有可达路径")
            return None
        except nx.NodeNotFound as e:
            logger.warning(f"节点未找到: {e}")
            return None
        except Exception as e:
            logger.warning(f"计算路径时发生未知错误: {e}")
            return None

if __name__ == "__main__":
    # 创建路径基类实例
    pathbase = PathBase()
    # print(pathbase.G.number_of_edges())
    # print(pathbase.G.number_of_nodes())

    # 绘制地图和路径
    source = "1,3,1"
    target = "5,5,1"
    
    path = pathbase.find_shortest_path(source, target)
    if path is None:
        logger.warning("没有找到路径")
        exit()
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
    pathbase.draw_path(path)