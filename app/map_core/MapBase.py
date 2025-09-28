# /map_core/MapBase.py
# 用于地图的构建
import networkx as nx
import matplotlib.pyplot as plt

class MapBase:
    """
    地图基类，提供地图的基本功能
    """
    def __init__(self):
        import os
        import json
        # 动态获取地图配置文件路径 'map_core/data/map_config.json'
        config_path = os.path.join(os.path.dirname(__file__), 'data', 'map_config copy.json')
        # print("Config path: ",config_path)
        # 读取地图配置文件
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                map_info = json.load(f)
            # 获取节点和边的定义
            self.nodes_form = map_info["nodes"]
            self.edges_form = map_info["edges"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(f"错误: 无法读取地图配置文件 {config_path} - {e}")
        
    def create_map(self):
        """
        创建地图并返回图对象和坐标映射
        """
        # 创建一个无向图
        G = nx.Graph()
        G.add_nodes_from(self.nodes_form)
        G.add_edges_from(self.edges_form)

        # 使用节点名称解析坐标
        # 使用更安全的方式解析节点名称中的坐标
        self.pos = {
            node: self._parse_node_coords(node)
            for node in G.nodes()
        }
        return G, self.pos
    
    def map_info(self):
        """
        获取地图信息
        节点数量、边数量、节点列表和边列表
        """
        G, _ = self.create_map()
        # 获取图的属性
        nodes = G.nodes()
        edges = G.edges()
        num_of_nodes = G.number_of_nodes()
        num_of_edges = G.number_of_edges()

        # 返回节点数量、边数量、节点列表和边列表
        return num_of_nodes, num_of_edges, nodes, edges
    
    def _parse_node_coords(self, node):
        """
        解析节点名称中的坐标
        :param node: 节点名称
        :return: 坐标列表
        """
        try:
            coords = [int(coord) for coord in node.strip().split(',')]
            if len(coords) < 2:
                raise ValueError(f"节点 {node} 的坐标格式错误，至少需要两个坐标值")
            # 返回前两个坐标值作为位置
            return coords[:2]
        except ValueError as e:
            raise ValueError(f"节点 {node} 的坐标格式错误 - {e}")

    def draw_map(self, G, pos):
        """
        绘制地图
        :param G: 图对象
        :param pos: 节点位置字典
        """
        plt.figure(figsize=(10, 8))
        nx.draw(G, pos, with_labels=True, node_size=800, node_color='lightblue', font_size=14, font_color='black', edge_color='gray')
        plt.title("Map Visualization")
        plt.show()

# 测试样例
if __name__ == "__main__":
    # 创建地图基类实例
    map_base = MapBase()

    # 获取地图信息
    num_of_nodes, num_of_edges, nodes, edges = map_base.map_info()
    print("地图信息：")  # 输出地图信息
    print(f"节点数量：{num_of_nodes}")
    print(f"边数量：{num_of_edges}")
    print("节点列表：", list(nodes)[:2])    # 输出前两个节点
    print("边列表：", list(edges)[:2])  # 输出前两个边

    # 创建地图并绘制
    G, pos = map_base.create_map()
    map_base.draw_map(G, pos)
    
    # 测试节点坐标解析
    location = "2,7,1"
    print(f"节点({location})的坐标：", pos.get(location, "节点不存在"))