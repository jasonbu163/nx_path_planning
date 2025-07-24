# /core/PathCustom.py
# 用于自定义路径规划
import networkx as nx
import matplotlib.pyplot as plt
from .PathBase import PathBase

class PathCustom(PathBase):
    """
    自定义路径类，继承自 PathBase
    可以添加更多自定义方法和属性
    """
    def __init__(self):
        super().__init__()  # 调用父类的初始化方法

    # 获取坐标x轴y轴z轴
    def get_point(self, point):
        x, y, z = map(int, point.split(","))
        return x, y, z
    
    # 可以在这里添加更多自定义方法
    def cut_path(self, path):
        """
        剪切路径为按X/Y轴连续的子路径
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

            :param path: 路径列表
            :return: 剪切后的路径列表
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
        """
        获取两点间的移动方向
        :return: 'x' (水平移动), 'y' (垂直移动), 'diagonal' (斜线移动)
        """
        x0, y0 = map(int, point1.split(',')[:2])
        x1, y1 = map(int, point2.split(',')[:2])
        
        if x0 == x1:
            return 'y'
        elif y0 == y1:
            return 'x'
        return 'diagonal'
    
    def find_path(self, source, target):
        """
        找到的路径: 
        """
        found_path = self.find_shortest_path(source, target)
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
    

    def build_segments(self, source: str, target: str):
        """
        生成移动路径
        :param source: 起点坐标 如，source = "1,1,1"
        :param target: 终点坐标 如，target = "1,3,1"
        """
        
        found_path = self.find_path(source, target)
        if found_path is None:
            print("未找到路径")
            return False
        # print(f"找到的路径: {found_path}")

        cuted_path = self.cut_path(found_path)
        # print(f"切分之后的路径: {cuted_path}")

        task_path = self.task_path(cuted_path)
        # print(f"任务路径: {task_path}")

        task_segments = self.generate_point_list(task_path)
        # print(f"任务分段: {task_segments}")

        return task_segments
    
    def add_pick_drop_actions(self, point_list):
        """
        在路径列表的起点和终点添加货物操作动作
        :param point_list: generate_point_list()生成的路径列表
        :return: 修改后的路径列表（起点动作=1提起，终点动作=2放下）
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
        """
        生成取货/放货路径
        :param source: 起点坐标 如，source = "1,1,1"
        :param target: 终点坐标 如，target = "1,3,1"
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
    path_custom.draw_path(path, path_custom.G, path_custom.pos)


#################################
# 注意⚠️ 临时删除了边 ["4,5,1", "5,5,1"],
# 删除的文件路径为 /map_core/data/map_config copy.json
# 因为临时需要禁用 5,5,1 这个点

#################################
