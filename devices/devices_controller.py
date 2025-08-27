# devices/devices_controller.py
import random
import time
import asyncio

from .devices_logger import DevicesLogger
from .plc_controller import PLCController
from .plc_enum import DB_11, DB_12, LIFT_TASK_TYPE, FLOOR_CODE
from .car_controller import CarController, AsyncCarController, AsyncSocketCarController
from .car_enum import CarStatus

class DevicesController(DevicesLogger):
    """
    [同步 - 设备控制器] - 联合PLC控制系统和穿梭车控制系统, 实现立体仓库设备自动化控制
    
    !!! 注意：此为设备安全与人生安全操作首要原则，必须遵守 !!!

    所有穿梭车的操作都要确保电梯在穿梭车所在楼层（因为只有电梯有对穿梭车的防飞出限位保险结构），避免穿梭车到达电梯口发生冲击力过大造成飞出“跳楼”危险。
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
            ) -> list:
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

        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info("🚧 电梯移动到穿梭车楼层")
            time.sleep(1)
            if self.plc._lift_move_by_layer(TASK_NO, car_current_floor):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False ,"❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        
        ############################################################
        # step 2: 车到电梯前等待
        ############################################################

        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        if self.car.car_current_location() != car_current_lift_pre_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            if self.car.car_move(TASK_NO+1, car_current_lift_pre_location):
                # 等待穿梭车移动到位
                self.logger.info(f"⏳ 等待穿梭车前往 5,3,{car_current_floor} 位置...")
                self.car.wait_car_move_complete_by_location_sync(car_current_lift_pre_location)
                time.sleep(2)
                if self.car.car_current_location() == car_current_lift_pre_location and self.car.car_status()['car_status'] == CarStatus.READY.value:
                    self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
                else:
                    self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                    return [False, "❌ 穿梭车运行错误"]
            else:
                self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                return [False, "❌ 穿梭车运行错误"]
        
        ############################################################
        # step 3: 车进电梯
        ############################################################

        # 穿梭车进入电机
        self.logger.info("🚧 穿梭车进入电梯")
        car_current_lift_location = f"6,3,{car_current_floor}"
        
        if self.car.car_current_location() != car_current_lift_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            if self.car.car_move(TASK_NO+2, car_current_lift_location):
                # 等待穿梭车进入电梯
                self.logger.info(f"⏳ 等待穿梭车前往 电梯内 6,3,{car_current_floor} 位置...")
                self.car.wait_car_move_complete_by_location_sync(car_current_lift_location)
                time.sleep(2)
                if self.car.car_current_location() == car_current_lift_location and self.car.car_status()['car_status'] == CarStatus.READY.value:
                    self.logger.info(f"✅ 穿梭车已到达 电梯内 {car_current_lift_location} 位置")
                else:
                    self.logger.error(f"❌ 穿梭车未到达 电梯内 {car_current_lift_location} 位置")
                    return [False, "❌ 穿梭车运行错误"]
            else:
                self.logger.error(f"❌ 穿梭车未到达 电梯内 {car_current_lift_location} 位置")
                return [False, "❌ 穿梭车运行错误"]

        
        ############################################################
        # step 4: 电梯送车到目标层
        ############################################################

        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info("🚧 移动电梯载车到目标楼层")
            time.sleep(1)
            if self.plc._lift_move_by_layer(TASK_NO+3, TARGET_LAYER):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False,"❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        ############################################################
        # step 5: 更新车坐标，更新车层坐标
        ############################################################

        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            time.sleep(2)
            if self.plc.get_lift() == TARGET_LAYER and self.plc.read_bit(11, DB_11.IDLE.value) == 1:
                self.plc.disconnect()
                self.logger.info("🚧 更新穿梭车楼层")
                car_target_lift_location = f"6,3,{TARGET_LAYER}"
                self.car.change_car_location(TASK_NO+4, car_target_lift_location)
                self.logger.info(f"✅ 穿梭车位置: {car_target_lift_location}")
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯未到达")
                return [False, "❌ 电梯未到达"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC未连接")
            return [False, "❌ PLC未连接"]

        
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
        
        if self.car.car_current_location() == target_lift_pre_location and self.car.car_status()['car_status'] == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 指定楼层 {TARGET_LAYER} 层")
        else:
            self.logger.info(f"❌ 穿梭车未到达 指定楼层 {TARGET_LAYER} 层")
            return [False, "❌ 穿梭车运行错误"]
        

        ############################################################
        # step 7: 校准电梯水平操作
        ############################################################

        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info("🚧 空载校准电梯楼层")
            time.sleep(2)
            if self.plc._lift_move_by_layer(TASK_NO+6, TARGET_LAYER):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        # 返回穿梭车位置
        last_location = self.car.car_current_location()
        return [True, last_location]


    ############################################################
    ############################################################
    # 任务入库
    ############################################################
    ############################################################

    def task_inband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
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
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info("🚧 移动空载电梯到1层")
            time.sleep(1)
            if self.plc._lift_move_by_layer(TASK_NO+1, 1):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        
        ############################################################
        # step 1: 货物进入电梯
        ############################################################
        
        self.logger.info("▶️ 入库开始")

        # 人工放货到入口完成后, 输送线将货物送入电梯
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info("📦 货物开始进入电梯...")
            time.sleep(2)
            self.plc.inband_to_lift()

            self.logger.info("⏳ 输送线移动中...")
            self.plc.wait_for_bit_change_sync(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
        
            self.logger.info("✅ 货物到达电梯")
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC运行错误")
            return [False, "❌ PLC运行错误"]


        ############################################################
        # step 2: 电梯送货到目标层
        ############################################################

        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            time.sleep(1)
            self.logger.info(f"🚧 移动电梯载货到目标楼层 {target_layer}层")
            if self.plc._lift_move_by_layer(TASK_NO+2, target_layer):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        
        ############################################################
        # step 3: 货物进入目标层
        ############################################################

        # 电梯载货到到目标楼层, 电梯输送线将货物送入目标楼层
        self.logger.info("▶️ 货物进入楼层")
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            time.sleep(1)
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
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC运行错误")
            return [False, "❌ PLC运行错误"]
        
        ############################################################
        # step 4: 车到电梯前等待
        ############################################################

        # 穿梭车移动到接驳位接货
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{target_layer}"
        if self.car.car_current_location() != car_current_lift_pre_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            self.car.car_move(TASK_NO+3, car_current_lift_pre_location)
            
            # 等待穿梭车移动到位
            self.logger.info(f"⏳ 等待穿梭车前往 5,3,{target_layer} 位置...")
            self.car.wait_car_move_complete_by_location_sync(car_current_lift_pre_location)
            time.sleep(2)

            if self.car.car_current_location() == car_current_lift_pre_location and self.car.car_status()['car_status'] == CarStatus.READY.value:
                self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
            else:
                self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                return [False, "❌ 穿梭车运行错误"]

        ############################################################
        # step 5: 穿梭车载货进入目标位置
        ############################################################
        
        # 发送取货进行中信号给PLC
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 穿梭车开始取货...")
            time.sleep(1)
            self.plc.pick_in_process(target_layer)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC接收取货信号异常")
            return [False, "❌ PLC接收取货信号异常"]
        
        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车将货物移动到目标位置 {TARGET_LOCATION}")
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.good_move(TASK_NO+4, TARGET_LOCATION)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
        self.car.wait_car_move_complete_by_location_sync(TARGET_LOCATION)
        time.sleep(2)
        
        if self.car.car_current_location() == TARGET_LOCATION and self.car.car_status()['car_status'] == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 目标位置 {TARGET_LOCATION}")
        else:
            self.logger.error(f"❌ 货物未到达 目标位置 {TARGET_LOCATION}")
            return [False, "❌ 穿梭车运行错误"]
        
        ############################################################
        # step 6: 
        ############################################################

        # 发送取货完成信号给PLC
        if self.plc.connect() and self.plc.plc_checker():
            time.sleep(1)
            self.plc.pick_complete(target_layer)
            self.logger.info(f"✅ 入库完成")
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]

        # 返回穿梭车位置
        last_location = self.car.car_current_location()
        return [True, last_location]


    ############################################################
    ############################################################
    # 任务出库
    ############################################################
    ############################################################

    def task_outband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
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
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 移动空载电梯到 {target_layer} 层")
            time.sleep(2)
            if self.plc._lift_move_by_layer(TASK_NO+1, target_layer):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        
        ############################################################
        # step 1: 穿梭车载货到楼层接驳位
        ############################################################
        
        self.logger.info(f"▶️ 出库开始")

        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车前往货物位置 {TARGET_LOCATION}")
        if self.car.car_current_location() != TARGET_LOCATION:
            self.logger.info("⏳ 穿梭车开始移动...")
            self.car.car_move(TASK_NO+2, TARGET_LOCATION)
            
            # 等待穿梭车进入接驳位
            self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
            self.car.wait_car_move_complete_by_location_sync(TARGET_LOCATION)
            time.sleep(2)
            
            if self.car.car_current_location() == TARGET_LOCATION and self.car.car_status()['car_status'] == CarStatus.READY.value:
                self.logger.info(f"✅ 穿梭车已到达 货物位置 {TARGET_LOCATION}")
            else:
                
                self.logger.error(f"❌ 穿梭车未到达 货物位置 {TARGET_LOCATION}")
                return [False, "❌ 穿梭车运行错误"]

        # 发送放货进行中信号给PLC
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 穿梭车开始取货...")
            time.sleep(1)
            self.plc.feed_in_process(target_layer)
            self.plc.disconnect()
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]
        
        # 穿梭车将货物移动到楼层接驳位
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭车将货物移动到楼层接驳位输送线 {target_lift_pre_location}")
        self.logger.info("⏳ 穿梭车开始移动...")
        self.car.good_move(TASK_NO+3, target_lift_pre_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {target_lift_pre_location} 位置...")
        self.car.wait_car_move_complete_by_location_sync(target_lift_pre_location)
        time.sleep(2)
        
        if self.car.car_current_location() == target_lift_pre_location and self.car.car_status()['car_status'] == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 楼层接驳输送线位置 {target_lift_pre_location}")
        else:
            self.logger.error(f"❌ 货物未到达 楼层接驳输送线位置 {target_lift_pre_location}")
            return [False, "❌ 穿梭车运行错误"]
        

        ############################################################
        # step 2: 货物进入电梯
        ############################################################

        # 发送放货完成信号给PLC
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info(f"✅ 货物放置完成")
            time.sleep(2)
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
            return [False, "❌ 货物进入电梯失败"]

        
        ############################################################
        # step 3: 电梯送货到1楼
        ############################################################

        # 电梯带货移动到1楼
        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 移动电梯载货到1层")
            time.sleep(1)
            if self.plc._lift_move_by_layer(TASK_NO+4, 1):
                self.plc.disconnect()
            else:
                self.plc.disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            self.plc.disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        
        ############################################################
        # step 4: 
        ############################################################

        time.sleep(1)
        if self.plc.connect() and self.plc.plc_checker():
            self.logger.info("🚧 货物离开电梯出库")
            time.sleep(1)
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
            return [False, "❌ 货物离开电梯出库失败"]

        
        # 返回穿梭车位置
        last_location = self.car.car_current_location()
        return [True, last_location]
    

class AsyncDevicesController(DevicesLogger):
    """
    [异步 - 设备控制器] - 联合PLC控制系统和穿梭车控制系统, 实现立体仓库设备自动化控制
    
    !!! 注意：此为设备安全与人生安全操作首要原则，必须遵守 !!!

    所有穿梭车的操作都要确保电梯在穿梭车所在楼层（因为只有电梯有对穿梭车的防飞出限位保险结构），避免穿梭车到达电梯口发生冲击力过大造成飞出“跳楼”危险。
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
        self.car = AsyncSocketCarController(self._car_ip, self._car_port)


    ############################################################
    ############################################################
    # 穿梭车全库跨层
    ############################################################
    ############################################################
    
    async def car_cross_layer(
            self,
            TASK_NO: int,
            TARGET_LAYER: int
            ) -> list:
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
        car_location = await self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        
        car_cur_loc = list(map(int, car_location.split(',')))
        car_current_floor = car_cur_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_current_floor} 层")

        # 获取目标位置 -> 坐标: 如, "1,1,1" 楼层: 如, 1
        self.logger.info(f"🧭 穿梭车目的楼层: {TARGET_LAYER} 层")

        
        ############################################################
        # step 1: 电梯到位接车
        ############################################################

        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("🚧 电梯移动到穿梭车楼层")
            await asyncio.sleep(1)
            if await self.plc.lift_move_by_layer(TASK_NO, car_current_floor):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False ,"❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        
        ############################################################
        # step 2: 车到电梯前等待
        ############################################################

        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        if await self.car.car_current_location() != car_current_lift_pre_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            if await self.car.car_move(TASK_NO+1, car_current_lift_pre_location):
                # 等待穿梭车移动到位
                self.logger.info(f"⏳ 等待穿梭车前往 5,3,{car_current_floor} 位置...")
                await self.car.wait_car_move_complete_by_location(car_current_lift_pre_location)
                await asyncio.sleep(2)
                car_status = await self.car.car_status()
                if await self.car.car_current_location() == car_current_lift_pre_location and car_status['car_status'] == CarStatus.READY.value:
                    self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
                else:
                    self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                    return [False, "❌ 穿梭车运行错误"]
            else:
                self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                return [False, "❌ 穿梭车运行错误"]
        
        ############################################################
        # step 3: 车进电梯
        ############################################################

        # 穿梭车进入电机
        self.logger.info("🚧 穿梭车进入电梯")
        car_current_lift_location = f"6,3,{car_current_floor}"
        
        if await self.car.car_current_location() != car_current_lift_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            if await self.car.car_move(TASK_NO+2, car_current_lift_location):
                # 等待穿梭车进入电梯
                self.logger.info(f"⏳ 等待穿梭车前往 电梯内 6,3,{car_current_floor} 位置...")
                await self.car.wait_car_move_complete_by_location(car_current_lift_location)
                await asyncio.sleep(2)
                car_status = await self.car.car_status()
                if await self.car.car_current_location() == car_current_lift_location and car_status['car_status'] == CarStatus.READY.value:
                    self.logger.info(f"✅ 穿梭车已到达 电梯内 {car_current_lift_location} 位置")
                else:
                    self.logger.error(f"❌ 穿梭车未到达 电梯内 {car_current_lift_location} 位置")
                    return [False, "❌ 穿梭车运行错误"]
            else:
                self.logger.error(f"❌ 穿梭车未到达 电梯内 {car_current_lift_location} 位置")
                return [False, "❌ 穿梭车运行错误"]

        
        ############################################################
        # step 4: 电梯送车到目标层
        ############################################################

        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("🚧 移动电梯载车到目标楼层")
            await asyncio.sleep(1)
            if await self.plc.lift_move_by_layer(TASK_NO+3, TARGET_LAYER):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False,"❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        ############################################################
        # step 5: 更新车坐标，更新车层坐标
        ############################################################

        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            await asyncio.sleep(2)
            if self.plc.get_lift() == TARGET_LAYER and self.plc.read_bit(11, DB_11.IDLE.value) == 1:
                await self.plc.async_disconnect()
                self.logger.info("🚧 更新穿梭车楼层")
                car_target_lift_location = f"6,3,{TARGET_LAYER}"
                await self.car.change_car_location(TASK_NO+4, car_target_lift_location)
                self.logger.info(f"✅ 穿梭车位置: {car_target_lift_location}")
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯未到达")
                return [False, "❌ 电梯未到达"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC未连接")
            return [False, "❌ PLC未连接"]

        
        ############################################################
        # step 6: 车进目标层
        ############################################################

        # 穿梭车离开提升机进入接驳位
        target_lift_pre_location = f"5,3,{TARGET_LAYER}"
        self.logger.info(f"🚧 穿梭车开始离开电梯进入接驳位 {target_lift_pre_location}")
        
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car.car_move(TASK_NO+5, target_lift_pre_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 接驳位 {target_lift_pre_location} 位置...")
        await self.car.wait_car_move_complete_by_location(target_lift_pre_location)
        
        # car_status = await self.car.car_status()
        # if await self.car.car_current_location() == target_lift_pre_location and car_status['car_status'] == CarStatus.READY.value:
        if await self.car.car_current_location() == target_lift_pre_location:
            self.logger.info(f"✅ 穿梭车已到达 指定楼层 {TARGET_LAYER} 层")
        else:
            self.logger.info(f"❌ 穿梭车未到达 指定楼层 {TARGET_LAYER} 层")
            return [False, "❌ 穿梭车运行错误"]
        

        ############################################################
        # step 7: 校准电梯水平操作
        ############################################################

        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("🚧 空载校准电梯楼层")
            await asyncio.sleep(2)
            if await self.plc.lift_move_by_layer(TASK_NO+6, TARGET_LAYER):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        # 返回穿梭车位置
        last_location = await self.car.car_current_location()
        return [True, last_location]


    ############################################################
    ############################################################
    # 任务入库
    ############################################################
    ############################################################

    async def task_inband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
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
        car_location = await self.car.car_current_location()
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
            car_location = await self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")

        # 电梯初始化: 移动到1层
        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("🚧 移动空载电梯到1层")
            await asyncio.sleep(1)
            if await self.plc.lift_move_by_layer(TASK_NO+1, 1):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]
        
        
        ############################################################
        # step 1: 货物进入电梯
        ############################################################
        
        self.logger.info("▶️ 入库开始")

        # 人工放货到入口完成后, 输送线将货物送入电梯
        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("📦 货物开始进入电梯...")
            await asyncio.sleep(2)
            self.plc.inband_to_lift()

            self.logger.info("⏳ 输送线移动中...")
            await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
        
            self.logger.info("✅ 货物到达电梯")
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC运行错误")
            return [False, "❌ PLC运行错误"]


        ############################################################
        # step 2: 电梯送货到目标层
        ############################################################

        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 移动电梯载货到目标楼层 {target_layer}层")
            await asyncio.sleep(1)
            if await self.plc.lift_move_by_layer(TASK_NO+2, target_layer):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC错误")
            return [False ,"❌ PLC错误"]

        
        ############################################################
        # step 3: 货物进入目标层
        ############################################################

        # 电梯载货到到目标楼层, 电梯输送线将货物送入目标楼层
        self.logger.info("▶️ 货物进入楼层")
        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("📦 货物开始进入楼层...")
            await asyncio.sleep(1)
            self.plc.lift_to_everylayer(target_layer)

            self.logger.info("⏳ 输送线移动中...")
            await asyncio.sleep(2)
            # 等待电梯输送线工作结束
            if target_layer == 1:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1)
            elif target_layer == 2:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1)
            elif target_layer == 3:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1)
            elif target_layer == 4:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1)
            
            self.logger.info(f"✅ 货物到达 {target_layer} 层接驳位")
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC运行错误")
            return [False, "❌ PLC运行错误"]
        
        ############################################################
        # step 4: 车到电梯前等待
        ############################################################

        # 穿梭车移动到接驳位接货
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{target_layer}"
        if await self.car.car_current_location() != car_current_lift_pre_location:
            self.logger.info("⏳ 穿梭车开始移动...")
            await self.car.car_move(TASK_NO+3, car_current_lift_pre_location)
            
            # 等待穿梭车移动到位
            self.logger.info(f"⏳ 等待穿梭车前往 5,3,{target_layer} 位置...")
            await self.car.wait_car_move_complete_by_location(car_current_lift_pre_location)
            await asyncio.sleep(2)

            # car_status = await self.car.car_status()
            # if await self.car.car_current_location() == car_current_lift_pre_location and car_status['car_status'] == CarStatus.READY.value:
            if await self.car.car_current_location() == car_current_lift_pre_location:
                self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
            else:
                self.logger.warning(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
                return [False, "❌ 穿梭车运行错误"]

        ############################################################
        # step 5: 穿梭车载货进入目标位置
        ############################################################
        
        # 发送取货进行中信号给PLC
        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 穿梭车开始取货...")
            await asyncio.sleep(1)
            self.plc.pick_in_process(target_layer)
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC接收取货信号异常")
            return [False, "❌ PLC接收取货信号异常"]
        
        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车将货物移动到目标位置 {TARGET_LOCATION}")
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car.good_move(TASK_NO+4, TARGET_LOCATION)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
        await self.car.wait_car_move_complete_by_location(TARGET_LOCATION)
        await asyncio.sleep(2)
        
        # car_status = await self.car.car_status()
        # if await self.car.car_current_location() == TARGET_LOCATION and car_status['car_status'] == CarStatus.READY.value:
        if await self.car.car_current_location() == TARGET_LOCATION:
            self.logger.info(f"✅ 货物已到达 目标位置 {TARGET_LOCATION}")
        else:
            self.logger.error(f"❌ 货物未到达 目标位置 {TARGET_LOCATION}")
            return [False, "❌ 穿梭车运行错误"]
        
        ############################################################
        # step 6: 
        ############################################################

        # 发送取货完成信号给PLC
        if await self.plc.async_connect() and self.plc.plc_checker():
            await asyncio.sleep(1)
            self.plc.pick_complete(target_layer)
            self.logger.info(f"✅ 入库完成")
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]

        # 返回穿梭车位置
        last_location = await self.car.car_current_location()
        return [True, last_location]


    ############################################################
    ############################################################
    # 任务出库
    ############################################################
    ############################################################

    async def task_outband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
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
        car_location = await self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 目标货物坐标: {TARGET_LOCATION}")
        target_loc = list(map(int, TARGET_LOCATION.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 目标货物楼层: {target_layer}")

        # # 穿梭车不在任务层, 操作穿梭车到达任务入库楼层等待
        if car_layer != target_layer:
            car_location = await self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")

        # 电梯初始化: 移动到目标货物层
        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 移动空载电梯到 {target_layer} 层")
            await asyncio.sleep(2)
            if await self.plc.lift_move_by_layer(TASK_NO+1, target_layer):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]
            
        
        ############################################################
        # step 1: 穿梭车载货到楼层接驳位
        ############################################################
        
        self.logger.info(f"▶️ 出库开始")

        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车前往货物位置 {TARGET_LOCATION}")
        if await self.car.car_current_location() != TARGET_LOCATION:
            self.logger.info("⏳ 穿梭车开始移动...")
            await self.car.car_move(TASK_NO+2, TARGET_LOCATION)
            
            # 等待穿梭车进入接驳位
            self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
            await self.car.wait_car_move_complete_by_location(TARGET_LOCATION)
            await asyncio.sleep(2)
            
            # car_status = await self.car.car_status()
            # if await self.car.car_current_location() == TARGET_LOCATION and car_status['car_status'] == CarStatus.READY.value:
            if await self.car.car_current_location() == TARGET_LOCATION:
                self.logger.info(f"✅ 穿梭车已到达 货物位置 {TARGET_LOCATION}")
            else:
                self.logger.error(f"❌ 穿梭车未到达 货物位置 {TARGET_LOCATION}")
                return [False, "❌ 穿梭车运行错误"]

        # 发送放货进行中信号给PLC
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 穿梭车开始取货...")
            await asyncio.sleep(1)
            self.plc.feed_in_process(target_layer)
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]
        
        # 穿梭车将货物移动到楼层接驳位
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭车将货物移动到楼层接驳位输送线 {target_lift_pre_location}")
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car.good_move(TASK_NO+3, target_lift_pre_location)
        
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {target_lift_pre_location} 位置...")
        await self.car.wait_car_move_complete_by_location(target_lift_pre_location)
        await asyncio.sleep(2)
        
        # car_status = await self.car.car_status()
        # if await self.car.car_current_location() == target_lift_pre_location and car_status['car_status'] == CarStatus.READY.value:
        if await self.car.car_current_location() == target_lift_pre_location:
            self.logger.info(f"✅ 货物已到达 楼层接驳输送线位置 {target_lift_pre_location}")
        else:
            self.logger.error(f"❌ 货物未到达 楼层接驳输送线位置 {target_lift_pre_location}")
            return [False, "❌ 穿梭车运行错误"]
        

        ############################################################
        # step 2: 货物进入电梯
        ############################################################

        # 发送放货完成信号给PLC
        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"✅ 货物放置完成")
            await asyncio.sleep(2)
            self.plc.feed_complete(target_layer)

            self.logger.info(f"🚧 货物进入电梯")
            self.logger.info("📦 货物开始进入电梯...")
            await asyncio.sleep(1)
            self.logger.info("⏳ 输送线移动中...")
            # 等待电梯输送线工作结束
            await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
            self.logger.info("✅ 货物到达电梯")
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ 货物进入电梯失败")
            return [False, "❌ 货物进入电梯失败"]

        
        ############################################################
        # step 3: 电梯送货到1楼
        ############################################################

        # 电梯带货移动到1楼
        await asyncio.sleep(1)
        if await self.plc.async_connect():
            self.logger.info(f"🚧 移动电梯载货到1层")
            await asyncio.sleep(1)
            if await self.plc.lift_move_by_layer(TASK_NO+4, 1):
                await self.plc.async_disconnect()
            else:
                await self.plc.async_disconnect()
                self.logger.error("❌ 电梯运行错误")
                return [False, "❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ PLC 运行错误")
            return [False, "❌ PLC 运行错误"]

        
        ############################################################
        # step 4: 
        ############################################################

        await asyncio.sleep(1)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("🚧 货物离开电梯出库")
            await asyncio.sleep(1)
            self.logger.info("📦 货物开始离开电梯...")
            self.plc.lift_to_outband()
            self.logger.info("⏳ 输送线移动中...")
            # 等待电梯输送线工作结束
            await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)
            self.logger.info("✅ 货物到达出口")
            await asyncio.sleep(1)
            self.logger.info("✅ 出库完成")
            await self.plc.async_disconnect()
        else:
            await self.plc.async_disconnect()
            self.logger.error("❌ 货物离开电梯出库失败")
            return [False, "❌ 货物离开电梯出库失败"]

        
        # 返回穿梭车位置
        last_location = await self.car.car_current_location()
        return [True, last_location]
    
