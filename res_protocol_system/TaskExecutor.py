# res_protocol_system/TaskExecutor.py
# -*- coding: utf-8 -*-
"""
RES+3.1 穿梭车通信协议上位机系统 - 模块化设计
按功能划分不同模块，便于团队协作维护
"""

import asyncio
import threading
import time

# ------------------------
# 模块 6: 任务执行器
# 职责: 管理任务的下发和执行流程
# 维护者: 任务调度工程师
# ------------------------
class TaskExecutor:
    def __init__(self, network_manager, packet_builder):
        self.network = network_manager
        self.builder = packet_builder
        self.current_task_id = 0
        self.task_queue = []
        self.active_task = None
        self.lock = threading.Lock()
    
    def get_next_task_id(self):
        """获取下一个任务ID (1-255循环)"""
        with self.lock:
            self.current_task_id = (self.current_task_id % 255) + 1
            return self.current_task_id
    
    def queue_task(self, segments):
        """
        排队任务
        :param segments: 路径段列表 [(x, y, z, action), ...]
        :return: 任务ID
        """
        task_id = self.get_next_task_id()
        self.task_queue.append((task_id, segments))
        return task_id
    
    def start_task(self, task_id, segments):
        """
        开始执行任务
        :return: 是否成功下发
        """
        # 构建任务报文
        packet = self.builder.build_task_command(task_id, segments)
        
        # 发送任务
        if self.network.send(packet):
            self.active_task = {
                'id': task_id,
                'segments': segments,
                'sent_segments': 0,
                'status': 'sent',
                'start_time': time.time()
            }
            return True
    
    async def send_task(self, task_id, segments):
        """
        发送穿梭车任务
        :param task_id: 任务ID
        :param segments: 路径段列表 [(x, y, z, action), ...]
        :return: 是否成功发送
        """
        # 构建任务报文
        packet = self.builder.build_task_command(task_id, segments)
        
        # 发送任务
        return self.network.send(packet)

    async def send_emergency_stop(self):
        """发送紧急停止命令"""
        # 构建紧急停止报文
        packet = self.builder.build_emergency_stop()
        
        # 发送命令
        return self.network.send(packet)

    async def send_command(self, command_id, cmd_no=1, task_no=0, param=0):
        """
        发送控制命令
        :param command_id: 命令ID
        :param cmd_no: 命令序号
        :param task_no: 任务序号
        :param param: 命令参数
        :return: 是否成功发送
        """
        # 构建通用命令报文
        packet = self.builder.build_general_command(
            command_id, cmd_no, task_no, param
        )
        
        # 发送命令
        return self.network.send(packet)
