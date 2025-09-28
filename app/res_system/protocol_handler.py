# res_protocol_system/protocol_handler.py

import asyncio
import logging

from .res_protocol import RESProtocol, CarStatus, ImmediateCommand, WorkCommand, Debug, FrameType, ErrorHandler
from packet_builder import PacketBuilder
from packet_parser import PacketParser

logger = logging.getLogger("res_protocol")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class ProtocolHandler:
        """RES协议处理核心"""
        def __init__(self, host, port, device_id=1):
            self.host = host
            self.port = port
            self.device_id = device_id
            self.builder = PacketBuilder(device_id)
            self.parser = PacketParser()
            self.reader = None
            self.writer = None
            self.connected = False
            self.latest_status = {
                'location': (0, 0, 0),
                'car_status': CarStatus.READY,
                'battery': 100,
                'last_update': None
            }
            self._heartbeat_counter = 0
            self._running = False
            
        async def connect(self):
            """连接到穿梭车设备"""
            try:
                self.reader, self.writer = await asyncio.open_connection(
                    self.host, self.port)
                self.connected = True
                self._running = True
                logger.info(f"成功连接到设备 {self.host}:{self.port}")
                
                # 启动心跳任务
                asyncio.create_task(self._heartbeat_loop())
                # 启动接收循环
                asyncio.create_task(self._receive_loop())
                return True
            except (OSError, asyncio.TimeoutError) as e:
                logger.error(f"连接失败: {e}")
                return False
                
        async def disconnect(self):
            """断开连接"""
            self._running = False
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
                self.connected = False
                logger.info("连接已关闭")
                
        async def _heartbeat_loop(self):
            """心跳发送循环"""
            while self._running and self.connected:
                try:
                    # 每5次发送一个带电量心跳
                    if self._heartbeat_counter % 5 == 0:
                        frame_type = FrameType.HEARTBEAT_WITH_BATTERY
                    else:
                        frame_type = RESProtocol.FrameType.HEARTBEAT
                        
                    heartbeat = self.builder.build_heartbeat(frame_type)
                    self.writer.write(heartbeat)
                    await self.writer.drain()
                    
                    self._heartbeat_counter += 1
                    await asyncio.sleep(RESProtocol.HEARTBEAT_INTERVAL)
                except (ConnectionResetError, asyncio.CancelledError) as e:
                    logger.error(f"心跳发送失败: {e}")
                    self.connected = False
                    break
                except Exception as e:
                    logger.error(f"心跳发送异常: {e}")
                    await asyncio.sleep(1)
                    
        async def _receive_loop(self):
            """数据接收循环"""
            while self._running and self.connected:
                try:
                    data = await self.reader.read(1024)
                    if not data:
                        logger.warning("连接已断开")
                        self.connected = False
                        break
                        
                    logger.debug(f"收到数据: {data.hex()}")
                    parsed = self.parser.parse_generic_response(data)
                    self._update_status(parsed)
                    
                except (ConnectionResetError, asyncio.CancelledError) as e:
                    logger.error(f"接收失败: {e}")
                    self.connected = False
                except Exception as e:
                    logger.error(f"接收数据异常: {e}")
                    
        def _update_status(self, status_data):
            """更新小车状态"""
            # 忽略错误数据
            if 'error' in status_data or 'warning' in status_data:
                return
                
            # 更新时间戳
            self.latest_status['last_update'] = asyncio.get_event_loop().time()
            
            # 更新位置和状态
            if 'location' in status_data:
                self.latest_status['location'] = status_data['location']
                self.latest_status['car_status'] = status_data.get('car_status', RESProtocol.CarStatus.READY)
                
            # 更新电池信息
            if 'battery' in status_data:
                self.latest_status['battery'] = status_data['battery']
                
            # 更新错误信息
            if 'result' in status_data and status_data['result'] != 0:
                error_code = status_data['result']
                error_info = ErrorHandler.get_error_info(error_code)
                logger.warning(f"错误码 {error_code}: {error_info[0]}")
                
                # 记录错误
                self.latest_status['last_error'] = {
                    'code': error_code,
                    'message': error_info[0],
                    'solution': error_info[1]
                }
                
                # 如果是关键错误，触发紧急处理
                if ErrorHandler.is_critical_error(error_code):
                    logger.error("关键错误，触发紧急处理")
                    asyncio.create_task(self.send_emergency_stop())
                    
        async def send_task(self, task_no, segments):
            """发送任务到穿梭车"""
            if not self.connected:
                logger.error("未连接到设备，无法发送任务")
                return False
                
            try:
                task_packet = self.builder.build_task(task_no, segments)
                self.writer.write(task_packet)
                await self.writer.drain()
                logger.info(f"任务 {task_no} 已发送，包含 {len(segments)} 个路径段")
                return True
            except Exception as e:
                logger.error(f"发送任务失败: {e}")
                return False
            
        async def send_command(self, cmd_id, cmd_no=1, task_no=0, param=0):
            """发送控制命令到穿梭车"""
            if not self.connected:
                logger.error("未连接到设备，无法发送命令")
                return False
                
            try:
                command_packet = self.builder.build_command(cmd_id, cmd_no, task_no, param)
                self.writer.write(command_packet)
                await self.writer.drain()
                logger.info(f"命令 {cmd_id} 已发送")
                return True
            except Exception as e:
                logger.error(f"发送命令失败: {e}")
                return False
            
        async def send_emergency_stop(self):
            """发送紧急停止命令"""
            return await self.send_command(
                cmd_id=ImmediateCommand.EMERGENCY_STOP.value,
                cmd_no=0xFF  # 特殊命令号表示紧急停止
            )
            
        def get_status(self):
            """获取最新小车状态"""
            # 添加连接状态
            status = self.latest_status.copy()
            status['connected'] = self.connected
            return status
