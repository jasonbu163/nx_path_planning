"""
西门子PLC生产级异步连接类
基于python-snap7，符合工业控制规范
设计目标：为高级工作流和PLC任务流提供稳定可靠的基础
"""

import asyncio
import snap7
from snap7.util import *
import logging
import time
from threading import Lock
from typing import Union, Optional, Callable, Any, Dict
from enum import Enum
import json


class PLCConnectionStatus(Enum):
    """PLC连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class IndustrialPLCConnector:
    """
    西门子PLC工业级连接器
    支持同步和异步操作，具备自动重连、心跳检测、线程安全等特性
    """
    
    def __init__(self, ip_address: str, rack: int = 0, slot: int = 1, 
                 config_file: str = None):
        """
        初始化PLC连接器
        
        Args:
            ip_address: PLC IP地址
            rack: 机架号 (默认0)
            slot: 槽号 (默认1)
            config_file: 配置文件路径
        """
        self._ip = ip_address
        self._rack = rack
        self._slot = slot
        
        # 连接状态管理
        self._status = PLCConnectionStatus.DISCONNECTED
        self._client = None
        self._connection_lock = Lock()  # 连接操作锁
        self._write_lock = Lock()      # 写操作锁
        
        # 异步任务管理
        self._monitor_task = None
        self._heartbeat_task = None
        self._stop_event = asyncio.Event()
        
        # 配置管理
        self._config = self._load_default_config()
        if config_file:
            self.load_config(config_file)
        
        # 日志初始化
        self._logger = self._setup_logging()
        
        # 统计信息
        self._stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'read_operations': 0,
            'write_operations': 0,
            'last_error': None
        }

    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            'timeout': 5.0,
            'heartbeat_interval': 10,
            'max_retries': 3,
            'retry_interval': 2,
            'auto_reconnect': True,
            'verify_writes': True,
            'max_read_size': 1024,
            'heartbeat_db': 1,
            'heartbeat_offset': 0,
            'log_level': 'INFO'
        }

    def _setup_logging(self) -> logging.Logger:
        """配置工业级日志记录"""
        logger = logging.getLogger(f'PLCConnector_{self._ip.replace(".", "_")}')
        
        if not logger.handlers:
            logger.setLevel(getattr(logging, self._config['log_level']))
            
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '[%(filename)s:%(lineno)d] - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    def load_config(self, config_file: str) -> None:
        """从JSON文件加载配置"""
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                self._config.update(user_config)
            self._logger.info(f"配置文件加载成功: {config_file}")
        except Exception as e:
            self._logger.error(f"配置文件加载失败: {e}")

    def connect(self, retry_count: int = None, retry_interval: float = None) -> bool:
        """
        同步连接PLC（线程安全）
        
        Args:
            retry_count: 重试次数（覆盖配置）
            retry_interval: 重试间隔（覆盖配置）
            
        Returns:
            bool: 连接是否成功
        """
        with self._connection_lock:
            if self._status == PLCConnectionStatus.CONNECTED:
                self._logger.info("PLC连接已存在，无需重新连接")
                return True

            # 使用配置或参数
            max_retries = retry_count or self._config['max_retries']
            retry_delay = retry_interval or self._config['retry_interval']
            
            self._update_status(PLCConnectionStatus.CONNECTING)
            
            for attempt in range(1, max_retries + 1):
                try:
                    self._stats['connection_attempts'] += 1
                    
                    # 创建新客户端实例
                    self._client = snap7.client.Client()
                    self._client.set_connection_type(3)  # PG模式
                    
                    self._logger.info(f"尝试连接PLC {self._ip} (尝试 {attempt}/{max_retries})")
                    self._client.connect(self._ip, self._rack, self._slot)
                    
                    # 验证连接
                    if self._client.get_connected():
                        # 连接验证测试
                        if self._validate_connection():
                            self._update_status(PLCConnectionStatus.CONNECTED)
                            self._stats['successful_connections'] += 1
                            
                            # 启动后台任务
                            self._start_background_tasks()
                            
                            self._logger.info(f"✅ PLC连接成功: {self._ip}")
                            return True
                    else:
                        self._logger.error("PLC客户端报告连接失败")
                        
                except Exception as e:
                    self._stats['failed_connections'] += 1
                    self._stats['last_error'] = str(e)
                    self._logger.error(f"连接尝试 {attempt}/{max_retries} 失败: {e}")
                    
                    # 清理失败的连接
                    try:
                        if self._client:
                            self._client.destroy()
                    except:
                        pass
                    
                    # 最后一次尝试不等待
                    if attempt < max_retries:
                        time.sleep(retry_delay)
            
            # 所有尝试都失败
            self._update_status(PLCConnectionStatus.ERROR)
            self._logger.error(f"无法连接PLC，已重试{max_retries}次")
            return False

    async def async_connect(self) -> bool:
        """
        异步连接PLC
        """
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self.connect)
        except Exception as e:
            self._logger.error(f"异步连接失败: {e}")
            return False

    def disconnect(self) -> bool:
        """
        安全断开PLC连接
        """
        with self._connection_lock:
            if self._status == PLCConnectionStatus.DISCONNECTED:
                return True
            
            self._update_status(PLCConnectionStatus.DISCONNECTING)
            
            # 停止后台任务
            self._stop_background_tasks()
            
            try:
                if self._client:
                    self._client.disconnect()
                    self._client.destroy()
                    self._logger.info("PLC连接已安全断开")
                
                self._update_status(PLCConnectionStatus.DISCONNECTED)
                return True
                
            except Exception as e:
                self._logger.error(f"断开连接时发生错误: {e}")
                self._update_status(PLCConnectionStatus.ERROR)
                return False

    async def async_disconnect(self) -> bool:
        """
        异步断开连接
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.disconnect)

    def _validate_connection(self) -> bool:
        """
        验证PLC连接有效性
        """
        try:
            # 尝试读取PLC基本信息
            cpu_info = self._client.get_cpu_info()
            self._logger.debug(f"PLC型号: {cpu_info.ModuleTypeName.decode('utf-8').strip()}")
            
            # 可选：读取一个测试区域验证通信
            # self._client.db_read(1, 0, 1)
            return True
            
        except Exception as e:
            self._logger.error(f"连接验证失败: {e}")
            return False

    def _start_background_tasks(self):
        """启动后台监控任务"""
        if self._config['auto_reconnect']:
            self._stop_event.clear()
            self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

    def _stop_background_tasks(self):
        """停止后台任务"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._stop_event.set()

    async def _heartbeat_monitor(self):
        """心跳检测和自动重连"""
        while not self._stop_event.is_set() and self._status == PLCConnectionStatus.CONNECTED:
            try:
                await asyncio.sleep(self._config['heartbeat_interval'])
                
                # 检查连接状态
                if not await self._check_heartbeat():
                    self._logger.warning("PLC心跳检测失败")
                    
                    if self._config['auto_reconnect']:
                        await self._reconnect()
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"心跳监控异常: {e}")

    async def _check_heartbeat(self) -> bool:
        """检查PLC心跳"""
        try:
            loop = asyncio.get_event_loop()
            # 尝试读取系统时间等基本信息
            await loop.run_in_executor(None, self._client.get_plc_time)
            return True
        except Exception:
            return False

    async def _reconnect(self) -> bool:
        """自动重连机制"""
        self._update_status(PLCConnectionStatus.RECONNECTING)
        self._logger.info("尝试自动重新连接...")
        
        success = await self.async_connect()
        if success:
            self._logger.info("自动重连成功")
        else:
            self._logger.error("自动重连失败")
            
        return success

    def _update_status(self, status: PLCConnectionStatus):
        """更新连接状态"""
        self._status = status
        self._logger.debug(f"连接状态更新: {status.value}")

    def is_connected(self) -> bool:
        """检查连接状态"""
        return (self._status == PLCConnectionStatus.CONNECTED and 
                self._client and 
                self._client.get_connected())

    # 数据读写方法
    def read_db(self, db_number: int, start_offset: int, size: int) -> Optional[bytes]:
        """
        读取DB块数据（线程安全）
        """
        if not self._validate_operation(db_number, start_offset, size):
            return None
        
        try:
            with self._connection_lock:
                data = self._client.db_read(db_number, start_offset, size)
                self._stats['read_operations'] += 1
                self._logger.debug(f"读取DB{db_number}[{start_offset}:{size}]成功")
                return data
                
        except Exception as e:
            self._logger.error(f"读取DB{db_number}失败: {e}")
            self._stats['last_error'] = str(e)
            return None

    async def async_read_db(self, db_number: int, start_offset: int, size: int) -> Optional[bytes]:
        """异步读取DB块"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read_db, db_number, start_offset, size)

    def write_db(self, db_number: int, start_offset: int, data: bytes) -> bool:
        """
        写入DB块数据（线程安全，含验证）
        """
        if not self._validate_operation(db_number, start_offset, len(data)):
            return False
        
        try:
            with self._write_lock:
                # 写入数据
                self._client.db_write(db_number, start_offset, data)
                
                # 验证写入（如果启用）
                if self._config['verify_writes']:
                    verify_data = self._client.db_read(db_number, start_offset, len(data))
                    if verify_data != data:
                        raise ValueError("写入验证失败")
                
                self._stats['write_operations'] += 1
                self._logger.info(f"写入DB{db_number}[{start_offset}]成功，大小: {len(data)}字节")
                return True
                
        except Exception as e:
            self._logger.error(f"写入DB{db_number}失败: {e}")
            self._stats['last_error'] = str(e)
            return False

    async def async_write_db(self, db_number: int, start_offset: int, data: bytes) -> bool:
        """异步写入DB块"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.write_db, db_number, start_offset, data)

    def _validate_operation(self, db_number: int, offset: int, size: int) -> bool:
        """验证操作参数"""
        if not self.is_connected():
            self._logger.error("PLC未连接")
            return False
            
        if db_number < 1 or offset < 0 or size <= 0:
            self._logger.error(f"操作参数无效: DB{db_number}, 偏移{offset}, 大小{size}")
            return False
            
        if size > self._config['max_read_size']:
            self._logger.error(f"读取大小超出限制: {size} > {self._config['max_read_size']}")
            return False
            
        return True

    # 数据类型便捷方法
    def read_real(self, db_number: int, offset: int) -> Optional[float]:
        """读取REAL类型数据"""
        data = self.read_db(db_number, offset, 4)
        if data:
            return get_real(data, 0)
        return None

    def write_real(self, db_number: int, offset: int, value: float) -> bool:
        """写入REAL类型数据"""
        data = bytearray(4)
        set_real(data, 0, value)
        return self.write_db(db_number, offset, data)

    def read_int(self, db_number: int, offset: int) -> Optional[int]:
        """读取INT类型数据"""
        data = self.read_db(db_number, offset, 2)
        if data:
            return get_int(data, 0)
        return None

    # 上下文管理器支持
    def __enter__(self):
        """同步上下文管理器"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器退出"""
        self.disconnect()

    async def __aenter__(self):
        """异步上下文管理器"""
        await self.async_connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.async_disconnect()

    @property
    def connection_status(self) -> PLCConnectionStatus:
        """获取当前连接状态"""
        return self._status

    @property
    def statistics(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        return self._stats.copy()

    def get_diagnostic_info(self) -> Dict[str, Any]:
        """获取诊断信息"""
        return {
            'ip_address': self._ip,
            'status': self._status.value,
            'statistics': self._stats,
            'config': self._config
        }


# 使用示例和高级工作流基础
class PLCWorkflowBase:
    """
    基于PLC连接器的高级工作流基类
    提供任务管理、错误恢复、状态跟踪等功能
    """
    
    def __init__(self, plc_connector: IndustrialPLCConnector):
        self.plc = plc_connector
        self._tasks = []
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute_workflow(self, workflow_config: Dict) -> bool:
        """
        执行工作流模板方法
        """
        try:
            # 工作流前置检查
            if not await self._pre_check():
                return False
            
            # 执行工作流步骤
            for step in workflow_config.get('steps', []):
                if not await self._execute_step(step):
                    self._logger.error(f"工作流步骤失败: {step}")
                    await self._on_failure(step)
                    return False
            
            # 工作流后置处理
            await self._post_process()
            return True
            
        except Exception as e:
            self._logger.error(f"工作流执行异常: {e}")
            await self._on_error(e)
            return False

    async def _execute_step(self, step_config: Dict) -> bool:
        """执行单个步骤（子类重写）"""
        raise NotImplementedError("子类必须实现此方法")

    async def _pre_check(self) -> bool:
        """工作流前置检查"""
        if not self.plc.is_connected():
            self._logger.error("PLC未连接，无法执行工作流")
            return False
        return True

    async def _on_failure(self, failed_step: Dict):
        """失败处理"""
        self._logger.info(f"执行失败处理 for step: {failed_step}")

    async def _on_error(self, error: Exception):
        """错误处理"""
        self._logger.error(f"工作流错误处理: {error}")

    async def _post_process(self):
        """后置处理"""
        self._logger.info("工作流执行完成")


# 示例：具体工作流实现
class QualityControlWorkflow(PLCWorkflowBase):
    """质量控制系统工作流示例"""
    
    async def _execute_step(self, step_config: Dict) -> bool:
        step_type = step_config.get('type')
        
        if step_type == 'read_quality_data':
            return await self._read_quality_data(step_config)
        elif step_type == 'evaluate_quality':
            return await self._evaluate_quality(step_config)
        elif step_type == 'write_decision':
            return await self._write_decision(step_config)
        else:
            self._logger.error(f"未知的工作流步骤类型: {step_type}")
            return False

    async def _read_quality_data(self, config: Dict) -> bool:
        """读取质量数据"""
        try:
            # 从PLC读取质量相关数据
            temperature = await self.plc.async_read_real(config['db_number'], config['temp_offset'])
            pressure = await self.plc.async_read_real(config['db_number'], config['pressure_offset'])
            
            self._logger.info(f"质量数据读取: 温度={temperature}, 压力={pressure}")
            return temperature is not None and pressure is not None
            
        except Exception as e:
            self._logger.error(f"读取质量数据失败: {e}")
            return False


# 配置文件示例
"""
plc_config.json:
{
    "timeout": 5.0,
    "heartbeat_interval": 10,
    "max_retries": 3,
    "retry_interval": 2,
    "auto_reconnect": true,
    "verify_writes": true,
    "max_read_size": 1024,
    "log_level": "INFO"
}

workflow_config.json:
{
    "steps": [
        {
            "type": "read_quality_data",
            "db_number": 100,
            "temp_offset": 0,
            "pressure_offset": 4
        },
        {
            "type": "evaluate_quality",
            "thresholds": {
                "max_temp": 85.0,
                "max_pressure": 10.0
            }
        }
    ]
}
"""


async def main():
    """使用示例"""
    # 创建PLC连接器
    plc = IndustrialPLCConnector("192.168.1.100", config_file="plc_config.json")
    
    # 使用异步上下文管理器
    async with plc:
        if plc.is_connected():
            # 读取数据示例
            temperature = await plc.async_read_real(100, 0)
            print(f"当前温度: {temperature}")
            
            # 创建工作流并执行
            workflow = QualityControlWorkflow(plc)
            workflow_config = {
                "steps": [
                    {"type": "read_quality_data", "db_number": 100, "temp_offset": 0, "pressure_offset": 4}
                ]
            }
            
            success = await workflow.execute_workflow(workflow_config)
            print(f"工作流执行结果: {success}")
            
            # 查看诊断信息
            print("诊断信息:", plc.get_diagnostic_info())


if __name__ == "__main__":
    asyncio.run(main())