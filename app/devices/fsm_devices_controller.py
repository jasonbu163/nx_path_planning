# app/devices/fsm_devices_controller.py
import time
from enum import Enum, auto
from typing import Tuple, Dict, Any

from abc import ABC, abstractmethod

from app.utils.devices_logger import DevicesLogger
from app.plc_system.controller import PLCController
from app.plc_system.enum import DB_11, DB_12, LIFT_TASK_TYPE, FLOOR_CODE
from app.res_system.controller import ControllerBase as CarController


class TaskType(Enum):
    CROSS_LAYER = "cross_layer"
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class TaskState(Enum):
    INIT = auto()
    # ... 其他状态定义
    COMPLETED = auto()
    ERROR = auto()

class CrossLayerState(Enum):
    """穿梭车跨层任务状态枚举"""
    INIT = auto()                    # 初始状态：获取设备当前位置
    PLC_CONNECTING = auto()          # 连接PLC系统
    LIFT_MOVING_TO_CAR = auto()     # 电梯移动至穿梭车所在楼层
    CAR_TO_LIFT_ENTRANCE = auto()   # 穿梭车移动至电梯预备口
    CAR_ENTERING_LIFT = auto()      # 穿梭车进入电梯内部
    LIFT_MOVING_WITH_CAR = auto()   # 电梯载车前往目标层
    CAR_LEAVING_LIFT = auto()       # 穿梭车离开电梯
    PLC_DISCONNECTING = auto()      # 断开PLC连接
    COMPLETED = auto()              # 任务成功完成
    ERROR = auto()                  # 错误状态


class BaseTask(ABC, DevicesLogger):
    """任务基类，定义公共接口和共享方法。"""

    def __init__(self, task_type: TaskType, plc_controller: PLCController, car_controller: CarController):
        super().__init__(self.__class__.__name__)
        self.task_type = task_type
        self.plc = plc_controller
        self.car = car_controller
        self.current_state = TaskState.INIT
        self.context = {}

    @abstractmethod
    def execute(self, task_id: int, **kwargs) -> Tuple[bool, str]:
        """执行任务的核心抽象方法。由子类实现具体逻辑。"""
        pass

    # 公共方法：状态持久化与恢复
    def save_state_to_db(self, task_id: int):
        """将当前任务状态和上下文保存到数据库。"""
        # 使用 SQLite 持久化状态，实现故障恢复 [1,5](@ref)
        # conn = sqlite3.connect('task_state.db')
        # ... 将 self.current_state 和 self.context 存入数据库
        # conn.close()

    def recover_state_from_db(self, task_id: int):
        """从数据库恢复任务状态和上下文。"""
        # ... 从数据库读取并恢复 self.current_state 和 self.context
        pass

    # 其他公共方法，如日志记录、超时处理等




