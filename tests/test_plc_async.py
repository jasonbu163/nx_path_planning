# tests/test_plc_async.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import struct
import random
from devices.plc_service_asyncio import PLCService
from devices.plc_enum import PLCAddress, TASK_TYPE
import time
import logging
from snap7.client import Client

class Task(PLCService):
    def __init__(self, plc_ip:str, car_ip:str, car_port:int):
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('plc_test.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.service = Client()


    async def task_inband(self, target):
        """
        入库任务
        :param target: 入库坐标 如，(3,3,2)
        """
        try:
            self.logger.info(f"🔌 正在尝试连接到PLC {self.plc_ip}")
            await self.service.async_connect()
            
            if not self.service.is_connected():
                self.logger.error("❌ 连接失败，无法继续测试")
                return

            # 任务号
            task_num = random.randint(0,99)

            # 入库记录开始时间
            start = time.time()
            
            # 第一步: 提升机到位
            self.logger.info("⬆️ 提升机到达一层...")
            self.service.lift_move(TASK_TYPE.IDEL, task_num, 1)
            # 确认电梯到位后，清除到位状态
            if self.service.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                self.service.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)

            # 第二步: 确认电梯到位之后开始入库
            self.logger.info("🚚 开始执行入库操作第一步...")
            self.service.inband()
            # 等待plc动作完成
            self.logger.info("⏳ 等待PLC动作完成...")
            await self.service.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1020.value, 1)
                
            # 第三步 读取任务坐标楼层
            if target[2] == 2:
                self.logger.info("⬆️ 执行提升机动作...")
                self.service.lift_move(TASK_TYPE.GOOD, task_num+1, 2)
                # 等待提升机动作完成
                self.logger.info("⏳ 等待提升机动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
                self.logger.info("🆗 提升机动作完成...")
                # 确认电梯到位后，清除到位状态
                if self.service.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                    self.service.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            elif target[2] == 3:
                self.logger.info("⬆️ 执行提升机动作...")
                self.service.lift_move(TASK_TYPE.GOOD, task_num+1, 3)
                # 等待提升机动作完成
                self.logger.info("⏳ 等待提升机动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
                self.logger.info("🆗 提升机动作完成...")
                # 确认电梯到位后，清除到位状态
                if self.service.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                    self.service.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            elif target[2] == 4:
                self.logger.info("⬆️ 执行提升机动作...")
                self.service.lift_move(TASK_TYPE.GOOD, task_num+1, 4)
                # 等待提升机动作完成
                self.logger.info("⏳ 等待提升机动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
                self.logger.info("🆗 提升机动作完成...")
                # 确认电梯到位后，清除到位状态
                if self.service.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                    self.service.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            else:
                pass

            # 第四步 货物进入对应楼层
            if target[2] == 1:
                self.logger.info("开始执行进入一楼操作...")
                time.sleep(2)
                self.service.lift_to_everylayer(1)
                # 等待plc动作完成
                self.logger.info("⏳ 等待PLC动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1030, 1)
            elif target[2] == 2:
                self.logger.info("开始执行进入二楼操作...")
                time.sleep(2)
                self.service.lift_to_everylayer(2)
                # 等待plc动作完成
                self.logger.info("⏳ 等待PLC动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1040, 1)
            elif target[2] == 3:
                self.logger.info("开始执行进入三楼操作...")
                time.sleep(2)
                self.service.lift_to_everylayer(3)
                # 等待plc动作完成
                self.logger.info("⏳ 等待PLC动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1050, 1)
            elif target[2] == 4:
                self.logger.info("开始执行进入四楼操作...")
                time.sleep(2)
                self.service.lift_to_everylayer(4)
                # 等待plc动作完成
                self.logger.info("⏳ 等待PLC动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1060, 1)


            # 第五步 小车开始取料
            time.sleep(3)
            self.service.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1030.value, 1)
            # 小车移动货物
            # good_move()
            # 等待小车动作完成
            self.logger.info("⏳ 等待小车动作完成...")
            # 请按回车键确认小车放料完成！
            finish = input("人工确认小车取料, 完成请输入(ok):")
            if finish == "ok":
                self.logger.info("人工确认小车取料完成！！")
            time.sleep(1)
            # 写入取料完成信号
            self.service.write_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 1)
            if self.service.read_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 1) == 1:
                self.service.write_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 0)

            # 记录入库结束时间
            end = time.time()
            self.logger.info(f"✅ 完成动作，总用时{end - start:.2f}秒")
            
        except ConnectionError as ce:
            self.logger.error(f"🛑 连接错误: {str(ce)}")
        except Exception as e:
            self.logger.error(f"💥 意外错误: {str(e)}", exc_info=True)
        finally:
            if self.service.is_connected():
                self.service.disconnect()
                self.logger.info("🔌 PLC连接已手动关闭")


    async def task_outband(self, target):
        """
        入库任务
        :param target: 出库坐标 如，(3,3,2)
        """
        try:
            self.logger.info(f"🔌 正在尝试连接到PLC {self.plc_ip}")
            await self.service.async_connect()
            
            if not self.service.is_connected():
                self.logger.error("❌ 连接失败，无法继续测试")
                return
            
            # 任务号
            task_num = random.randint(0,99)

            # 入库记录开始时间
            start = time.time()
            
            # 第一步: 提升机到出库物料层
            # 读取任务坐标楼层
            current_layer = self.service.get_lift()
            if target[2] != current_layer:
                self.logger.info("⬆️ 执行提升机动作...")
                self.service.lift_move(TASK_TYPE.IDEL, task_num, target[2])
                # 等待提升机动作完成
                self.logger.info("⏳ 等待提升机动作完成...")
                await self.service.wait_for_bit_change(11, PLCAddress.RUNNING.value, 0)
                self.logger.info("🆗 提升机动作完成...")
                # 确认电梯到位后，清除到位状态
                if self.service.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
                    self.service.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            else:
                pass

            # logger.info("🚚 开始执行取货操作第一步...")
            # plc.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1030.value, 1)
            # # 小车移动货物
            # # good_move()
            # # 等待小车动作完成
            # logger.info("⏳ 等待小车动作完成...")
            # finish = input("人工确认小车放料, 完成请输入(ok):")
            # if finish == "ok":
            #     logger.info("人工确认小车放料完成！！")
            # time.sleep(1)
            # # 写入放料完成信号
            # plc.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1)
            # time.sleep(1)
            # if plc.read_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1):
            #     plc.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 0)

            # 第二步
            # logger.info("⬆️ 开始执行升降操作...")
            # logger.info("⬆️ 目标层到达")
            # target_floor = struct.pack("!H", 1)
            # if plc.get_lift() == target_floor:
            #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 1)
            #     time.sleep(2)
            #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
            

            # # 第三步
            # logger.info("开始执行进入提升机操作...")
            # # plc.floor_to_lift(1)
            # # 等待plc动作完成
            # logger.info("⏳ 等待PLC动作完成...")
            # await plc.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1020.value, 1)

            # # 第四步
            # logger.info("开始执行提升机出库操作...")
            # plc.outband()
            # await plc.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1020.value, 1)

            # 记录出库结束时间
            end = time.time()
            self.logger.info(f"✅ 完成动作，总用时{end - start:.2f}秒")
                
        except ConnectionError as ce:
            self.logger.error(f"🛑 连接错误: {str(ce)}")
        except Exception as e:
            self.logger.error(f"💥 意外错误: {str(e)}", exc_info=True)
        finally:
            if self.service.is_connected():
                self.service.disconnect()
                self.logger.info("🔌 PLC连接已手动关闭")



async def main():
    plc_ip = "192.168.8.10"
    car_ip = "192.168.8.30"
    car_port = 2504
    plc = PLCService(plc_ip, car_ip, car_port)
    await plc.async_connect()
    
    # task_location = (3,2,2)

    ############### 入库 ##################
    # await plc.task_inband(task_location)
        
    ############### 出库 ##################
    # await plc.task_outband(task_location)
    
    ########################## 车辆跨层 ################################
    # car_location = (3,3,2)
    # await plc.car_to_floor(car_location, 1)


    ######################### 测试电梯移动 ##############################
    # task_num = random.randint(0,99)
    # plc.lift_move(TASK_TYPE.IDEL, task_num, end_floor=2)
    # plc.lift_move(TASK_TYPE.CAR, task_num, end_floor=1)

    # time.sleep(2) # 等待两秒后必能监控到电梯正在运行的状态
    # print(f"提升机运行状态：{plc.read_bit(11, PLCAddress.RUNNING.value)}")

    ######################### 测试入提升机移动 ##############################
    # plc.inband()

    ######################## 测试监控状态完成代码 ################################

    # ⚠️注意： 监控目标工位即可，
    # 比如：
    # 1010 -> 1020 就监控 1020 的托盘到位状态变化
    # 1020 -> 1010 就监控 1010 的托盘到位状态变化

    # time.sleep(1)
    # await plc.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1020.value, 1)
    # time.sleep(1)

    ######################### 测试入提升机移动 ##############################
    # plc.outband()

    ######################### 测试电梯 -》库内 ##############################
    # # 确认电梯到位后，清除到位状态
    # if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
    #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)
    # # 开始执行物料入库动作
    # plc.lift_to_everylayer(1)
    # # 等待plc动作完成
    # # logger.info("⏳ 等待PLC动作完成...")
    # await plc.wait_for_bit_change(11, PLCAddress.PLATFORM_PALLET_READY_1030.value, 1)
    
    # # 发送小车 取料中信号
    # time.sleep(3)
    # plc.write_bit(12, PLCAddress.PICK_IN_PROGRESS_1030.value, 1)
    # # 小车移动货物
    # # good_move()
    # # 等待小车动作完成
    # # logger.info("⏳ 等待小车动作完成...")
    # print("⏳ 等待小车动作完成...")
    # # 请按回车键确认小车放料完成！
    # finish = input("人工确认小车取料, 完成请输入(ok):")
    # if finish == "ok":
    #     # logger.info("人工确认小车取料完成！！")
    #     print("👷取料完成")

    # time.sleep(1)
    # # 写入取料完成信号
    # plc.write_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 1)
    # if plc.read_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 1) == 1:
    #     plc.write_bit(12, PLCAddress.PICK_COMPLETE_1030.value, 0)

    ######################### 测试 库内 -》电梯 ##############################
    
    # logger.info("🚚 开始执行放货操作第一步...")
    print("🚚 开始执行放货操作第一步...")
    plc.write_bit(12, PLCAddress.FEED_IN_PROGRESS_1030.value, 1)
    # 小车移动货物
    # good_move()
    # 等待小车动作完成
    # logger.info("⏳ 等待小车动作完成...")
    print("⏳ 等待小车动作完成...")
    finish = input("人工确认小车放料, 完成请输入(ok):")
    if finish == "ok":
        # logger.info("人工确认小车放料完成！！")
        print("人工确认小车放料完成！！")

    time.sleep(1)
    # 写入放料完成信号
    plc.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1)
    time.sleep(1)
    if plc.read_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 1):
        plc.write_bit(12, PLCAddress.FEED_COMPLETE_1030.value, 0)

    ######################## 电梯清零 #################################
    # # 确认电梯到位后，清除到位状态
    # if plc.read_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value) == 1:
    #     plc.write_bit(12, PLCAddress.TARGET_LAYER_ARRIVED.value, 0)


    await plc.disconnect()

if __name__ == "__main__":
    
    # 运行主异步函数
    asyncio.run(main())