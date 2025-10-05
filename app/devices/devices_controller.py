# app/devices/devices_controller.py
import time
from typing import Tuple, Union

from app.utils.devices_logger import DevicesLogger
from app.plc_system.controller import PLCController
from app.plc_system.enum import DB_11, DB_12, LIFT_TASK_TYPE, FLOOR_CODE
from app.res_system.controller import ControllerBase as CarController
from app.res_system.enum import CarStatus

class DevicesController(DevicesLogger):
    """同步设备控制器。
    
    联合PLC控制系统和穿梭车控制系统, 实现立体仓库设备自动化控制
    
    !!! 注意：此为设备安全与人生安全操作首要原则，必须遵守 !!!

    所有穿梭车的操作都要确保电梯在穿梭车所在楼层（因为只有电梯有对穿梭车的防飞出限位保险结构），避免穿梭车到达电梯口发生冲击力过大造成飞出“跳楼”危险。
    """
    
    def __init__(self, plc_ip: str, car_ip: str, car_port: int):
        """初始化设备控制器。

        Args:
            plc_ip: plc地址, 如 “192.168.8.10”
            car_ip: 穿梭车地址, 如 “192.168.8.30”
            car_port: 穿梭车端口, 如 2504
        """
        super().__init__(self.__class__.__name__)
        self._plc_ip = plc_ip
        self._car_ip = car_ip
        self._car_port = car_port
        self.plc = PLCController(self._plc_ip)
        self.car = CarController(self._car_ip, self._car_port)

    ############################################################
    ############################################################
    # 穿梭车全库跨层
    ############################################################
    ############################################################
    
    def car_cross_layer(
            self,
            task_no: int,
            target_layer: int
    ) -> Tuple[bool, str]:
        """穿梭车跨层。
        
        穿梭车系统联合PLC电梯系统, 控制穿梭车去到目标楼层。

        Args:
            task_no: 任务号
            target_layer: 目标楼层, 如一层为 1

        Returns:
            list: [标志, 信息]
        """
        ############################################################
        # step 0: 准备工作
        ############################################################

        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location = self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        
        car_cur_loc = list(map(int, car_location.split(',')))
        car_current_floor = car_cur_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_current_floor} 层")

        # 获取目标位置 -> 坐标: 如, "1,1,1" 楼层: 如, 1
        self.logger.info(f"🧭 穿梭车目的楼层: {target_layer} 层")
        
        ############################################################
        # step 1: 连接PLC
        ############################################################

        self.logger.info("🚧 连接PLC")
        
        if self.plc.connect():
            self.logger.info("✅ PLC连接正常")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return False ,"❌ PLC错误"
        
        ############################################################
        # step 2: 电梯移动到穿梭车楼层
        ############################################################

        self.logger.info("🚧 电梯移动到穿梭车楼层")
        
        if self.plc.plc_checker():

            self.logger.info("🚧 电梯开始移动...")

            if self.plc.lift_move_by_layer_sync(task_no, car_current_floor):
                self.logger.info("✅ 电梯工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯工作指令发送失败")
                return False ,"❌ 电梯工作指令发送失败"
        
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return False, "❌ PLC错误"
        
        ############################################################
        # step 3: 移动空载电梯到电机口
        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        ############################################################

        self.logger.info("🚧 移动空载电梯到电机口")

        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        
        if self.car.car_current_location() != car_current_lift_pre_location:
            
            self.logger.info("⏳ 穿梭车开始移动...")

            if self.car.car_move(task_no+1, car_current_lift_pre_location):
                self.logger.info("✅ 穿梭车工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 穿梭车移动指令发送错误")
                return False, "❌ 穿梭车移动指令发送错误"
            
            self.logger.info(f"⏳ 等待穿梭车前往 {car_current_lift_pre_location} 位置...")
                
            if self.car.wait_car_move_complete_by_location_sync(car_current_lift_pre_location):
                self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")    
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                return False, f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置"
            
        # 等待电梯到达
        if self.plc.plc_checker():
            
            self.logger.info(f"⌛️ 等待电梯到达{car_current_floor}层")

            if self.plc.wait_lift_move_complete_by_location_sync():
                self.logger.info(f"✅ 电梯已到达{car_current_floor}层")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 电梯未到达{car_current_floor}层")
                return False, f"❌ 电梯未到达{car_current_floor}层"
        
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return False, "❌ PLC错误"
        
        ############################################################
        # step 4: 穿梭车进入电梯
        ############################################################

        self.logger.info("🚧 穿梭车进入电梯")
        
        car_current_lift_location = f"6,3,{car_current_floor}"
        
        if self.car.car_current_location() != car_current_lift_location:
            
            self.logger.info("⏳ 穿梭车开始移动...")
            
            if self.car.car_move(task_no+2, car_current_lift_location):
                self.logger.info("✅ 穿梭车工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 穿梭车移动指令发送错误")
                return False, f"❌ 穿梭车移动指令发送错误"
            
            self.logger.info(f"⏳ 等待穿梭车前往 电梯内 {car_current_lift_location} 位置...")
                
            if self.car.wait_car_move_complete_by_location_sync(car_current_lift_location):
                self.logger.info(f"✅ 穿梭车已到达 电梯内 {car_current_lift_location} 位置")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 穿梭车未到达电梯内 {car_current_lift_location} 位置")
                return False, f"❌ 穿梭车未到达电梯内 {car_current_lift_location} 位置"

        ############################################################
        # step 5: 电梯送车到目标层
        ############################################################

        self.logger.info("🚧 移动电梯载车到目标楼层")
        
        if self.plc.plc_checker():
            
            self.logger.info("🚧 电梯开始移动...")

            if self.plc.lift_move_by_layer_sync(task_no+3, target_layer):
                self.logger.info("✅ 电梯工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯工作指令发送失败")
                return False,"❌ 电梯工作指令发送失败"
        
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return False ,"❌ PLC错误"

        ############################################################
        # step 6: 更新穿梭车坐标（楼层）
        ############################################################

        self.logger.info("🚧 更新穿梭车坐标（楼层）")

        if self.plc.plc_checker():

            if self.plc.get_lift() == target_layer and self.plc.read_bit(11, DB_11.IDLE.value) == 1:
                car_target_lift_location = f"6,3,{target_layer}"
                self.car.change_car_location(task_no+4, car_target_lift_location)
                self.logger.info(f"✅ 穿梭车位置: {car_target_lift_location}")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯未到达")
                return False, "❌ 电梯未到达"
            
            self.logger.info(f"⌛️ 等待电梯到达{target_layer}层")

            if self.plc.wait_lift_move_complete_by_location_sync():
                self.logger.info(f"✅ 电梯已到达{target_layer}层")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 电梯未到达{target_layer}层")
                return False, f"❌ 电梯未到达{target_layer}层"
        
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC未连接")
            return False, "❌ PLC未连接"
        
        ############################################################
        # step 7: 穿梭车开始离开电梯进入目标层接驳位
        ############################################################

        target_lift_pre_location = f"5,3,{target_layer}"
        
        self.logger.info(f"🚧 穿梭车开始离开电梯进入接驳位 {target_lift_pre_location}")
        
        self.logger.info("⏳ 穿梭车开始移动...")
        
        if self.car.car_move(task_no+5, target_lift_pre_location):
            self.logger.info("✅ 穿梭车工作指令发送成功")
        else:
            self.plc.disconnect()
            self.logger.error(f"❌ 穿梭车移动指令发送错误")
            return False, f"❌ 穿梭车移动指令发送错误"
        
        self.logger.info(f"⏳ 等待穿梭车前往 接驳位 {target_lift_pre_location} 位置...")
            
        if self.car.wait_car_move_complete_by_location_sync(target_lift_pre_location):
            self.logger.info(f"✅ 穿梭车已到达 指定楼层 {target_layer} 层")    
        else:
            self.plc.disconnect()
            self.logger.error(f"❌ 穿梭车未到达指定楼层 {target_layer} 层")
            return False, f"❌ 穿梭车未到达指定楼层 {target_layer} 层"
        
        ############################################################
        # step 8: 断开PLC连接
        ############################################################
        
        self.logger.info("🚧 断开PLC连接")
        
        if self.plc.disconnect():
            self.logger.info("✅ PLC已断开")
        else:
            self.logger.error("❌ PLC未连接")
            return False, "❌ PLC未连接"
        
        return True, "✅ 跨层完成"

    ############################################################
    ############################################################
    # 任务入库
    ############################################################
    ############################################################

    def task_inband(
            self,
            task_no: int,
            target_location: str
    ) -> list:
        """任务入库。
        
        穿梭车系统联合PLC电梯输送线系统, 执行入库任务。

        Args:
            task_no: 任务号
            target_location: 货物入库目标位置, 如 "1,2,4"

        Returns:
            list: [标志, 信息]
        """

        ############################################################
        # step 0: 准备工作
        ############################################################

        # 判断任务坐标是否合法
        disable_location = ["6,3,1", "6,3,2", "6,3,3", "6,3,4"]
        if target_location in disable_location:
            self.logger.error("❌ 任务坐标错误")
            return [False, "❌ 任务坐标错误"]
        
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 货物目标坐标: {target_location}")
        target_loc = list(map(int, target_location.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 货物目标楼层: {target_layer}")

        # 穿梭车不在任务层, 操作穿梭车到达任务楼层等待
        if car_layer != target_layer:
            car_info = self.car_cross_layer(task_no, target_layer)
            if car_info[0]:
                self.logger.info(f"{car_info[1]}")
            else:
                self.logger.error(f"{car_info[1]}")
                return [False, f"{car_info[1]}"]

        ############################################################
        # step 1: 连接PLC
        ############################################################

        self.logger.info("连接PLC")
        
        if self.plc.connect():
            self.logger.info("✅ PLC连接正常")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        ############################################################
        # step 2: 移动空载电梯到1层
        ############################################################
        
        self.logger.info("🚧 移动空载电梯到1层")

        if self.plc.plc_checker():
            
            self.logger.info("🚧 电梯开始移动...")

            if self.plc.lift_move_by_layer_sync(task_no+1, 1):
                self.logger.info("✅ 电梯工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯工作指令发送失败")
                return [False, "❌ 电梯工作指令发送失败"]
            
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        
        ############################################################
        # step 3: 货物进入电梯
        ############################################################
        
        self.logger.info("▶️ 入库开始")

        # 人工放货到入口完成后, 输送线将货物送入电梯
        if self.plc.plc_checker():

            self.logger.info("📦 货物开始进入电梯...")
            self.plc.inband_to_lift()

            self.logger.info("⏳ 输送线移动中...")
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
        
            self.logger.info("✅ 货物到达电梯")

        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC运行错误")
            return [False, "❌ PLC运行错误"]
        
        # 等待电梯到达
        if self.plc.plc_checker():
            
            self.logger.info(f"⌛️ 等待电梯到达{1}层")

            if self.plc.wait_lift_move_complete_by_location_sync():
                self.logger.info(f"✅ 电梯已到达{1}层")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 电梯未到达{1}层")
                return [False, f"❌ 电梯未到达{1}层"]
        
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False, "❌ PLC错误"]

        ############################################################
        # step 4: 电梯送货到目标层
        ############################################################

        self.logger.info(f"🚧 移动电梯载货到目标楼层 {target_layer}层")
        
        if self.plc.plc_checker():

            self.logger.info("🚧 电梯开始移动...")

            if self.plc.lift_move_by_layer_sync(task_no+2, target_layer):
                self.logger.info("✅ 电梯工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯工作指令发送失败")
                return [False, "❌ 电梯工作指令发送失败"]
            
            self.logger.info(f"⌛️ 等待电梯到达{target_layer}层")

            if self.plc.wait_lift_move_complete_by_location_sync():
                self.logger.info(f"✅ 电梯已到达{target_layer}层")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 电梯未到达{target_layer}层")
                return [False, f"❌ 电梯未到达{target_layer}层"]
            
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        ############################################################
        # step 5: 货物进入目标层
        ############################################################

        # 电梯载货到到目标楼层, 电梯输送线将货物送入目标楼层
        self.logger.info("▶️ 货物进入楼层")
        
        if self.plc.plc_checker():

            self.logger.info("📦 货物开始进入楼层...")
            self.plc.lift_to_everylayer(target_layer)

            self.logger.info("⏳ 输送线移动中...")
            time.sleep(0.5)
            # 等待电梯输送线工作结束
            if target_layer == 1:
                self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1)
            elif target_layer == 2:
                self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1)
            elif target_layer == 3:
                self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1)
            elif target_layer == 4:
                self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1)
            
            self.logger.info(f"✅ 货物到达 {target_layer} 层接驳位")
            
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC运行错误")
            return [False, "❌ PLC运行错误"]
        
        ############################################################
        # step 6: 穿梭车移动到接驳位
        ############################################################
        self.logger.info("🚧 穿梭车移动到接驳位")

        car_current_lift_pre_location = f"5,3,{target_layer}"
        if self.car.car_current_location() != car_current_lift_pre_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            self.car.car_move(task_no+3, car_current_lift_pre_location)
            
            # 等待穿梭车移动到位
            self.logger.info(f"⏳ 等待穿梭车前往 5,3,{target_layer} 位置...")
            self.car.wait_car_move_complete_by_location_sync(car_current_lift_pre_location)
            time.sleep(2)

            if self.car.car_current_location() == car_current_lift_pre_location:
                self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
            
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                return [False, "❌ 穿梭车运行错误"]

        ############################################################
        # step 5: 发送取货信号给PLC
        ############################################################
        
        self.logger.info("🚧 发送取货信号给PLC")
        
        if self.plc.plc_checker():
            self.plc.pick_in_process(target_layer)
            self.logger.info(f"✅ 信号已发送给PLC")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC接收取货信号异常")
            return [False, "❌ PLC接收取货信号异常"]
        
        ############################################################
        # step 6: 穿梭车将货物移动到目标位置
        ############################################################
        
        self.logger.info(f"🚧 穿梭车将货物移动到目标位置 {target_location}")
        
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.good_move(task_no+4, target_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {target_location} 位置...")
        self.car.wait_car_move_complete_by_location_sync(target_location)
        time.sleep(2)
        
        if self.car.car_current_location() == target_location:
            self.logger.info(f"✅ 货物已到达 目标位置 {target_location}")
        else:
            self.plc.disconnect()
            self.logger.error(f"❌ 货物未到达 目标位置 {target_location}")
            return [False, "❌ 穿梭车运行错误"]
        
        ############################################################
        # step 7: 发送取货完成信号给PLC
        ############################################################

        self.logger.info("🚧 发送取货完成信号给PLC")

        if self.plc.plc_checker():
            self.plc.pick_complete(target_layer)
            self.logger.info(f"✅ 入库完成")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]
        
        ############################################################
        # step 8: 断开PLC连接
        ############################################################
        
        self.logger.info("🚧 断开PLC连接")
        
        if self.plc.disconnect():
            self.logger.info("✅ PLC已断开")
        else:
            self.logger.error("❌ PLC未连接")
            return [False, "❌ PLC未连接"]

        return [True, "✅ 入库完成"]

    ############################################################
    ############################################################
    # 任务出库
    ############################################################
    ############################################################

    def task_outband(
            self,
            task_no: int,
            target_location: str
            ) -> list:
        """任务出库。
        
        穿梭车系统联合PLC电梯输送线系统, 执行出库任务。

        Args:
            task_no: 任务号
            target_location: 出库货物位置, 如 "1,2,4"

        Returns:
            list: [标志, 信息]
        """

        ############################################################
        # step 0: 准备工作
        ############################################################

        # 判断任务坐标是否合法
        disable_location = ["6,3,1", "6,3,2", "6,3,3", "6,3,4"]
        if target_location in disable_location:
            self.logger.error("❌ 任务坐标错误")
            return [False, "❌ 任务坐标错误"]
        
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location = self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 目标货物坐标: {target_location}")
        target_loc = list(map(int, target_location.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 目标货物楼层: {target_layer}")

        # 穿梭车不在任务层, 操作穿梭车到达任务楼层等待
        if car_layer != target_layer:
            car_info = self.car_cross_layer(task_no, target_layer)
            if car_info[0]:
                self.logger.info(f"{car_info[1]}")
            else:
                self.logger.error(f"{car_info[1]}")
                return [False, f"{car_info[1]}"]

        ############################################################
        # step 1: 连接PLC
        ############################################################

        self.logger.info("连接PLC")
        
        if self.plc.connect():
            self.logger.info("✅ PLC连接正常")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        ############################################################
        # step 2: 移动到目标货物层
        ############################################################
        
        self.logger.info(f"🚧 移动空载电梯到 {target_layer} 层")

        if self.plc.plc_checker():

            self.logger.info("🚧 电梯开始移动...")

            if self.plc.lift_move_by_layer_sync(task_no+1, target_layer):
                self.logger.info("✅ 电梯工作指令发送成功")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯工作指令发送失败")
                return [False, "❌ 电梯工作指令发送失败"]
            
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        ############################################################
        # step 1: 穿梭车前往货物位置
        ############################################################
        
        self.logger.info(f"▶️ 出库开始")

        self.logger.info(f"🚧 穿梭车前往货物位置 {target_location}")

        if self.car.car_current_location() != target_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            self.car.car_move(task_no+2, target_location)
            
            # 等待穿梭车进入接驳位
            self.logger.info(f"⏳ 等待穿梭车前往 {target_location} 位置...")
            if self.car.wait_car_move_complete_by_location_sync(target_location):
                self.logger.info(f"✅ 穿梭车已到达 货物位置 {target_location}")
            
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 穿梭车未到达 货物位置 {target_location}")
                return [False, f"❌ 穿梭车未到达 货物位置 {target_location}"]
            
        # 等待电梯到达
        if self.plc.plc_checker():
            
            self.logger.info(f"⌛️ 等待电梯到达{target_layer}层")

            if self.plc.wait_lift_move_complete_by_location_sync():
                self.logger.info(f"✅ 电梯已到达{target_layer}层")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 电梯未到达{target_layer}层")
                return [False, f"❌ 电梯未到达{target_layer}层"]
        
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False, "❌ PLC错误"]

        ############################################################
        # step 2: 发送放货进行中信号给PLC
        ############################################################

        self.logger.info(f"🚧 发送放货进行中信号给PLC")

        if self.plc.plc_checker():
            self.plc.feed_in_process(target_layer)
            self.logger.info(f"✅ 信号已发送给PLC")
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]
        
        ############################################################
        # step 3: 穿梭车将货物移动到楼层接驳位
        ############################################################
        
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭车将货物移动到楼层接驳位输送线 {target_lift_pre_location}")
       
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.good_move(task_no+3, target_lift_pre_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {target_lift_pre_location} 位置...")
        self.car.wait_car_move_complete_by_location_sync(target_lift_pre_location)
        time.sleep(2)
        
        if self.car.car_current_location() == target_lift_pre_location and self.car.car_status()['car_status'] == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 楼层接驳输送线位置 {target_lift_pre_location}")
        else:
            self.plc.disconnect()
            self.logger.error(f"❌ 货物未到达 楼层接驳输送线位置 {target_lift_pre_location}")
            return [False, "❌ 穿梭车运行错误"]
        

        ############################################################
        # step 4: 发送放货完成信号给PLC 且 货物进入电梯
        ############################################################

        self.logger.info(f"🚧 发送放货完成信号给PLC")
        
        if self.plc.plc_checker():
            self.plc.feed_complete(target_layer)
            self.logger.info(f"✅ 信号已发送给PLC")

            self.logger.info(f"🚧 货物进入电梯")
            self.logger.info("📦 货物开始进入电梯...")
            time.sleep(1)
            self.logger.info("⏳ 输送线移动中...")
            # 等待电梯输送线工作结束
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
            self.logger.info("✅ 货物到达电梯")
            
        else:
            self.plc.disconnect()
            self.logger.error("❌ 货物进入电梯失败")
            return [False, "❌ 货物进入电梯失败"]

        
        ############################################################
        # step 5: 电梯送货到1楼
        ############################################################

        self.logger.info(f"🚧 移动电梯载货到1层")
        
        if self.plc.plc_checker():

            self.logger.info("🚧 电梯开始移动...")

            if self.plc.lift_move_by_layer_sync(task_no+4, 1):
                self.logger.info("✅ 电梯运行正常")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
            
            self.logger.info(f"⌛️ 等待电梯到达{1}层")

            if self.plc.wait_lift_move_complete_by_location_sync():
                self.logger.info(f"✅ 电梯已到达{1}层")
            else:
                self.plc.disconnect()
                self.logger.error(f"❌ 电梯未到达{1}层")
                return [False, f"❌ 电梯未到达{1}层"]
            
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        
        ############################################################
        # step 6: 货物离开电梯出库
        ############################################################

        self.logger.info("🚧 货物离开电梯出库")

        if self.plc.plc_checker():
            
            self.logger.info("📦 货物开始离开电梯...")
            self.plc.lift_to_outband()

            self.logger.info("⏳ 输送线移动中...")
            # 等待电梯输送线工作结束
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)
            
            self.logger.info("✅ 货物到达出口")
            time.sleep(1)
            self.logger.info("✅ 出库完成")

        else:
            self.plc.disconnect()
            self.logger.error("❌ 货物离开电梯出库失败")
            return [False, "❌ 货物离开电梯出库失败"]

        ############################################################
        # step 7: 断开PLC连接
        ############################################################
        
        self.logger.info("🚧 断开PLC连接")
        
        if self.plc.disconnect():
            self.logger.info("✅ PLC已断开")
        else:
            self.logger.error("❌ PLC未连接")
            return [False, "❌ PLC未连接"]
        
        return [True, "✅ 出库完成"]