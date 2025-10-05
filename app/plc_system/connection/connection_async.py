# /devices/plc_connection_module.py
import asyncio
import time
from typing import Union, Callable, Any

from snap7.client import Client

from app.utils.devices_logger import DevicesLogger
from app.core.config import settings
from ..enum import DB_2, DB_11

class ConnectionAsync(DevicesLogger):
    """
    PLC连接模块
    """
    def __init__(self, HOST: str):
        """
        [初始化PLC连接模块]\n
        ::: param :::\n
            HOST: 服务器主机地址, 如 "192.168.8.30"
        """
        super().__init__(self.__class__.__name__)
        self._ip = HOST
        self.client = Client()
        self._connected = False

        self._monitor_task = None  # 用于存储监控任务的引用
        self._stop_monitor = asyncio.Event()  # 停止监控的事件标志

    
    #####################################################
    ####################### 同步方法 #####################
    #####################################################

    def connect(self, retry_count: int = 3, retry_interval: float = 2.0) -> bool:
        """
        [同步连接PLC]
        """
        # 双重检查连接状态
        if self._connected and self.client.get_connected():
            self.logger.info("[PLC] 连接已存在，无需重新连接")
            return True
        
        # 如果已有连接但状态不一致，先断开
        if self._connected or self.client.get_connected():
            self.logger.warning("[PLC] 连接状态不一致，先关闭现有连接")
            self.disconnect()

        for attempt in range(1, retry_count + 1):
            try:
                self.logger.info(f"🔌 正在连接到 PLC: {self._ip} (rack=0, slot=1)")
                self.logger.info(f"[PLC] 尝试连接 {attempt}/{retry_count} {self._ip}")
                
                # 创建新的Client实例（避免重用问题连接）
                self.client = Client()
                
                # 尝试连接
                self.client.connect(self._ip, 0, 1)  # 默认 rack=0, slot=1
                self._connected = self.client.get_connected()

                if not self._connected:
                    self.logger.error("❌ PLC返回连接失败")
                    continue

                # 简单验证连接（可选）
                try:
                    # 读取一个测试值验证连接
                    data = self.client.db_read(11, DB_11.WEIGHT.value, 1)
                    self.logger.info(f"读取DB_11.WEIGHT成功，数据: {data}")
                except Exception as test_e:
                    self.logger.error(f"连接验证失败: {test_e}")
                    self._connected = False
                    continue
                
                self.logger.info(f"✅ 成功连接 PLC: {self._ip}")
                return True
            
            except Exception as e:
                self.logger.error(f"❌ PLC连接失败{attempt}/{retry_count}:{str(e)}", exc_info=True)
                self._connected = False

                # 清理（如果连接部分成功）
                try:
                    self.client.disconnect()
                except:
                    pass
                
                # 等待（最后一次尝试不等待）
                if attempt < retry_count:
                    time.sleep(retry_interval)

        self._connected = False
        return False
    
    def disconnect(self) -> bool:
        """
        [断开PLC连接]
        """
        # 如果未连接，直接返回成功
        if not self._connected and not self.client.get_connected():        
            self.logger.info(f"⚠️ PLC连接已断开, 无需操作")
            return True
        
        try:
            # 尝试断开连接
            self.client.disconnect()
            self.logger.info(f"⛓️‍💥 PLC已断开连接")
            return True
        except Exception as e:
            self.logger.error(f"❌ 断开连接失败: {e}", exc_info=True)
            return False
        finally:
            # 无论成功与否，更新状态
            self._connected = False
            # 重置客户端实例
            self.client = Client()
    
    def is_connected(self) -> bool:
        """
        [检查PLC是否已连接]
        """
        return self.client.get_connected() and self._connected

    def read_db(self, db_number: int, start: int, size: int) -> bytes:
        """
        [按字节读取DB块信息] 读取指定 DB 块，从 start 偏移开始，长度为 size（单位：字节）\n
        ::: param :::\n
            db_number: DB块号\n
            start: 偏移量\n
            size: 字节数量
        ::: return :::
            返回DB块数据
        """
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        return self.client.db_read(db_number, start, size)

    def write_db(self, db_number: int, start: int, data: bytes) -> None:
        """
        [按字节写入DB块信息] 将 data 写入指定 DB 块的偏移位置\n
        ::: param :::\n
            db_number: DB块号\n
            start: 偏移量\n
            size: 字节数量
        """
        if not self.is_connected():
            raise ConnectionError("未连接到PLC")
        self.client.db_write(db_number, start, data)
        self.logger.info(f"📤 写入 DB{db_number}[{start}] 成功，长度: {len(data)} bytes")

    def read_bit(self, db_number: int, offset: Union[float, int], size: int = 1) -> int:
        """
        [读取指定位的值]\n
        ::: param :::\n
            db_number: DB块编号\n
            offset: 偏移地址 (格式：字节.位 如 22.0)\n
            size: 读取位数 (默认为1位)\n
        ::: return :::\n
            读取到的位值（0/1）或多位值（当size>1时返回整数）
        """
        if not isinstance(offset, float) and '.' not in str(offset):
            raise ValueError("位偏移量必须使用float格式(如22.0)")
        
        byte_offset = int(offset)
        bit_offset = int(round((offset - byte_offset) * 10))
        
        # 验证位偏移范围
        if not 0 <= bit_offset <= 7:
            raise ValueError("位偏移必须在0-7范围内")
        
        # 读取包含目标位的整个字节
        data = self.read_db(db_number, byte_offset, 1)
        byte_value = data[0]
        
        # 提取指定位
        if size == 1:
            return (byte_value >> bit_offset) & 0x01
        else:
            # 提取多位值
            mask = (1 << size) - 1
            return (byte_value >> bit_offset) & mask
    
    def write_bit(self, db_number: int, offset: Union[float, int], value: Union[int, bool], size: int = 1) -> None:
        """
        [写入指定位的值]\n
        ::: param :::\n
            db_number: DB块编号\n
            offset: 偏移地址 (格式：字节.位 如 22.0)\n
            value: 要写入的值 (0/1或布尔值)\n
            size: 写入位数 (默认为1位)
        """
        if not isinstance(offset, float) and '.' not in str(offset):
            raise ValueError("位偏移量必须使用float格式(如22.0)")
            
        byte_offset = int(offset)
        bit_offset = int(round((offset - byte_offset) * 10))
        
        # 验证位偏移范围
        if not 0 <= bit_offset <= 7:
            raise ValueError("位偏移必须在0-7范围内")
            
        if size > (8 - bit_offset):
            raise ValueError("请求位数超出字节边界")
        
        # 读取当前字节值
        current_data = self.read_db(db_number, byte_offset, 1)
        current_value = current_data[0]
        
        # 创建位掩码
        mask = (1 << size) - 1
        clear_mask = ~(mask << bit_offset)
        
        # 转换为整数
        if isinstance(value, bool):
            value = 1 if value else 0
        
        # 验证取值范围
        if value < 0 or value >= (1 << size):
            raise ValueError(f"值必须介于0和{(1 << size) - 1}之间")
        
        # 更新字节值
        new_value = (current_value & clear_mask) | (value << bit_offset)
        
        # 写回PLC
        self.write_db(db_number, byte_offset, bytes([new_value]))
        self.logger.info(f"🔧 位写入成功 DB{db_number}[{offset}]: 值={value}")


    def wait_for_bit_change_sync(
            self,
            DB_NUMBER: int,
            ADDRESS: float,
            TRAGET_VALUE: int,
            TIMEOUT: float = settings.PLC_ACTION_TIMEOUT
            ) -> bool:
        """
        [同步 - PLC等待器] 等待PLC指定的位状态变化为目标值
        
        ::: param :::
            DB_NUMBER: DB块号 
            ADDRESS: 位地址 
            TRAGET_VALUE: 目标值 
            TIMEOUT: 超时时间（秒）
        """
        time.sleep(2)
        start_time = time.time()
        
        while True:
            # 读取当前值
            current_value = self.read_bit(DB_NUMBER, ADDRESS, 1)
            
            if current_value == TRAGET_VALUE:
                self.logger.info(f"✅ PLC动作完成: DB{DB_NUMBER}[{ADDRESS}] == {TRAGET_VALUE}")
                return True
                
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > TIMEOUT:
                self.logger.info(f"❌ 超时错误: 等待PLC动作超时 ({TIMEOUT}s)")
                return False
                
            # 等待一段时间再次检查
            time.sleep(0.5)

    
    #####################################################
    ####################### 异步方法 #####################
    #####################################################
    
    async def async_connect(self) -> bool:
        """
        [异步连接PLC]
        """
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(None, self.connect)
            if self._connected:
                self.logger.info(f"🔌 PLC连接状态: 已连接到 {self._ip}")
                return True
            else:
                self.logger.error("❌ 异步连接失败，未知原因")
                return False
        except Exception as e:
            self.logger.error(f"🚨 异步连接异常: {str(e)}", exc_info=True)
            return False

    async def async_disconnect(self) -> bool:
        """
        [异步断开PLC连接]
        """
        loop = asyncio.get_running_loop()
        try:
            # 使用异步执行器调用同步的断开连接方法
            return await loop.run_in_executor(None, self.disconnect)
        except Exception as e:
            self.logger.error(f"异步断开连接失败: {e}")
            return False
    
    async def monitor_condition(
        self,
        MONITOR_DB: int,
        MONITOR_OFFSET: float,
        BITS: int,
        TARGET_VALUE: int,
        CALLBACK: Callable[[], Any],
        POLL_INTERVAL: float = 0.5
    ) -> None:
        """
        [监控PLC状态] - 监控PLC状态并执行回调
        
        ::: param :::
            MONITOR_DB: 监控的DB块号
            MONITOR_OFFSET: 监控的地址偏移 
            BITS: 监控的位数
            TARGET_VALUE: 要匹配的目标值
            CALLBACK: 条件满足时的回调函数
            POLL_INTERVAL: 轮询间隔(秒)
        """
        try:
            self.logger.info(f"🔍 启动PLC监控: DB{MONITOR_DB}[{MONITOR_OFFSET}] {BITS}位 == 0x{TARGET_VALUE:02X}")
            
            while not self._stop_monitor.is_set():
                # 异步读取PLC状态
                try:
                    current_value = await asyncio.to_thread(
                        self.read_bit, MONITOR_DB, MONITOR_OFFSET, BITS
                    )
                except Exception as e:
                    self.logger.error(f"读取PLC状态失败: {e}")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                
                # 检查条件是否满足
                if current_value == TARGET_VALUE:
                    self.logger.info("🎯 条件满足! 执行回调函数")
                    try:
                        # 执行回调函数
                        if asyncio.iscoroutinefunction(CALLBACK):
                            await CALLBACK()
                        else:
                            await asyncio.to_thread(CALLBACK)
                        self.logger.info("✅ 回调执行完成")
                        return
                    except Exception as e:
                        self.logger.error(f"回调执行失败: {e}")
                        return
                
                await asyncio.sleep(POLL_INTERVAL)
        except asyncio.CancelledError:
            self.logger.info("⏹️ 监控任务已取消")
        finally:
            self._stop_monitor.clear()

    async def start_monitoring(
        self,
        MONITOR_DB: int,
        MONITOR_OFFSET: float,
        BITS: int,
        TARGET_VALUE: int,
        CALLBACK: Callable[[], Any],
        POLL_INTERVAL: float = 0.5
    ) -> asyncio.Task:
        """
        [启动监控任务] - 启动监控任务

        ::: param :::
            MONITOR_DB: 监控的DB块号
            MONITOR_OFFSET: 监控的偏移地址
            BITS: 监控的位数
            TARGET_VALUE: 要匹配的目标值
            CALLBACK: 条件满足时执行的回调函数
            POLL_INTERVAL: 轮询间隔(秒)

        ::: return :::
            asyncio.Task: 监控任务对象 - 返回asyncio.Task类型
        """
        # 停止现有监控任务
        await self.stop_monitoring()
        
        # 创建新监控任务
        self._monitor_task = asyncio.create_task(
            self.monitor_condition(
                MONITOR_DB,
                MONITOR_OFFSET,
                BITS,
                TARGET_VALUE,
                CALLBACK,
                POLL_INTERVAL
            )
        )
        return self._monitor_task

    async def stop_monitoring(self) -> None:
        """
        [停止监控任务] - 停止当前正在运行的监控任务
        """
        if self._monitor_task and not self._monitor_task.done():
            self._stop_monitor.set()
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            finally:
                self._monitor_task = None
                self._stop_monitor.clear()

    
    async def wait_for_bit_change(
            self,
            DB_NUMBER: int,
            ADDRESS: float,
            TRAGET_VALUE: int,
            TIMEOUT: float = settings.PLC_ACTION_TIMEOUT
            ) -> bool:
        """
        [异步 - PLC等待器] 等待PLC指定的位状态变化为目标值
        
        ::: param :::
            DB_NUMBER: DB块号 
            ADDRESS: 位地址 
            TRAGET_VALUE: 目标值 
            TIMEOUT: 超时时间（秒）
        """
        await asyncio.sleep(2)
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # 读取当前值
            # Address = f"{byte_offset}.{bit_offset}"
            current_value = await asyncio.to_thread(self.read_bit, DB_NUMBER, ADDRESS, 1)
            
            if current_value == TRAGET_VALUE:
                # self.logger.info(f"✅ PLC动作完成: DB{db_number}[{byte_offset}.{bit_offset}] == {target_value}")
                self.logger.info(f"✅ PLC动作完成: DB{DB_NUMBER}[{ADDRESS}] == {TRAGET_VALUE}")
                return True
                
            # 检查超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > TIMEOUT:
                self.logger.info(f"❌ 超时错误: 等待PLC动作超时 ({TIMEOUT}s)")
                return False
                
            # 等待一段时间再次检查
            await asyncio.sleep(0.5)


###############################################################
# 在FastAPI中这样使用：
###############################################################

# from fastapi import FastAPI
# from .plc_connection_module import PLCConnectionBase

# app = FastAPI()
# plc = PLCConnectionBase("192.168.8.30")

# @app.on_event("startup")
# async def startup():
#     # 异步连接PLC
#     if not await plc.async_connect():
#         raise RuntimeError("PLC连接失败")

# @app.on_event("shutdown")
# async def shutdown():
#     # 异步断开PLC连接
#     await plc.async_disconnect()

# @app.post("/set-bit")
# async def set_bit(db: int, address: float, value: int):
#     """设置位值（同步操作）"""
#     # 在异步环境中安全调用同步方法
#     loop = asyncio.get_running_loop()
#     await loop.run_in_executor(None, plc.write_bit, db, address, value)
#     return {"status": "success"}

# @app.get("/monitor-status")
# async def monitor_status():
#     """启动状态监控"""
#     async def on_condition_met():
#         print("条件满足！执行操作")
    
#     await plc.start_monitoring(
#         MONITOR_DB=10,
#         MONITOR_OFFSET=5.0,
#         BITS=1,
#         TARGET_VALUE=1,
#         CALLBACK=on_condition_met
#     )
#     return {"status": "监控已启动"}