class CrossLayerTask(BaseTask):
    """基于状态机的车辆跨层任务类"""
    
    def __init__(self, plc_controller: PLCController, car_controller: CarController):
        super().__init__(TaskType.CROSS_LAYER, plc_controller, car_controller)
        
        # 状态转移映射表（可选，用于更复杂的状态逻辑）
        self.state_transitions = {
            CrossLayerState.INIT: CrossLayerState.PLC_CONNECTING,
            CrossLayerState.PLC_CONNECTING: CrossLayerState.LIFT_MOVING_TO_CAR,
            CrossLayerState.LIFT_MOVING_TO_CAR: CrossLayerState.CAR_TO_LIFT_ENTRANCE,
            # ... 其他状态转移
        }

    def execute(
            self, 
            task_no: int, 
            target_layer: int, 
            timeout: int = 360
    ) -> Tuple[bool, str]:
        """基于状态机的穿梭车跨层控制
        
        Args:
            task_no: 任务编号
            target_layer: 目标楼层
            timeout: 整体超时时间（秒）
            
        Returns:
            (成功标志, 状态信息)
        """
        start_time = time.time()
        current_state = CrossLayerState.INIT
        context = {
            'task_no': task_no,
            'target_layer': target_layer,
            'car_current_floor': None,
            'car_start_location': None,
            'error_message': '',
            'start_time': start_time
        }
        
        self.logger.info(f"🚀 开始穿梭车跨层任务，目标楼层: {target_layer}层，任务号: {task_no}")
        
        # 状态机主循环
        while current_state not in (CrossLayerState.COMPLETED, CrossLayerState.ERROR):
            # 检查超时
            if time.time() - start_time > timeout:
                self.logger.error("⏰ 任务执行超时")
                current_state = CrossLayerState.ERROR
                context['error_message'] = "任务执行超时"
                break
                
            self.logger.info(f"🔄 当前状态: {current_state.name}")
            
            # 使用match-case集中管理状态逻辑
            match current_state:
                case CrossLayerState.INIT:
                    success, msg, next_state = self._handle_init_state(context)
                    
                case CrossLayerState.PLC_CONNECTING:
                    success, msg, next_state = self._handle_plc_connecting_state(context)
                    
                case CrossLayerState.LIFT_MOVING_TO_CAR:
                    success, msg, next_state = self._handle_lift_to_car_state(context)
                    
                case CrossLayerState.CAR_TO_LIFT_ENTRANCE:
                    success, msg, next_state = self._handle_car_to_entrance_state(context)
                    
                case CrossLayerState.CAR_ENTERING_LIFT:
                    success, msg, next_state = self._handle_car_entering_state(context)
                    
                case CrossLayerState.LIFT_MOVING_WITH_CAR:
                    success, msg, next_state = self._handle_lift_with_car_state(context)
                    
                case CrossLayerState.CAR_LEAVING_LIFT:
                    success, msg, next_state = self._handle_car_leaving_state(context)
                    
                case CrossLayerState.PLC_DISCONNECTING:
                    success, msg, next_state = self._handle_plc_disconnecting_state(context)
                    
                case _:
                    # 未知状态处理
                    self.logger.error(f"❌ 遇到未知状态: {current_state}")
                    success, msg, next_state = False, "未知状态", CrossLayerState.ERROR
            
            # 处理状态执行结果
            if success:
                self.logger.info(f"✅ {msg}")
                current_state = next_state
            else:
                self.logger.error(f"❌ 状态{current_state.name}执行失败: {msg}")
                context['error_message'] = msg
                current_state = CrossLayerState.ERROR
                self._cleanup_on_error(context)
        
        # 返回最终结果
        if current_state == CrossLayerState.COMPLETED:
            duration = time.time() - start_time
            self.logger.info(f"🎉 跨层任务完成，总耗时: {duration:.2f}秒")
            return True, "跨层任务完成"
        else:
            return False, f"跨层任务失败: {context['error_message']}"

    # ========== 状态处理函数 ==========
    
    def _handle_init_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理初始化状态：获取设备当前位置"""
        try:
            # 获取穿梭车当前位置
            car_location = self.car.car_current_location()
            car_cur_loc = list(map(int, car_location.split(',')))
            context['car_current_floor'] = car_cur_loc[2]
            context['car_start_location'] = car_location
            
            self.logger.info(f"🚗 穿梭车初始位置: {car_location}, 当前楼层: {context['car_current_floor']}层")
            self.logger.info(f"🎯 目标楼层: {context['target_layer']}层")
            
            return True, "初始化完成", CrossLayerState.PLC_CONNECTING
            
        except Exception as e:
            return False, f"初始化失败: {str(e)}", CrossLayerState.ERROR

    def _handle_plc_connecting_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理PLC连接状态"""
        try:
            if self.plc.connect():
                self.logger.info("🔌 PLC连接成功")
                return True, "PLC连接成功", CrossLayerState.LIFT_MOVING_TO_CAR
            else:
                return False, "PLC连接失败", CrossLayerState.ERROR
        except Exception as e:
            return False, f"PLC连接异常: {str(e)}", CrossLayerState.ERROR

    def _handle_lift_to_car_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理电梯移动至穿梭车楼层状态"""
        try:
            if not self.plc.plc_checker():
                return False, "PLC状态检查失败", CrossLayerState.ERROR
            
            task_no = context['task_no']
            current_floor = context['car_current_floor']
            
            if self.plc.lift_move_by_layer_sync(task_no, current_floor):
                # 等待电梯到达
                if self.plc.wait_lift_move_complete_by_location_sync():
                    self.logger.info(f"✅ 电梯已到达{current_floor}层")
                    return True, f"电梯到达{current_floor}层", CrossLayerState.CAR_TO_LIFT_ENTRANCE
                else:
                    return False, f"电梯未到达{current_floor}层", CrossLayerState.ERROR
            else:
                return False, "电梯移动指令发送失败", CrossLayerState.ERROR
                
        except Exception as e:
            return False, f"电梯移动异常: {str(e)}", CrossLayerState.ERROR

    def _handle_car_to_entrance_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理穿梭车移动至电梯预备口状态"""
        try:
            current_floor = context['car_current_floor']
            lift_pre_location = f"5,3,{current_floor}"
            task_no = context['task_no'] + 1
            
            # 检查是否已经在预备位置
            if self.car.car_current_location() == lift_pre_location:
                self.logger.info(f"✅ 穿梭车已在电梯预备位置: {lift_pre_location}")
                return True, "穿梭车已在预备位置", CrossLayerState.CAR_ENTERING_LIFT
            
            # 移动穿梭车到预备位置
            if self.car.car_move(task_no, lift_pre_location):
                if self.car.wait_car_move_complete_by_location_sync(lift_pre_location):
                    self.logger.info(f"✅ 穿梭车已到达电梯预备位置: {lift_pre_location}")
                    return True, "穿梭车到达预备位置", CrossLayerState.CAR_ENTERING_LIFT
                else:
                    return False, f"穿梭车未到达预备位置: {lift_pre_location}", CrossLayerState.ERROR
            else:
                return False, "穿梭车移动指令发送失败", CrossLayerState.ERROR
                
        except Exception as e:
            return False, f"穿梭车移动异常: {str(e)}", CrossLayerState.ERROR

    def _handle_car_entering_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理穿梭车进入电梯状态"""
        try:
            current_floor = context['car_current_floor']
            lift_location = f"6,3,{current_floor}"
            task_no = context['task_no'] + 2
            
            # 检查是否已经在电梯内
            if self.car.car_current_location() == lift_location:
                self.logger.info(f"✅ 穿梭车已在电梯内: {lift_location}")
                return True, "穿梭车已在电梯内", CrossLayerState.LIFT_MOVING_WITH_CAR
            
            # 移动穿梭车进入电梯
            if self.car.car_move(task_no, lift_location):
                if self.car.wait_car_move_complete_by_location_sync(lift_location):
                    self.logger.info(f"✅ 穿梭车已进入电梯: {lift_location}")
                    return True, "穿梭车进入电梯", CrossLayerState.LIFT_MOVING_WITH_CAR
                else:
                    return False, f"穿梭车未进入电梯: {lift_location}", CrossLayerState.ERROR
            else:
                return False, "穿梭车进入电梯指令发送失败", CrossLayerState.ERROR
                
        except Exception as e:
            return False, f"穿梭车进入电梯异常: {str(e)}", CrossLayerState.ERROR

    def _handle_lift_with_car_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理电梯载车移动状态"""
        try:
            if not self.plc.plc_checker():
                return False, "PLC状态检查失败", CrossLayerState.ERROR
            
            task_no = context['task_no'] + 3
            target_layer = context['target_layer']
            
            # 移动电梯到目标楼层
            if self.plc.lift_move_by_layer_sync(task_no, target_layer):
                # 等待电梯到达目标层
                if self.plc.wait_lift_move_complete_by_location_sync():
                    # 更新穿梭车坐标到目标层
                    target_lift_location = f"6,3,{target_layer}"
                    self.car.change_car_location(task_no + 1, target_lift_location)
                    self.logger.info(f"✅ 电梯已到达目标层{target_layer}层，穿梭车坐标已更新")
                    return True, f"电梯到达目标层{target_layer}", CrossLayerState.CAR_LEAVING_LIFT
                else:
                    return False, f"电梯未到达目标层{target_layer}", CrossLayerState.ERROR
            else:
                return False, "电梯移动指令发送失败", CrossLayerState.ERROR
                
        except Exception as e:
            return False, f"电梯载车移动异常: {str(e)}", CrossLayerState.ERROR

    def _handle_car_leaving_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理穿梭车离开电梯状态"""
        try:
            target_layer = context['target_layer']
            target_pre_location = f"5,3,{target_layer}"
            task_no = context['task_no'] + 4
            
            # 移动穿梭车离开电梯
            if self.car.car_move(task_no, target_pre_location):
                if self.car.wait_car_move_complete_by_location_sync(target_pre_location):
                    self.logger.info(f"✅ 穿梭车已到达目标层接驳位: {target_pre_location}")
                    return True, "穿梭车到达目标层", CrossLayerState.PLC_DISCONNECTING
                else:
                    return False, f"穿梭车未到达接驳位: {target_pre_location}", CrossLayerState.ERROR
            else:
                return False, "穿梭车离开指令发送失败", CrossLayerState.ERROR
                
        except Exception as e:
            return False, f"穿梭车离开电梯异常: {str(e)}", CrossLayerState.ERROR

    def _handle_plc_disconnecting_state(self, context: Dict[str, Any]) -> Tuple[bool, str, CrossLayerState]:
        """处理PLC断开连接状态"""
        try:
            if self.plc.disconnect():
                self.logger.info("🔌 PLC断开连接成功")
                return True, "PLC断开连接", CrossLayerState.COMPLETED
            else:
                self.logger.warning("⚠️ PLC断开连接异常，但任务继续完成")
                return True, "PLC断开连接异常忽略", CrossLayerState.COMPLETED
        except Exception as e:
            self.logger.warning(f"⚠️ PLC断开连接异常: {str(e)}，但任务继续完成")
            return True, "PLC断开连接异常忽略", CrossLayerState.COMPLETED

    def _cleanup_on_error(self, context: Dict[str, Any]):
        """错误状态下的清理操作"""
        self.logger.warning("🧹 执行错误清理操作...")
        try:
            self.plc.disconnect()
        except:
            pass  # 忽略断开连接时的异常

    # ========== 兼容性方法 ==========
    
    def car_cross_layer(self, task_no: int, target_layer: int) -> Tuple[bool, str]:
        """保持向后兼容的原始方法（委托给状态机版本）"""
        self.logger.info("🔀 使用状态机版本执行跨层任务")
        return self.execute(task_no, target_layer)
    

class InboundTask(BaseTask):
    def __init__(self, plc_controller: PLCController, car_controller: CarController):
        super().__init__(TaskType.INBOUND, plc_controller, car_controller)

    def execute(self, task_id: int, target_location: str, goods_info: dict) -> Tuple[bool, str]:
        """执行入库任务的具体流程。"""
        self.logger.info(f"开始执行入库任务 {task_id}")
        # 1. 检查目标货位状态
        # 2. 调度穿梭车取货
        # 3. 协同提升机将货物运至目标楼层
        # 4. 穿梭车将货物存入指定货位
        # 5. 更新库存信息 (WMS) [1](@ref)
        # ... 每个步骤都包含状态持久化
        return True, "入库任务完成"
    

class OutboundTask(BaseTask):
    def __init__(self, plc_controller: PLCController, car_controller: CarController):
        super().__init__(TaskType.OUTBOUND, plc_controller, car_controller)

    def execute(self, task_id: int, source_location: str) -> Tuple[bool, str]:
        """执行出库任务的具体流程。"""
        self.logger.info(f"开始执行出库任务 {task_id}")
        # 1. 根据WMS指令定位货物 [1](@ref)
        # 2. 调度穿梭车至目标货位取货
        # 3. 协同提升机将货物运至出口层
        # 4. 穿梭车将货物送至出库站台
        # 5. 更新库存信息
        # ... 
        return True, "出库任务完成"