class DevicesControllerByStep(DevicesLogger):
    """
    [异步 - 设备控制器] - 联合PLC控制系统和穿梭车控制系统, 实现立体仓库设备自动化控制
    
    !!! 注意：此为设备安全与人生安全操作首要原则，必须遵守 !!!

    所有穿梭车的操作都要确保电梯在穿梭车所在楼层（因为只有电梯有对穿梭车的防飞出限位保险结构），避免穿梭车到达电梯口发生冲击力过大造成飞出“跳楼”危险。
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
        self.car = AsyncSocketCarController(self._car_ip, self._car_port)

    ############################################################
    ############################################################
    # 单步 动作
    ############################################################
    ############################################################
    
    ############################################################
    # 电梯动作
    ############################################################

    async def action_lift_move_backup(
            self,
            TASK_NO: int,
            LAYER: int
            ) -> list:
        """
        [动作 - 电梯移动] - 备用动作

        ::: param :::
        TASK_NO: int
        LAYER: int
        """
        self.logger.info(f"▶️ 电梯开始移动到{LAYER}层...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            await asyncio.sleep(2)
            if await self.plc.lift_move_by_layer(TASK_NO, LAYER):
                await self.plc.async_disconnect()
                return [True, f"✅ 电梯已到达{LAYER}层"]
            else:
                await self.plc.async_disconnect()
                return [False, "❌ 电梯运行错误"]
        else:
            await self.plc.async_disconnect()
            return [False ,"❌ PLC错误"]

    
    async def action_lift_move(
            self,
            TASK_NO: int,
            LAYER: int
            ) -> list:
        """
        [动作 - 电梯移动] - 包括尝试连接电梯发送指令

        ::: param :::
            TASK_NO: 任务编号
            LAYER: 层数
        """
        max_attempts = 5  # 最多尝试5次，约60秒超时
        attempt = 0
        
        await asyncio.sleep(2)
        if not (await self.plc.async_connect() and self.plc.plc_checker()):
            await asyncio.sleep(2)
            await self.plc.async_disconnect()
            return [False, "❌ PLC连接失败"]
        
        self.logger.info(f"▶️ 电梯开始移动到{LAYER}层...")
        
        try:
            while attempt < max_attempts:
                await asyncio.sleep(2)
                current_layer = self.plc.get_lift()
                await asyncio.sleep(2)
                if current_layer == LAYER:
                    return [True, f"✅ 电梯已到达{LAYER}层"]
                
                # 执行电梯移动操作
                move_result = await self.plc.lift_move_by_layer(TASK_NO, LAYER)
                if not move_result:
                    return [False, "❌ 电梯移动指令发送失败"]
                
                attempt += 1
                await asyncio.sleep(2)  # 等待电梯移动
                
            return [False, "❌ 电梯移动超时"]
        finally:
            await self.plc.async_disconnect()
        
    
    async def get_lift_layer(self) -> list:
        """
        [读取 - 电梯位置]

        ::: return :::
            [True, layer]
        """
        self.logger.info("⌛️ 正在获取电梯层号...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            await asyncio.sleep(2)
            layer = self.plc.get_lift()
            await self.plc.async_disconnect()
            return [True, layer]
        else:
            await self.plc.async_disconnect()
            return [False ,"❌ PLC错误"]


    ############################################################
    # 输送线动作
    ############################################################

    async def action_inband_to_lift(self) -> list:
        """
        [动作 - 入口-电梯输送线] - 货物从入库口进入电梯
        """

        self.logger.info("🚧 入口-电梯输送线启动...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("📦 货物开始进入电梯...")
            await asyncio.sleep(2)
            if self.plc.inband_to_lift():
                self.logger.info("⏳ 输送线移动中...")
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)
            
                await self.plc.async_disconnect()
                return [True, "✅ 货物到达电梯"]
            else:
                await self.plc.async_disconnect()
                return [False, "❌ 货物未到达"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]
        
    
    async def action_lift_to_outband(self) -> list:
        """
        [动作 - 电梯-出口输送线] - 货物从电梯进入出库口
        """

        self.logger.info("🚧 电梯-出口输送线启动...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info("📦 货物开始进入出库口...")
            await asyncio.sleep(2)
            if self.plc.lift_to_outband():
                self.logger.info("⏳ 输送线移动中...")
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_MAN.value, 1)
            
                await self.plc.async_disconnect()
                return [True, "✅ 货物到达出库口"]
            else:
                await self.plc.async_disconnect()
                return [False, "❌ 货物未到达"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]
    

    async def action_lift_to_everylayer(
            self, 
            TARGET_LAYER: int
            ) -> list:
        """
        [动作 - 电梯-楼层输送线] - 货物从电梯输送线进入楼层输送线

        ::: param :::
            TARGET_LAYER: 目标楼层
        """
        self.logger.info(f"🚧 {TARGET_LAYER}层电梯-{TARGET_LAYER}输送线启动...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"📦 货物开始进入{TARGET_LAYER}层...")
            await asyncio.sleep(2)
            self.plc.lift_to_everylayer(TARGET_LAYER)

            self.logger.info(f"⏳ {TARGET_LAYER}层输送线移动中...")
            await asyncio.sleep(0.5)
            # 等待电梯输送线工作结束
            if TARGET_LAYER == 1:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1030.value, 1)
            elif TARGET_LAYER == 2:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1040.value, 1)
            elif TARGET_LAYER == 3:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1050.value, 1)
            elif TARGET_LAYER == 4:
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1060.value, 1)
            
            await self.plc.async_disconnect()
            return [True, f"✅ 货物到达 {TARGET_LAYER} 层接驳位"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]
        
    
    async def action_pick_in_process(
            self,
            TARGET_LAYER: int
            ) -> list:
        """
        [动作 - 取货进行中 - 入库] - 发送取货进行中信号给PLC

        ::: param :::
            TARGET_LAYER: 目标层
        """
        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 发送{TARGET_LAYER}层取货进行中信号...")
            await asyncio.sleep(2)
            if self.plc.pick_in_process(TARGET_LAYER):
                await self.plc.async_disconnect()
                return [True, f"✅ {TARGET_LAYER}层取货进行中信号发送成功"]
            else:
                await self.plc.async_disconnect()
                return [False, f"❌ {TARGET_LAYER}层取货进行中信号发送失败"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]
        
    
    async def action_pick_complete(
            self,
            TARGET_LAYER: int
            ) -> list:
        """
        [动作 - 取货完成 - 入库] - 发送取货完成信号给PLC

        ::: param :::
            TARGET_LAYER: 目标层
        """
        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 发送{TARGET_LAYER}层取货完成信号...")
            await asyncio.sleep(2)
            if self.plc.pick_complete(TARGET_LAYER):
                await self.plc.async_disconnect()
                return [True, f"✅ 发送{TARGET_LAYER}层取货完成信号成功"]
            else:
                await self.plc.async_disconnect()
                return [False, f"❌ 发送{TARGET_LAYER}层取货完成信号失败"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]

        
    async def action_feed_in_process(
            self,
            TARGET_LAYER: int
            ) -> list:
        """
        [动作 - 放货进行中 - 出库] - 发送放货进行中信号给PLC

        ::: param :::
            TARGET_LAYER: 目标层
        """
        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 发送{TARGET_LAYER}层放货进行中信号...")
            await asyncio.sleep(2)
            if self.plc.feed_in_process(TARGET_LAYER):
                await self.plc.async_disconnect()
                return [True, f"✅ 发送{TARGET_LAYER}层放货进行中信号成功"] 
            else:
                await self.plc.async_disconnect()
                return [False, f"❌ 发送{TARGET_LAYER}层放货进行中信号失败"] 
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]
        
    
    async def action_feed_complete(
            self,
            TARGET_LAYER: int
            ) -> list:
        """
        [动作 - 取货完成 - 出库] - 发送放货完成信号给PLC

        ::: param :::
            TARGET_LAYER: 目标层
        """
        self.logger.info(f"🚧 {TARGET_LAYER}楼层-电梯输送线启动...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            self.logger.info(f"🚧 发送{TARGET_LAYER}层放货完成信号...")
            await asyncio.sleep(2)
            if self.plc.feed_complete(TARGET_LAYER):
                self.logger.info(f"✅ 发送{TARGET_LAYER}层放货完成信号成功")
    
                self.logger.info(f"⏳ {TARGET_LAYER}层接驳位和电梯输送线移动中...")
                await self.plc.wait_for_bit_change(11, DB_11.PLATFORM_PALLET_READY_1020.value, 1)

                await self.plc.async_disconnect()
                return [True, f"✅ 货物到达{TARGET_LAYER}层电梯内"]
            else:
                await self.plc.async_disconnect()
                return [False, f"❌ 发送{TARGET_LAYER}层放货完成信号失败, 货物未到达"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC错误"]


    ############################################################
    # 穿梭车动作
    ############################################################

    async def action_car_move(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
        """
        [动作 - 移动车辆]

        ::: param :::
            TASK_NO: int
            TARGET_LOCATION: str
        """
        await asyncio.sleep(1)
        car_info = await self.car.car_current_location()
        
        if car_info == "error":
            return [False, "❌ 穿梭车运行错误"]
        
        elif car_info != TARGET_LOCATION:
            
            self.logger.info("⏳ 穿梭车开始移动...")
            await asyncio.sleep(1)
            if await self.car.car_move(TASK_NO, TARGET_LOCATION):
                
                self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
                await self.car.wait_car_move_complete_by_location(TARGET_LOCATION)
                
                await asyncio.sleep(1)
                if await self.car.car_current_location() == TARGET_LOCATION:
                    return [True, f"✅ 穿梭车已到达 {TARGET_LOCATION} 位置"]
                else:
                    return [False, f"❌ 穿梭车未到达 {TARGET_LOCATION} 位置"]
            else:
                return [False, "❌ 穿梭车运行错误"]
        else:
            return [True, f"✅ 穿梭车已到达 {TARGET_LOCATION} 位置"]
    

    async def action_good_move(
            self,
            TASK_NO: int,
            SOURCE_LOCATION: str,
            TARGET_LOCATION: str
            ) -> list:
        """
        [动作 - 移动货物]

        ::: params :::
            TASK_NO: int 任务编号
            SOURCE_LOCATION: str 源坐标
            TARGET_LOCATION: str 目标坐标
        """
        self.logger.info(f"⏳ 穿梭车前往需要移动货物 {SOURCE_LOCATION} 处...")
        move_car_info =  await self.action_car_move(TASK_NO, SOURCE_LOCATION)
        if move_car_info[0]:
            self.logger.info(f"✅ {move_car_info[1]}")
        else:
            self.logger.error(f"❌ {move_car_info[1]}")
            return [False, f"❌ {move_car_info[1]}"]
        
        self.logger.info(f"⏳ 移动货物正在前往 {TARGET_LOCATION} 处...")
        await asyncio.sleep(1)
        if await self.car.car_current_location() != TARGET_LOCATION:
            
            self.logger.info("⏳ 货物开始移动...")
            await asyncio.sleep(1)
            if await self.car.good_move(TASK_NO+1, TARGET_LOCATION):

                self.logger.info(f"⏳ 等待货物前往 {TARGET_LOCATION} 位置...")
                await self.car.wait_car_move_complete_by_location(TARGET_LOCATION)
                
                await asyncio.sleep(1)
                if await self.car.car_current_location() == TARGET_LOCATION:
                    return [True, f"{TARGET_LOCATION}"]
                else:
                    return [False, f"❌ 货物未到达目标位置 {TARGET_LOCATION}"]
            else:
                return [False, "❌ 穿梭车运行错误"]
        else:
            return [True, f"{TARGET_LOCATION}"]
        
    
    ############################################################
    # PLC 穿梭车 系统联动
    ############################################################
    
    async def comb_change_car_location(
            self,
            TASK_NO: int,
            TARGET_LAYER: int
            ) -> list:
        """
        [联动 - 改变穿梭车位置] 仅用于在电梯内修改位置。

        ::: param :::
            TASK_NO: 任务编号
            TARGET_LAYER: 目标层
        """

        self.logger.info(f"▶️ 正在获取电梯层号...")

        await asyncio.sleep(2)
        if await self.plc.async_connect() and self.plc.plc_checker():
            await asyncio.sleep(2)
            if self.plc.get_lift() == TARGET_LAYER and self.plc.read_bit(11, DB_11.IDLE.value) == 1:
                self.logger.info(f"🚧 电梯到达{TARGET_LAYER}, 开始更新穿梭车位置...")
                await self.plc.async_disconnect()
                
                car_target_lift_location = f"6,3,{TARGET_LAYER}"
                
                await asyncio.sleep(1)
                if await self.car.change_car_location(TASK_NO, car_target_lift_location):
                    return [True, f"✅ 更新穿梭车位置 -> {car_target_lift_location}"]
                else:
                    return [False, "❌ 更新穿梭车位置失败"]
            else:
                await self.plc.async_disconnect()
                return [False, f"❌ 电梯未到达 {TARGET_LAYER}层"]
        else:
            await self.plc.async_disconnect()
            return [False, "❌ PLC未连接"]
    

    ############################################################
    ############################################################
    # 穿梭车全库跨层
    ############################################################
    ############################################################
    
    async def car_cross_layer(
            self,
            TASK_NO: int,
            TARGET_LAYER: int
            ) -> list:
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
        car_location = await self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        
        car_cur_loc = list(map(int, car_location.split(',')))
        car_current_floor = car_cur_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_current_floor} 层")

        # 获取目标位置 -> 坐标: 如, "1,1,1" 楼层: 如, 1
        self.logger.info(f"🧭 穿梭车目的楼层: {TARGET_LAYER} 层")

        
        ############################################################
        # step 1: 电梯到位接车
        ############################################################

        self.logger.info(f"🚧 电梯移动到穿梭车楼层 {car_current_floor}层...")
        
        lift_move_info =  await self.action_lift_move(TASK_NO, car_current_floor)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == car_current_floor:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]

        
        ############################################################
        # step 2: 车到电梯前等待
        ############################################################

        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        self.logger.info(f"🚧 移动空载电梯到电机口 {car_current_lift_pre_location}...")

        car_move_info = await self.action_car_move(TASK_NO+1, car_current_lift_pre_location)
        if car_move_info[0]:
            self.logger.info(f"{car_move_info[1]}")
        else:
            self.logger.error(f"{car_move_info[1]}")
            return [False, car_move_info[1]]
        
        ############################################################
        # step 3: 车进电梯
        ############################################################

        # 穿梭车进入电机
        car_current_lift_location = f"6,3,{car_current_floor}"
        self.logger.info(f"🚧 穿梭车进入电梯内 {car_current_lift_location} ...")

        car_move_info = await self.action_car_move(TASK_NO+2, car_current_lift_location)
        if car_move_info[0]:
            self.logger.info(f"{car_move_info[1]}")
        else:
            self.logger.error(f"{car_move_info[1]}")
            return [False, car_move_info[1]]

        
        ############################################################
        # step 4: 电梯送车到目标层
        ############################################################

        self.logger.info(f"🚧 移动电梯载车到{TARGET_LAYER}层...")

        lift_move_info =  await self.action_lift_move(TASK_NO+3, TARGET_LAYER)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == TARGET_LAYER:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]
        

        ############################################################
        # step 5: 更新车坐标，更新车层坐标
        ############################################################

        self.logger.info(f"🚧 更新电梯内穿梭车车到{TARGET_LAYER}层位置...")
        
        comb_plc_car_info = await self.comb_change_car_location(TASK_NO+4, TARGET_LAYER)
        if comb_plc_car_info[0]:
            self.logger.info(f"{comb_plc_car_info[1]}")
        else:
            self.logger.error(f"{comb_plc_car_info[1]}")
            return [False, comb_plc_car_info[1]]

        
        ############################################################
        # step 6: 车进目标层
        ############################################################

        # 穿梭车离开提升机进入接驳位
        target_lift_pre_location = f"5,3,{TARGET_LAYER}"
        self.logger.info(f"🚧 穿梭车开始离开电梯进入接驳位 {target_lift_pre_location} ...")

        car_move_info = await self.action_car_move(TASK_NO+5, target_lift_pre_location)
        if car_move_info[0]:
            self.logger.info(f"{car_move_info[1]}")
        else:
            self.logger.error(f"{car_move_info[1]}")
            return [False, car_move_info[1]]


        ############################################################
        # step 7: 校准电梯水平操作
        ############################################################
        
        self.logger.info(f"🚧 校准电梯{TARGET_LAYER}层水平位置...")
        
        lift_move_info =  await self.action_lift_move(TASK_NO+6, TARGET_LAYER)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == TARGET_LAYER:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]
        
        # 返回穿梭车位置
        last_location = await self.car.car_current_location()
        return [True, last_location]


    ############################################################
    ############################################################
    # 任务入库
    ############################################################
    ############################################################

    async def task_inband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
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
        car_location = await self.car.car_current_location()
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
            car_location = await self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")


        ### 阻挡货物处理添加在此处 ###

        
        # 电梯初始化: 移动到1层
        self.logger.info(f"🚧 电梯移动到穿梭车楼层 {1}层...")
        
        lift_move_info =  await self.action_lift_move(TASK_NO+1, 1)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == 1:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]
        
        
        ############################################################
        # step 1: 货物进入电梯
        ############################################################
        
        self.logger.info("▶️ 入库开始...")

        # 人工放货到入口完成后, 输送线将货物送入电梯
        good_move_info = await self.action_inband_to_lift()
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            self.logger.error(f"{good_move_info[1]}")
            return [False, f"{good_move_info[1]}"]


        ############################################################
        # step 2: 电梯送货到目标层
        ############################################################
        
        self.logger.info(f"🚧 电梯载货到目标楼层 {target_layer}层...")

        lift_move_info =  await self.action_lift_move(TASK_NO+2, target_layer)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == target_layer:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]

        
        ############################################################
        # step 3: 货物进入目标层
        ############################################################

        # 电梯载货到到目标楼层, 电梯输送线将货物送入目标楼层
        self.logger.info(f"🚧 货物进入 {target_layer}层...")
        
        good_move_info =  await self.action_lift_to_everylayer(target_layer)
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            return [False, f"{good_move_info[1]}"]
        
        
        ############################################################
        # step 4: 发送取货进行中信号给PLC
        ############################################################

        self.logger.info(f"🚧 发送{target_layer}层取货进行中信号给PLC...")

        good_move_info =  await self.action_pick_in_process(target_layer)
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            return [False, f"{good_move_info[1]}"]
        

        ############################################################
        # step 5: 穿梭车将接驳位货物移动到目标位置
        ############################################################
        
        car_current_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭车移动 {car_current_lift_pre_location} 货物到 {TARGET_LOCATION} ...")

        good_move_info = await self.action_good_move(
            TASK_NO+3,
            car_current_lift_pre_location,
            TARGET_LOCATION
            )
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            self.logger.error(f"{good_move_info[1]}")
            return [False, good_move_info[1]]
        
        
        ############################################################
        # step 6: 发送取货完成信号给PLC
        ############################################################
        
        self.logger.info(f"🚧 发送{target_layer}层取货完成信号给PLC...")

        good_move_info =  await self.action_pick_complete(target_layer)
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            self.logger.error(f"{good_move_info[1]}")
            return [False, f"{good_move_info[1]}"]
        
        
        self.logger.info("✅ 入库完成")

        # 返回穿梭车位置
        last_location = await self.car.car_current_location()
        return [True, last_location]


    ############################################################
    ############################################################
    # 任务出库
    ############################################################
    ############################################################

    async def task_outband(
            self,
            TASK_NO: int,
            TARGET_LOCATION: str
            ) -> list:
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
        car_location = await self.car.car_current_location()
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 目标货物坐标: {TARGET_LOCATION}")
        target_loc = list(map(int, TARGET_LOCATION.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 目标货物楼层: {target_layer}")

        # # 穿梭车不在任务层, 操作穿梭车到达任务入库楼层等待
        if car_layer != target_layer:
            car_location = await self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")

        
        ### 阻挡货物处理添加在此处 ###
        
        
        # 电梯初始化: 移动到目标货物层
        self.logger.info(f"🚧 电梯移动到目标层 {target_layer} 层")

        lift_move_info =  await self.action_lift_move(TASK_NO+1, target_layer)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == target_layer:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]
            
        
        ############################################################
        # step 1: 发送放货进行中信号给PLC
        ############################################################
        
        self.logger.info(f"▶️ 出库开始...")

        self.logger.info(f"🚧 发送{target_layer}层放货进行中信号给PLC...")

        good_move_info =  await self.action_feed_in_process(target_layer)
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            return [False, f"{good_move_info[1]}"]

        ############################################################
        # step 2: 穿梭车载货到楼层接驳位
        ############################################################
        
        self.logger.info(f"▶️ 出库开始...")
        
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧  穿梭车移动 {TARGET_LOCATION} 货物到 {target_lift_pre_location} ...")

        good_move_info = await self.action_good_move(
            TASK_NO+2,
            TARGET_LOCATION,
            target_lift_pre_location
            )
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            self.logger.error(f"{good_move_info[1]}")
            return [False, good_move_info[1]]
        

        ############################################################
        # step 3: 货物进入电梯，发送放货完成信号给PLC
        ############################################################

        self.logger.info(f"🚧 发送{target_layer}层放货完成信号给PLC...")

        good_move_info =  await self.action_feed_complete(target_layer)
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            return [False, f"{good_move_info[1]}"]

        
        ############################################################
        # step 4: 电梯送货到1楼
        ############################################################

        self.logger.info(f"🚧 移动电梯载货到 {1}层")

        lift_move_info =  await self.action_lift_move(TASK_NO+3, 1)
        if lift_move_info[0]:
            self.logger.info(f"{lift_move_info[1]}")
            lift_layer_info = await self.get_lift_layer()
            if lift_layer_info[0] and lift_layer_info[1] == 1:
                self.logger.info(f"✅ 再次确认电梯到达{lift_layer_info[1]}层")
            else:
                self.logger.error(f"{lift_layer_info[1]}")
                return [False, f"{lift_layer_info[1]}"]
        else:
            self.logger.error(f"{lift_move_info[1]}")
            return [False, f"{lift_move_info[1]}"]

        
        ############################################################
        # step 5: 货物从电梯进入出库口
        ############################################################

        self.logger.info("🚧 货物离开电梯出库...")
        
        good_move_info =  await self.action_lift_to_outband()
        if good_move_info[0]:
            self.logger.info(f"{good_move_info[1]}")
        else:
            self.logger.error(f"{good_move_info[1]}")
            return [False, f"{good_move_info[1]}"]
        
        
        self.logger.info("✅ 出库完成")
        
        # 返回穿梭车位置
        last_location = await self.car.car_current_location()
        return [True, last_location]