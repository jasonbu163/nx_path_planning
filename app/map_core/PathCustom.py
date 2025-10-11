# /core/PathCustom.py
import logging
logger = logging.getLogger(__name__)

# 用于自定义路径规划
import networkx as nx

from .PathBase import PathBase

class PathCustom(PathBase):
    """[自定义路径类] 继承自PathBase, 可以添加更多自定义方法和属性。"""
    def __init__(self):
        super().__init__()  # 调用父类的初始化方法

    # 获取坐标x轴y轴z轴
    def get_point(self, point: str):
        """
        获取坐标x轴y轴z轴

        :param point: 坐标，例如："6,3,1"

        :return: x轴y轴z轴
        """
        x, y, z = map(int, point.split(","))
        return x, y, z
    
    def cut_path(self, path):
        """剪切路径为按X/Y轴连续的子路径。

        1. 当移动方向从X轴变为Y轴或反之，进行切割
        2. 支持连续X/Y轴移动
        3. 保留完整路径连接性

        剪切路径，下面给出三个例子
        1. 起点和终点为['1,2,1', '2,5,1']时，
            则，路径为
                ['1,2,1', '2,2,1', '3,2,1', '4,2,1', '4,3,1', '4,4,1', '4,5,1', '4,6,1', '4,7,1', '5,7,1', '6,7,1', '7,7,1', '8,7,1']
            那么，切割为
                [['1,2,1', '2,2,1', '3,2,1', '4,2,1'],
                ['4,2,1', '4,3,1', '4,4,1', '4,5,1', '4,6,1', '4,7,1'],
                ['4,7,1', '5,7,1', '6,7,1', '7,7,1', '8,7,1']]
        2. 起点和终点为['1,2,1', '4,5,1']时，
            则，路径为
                ['1,2,1', '2,2,1', '3,2,1', '4,2,1', '4,3,1', '4,4,1', '4,5,1']
            那么，切割为
                [['1,2,1', '2,2,1', '3,2,1', '4,2,1'],
                ['4,2,1', '4,3,1', '4,4,1', '4,5,1']]
        3. 起点和终点为['4,2,1', '4,6,1']时， #这种情况，就是x或者y轴上连续的情况
            则，路径为
                ['4,2,1', '4,3,1', '4,4,1', '4,5,1', '4,6,1']
            那么，切割为
                [['4,2,1', '4,3,1', '4,4,1', '4,5,1', '4,6,1']]

        Args:
            path: 路径列表
        
        Returns:
            list: 剪切后的路径列表
        """
        if not path:
            return []
        if len(path) == 1:
            return [path] # 只有一个点，直接返回
        
        path_cut_list = []
        current_cut = [path[0]] # 起始点总是第一个子路径的开头
        prev_dir = self.get_direction(path[0],path[1])  # 记录前一段移动方向('x'/'y'/'none')
        
        for i in range(1, len(path)):
            curr_dir = self.get_direction(path[i-1],path[i])
            
            # 当方向改变时切割（保留交界点）
            if i > 1 and curr_dir != prev_dir and prev_dir != 'diagonal':
                path_cut_list.append(current_cut)
                current_cut = [path[i-1]]  # 保留交界点
            current_cut.append(path[i])

            # 当方向改变时切割（不保留交界点）
            # if curr_dir != prev_dir:
            #     path_cut_list.append(current_cut)
            #     current_cut = [path[i]]  # 不保留交界点
            # else:
            #     current_cut.append(path[i])

            prev_dir = curr_dir
        
        if current_cut:
            path_cut_list.append(current_cut)
        return path_cut_list
    
    def get_direction(self, point1, point2):
        """获取两点间的移动方向

        Args:
            point1: 起点坐标
            point2: 终点坐标

        Returns:
            str: 'x' (水平移动), 'y' (垂直移动), 'diagonal' (斜线移动)
        """
        x0, y0 = map(int, point1.split(',')[:2])
        x1, y1 = map(int, point2.split(',')[:2])
        
        if x0 == x1:
            return 'y'
        elif y0 == y1:
            return 'x'
        return 'diagonal'
    
    def find_path(self, source, target):
        """路径生成

        Args:
            source: 起点
            target: 终点
        """
        found_path = self.find_shortest_path(source, target)
        if found_path is None:
            print("无法找到路径")
            return
        # 计算列表长度
        path_length = len(found_path)
        print(f"路径长度: {path_length}")
        # 输出路径
        if path_length > 1:
            return found_path
        elif path_length == 1:
            return False, "起点和终点相同，无需路径规划"
        elif found_path is None:
            return False, "未找到路径"
        else:
            return False, "路径规划失败"
    
    def find_and_cut_path(self, source, target):
        path = self.find_path(source, target)
        cut_path = self.cut_path(path)
        return {
            "source": source,
            "target": target,
            "path": path,
            "cut_path": cut_path
        }
    
    def task_path(self, cuted_path):
        task_path = []
        for path in cuted_path:
            x1, y1, z1 = self.get_point(path[0])
            x2, y2, z2 = self.get_point(path[-1])
            point = [(x1, y1, z1), (x2, y2, z2)]
            task_path.append(point)
        # print(f"任务路径: {task_path}")
        return task_path
    
    def generate_point_list(self, segments):
        if not segments:
            return []
        
        # 起点（第一个元组的第一个点）
        result = [(*segments[0][0], 0)]
        
        for i, seg in enumerate(segments):
            p1, p2 = seg
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]  # Z轴暂不使用

            # 根据移动方向确定动作
            if i == len(segments) - 1:  # 终点强制为0
                action = 0
            else:
                if dx != 0 and dy == 0:  # X轴移动
                    action = 5
                elif dy != 0 and dx == 0:  # Y轴移动
                    action = 6
                else:  # 其他情况
                    action = 0
                    
            # 添加当前元组的第二个点
            result.append((*p2, action))
        
        return result
    

    def build_segments(self, source: str, target: str) -> list:
        """生成移动路径

        Args:
            source: 起点坐标 如，source = "1,1,1"
            target: 终点坐标 如，target = "1,3,1"
        """
        
        found_path = self.find_path(source, target)
        if found_path is None:
            print("未找到路径")
            return [False, "未找到路径"]
        # print(f"找到的路径: {found_path}")

        cuted_path = self.cut_path(found_path)
        # print(f"切分之后的路径: {cuted_path}")

        task_path = self.task_path(cuted_path)
        # print(f"任务路径: {task_path}")

        task_segments = self.generate_point_list(task_path)
        # print(f"任务分段: {task_segments}")

        return task_segments
    
    def add_pick_drop_actions(self, point_list):
        """在路径列表的起点和终点添加货物操作动作。

        Args:
            point_list: generate_point_list()生成的路径列表
        
        Returns:
            修改后的路径列表（起点动作=1提起，终点动作=2放下）
        """
        # 确保路径至少有两个点
        if len(point_list) < 2:
            return point_list
        
        # 创建列表副本防止修改原数据
        new_list = [tuple(point) for point in point_list]
        
        # 修改起点动作（索引0）为1（提起货物）
        new_list[0] = tuple(new_list[0][:3]) + (1,)
        
        # 修改终点动作（索引-1）为2（放下货物）
        new_list[-1] = tuple(new_list[-1][:3]) + (2,)
        
        return new_list
    
    def build_pick_task(self, source: str, target: str):
        """生成取货/放货路径

        Args:
            source: 起点坐标 如，source = "1,1,1"
            target: 终点坐标 如，target = "1,3,1"
        """
        
        found_path = self.find_path(source, target)
        if found_path is None:
            print("未找到路径")
            return
        # print(f"找到的路径: {found_path}")

        cuted_path = self.cut_path(found_path)
        # print(f"切分之后的路径: {cuted_path}")

        task_path = self.task_path(cuted_path)
        # print(f"任务路径: {task_path}")

        task_segments = self.generate_point_list(task_path)
        # print(f"任务分段: {task_segments}")

        pick_task_segments = self.add_pick_drop_actions(task_segments)
        # print(f"取货放货分段: {task_segments}")

        return pick_task_segments
    
    def find_blocking_nodes(self, SOURCE: str, TARGET: str, NODE_STATUS):
        """检查路径上的阻塞点。

        Args:
            SOURCE: 起点
            TARGET: 终点
            NODE_STATUS: 节点状态字典

        Returns:
            list:阻塞点列表
        """
        found_path = self.find_path(SOURCE, TARGET)
        if found_path is None:
            print("未找到路径")
            return [False, "未找到路径"]
        blocking_nodes = [node for node in found_path[1:-1] if NODE_STATUS.get(node) == "occupied"]
        return blocking_nodes

    def find_free_nodes_excluding_path(self,  SOURCE: str, TARGET: str, NODE_STATUS):
        """检查非路径上的空闲点。

        Args:
            SOURCE: 起点
            TARGET: 终点
            NODE_STATUS: 节点状态字典

        Returns:
            list: 不在路径上的空闲点列表
        """
        found_path = self.find_path(SOURCE, TARGET)
        if found_path is None:
            print("未找到路径")
            return [False, "未找到路径"]
        free_nodes_excluding_path = [node for node, status in NODE_STATUS.items()
                                    if status == "free" and node not in found_path]
        return free_nodes_excluding_path

    def find_nearest_free_node(self, TASK_START, TASK_END, MOVE_POINT, NODE_STATUS):
        """使用NetworkX最短路径算法找到离指定点最近的值为'free'且不在路径中的点。
        
        Args:
            G: 图对象
            TASK_START: 任务起点
            TASK_END: 任务终点
            MOVE_POINT: 需要移动的阻碍点
            NODE_STATUS: 节点状态字典

        Returns:
            最近的free点
        """
        
        # 检查指定点是否有效
        if MOVE_POINT not in self.G.nodes():
            raise ValueError(f"指定点 {MOVE_POINT} 不在图中")
        
        # 获取所有值为'free'且不在路径中的点
        free_nodes_excluding_path = self.find_free_nodes_excluding_path(TASK_START, TASK_END, NODE_STATUS)
        
        # 如果没有可用的free点，返回None
        if not free_nodes_excluding_path:
            return None
        
        # 计算距离并找到最近的点
        nearest_node = None
        min_distance = float('inf')
        
        for node in free_nodes_excluding_path:
            try:
                # 使用NetworkX的最短路径算法计算距离
                path = nx.shortest_path(self.G, MOVE_POINT, node)
                distance = len(path) - 1  # 路径长度为节点数减1
                
                # 检查路径上是否有阻塞点(除了起点和终点)
                blocking_nodes = [n for n in path[1:-1] if NODE_STATUS.get(n) == "occupied"]
                
                # 如果路径上有阻塞点，则跳过该节点
                if blocking_nodes:
                    continue

                # 更新最近的点
                if distance < min_distance:
                    min_distance = distance
                    nearest_node = node
            except nx.NetworkXNoPath:
                # 如果没有路径，跳过该节点
                continue
            except Exception:
                # 如果其他异常，也跳过该节点
                continue
        
        return nearest_node
    
    def find_nearest_highway_node(self, BLOCKING_NODES):
        """获取最接近的highway节点。

        Args:
            BLOCKING_NODES: 节点列表
        """
        if not BLOCKING_NODES:
            logger.warning("没有找到可访问的点")
            return None
        elif len(BLOCKING_NODES) == 1:
            return BLOCKING_NODES[0]
        else:
            x_1, y_1, z_1 = self.get_point(BLOCKING_NODES[0])
            closest = BLOCKING_NODES[0]
            min_diff = abs(x_1 - 4)
            for node in BLOCKING_NODES[1:]:
                x_2, y_2, z_2 = self.get_point(node)
                diff = abs(x_2 - 4)
                if diff < min_diff:
                    min_diff = diff
                    closest = node
            return closest

    
if __name__ == "__main__":
    # 创建路径自定义类实例
    path_custom = PathCustom()

    # 绘制地图和路径
    source = "1,3,1"
    target = "8,7,1"
    path = path_custom.find_path(source, target)

    # 路径切割
    cut_path = path_custom.cut_path(path)
    print("剪切后的路径:", cut_path)

    # 绘制地图和路径
    # path_custom.draw_path(path)


#################################
# 注意⚠️ 临时删除了边 ["4,5,1", "5,5,1"],
# 删除的文件路径为 /map_core/data/map_config copy.json
# 因为临时需要禁用 5,5,1 这个点

#################################
