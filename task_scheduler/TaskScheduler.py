# TaskScheduler.py
# 任务调度器模块
from map_core import PathCustom
from queue import PriorityQueue
import networkx as nx
import matplotlib.pyplot as plt

from models.base_model import LocationList
from models.base_enum import LocationStatus
from models.database import SessionLocal  # 导入SessionLocal

class TaskScheduler:
    def __init__(self):
        self.path_custom = PathCustom()
        self.G = self.path_custom.G
        self.pos = self.path_custom.pos
        self.task_queue = PriorityQueue()
        # 初始化节点状态
        self.node_status = {}
        self.db = SessionLocal()  # 使用SessionLocal创建会话
    def init_node_status(self):
        # 从数据库中获取节点状态
        locations =self.db.query(LocationList).all()
        # 数据库中，节点状态为highway的节点的location字段
        highway = [location.location for location in locations if location.status == LocationStatus.HIGHWAY]
        # 数据库中，节点状态为occupied的节点的location字段
        occupied = [location.location for location in locations if location.status == LocationStatus.OCCUPIED]
        # 数据库中，节点状态为free的节点的location字段
        free = [location.location for location in locations if location.status == LocationStatus.FREE]
        
        # 将上面状态加入到节点状态字典中
        for n in self.G.nodes:
            if n in highway:
                self.node_status[n] = 'highway'
            elif n in occupied:
                self.node_status[n] = 'occupied'
            elif n in free:
                self.node_status[n] = 'free'
            else:
                self.node_status[n] = 'unknown'

    # def add_task(self, source, target):
    #     path = self.path_custom.find_shortest_path(source, target)
    #     if not path:
    #         print(f"无法找到从 {source} 到 {target} 的路径")
    #         return
    #     # 检查路径上的阻塞点
    #     blocking_nodes = [node for node in path[1:-1] if self.node_status.get(node) == "occupied"]
    #     # 阻塞点优先级为数字越大优先级越高
    #     if blocking_nodes:
    #         priority = len(blocking_nodes)
    #         print(f"存在阻塞点，优先级为: {priority}")
    #         print(f"路径上的阻塞点: {blocking_nodes}")
    #         for node in blocking_nodes:
    #             print(f"等待节点 {node} 释放")
    #             # 找到非主路径上离源点最近的空闲节点
    #             free_nearby_nodes = self.free_nearby_nodes(node, path)
    #             self.task_queue.put((priority, node, free_nearby_nodes))
    #         self.task_queue.put((priority, source, target))
    #     else:
    #         self.task_queue.put((priority, source, target))

    # def free_nearby_nodes(self, point, path):
    #     """
    #     找到非主路径上离源点最近的空闲节点
    #     blcoking_point: 阻塞点
    #     path: 主路径
    #     """
    #     print(f"主路径: {path}")
    #     for node in path[1:-1]:
    #         if node != point and  self.node_status.get(node) == "free":
    #             return node
    
    # def visualize_graph(self, G, node_status):
    #     colors = ['green' if node_status.get(n) == 'free' else 'red' for n in G.nodes]
    #     plt.figure(figsize=(10, 10))
    #     nx.draw(self.G, self.pos, node_color=colors, with_labels=True, node_size=800)
    #     plt.show()

    # def process_tasks(self):
    #     while not self.task_queue.empty():
    #         priority, source, target = self.task_queue.get()
    #         print(f"处理任务: 从 {source} 到 {target}，优先级: {priority}")
    #         # 这里可以添加实际的任务处理逻辑
    #         # 例如，更新节点状态、绘制路径等
    #         # self.visualize_graph(self.G, self.node_status)
    
if __name__ == '__main__':
    ts = TaskScheduler()
    print(ts.node_status)
    # ts.add_task("1,2,1", "8,7,1")
    # ts.process_tasks()