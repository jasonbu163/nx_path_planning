# devices/devices_controller.py
import random
import time

from .devices_logger import DevicesLogger
from .plc_controller import PLCController
from .plc_enum import DB_11, DB_12, LIFT_TASK_TYPE, FLOOR_CODE
from .car_controller import CarController
from .car_enum import CarStatus

class DevicesController(DevicesLogger):
    """
    [设备控制器] - 联合PLC控制系统和穿梭车控制系统, 实现立体仓库设备自动化控制
    """
    
    def __init__(self, PLC_IP: str, CAR_IP: str, CAR_PORT: int):
        """
        [初始化设备控制服务]

        ::: param :::
            PLC_IP: plc地址, 如 “192.168.8.10”
            CAR_IP: 穿梭车地址, 如 “192.168.8.30”
            CAR_PORT: 穿梭车端口, 如 2504
        """
        super().__init__(self.__class__.__name__)
        self._plc_ip = PLC_IP
        self._car_ip = CAR_IP
        self._car_port = CAR_PORT
        self.plc = PLCController(self._plc_ip)
        self.car = CarController(self._car_ip, self._car_port)


    ############################################################
    ############################################################
    # 穿梭车全库跨层
    ############################################################
    ############################################################
    
    def car_cross_layer(
            self,
            TASK_NO: int,
            TARGET_LAYER: int
            ) -> str:
        """
        [穿梭车跨层] - 穿梭车系统联合PLC电梯系统, 控制穿梭车去到目标楼层

        ::: param :::
            TASK_NO: 任务号
            TARGET_LAYER: 目标楼层, 如一层为 1

        ::: return :::
            last_location: 返回穿梭车最后位置
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
        self.logger.info(f"🧭 穿梭车目的楼层: {TARGET_LAYER} 层")

        
        ############################################################
        # step 1: 电梯到位接车
        ############################################################

        if self.plc.connect():
            self.logger.info("🚧 电梯移动到穿梭车楼层")
            self.plc.lift_move_by_layer(TASK_NO, car_current_floor)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"

        
        ############################################################
        # step 2: 车到电梯前等待
        ############################################################

        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.car_move(TASK_NO+1, car_current_lift_pre_location)
        
        # 等待穿梭车移动到位
        self.logger.info(f"⏳ 等待穿梭车前往 5,3,{car_current_floor} 位置...")
        self.car.wait_car_move_complete_by_location_sync(car_current_lift_pre_location)
        
        if self.car.car_current_location() == car_current_lift_pre_location and self.car.car_status() == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
        else:
            self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
            return "❌ 穿梭车运行错误"
        
        ############################################################
        # step 3: 车进电梯
        ############################################################

        # 穿梭车进入电机
        self.logger.info("🚧 穿梭车进入电梯")
        car_current_lift_location = f"6,3,{car_current_floor}"
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.car_move(TASK_NO+2, car_current_lift_location)
        
        # 等待穿梭车进入电梯
        self.logger.info(f"⏳ 等待穿梭车前往 电梯内 6,3,{car_current_floor} 位置...")
        self.car.wait_car_move_complete_by_location_sync(car_current_lift_location)
        
        if self.car.car_current_location() == car_current_lift_pre_location and self.car.car_status() == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 电梯内 {car_current_lift_location} 位置")
        else:
            self.logger.error(f"❌ 穿梭车未到达 电梯内 {car_current_lift_location} 位置")
            return "❌ 穿梭车运行错误"

        
        ############################################################
        # step 4: 电梯送车到目标层
        ############################################################

        if self.plc.connect():
            self.logger.info("🚧 移动电梯载车到目标楼层")
            self.plc.lift_move_by_layer(TASK_NO+3, TARGET_LAYER)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"

        ############################################################
        # step 5: 更新车坐标，更新车层坐标
        ############################################################

        time.sleep(1)
        if self.plc.connect():
            if self.plc.get_lift() == TARGET_LAYER and self.plc.read_bit(11, DB_11.IDLE.value) == 1:
                self.plc.disconnect()
                self.logger.info("🚧 更新穿梭车楼层")
                car_target_lift_location = f"6,3,{TARGET_LAYER}"
                self.car.change_car_location(TASK_NO+4, car_target_lift_location)
                self.logger.info(f"✅ 穿梭车位置: {car_target_lift_location}")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯未到达")
                return "❌ 电梯未到达"
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC未连接")
            return "❌ PLC未连接"

        
        ############################################################
        # step 6: 车进目标层
        ############################################################

        # 穿梭车离开提升机进入接驳位
        target_lift_pre_location = f"5,3,{TARGET_LAYER}"
        self.logger.info(f"🚧 穿梭车开始离开电梯进入接驳位 {target_lift_pre_location}")
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.car_move(TASK_NO+5, target_lift_pre_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 接驳位 {target_lift_pre_location} 位置...")
        self.car.wait_car_move_complete_by_location_sync(target_lift_pre_location)
        
        if self.car.car_current_location() == target_lift_pre_location and self.car.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 指定楼层 {TARGET_LAYER} 层")
        else:
            self.logger.info(f"❌ 穿梭车未到达 指定楼层 {TARGET_LAYER} 层")
            return "❌ 穿梭车运行错误"
        

        ############################################################
        # step 7: 校准电梯水平操作
        ############################################################

        if self.plc.connect():
            self.logger.info("🚧 空载校准电梯楼层")
            self.plc.lift_move_by_layer(TASK_NO+6, TARGET_LAYER)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"
        
        # 返回穿梭车位置
        last_location = self.car.car_current_location()
        return last_location


    ############################################################
    ############################################################
    # 任务入库
    ############################################################
    ############################################################

    def task_inband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> str:
        """
        [任务入库] - 穿梭车系统联合PLC电梯输送线系统, 执行入库任务

        ::: param :::
            TASK_NO: 任务号
            TARGET_LOCATION: 货物入库目标位置, 如 "1,2,4"

        ::: return :::
            last_location: 返回穿梭车最后位置
        """

        ############################################################
        # step 0: 准备工作
        ############################################################

        # 穿梭车初始化
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 货物目标坐标: {TARGET_LOCATION}")
        target_loc = list(map(int, TARGET_LOCATION.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 货物目标楼层: {target_layer}")

        # 穿梭车不在任务层, 操作穿梭车到达任务入库楼层等待
        if car_layer != target_layer:
            car_location = self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")

        # 电梯初始化: 移动到1层
        if self.plc.connect():
            self.logger.info("🚧 移动空载电梯到1层")
            self.plc.lift_move_by_layer(TASK_NO+1, 1)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"
        
        
        ############################################################
        # step 1: 货物进入电梯
        ############################################################
        
        self.logger.info("▶️ 入库开始")

        # 人工放货到入口完成后, 输送线将货物送入电梯
        time.sleep(1)
        if self.plc.connect():
            self.logger.info("📦 货物开始进入电梯...")
            self.plc.inband_to_lift()

            self.logger.info("⏳ 输送线移动中...")
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
        
            self.logger.info("✅ 货物到达电梯")
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC运行错误")
            return "❌ PLC运行错误"


        ############################################################
        # step 2: 电梯送货到目标层
        ############################################################

        time.sleep(1)
        if self.plc.connect():
            self.logger.info(f"🚧 移动电梯载货到目标楼层 {target_layer}层")
            self.plc.lift_move(LIFT_TASK_TYPE.GOOD, TASK_NO+2, target_layer)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"

        
        ############################################################
        # step 3: 货物进入目标层
        ############################################################

        # 电梯载货到到目标楼层, 电梯输送线将货物送入目标楼层
        self.logger.info("▶️ 货物进入楼层")
        time.sleep(1)
        if self.plc.connect():

            self.logger.info("📦 货物开始进入楼层...")
            self.plc.lift_to_everylayer(target_layer)

            self.logger.info("⏳ 输送线移动中...")
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
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC运行错误")
            return "❌ PLC运行错误"

        ############################################################
        # step 4: 穿梭车载货进入目标位置
        ############################################################
        
        # 发送取货进行中信号给PLC
        time.sleep(1)
        if self.plc.connect():
            self.logger.info(f"🚧 穿梭车开始取货...")
            self.plc.pick_in_process(target_layer)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC接收取货信号异常")
            return "❌ PLC接收取货信号异常"
        
        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车将货物移动到目标位置 {TARGET_LOCATION}")
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.good_move(TASK_NO+3, TARGET_LOCATION)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
        self.car.wait_car_move_complete_by_location_sync(TARGET_LOCATION)
        
        if self.car.car_current_location() == TARGET_LOCATION and self.car.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 目标位置 {TARGET_LOCATION}")
        else:
            self.logger.error(f"❌ 货物未到达 目标位置 {TARGET_LOCATION}")
            return f"❌ 穿梭车运行错误"
        
        ############################################################
        # step 5: 
        ############################################################

        # 发送取货完成信号给PLC
        if self.plc.connect():
            self.plc.pick_complete(target_layer)
            self.logger.info(f"✅ 入库完成")
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC 运行错误")
            return "❌ PLC 运行错误"

        # 返回穿梭车位置
        last_location = self.car.car_current_location()
        return last_location


    ############################################################
    ############################################################
    # 任务出库
    ############################################################
    ############################################################

    def task_outband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> str:
        """
        [任务出库] - 穿梭车系统联合PLC电梯输送线系统, 执行出库任务

        ::: param :::
            TASK_NO: 任务号
            TRAGET_LOCATION: 出库货物位置, 如 "1,2,4"

        ::: return :::
            last_location: 返回穿梭车最后位置
        """

        ############################################################
        # step 0: 准备工作
        ############################################################

        # 穿梭车初始化
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location = self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 目标货物坐标: {TARGET_LOCATION}")
        target_loc = list(map(int, TARGET_LOCATION.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 目标货物楼层: {target_layer}")

        # 穿梭车不在任务层, 操作穿梭车到达任务入库楼层等待
        if car_layer != target_layer:
            car_location = self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")

        # 电梯初始化: 移动到目标货物层
        if self.plc.connect():
            self.logger.info(f"🚧 移动空载电梯到 {target_layer} 层")
            self.plc.lift_move_by_layer(TASK_NO+1, target_layer)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"
            
        
        
        ############################################################
        # step 1: 穿梭车载货到楼层接驳位
        ############################################################
        
        self.logger.info(f"▶️ 出库开始")

        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车前往货物位置 {TARGET_LOCATION}")
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.car_move(TASK_NO+2, TARGET_LOCATION)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
        self.car.wait_car_move_complete_by_location_sync(TARGET_LOCATION)
        
        if self.car.car_current_location() == TARGET_LOCATION and self.car.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 货物位置 {TARGET_LOCATION}")
        else:
            
            self.logger.error(f"❌ 穿梭车未到达 货物位置 {TARGET_LOCATION}")
            return "❌ 穿梭车运行错误"
        

        # 发送放货进行中信号给PLC
        if self.plc.connect():
            self.logger.info(f"🚧 穿梭车开始取货...")
            self.plc.feed_in_process(target_layer)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC 运行错误")
            return "❌ PLC 运行错误"
        
        # 穿梭车将货物移动到楼层接驳位
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭车将货物移动到楼层接驳位输送线 {target_lift_pre_location}")
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.good_move(TASK_NO+3, target_lift_pre_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {target_lift_pre_location} 位置...")
        self.car.wait_car_move_complete_by_location_sync(target_lift_pre_location)
        
        if self.car.car_current_location() == target_lift_pre_location and self.car.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 楼层接驳输送线位置 {target_lift_pre_location}")
        else:
            self.logger.error(f"❌ 货物未到达 楼层接驳输送线位置 {target_lift_pre_location}")
            return "❌ 穿梭车运行错误"
        

        ############################################################
        # step 2: 货物进入电梯
        ############################################################

        # 发送放货完成信号给PLC
        if self.plc.connect():
            self.logger.info(f"✅ 货物放置完成")
            self.plc.feed_complete(target_layer)

            self.logger.info(f"🚧 货物进入电梯")
            self.logger.info("📦 货物开始进入电梯...")
            time.sleep(1)
            self.logger.info("⏳ 输送线移动中...")
            # 等待电梯输送线工作结束
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
            self.logger.info("✅ 货物到达电梯")
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 货物进入电梯失败")
            return "❌ 货物进入电梯失败"

        
        ############################################################
        # step 3: 电梯送货到1楼
        ############################################################

        # 电梯带货移动到1楼
        time.sleep(1)
        if self.plc.connect():
            self.logger.info(f"🚧 移动电梯载货到1层")
            self.plc.lift_move_by_layer(TASK_NO+4, 1)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 电梯运行错误")
            return "❌ 电梯运行错误"

        
        ############################################################
        # step 4: 
        ############################################################

        time.sleep(1)
        if self.plc.connect():
            self.logger.info("🚧 货物离开电梯出库")
            self.logger.info("📦 货物开始离开电梯...")
            self.plc.lift_to_outband()
            self.logger.info("⏳ 输送线移动中...")
            # 等待电梯输送线工作结束
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)
            self.logger.info("✅ 货物到达出口")
            time.sleep(1)
            self.logger.info("✅ 出库完成")
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ 货物离开电梯出库失败")
            return "❌ 货物离开电梯出库失败"

        
        # 返回穿梭车位置
        last_location = self.car.car_current_location()
        return last_location