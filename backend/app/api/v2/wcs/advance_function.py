# app/
from typing import Optional, List, Tuple, Union, Dict, Any
import logging
logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from app.map_core import PathCustom
from .services import LocationServices

class AdvanceFunction():
    """高级功能类"""
    
    def __init__(self):
        self.path_planner = PathCustom()
        self.location_service = LocationServices()

    def get_node_status(
        self,
        layer: int,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        """[获取阻塞节点] 用于获取阻塞节点。

        Args:
            layer: 楼层
            db: Session 数据库会话

        Returns:
            Tuple: [bool, 阻塞节点列表]
        """
        
        if layer == 1:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=124, end_id=164)
            if success:
                return True, location_info
            else:
                return False, f"{location_info}"
        elif layer == 2:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=83, end_id=123)
            if success:
                return True, location_info
            else:
                return False, f"{location_info}"
        elif layer == 3:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=42, end_id=82)
            if success:
                return True, location_info
            else:
                return False, f"{location_info}"
        elif layer == 4:
            success, location_info = self.location_service.get_location_by_start_to_end(db=db, start_id=1, end_id=41)
            if success:
                return True, location_info
            else:
                return False, f"{location_info}"
        else:
            logger.error("❌ 未找到符合条件的库位信息")
            return False, "❌ 未找到符合条件的库位信息"
            
        
    def get_block_node(
        self,
        start_location: str,
        end_location: str,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        """[获取阻塞节点] 用于获取阻塞节点。

        Args:
            start_location: 路径起点
            end_location: 路径终点
            db: Session 数据库会话

        Returns:
            Tuple: [bool, 阻塞节点列表]
        """
        
        # 获取当前层所有库位信息
        node_status = dict()

        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, start_location.split(',')))
        start_layer = start_loc[2]
        end_loc = list(map(int, end_location.split(',')))
        end_layer = end_loc[2]

        if start_layer != end_layer:
            return False, "❌ 起点与终点楼层不一致"

        success, result = self.get_node_status(start_layer, db)

        if success:
            all_nodes = result
        else:
            logger.error(f"❌ 库位信息获取失败: {result}")
            return False, "❌ 库位信息获取失败"


        # 检查all_locations是否为列表
        if isinstance(all_nodes, list):
            # 打印每个位置的详细信息
            for node in all_nodes:
                if node.status in ["lift", "highway"]:
                    continue
                node_status[node.location] = node.status
                
            print(f"[SYSTEM] 第 {start_layer} 层有 {len(node_status)} 个节点")
            # return [True, node_status]
            
            blocking_nodes = self.path_planner.find_blocking_nodes(start_location, end_location, node_status)
        
            return True, blocking_nodes
                
        else:
            logger.error("❌ 库位信息获取失败")
            return False, "❌ 库位信息获取失败"
            
    def find_block_node_nearest_highway(
        self,
        start_location: str,
        end_location: str,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        success, blocking_nodes = self.get_block_node(start_location, end_location, db)
        if success:
            # step 3.1: 计算靠近高速道阻塞点(按距离排序)
            # 找到最接近 highway 的阻塞节点
            do_blocking_nodes = []
            # 创建阻塞节点的副本，避免修改原始列表
            remaining_nodes = set(blocking_nodes)
            
            # 持续查找并移除最近的节点，直到没有剩余节点
            while remaining_nodes:
                # 找到最接近 highway 的阻塞节点
                nearest_highway_node = self.path_planner.find_nearest_highway_node(list(remaining_nodes))
                if nearest_highway_node:
                    do_blocking_nodes.append(nearest_highway_node)
                    # 从剩余节点中移除已找到的节点
                    remaining_nodes.discard(nearest_highway_node)
                else:
                    # 如果找不到最近节点，跳出循环避免无限循环
                    break
                    
            logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")
            return True, do_blocking_nodes
        else:
            return False, []
        
    def find_free_nodes_excluding_path(
        self,
        start_location: str,
        end_location: str,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        # 获取当前层所有库位信息
        node_status = dict()

        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, start_location.split(',')))
        start_layer = start_loc[2]
        end_loc = list(map(int, end_location.split(',')))
        end_layer = end_loc[2]

        if start_layer != end_layer:
            return False, "❌ 起点与终点楼层不一致"

        success, result = self.get_node_status(start_layer, db)

        if success:
            all_nodes = result
        else:
            logger.error(f"❌ 库位信息获取失败: {result}")
            return False, "❌ 库位信息获取失败"
        
        # 检查all_locations是否为列表
        if isinstance(all_nodes, list):
            # 打印每个位置的详细信息
            for node in all_nodes:
                if node.status in ["lift", "highway"]:
                    continue
                node_status[node.location] = node.status
                
            print(f"[SYSTEM] 第 {start_layer} 层有 {len(node_status)} 个节点")
            # return [True, node_status]
            
            free_nodes = self.path_planner.find_free_nodes_excluding_path(start_location, end_location, node_status)
        
            return True, free_nodes
                
        else:
            logger.error("❌ 库位信息获取失败")
            return False, "❌ 库位信息获取失败"
        
    def find_nearest_free_node(
        self,
        start_location: str,
        end_location: str,
        move_point: str,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        """查询路径阻塞点可移动的最近空闲点"""
        
        # 获取当前层所有库位信息
        node_status = dict()

        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, start_location.split(',')))
        start_layer = start_loc[2]
        end_loc = list(map(int, end_location.split(',')))
        end_layer = end_loc[2]

        if start_layer != end_layer:
            return False, "❌ 起点与终点楼层不一致"

        success, result = self.get_node_status(start_layer, db)

        if success:
            all_nodes = result
        else:
            logger.error(f"❌ 库位信息获取失败: {result}")
            return False, "❌ 库位信息获取失败"
        
        # 检查all_locations是否为列表
        if isinstance(all_nodes, list):
            # 打印每个位置的详细信息
            for node in all_nodes:
                if node.status in ["lift", "highway"]:
                    continue
                node_status[node.location] = node.status
                
            print(f"[SYSTEM] 第 {start_layer} 层有 {len(node_status)} 个节点")
            # return [True, node_status]

            node = self.path_planner.find_nearest_free_node(start_location, end_location, move_point, node_status)
            print(f"[SYSTEM] 离 {move_point} 最近的库位: {node}")
        
            return True, [node]
                
        else:
            logger.error("❌ 库位信息获取失败")
            return False, "❌ 库位信息获取失败"
        
    def find_farthest_free_node(
        self,
        start_location: str,
        end_location: str,
        move_point: str,
        db: Session
    ) -> Tuple[bool, Union[str, List]]:
        """查询路径阻塞点可移动的最远空闲点"""
        
        # 获取当前层所有库位信息
        node_status = dict()

        # 拆解位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        start_loc = list(map(int, start_location.split(',')))
        start_layer = start_loc[2]
        end_loc = list(map(int, end_location.split(',')))
        end_layer = end_loc[2]

        if start_layer != end_layer:
            return False, "❌ 起点与终点楼层不一致"

        success, result = self.get_node_status(start_layer, db)

        if success:
            all_nodes = result
        else:
            logger.error(f"❌ 库位信息获取失败: {result}")
            return False, "❌ 库位信息获取失败"
        
        # 检查all_locations是否为列表
        if isinstance(all_nodes, list):
            # 打印每个位置的详细信息
            for node in all_nodes:
                if node.status in ["lift", "highway"]:
                    continue
                node_status[node.location] = node.status
                
            print(f"[SYSTEM] 第 {start_layer} 层有 {len(node_status)} 个节点")
            # return [True, node_status]

            node = self.path_planner.find_farthest_free_node(start_location, end_location, move_point, node_status)
            print(f"[SYSTEM] 离 {move_point} 最远的库位: {node}")
        
            return True, [node]
                
        else:
            logger.error("❌ 库位信息获取失败")
            return False, "❌ 库位信息获取失败"
    

    # def do_task_inband_with_solve_blocking(
    #     self,
    #     task_no: int,
    #     target_location: str,
    #     new_pallet_id: str,
    #     db: Session
    # ) -> Tuple[bool, Union[Dict, str]]:
    #         """[入库服务 - 数据库] 操作穿梭车联动PLC系统入库, 使用障碍检测功能。"""

    #         target_layer = 1 
    #         inband_location = f"5,3,{target_layer}"
            
    #         # ---------------------------------------- #
    #         # step 3: 处理入库阻挡货物
    #         # ---------------------------------------- #

    #         logger.info("[step 3] 处理入库阻挡货物")

    #         success, blocking_nodes = self.get_block_node(inband_location, target_location, db)
    #         if blocking_nodes and blocking_nodes[0] and blocking_nodes[1]:
    #             # step 3.1: 计算靠近高速道阻塞点(按距离排序)
    #             # 找到最接近 highway 的阻塞节点
    #             do_blocking_nodes = []
    #             # 创建阻塞节点的副本，避免修改原始列表
    #             remaining_nodes = set(blocking_nodes[1])
                
    #             # 持续查找并移除最近的节点，直到没有剩余节点
    #             while remaining_nodes:
    #                 # 找到最接近 highway 的阻塞节点
    #                 nearest_highway_node = self.path_planner.find_nearest_highway_node(list(remaining_nodes))
    #                 if nearest_highway_node:
    #                     do_blocking_nodes.append(nearest_highway_node)
    #                     # 从剩余节点中移除已找到的节点
    #                     remaining_nodes.discard(nearest_highway_node)
    #                 else:
    #                     # 如果找不到最近节点，跳出循环避免无限循环
    #                     break
                        
    #             logger.info(f"[SYSTEM] 靠近高速道阻塞点(按距离排序): {do_blocking_nodes}")

    #             # 定义临时存放点
    #             temp_storage_nodes = [f"1,3,{target_layer}", f"2,3,{target_layer}", f"3,3,{target_layer}"]
    #             # 记录移动映射关系，用于将货物移回原位
    #             move_mapping = {}

    #             # step 3.2: 处理遮挡货物
    #             block_taskno = task_no+1
    #             for i, blocking_node in enumerate(do_blocking_nodes):
    #                 if i < len(temp_storage_nodes):
    #                     temp_node = temp_storage_nodes[i]
    #                     logger.info(f"[CAR] 移动({blocking_node})遮挡货物到({temp_node})")
    #                     move_mapping[blocking_node] = temp_node

    #                     # 移动货物
    #                     success, good_move_info = await self.good_move_by_start_end_no_lock(block_taskno, blocking_node, temp_node)
    #                     if success:
    #                         logger.info(f"{good_move_info}")
    #                         block_taskno += 3
    #                     else:
    #                         logger.error(f"{good_move_info}")
    #                         return False, f"{good_move_info}"

    #                 else:
    #                     logger.warning(f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})")
    #                     return False, f"[SYSTEM] 没有足够的临时存储点来处理遮挡货物 ({blocking_node})"
    #         else:
    #             logger.info("[SYSTEM] 无阻塞节点，直接出库")