# devices/devices_controller.py
import random
import time

from .plc_controller import PLCController
from .plc_enum import PLCAddress, LIFT_TASK_TYPE, FLOOR_CODE
from .car_controller import CarController
from .car_enum import CarStatus

class DevicesController(PLCController, CarController):
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
        PLCController.__init__(self, PLC_IP)
        CarController.__init__(self, CAR_IP, CAR_PORT)


    ############################################################
    ############################################################
    # 穿梭车全库跨层
    ############################################################
    ############################################################
    
    async def car_cross_layer(
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
        # step 0:
        ############################################################

        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  await self.car_current_location(1)
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_cur_loc = list(map(int, car_location.split(',')))
        car_current_floor = car_cur_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_current_floor} 层")

        # 获取目标位置 -> 坐标: 如, "1,1,1" 楼层: 如, 1
        self.logger.info(f"🧭 穿梭车目的楼层: {TARGET_LAYER} 层")

        
        ############################################################
        # step 1: 
        ############################################################

        # 电梯所需状态
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value) # 电梯运行状态 0: 停止 1: 运行
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        # 电梯到达穿梭车所在层
        self.logger.info("🚧 移动空载电梯到穿梭车楼层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.IDEL, TASK_NO, car_current_floor)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯已到达穿梭车所在楼层 {self.get_lift()} 层")

        
        ############################################################
        # step 2:
        ############################################################

        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car_move(car_current_lift_pre_location)
        # 等待穿梭车移动到位
        self.logger.info(f"⏳ 等待穿梭车前往 5,3,{car_current_floor} 位置...")
        await self.wait_car_move_complete_by_location(car_current_lift_pre_location)
        if await self.car_current_location(1) == car_current_lift_pre_location and self.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
        else:
            raise ValueError(f"❌ 穿梭车未到达 {car_current_lift_pre_location} 位置")
        
        
        ############################################################
        # step 3:
        ############################################################

        # 穿梭车进入电机
        self.logger.info("🚧 穿梭车进入电梯")
        car_current_lift_location = f"6,3,{car_current_floor}"
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car_move(car_current_lift_location)
        # 等待穿梭车进入电梯
        self.logger.info(f"⏳ 等待穿梭车前往 电梯内 6,3,{car_current_floor} 位置...")
        await self.wait_car_move_complete_by_location(car_current_lift_location)
        if await self.car_current_location(1) == car_current_lift_pre_location and self.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 电梯内 {car_current_lift_location} 位置")
        else:
            raise ValueError(f"❌ 穿梭车未到达 电梯内 {car_current_lift_location} 位置")

        
        ############################################################
        # step 4:
        ############################################################

        # 电梯带穿梭车移动到 目标楼层
        # 任务安全状态识别位
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value)
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        self.logger.info("🚧 移动电梯载车到目标楼层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.CAR, TASK_NO+1, TARGET_LAYER)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯已到达 目标楼层 {self.get_lift()} 层")
        
       
        ############################################################
        # step 5:
        ############################################################

        # 更新穿梭车楼层坐标
        if self.get_lift() == TARGET_LAYER and self.read_bit(11, PLCAddress.IDLE.value) == 1:
            self.logger.info("🚧 更新穿梭车楼层")
            car_target_lift_location = f"6,3,{TARGET_LAYER}"
            await self.change_car_location(TASK_NO+2, car_target_lift_location)
            self.logger.info(f"✅ 穿梭车位置: {car_target_lift_location}")
        else:
            raise ValueError("❌ 电梯未到达")

        
        ############################################################
        # step 6:
        ############################################################

        # 穿梭车离开提升机进入接驳位
        target_lift_pre_location = f"5,3,{TARGET_LAYER}"
        self.logger.info(f"🚧 穿梭车开始离开电梯进入接驳位 {target_lift_pre_location}")
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car_move(target_lift_pre_location)
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 接驳位 {target_lift_pre_location} 位置...")
        await self.wait_car_move_complete_by_location(target_lift_pre_location)
        if await self.car_current_location(1) == target_lift_pre_location and self.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 指定楼层 {TARGET_LAYER} 层")
        else:
            raise ValueError(f"❌ 穿梭车未到达 指定楼层 {TARGET_LAYER} 层")
        

        ############################################################
        # step 7: 校准电梯水平操作
        ############################################################

        # 电梯所需状态
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value) # 电梯运行状态 0: 停止 1: 运行
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        # 电梯到达穿梭车所在层
        self.logger.info("🚧 空载校准电梯楼层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.IDEL, TASK_NO, TARGET_LAYER)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯已校准楼层 {self.get_lift()} 层")
        
        # 返回穿梭车位置
        last_location = await self.car_current_location(1)
        return last_location


    ############################################################
    ############################################################
    # 任务入库
    ############################################################
    ############################################################

    async def task_inband(
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
        # step 0:
        ############################################################

        # 穿梭车初始化
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  await self.car_current_location(1)
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
        # 电梯所需状态
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value)
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        self.logger.info("🚧 移动空载电梯到1层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.IDEL, TASK_NO+1, 1)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯初始化完成 当前所在层{self.get_lift()}")
        
        
        ############################################################
        # step 1:
        ############################################################
        
        # 人工放货到入口完成后, 输送线将货物送入电梯
        self.logger.info("▶️ 入库开始")
        self.logger.info("📦 货物开始进入电梯...")
        self.inband_to_lift()
        self.logger.info("⏳ 输送线移动中...")
        # 等待电梯输送线工作结束
        await self.wait_for_bit_change(11, PLCAddress.STATUS_1020.value, 1)
        self.logger.info("✅ 货物到达电梯中")


        ############################################################
        # step 2:
        ############################################################

        # 任务识别
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value)
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        # 电梯带货移动
        self.logger.info(f"🚧 移动电梯载货到目标楼层 {target_layer}层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.GOOD, TASK_NO+2, target_layer)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯运行结束, 货物到达 {self.get_lift()}层")

        
        ############################################################
        # step 3:
        ############################################################

        # 电梯载货到到目标楼层, 电梯输送线将货物送入目标楼层
        self.logger.info("▶️ 货物进入楼层")
        self.logger.info("📦 货物开始进入楼层...")
        self.lift_to_everylayer(target_layer)
        time.sleep(1)
        self.logger.info("⏳ 输送线移动中...")
        # 等待电梯输送线工作结束
        await self.wait_for_bit_change(11, PLCAddress.STATUS_1020.value, 1)
        self.logger.info("✅ 货物到达楼层接驳位")

        ############################################################
        # step 4: 穿梭车载货进入目标位置
        ############################################################
        
        # 发送取货进行中信号给PLC
        self.logger.info(f"🚧 穿梭车开始取货...")
        self.pick_in_process(target_layer)
        
        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车将货物移动到目标位置 {TARGET_LOCATION}")
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.good_move(TARGET_LOCATION)
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
        await self.wait_car_move_complete_by_location(TARGET_LOCATION)
        if await self.car_current_location(1) == TARGET_LOCATION and self.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 目标位置 {TARGET_LOCATION}")
        else:
            raise ValueError(f"❌ 货物未到达 目标位置 {TARGET_LOCATION}")
        
        ############################################################
        # step 5: 
        ############################################################

        # 发送取货完成信号给PLC
        self.pick_complete(target_layer)
        self.logger.info(f"✅ 入库完成")

        # 返回穿梭车位置
        last_location = await self.car_current_location(1)
        return last_location


    ############################################################
    ############################################################
    # 任务出库
    ############################################################
    ############################################################

    async def task_outband(
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
        # step 0:
        ############################################################

        # 穿梭车初始化
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  await self.car_current_location(1)
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
            car_location = await self.car_cross_layer(TASK_NO, target_layer)
            self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")

        # 电梯初始化: 移动到目标货物层
        # 电梯所需状态
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value)
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        self.logger.info(f"🚧 移动空载电梯到 {target_layer} 层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.IDEL, TASK_NO+1, target_layer)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯初始化完成 当前所在层{self.get_lift()}")
        
        
        ############################################################
        # step 1: 穿梭车载货到楼层接驳位
        ############################################################
        
        self.logger.info(f"▶️ 出库开始")

        # 穿梭车将货物移动到目标位置
        self.logger.info(f"🚧 穿梭车前往货物位置 {TARGET_LOCATION}")
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.car_move(TARGET_LOCATION)
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {TARGET_LOCATION} 位置...")
        await self.wait_car_move_complete_by_location(TARGET_LOCATION)
        if await self.car_current_location(1) == TARGET_LOCATION and self.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 穿梭车已到达 货物位置 {TARGET_LOCATION}")
        else:
            raise ValueError(f"❌ 穿梭车未到达 货物位置 {TARGET_LOCATION}")

        # 发送放货进行中信号给PLC
        self.logger.info(f"🚧 穿梭车开始取货...")
        self.feed_in_process(target_layer)
        
        # 穿梭车将货物移动到楼层接驳位
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭车将货物移动到楼层接驳位输送线 {target_lift_pre_location}")
        self.logger.info("⏳ 穿梭车开始移动...")
        await self.good_move(target_lift_pre_location)
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 {target_lift_pre_location} 位置...")
        await self.wait_car_move_complete_by_location(target_lift_pre_location)
        if await self.car_current_location(1) == target_lift_pre_location and self.car_status(1) == CarStatus.READY.value:
            self.logger.info(f"✅ 货物已到达 楼层接驳输送线位置 {target_lift_pre_location}")
        else:
            raise ValueError(f"❌ 货物未到达 楼层接驳输送线位置 {target_lift_pre_location}")
        
        
        ############################################################
        # step 2: 
        ############################################################

        # 发送放货完成信号给PLC
        self.logger.info(f"✅ 货物放置完成")
        self.feed_complete(target_layer)

        self.logger.info(f"🚧 货物进入电梯")
        self.logger.info("📦 货物开始进入电梯...")
        time.sleep(1)
        self.logger.info("⏳ 输送线移动中...")
        # 等待电梯输送线工作结束
        await self.wait_for_bit_change(11, PLCAddress.STATUS_1020.value, 1)
        self.logger.info("✅ 货物到达电梯中")

        
        ############################################################
        # step 3:
        ############################################################

        # 任务识别
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value)
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        # 电梯带货移动到1楼
        self.logger.info(f"🚧 移动电梯载货到1层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==0 and lift_has_cargo==1 and lift_has_car==0:
            self.logger.info("⏳ 电梯开始移动...")
            self.lift_move(LIFT_TASK_TYPE.GOOD, TASK_NO+2, 1)
            self.logger.info("⏳ 电梯移动中...")
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            self.logger.info(f"✅ 电梯运行结束, 货物到达 {self.get_lift()}层")

        
        ############################################################
        # step 4: 
        ############################################################

        self.logger.info(f"🚧 货物离开电梯出库")
        self.logger.info("📦 货物开始离开电梯...")
        self.lift_to_outband()
        self.logger.info("⏳ 输送线移动中...")
        # 等待电梯输送线工作结束
        await self.wait_for_bit_change(11, PLCAddress.STATUS_1010.value, 1)
        self.logger.info("✅ 货物到达出口")
        time.sleep(1)
        self.logger.info("✅ 出库完成")

        
        # 返回穿梭车位置
        last_location = await self.car_current_location(1)
        return last_location