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
        
        path_cut_list = []
        current_cut = [path[0]]
        prev_dir = None  # 记录前一段移动方向('x'/'y'/'none')
        
        for i in range(1, len(path)):
            x0, y0 = map(int, path[i-1].split(',')[:2])
            x1, y1 = map(int, path[i].split(',')[:2])
            
            # 判断当前移动方向
            if x0 == x1:
                curr_dir = 'y'
            elif y0 == y1:
                curr_dir = 'x'
            else:
                curr_dir = 'diagonal'  # 斜线情况
            
            # 当方向改变时切割
            if prev_dir and curr_dir != prev_dir and prev_dir != 'diagonal':
                path_cut_list.append(current_cut)
                current_cut = [path[i-1]]  # 保留交界点
            
            current_cut.append(path[i])
            prev_dir = curr_dir
        
        if current_cut:
            path_cut_list.append(current_cut)
        return path_cut_list
    
if __name__ == "__main__":
    # 创建路径自定义类实例
    path_custom = PathCustom()

    # 绘制地图和路径
    source = "1,3,1"
    target = "8,7,1"
    path = path_custom.find_shortest_path(source, target)

    # 路径切割
    cut_path = path_custom.cut_path(path)
    print("剪切后的路径:", cut_path)

    # 绘制地图和路径
    path_custom.draw_path(path, path_custom.G, path_custom.pos)