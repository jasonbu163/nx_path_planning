import random
import time
from .service_asyncio import (
    DevicesService,
    PLCAddress,
    TASK_TYPE,
    CarStatus
    )

class AutoService(DevicesService):
    """
    自动服务
    """
    def __init__(self, plc_ip: str, car_ip: str, car_port: int):
        super().__init__(plc_ip, car_ip, car_port)

    # 小车换层
    async def car_cross_layer(self, target_layer: int):
        """
        穿梭车跨层
        :::param traget_location: 目标楼层 如，1层为：1
        """
        # 任务号
        task_num = random.randint(100, 999) # 随机生成一个3位数整数

        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  await self.car_current_location(1)
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_cur_loc = list(map(int, car_location.split(',')))
        car_current_floor = car_cur_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_current_floor}")
        
        # 获取目标位置 -> 坐标: 如, "1,1,1" 楼层: 如, 1
        self.logger.info(f"🧭 穿梭车目的楼层: {target_layer}")

        
        # step 1: 
        # 电梯所需状态
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value) # 电梯运行状态 0: 停止 1: 运行
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        # 提升机到达小车所在层
        self.logger.info("🚧 移动空载电梯到穿梭车楼层")
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==0:
            self.lift_move(TASK_TYPE.IDEL, task_num, car_current_floor)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            # 
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            self.logger.info("✅ 提升机已到达穿梭车所在楼层")
        else:
            self.logger.info("🚧 提升机正在运行中，等待提升机到达穿梭车所在楼层")
            # 等待电梯到达楼层 读取电梯是否空闲
            await self.wait_for_bit_change(11, PLCAddress.IDLE.value, 1)
            self.logger.info("✅ 提升机已到达穿梭车所在楼层")

        
        # step 2:
        # 穿梭车先进入电梯口，不直接进入电梯，要避免冲击力过大造成危险
        self.logger.info("🚧 移动空载电梯到电机口")
        car_current_lift_pre_location = f"5,3,{car_current_floor}"
        await self.car_move(car_current_lift_pre_location)
        # 等待穿梭车移动到位
        self.logger.info(f"⏳ 等待穿梭车前往 5,3,{car_current_floor} 位置...")
        await self.wait_car_move_complete_by_location(car_current_lift_pre_location)
        if await self.car_current_location(1) == car_current_lift_pre_location and self.car_status(1) == CarStatus.CAR_READY.value:
            self.logger.info(f"✅ 穿梭车已到达 {car_current_lift_pre_location} 位置")
        else:
            raise ValueError(f"穿梭车未到达 {car_current_lift_pre_location} 位置")
        
       
        # step 3:
        # 穿梭车进入电机
        self.logger.info("🚧 穿梭车开始进入电梯")
        car_current_lift_location = f"6,3,{car_current_floor}"
        await self.car_move(car_current_lift_location)
        # 等待穿梭车进入电梯
        self.logger.info(f"⏳ 等待穿梭车前往 电梯 6,3,{car_current_floor} 位置...")
        await self.wait_car_move_complete_by_location(car_current_lift_location)
        if await self.car_current_location(1) == car_current_lift_pre_location and self.car_status(1) == CarStatus.CAR_READY.value:
            self.logger.info(f"✅ 穿梭车已到达 电梯 {car_current_lift_location} 位置")
        else:
            raise ValueError(f"穿梭车未到达 电梯 {car_current_lift_location} 位置")

        
        # step 4:
        # 电梯带穿梭车移动到 目标楼层
        # 任务安全状态识别位
        lift_running = self.read_bit(11, PLCAddress.RUNNING.value)
        lift_idle = self.read_bit(11, PLCAddress.IDLE.value)
        lift_no_cargo = self.read_bit(11, PLCAddress.NO_CARGO.value)
        lift_has_car = self.read_bit(11, PLCAddress.HAS_CAR.value)
        lift_has_cargo = self.read_bit(11, PLCAddress.HAS_CARGO.value)
        if lift_running==0 and lift_idle==1 and lift_no_cargo==1 and lift_has_cargo==0 and lift_has_car==1:
            self.lift_move(TASK_TYPE.CAR, task_num+1, target_layer)
            # 确认电梯到位后，清除到位状态
            if self.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            
            time.sleep(2)
            await self.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
            self.logger.info("✅ 提升机已到达 目标楼层")
        else:
            self.logger.info("🚧 提升机正在运行中，等待提升机到达 目标楼层")
            # 等待电梯到达楼层 读取电梯是否空闲
            await self.wait_for_bit_change(11, PLCAddress.IDLE.value, 1)
            self.logger.info("✅ 提升机已到达 目标楼层")
        
       
        # step 5:
        # 更新穿梭车楼层坐标
        if self.get_lift() == target_layer and self.read_bit(11, PLCAddress.IDLE.value) == 1:
            self.logger.info("🚧 更新穿梭车楼层")
            car_target_lift_location = f"6,3,{target_layer}"
            msg = await self.change_car_location(car_target_lift_location)
            self.logger.info(msg)
        else:
            raise ValueError("穿梭车未到达 提升机")

        
        # step 6:
        # 穿梭车离开提升机进入接驳位
        target_lift_pre_location = f"5,3,{target_layer}"
        self.logger.info(f"🚧 穿梭开始离开提升机进入接驳位 {target_lift_pre_location}")
        await self.car_move(target_lift_pre_location)
        # 等待穿梭车进入接驳位
        self.logger.info(f"⏳ 等待穿梭车前往 接驳位 {target_lift_pre_location} 位置...")
        await self.wait_car_move_complete_by_location(target_lift_pre_location)
        if await self.car_current_location(1) == target_lift_pre_location and self.car_status(1) == CarStatus.CAR_READY.value:
            self.logger.info(f"✅ 穿梭车已到达 指定楼层 {target_layer} 层")
        else:
            raise ValueError(f"穿梭车未到达 指定楼层 {target_layer} 层")
        
        # 返回穿梭车位置
        last_location = await self.car_current_location(1)
        
        return last_location

    async def auto_inband(self, target_location: str):
        """
        自动入库
        :::param traget_location: 货物入库目标位置, 如 "1,2,4"
        """
        # 任务号
        task_num = random.randint(100, 999) # 随机生成一个3位数整数

        # 获取穿梭车当前位置 用于判断小车是否在任务层
        # 获取穿梭车位置 -> 坐标: 如, "6,3,2" 楼层: 如, 2
        car_location =  await self.car_current_location(1)
        self.logger.info(f"🚗 穿梭车当前坐标: {car_location}")
        car_loc = list(map(int, car_location.split(',')))
        car_layer = car_loc[2]
        self.logger.info(f"🚗 穿梭车当前楼层: {car_layer}")
        # 拆解目标位置 -> 坐标: 如, "1,3,1" 楼层: 如, 1
        self.logger.info(f"📦 货物目标坐标: {target_location}")
        target_loc = list(map(int, target_location.split(',')))
        target_layer = target_loc[2]
        self.logger.info(f"📦 货物目标楼层: {target_layer}")

        # 穿梭车不在任务层
        if car_layer != target_layer:
            return
        
        # 穿梭车在
        elif car_layer == target_layer:
            return
        
        else:
            return


    async def auto_outband(self, target_location: str):
        """
        自动出库
        :::param traget_location: 出库货物位置, 如 "1,2,4"
        """
        return