# res_protocol_system/NetworkManager.py
# -*- coding: utf-8 -*-
"""
RES+3.1 穿梭车通信协议上位机系统 - 模块化设计
按功能划分不同模块，便于团队协作维护
"""

import threading
import time

from .res_protocol import RESProtocol, FrameType, ErrorHandler
from .packet_builder import PacketBuilder
from app.core.devices_logger import DevicesLogger

# ------------------------
# 模块 5: 心跳管理器
# 职责: 维护心跳机制和小车状态
# 维护者: 核心系统工程师
# ------------------------
class HeartbeatManager(DevicesLogger):
    def __init__(
            self,
            NETTWORK_MANAGER,
            PACKET_BUILDER
            ):
        """
        [初始化心跳管理器]

        ::: param :::
            NETTWORK_MANAGER: 网络管理实例
            PACKET_BUILDER: 数据包构造器实例
        """
        super().__init__(self.__class__.__name__)
        self.network = NETTWORK_MANAGER
        self.builder = PACKET_BUILDER if PACKET_BUILDER else PacketBuilder()
        self.last_heartbeat_time = 0
        self.last_response_time = 0
        self.heartbeat_active = True
        self.current_status = {}
        self.thread = None
        
    def start(self):
        """启动心跳线程"""
        self.heartbeat_active = True
        self.thread = threading.Thread(target=self._heartbeat_loop)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """停止心跳"""
        self.heartbeat_active = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
    
    def _heartbeat_loop(self):
        """心跳发送循环"""
        self.logger.info("[心跳] 开始运行心跳线程")
        while self.heartbeat_active:
            try:
                # 带电量心跳每5次发送一次
                frame_type = FrameType.HEARTBEAT_WITH_BATTERY.value if (
                    time.time() % 5 < 0.6) else FrameType.HEARTBEAT.value
                    
                packet = self.builder.build_heartbeat(frame_type)
                
                if self.network.sendall(packet):
                    self.last_heartbeat_time = time.time()

                # 等待间隔
                time.sleep(RESProtocol.HEARTBEAT_INTERVAL.value)
            except Exception as e:
                self.logger.error(f"[心跳] 发生异常: {str(e)}", exc_info=True)
                time.sleep(5)
    
    def update_status(self, data):
        """更新小车状态"""
        self.current_status = data
        self.last_response_time = time.time()
        
        # 检查是否需要触发警报
        if data['result'] != 0:
            return self.handle_error(data['result'])
    
    def handle_error(self, error_code):
        """处理错误码"""
        error_msg, solution = ErrorHandler.get_error_info(error_code)
        is_critical = ErrorHandler.is_critical_error(error_code)
        
        return {
            'error_code': error_code,
            'error_msg': error_msg,
            'solution': solution,
            'is_critical': is_critical,
            'timestamp': time.time()
        }
    
    def is_connected(self):
        """判断连接状态"""
        return time.time() - self.last_response_time < RESProtocol.HEARTBEAT_INTERVAL.value * 3   