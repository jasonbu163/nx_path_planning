# 在RES+3.1系统中增加接收处理模块
import threading
import time
import asyncio

from .packet_parser import PacketParser
from .res_protocol import FrameType, ErrorHandler, ImmediateCommand

class DataReceiver:
    """数据接收和解包处理中心"""
    def __init__(self, network_manager, parser, task_executor, heartbeat_mgr):
        """
        初始化数据接收器
        :param network_manager: 网络管理实例
        :param parser: 数据包解析器
        :param task_executor: 任务执行器实例
        :param heartbeat_mgr: 心跳管理器实例
        """
        self.network = network_manager
        self.parser = parser or PacketParser()
        self.task_executor = task_executor
        self.heartbeat_mgr = heartbeat_mgr
        self.running = False
        self.receive_thread = None
        
    def start(self):
        """启动接收线程"""
        if not self.running:
            self.running = True
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            print("数据接收器已启动")
            
    def _receive_loop(self):
        """接收数据的主循环"""
        while self.running:
            # 1. 从网络管理器获取原始数据
            raw_data = self.network.receive()
            
            if not raw_data:
                time.sleep(0.01)  # 短暂休眠避免CPU占用过高
                continue
            
            # 2. 尝试解析数据包
            try:
                parsed_data = self.parser.parse_generic_response(raw_data)
                if not isinstance(parsed_data, dict):
                    print("解析结果不是字典格式")
                    continue
            except Exception as e:
                print(f"解析数据包时出错: {e}")
                continue
                
            # 3. 根据帧类型处理不同数据
            frame_type = parsed_data.get('frame_type')
            
            if frame_type == FrameType.HEARTBEAT:
                self._handle_heartbeat(parsed_data)
            elif frame_type == FrameType.TASK:
                self._handle_task_response(parsed_data)
            elif frame_type == FrameType.COMMAND:
                self._handle_command_response(parsed_data)
            # elif frame_type == FrameType.DATA:
            #     self._handle_data_frame(parsed_data)
            else:
                print(f"未知帧类型: {frame_type}")
                
    def _handle_heartbeat(self, data):
        """处理心跳数据"""
        self.heartbeat_mgr.update_status(data)
        
        # 调试信息
        print(f"收到心跳包: 设备ID={data['device_id']}, 状态码={data['state']}")
        if 'x' in data and 'y' in data:
            print(f"当前位置: X={data['x']}, Y={data['y']}, Z={data.get('z', 0)}")
        if 'battery' in data:
            print(f"电池电量: {data['battery']}%")
            
    def _handle_task_response(self, data):
        """处理任务响应"""
        task_id = data.get('task_id')
        result_code = data.get('result')
        current_segment = data.get('current_segment')
        
        print(f"\n任务响应: 任务ID={task_id}, 结果={result_code}, 当前段={current_segment}")
        
        # 处理错误代码
        if result_code != ErrorHandler.ERROR_MAP[0]:
            self._handle_error(result_code)
        
        # 更新任务执行器状态
        self.task_executor.update_task_status(task_id, result_code, current_segment)
        
    def _handle_command_response(self, data):
        """处理命令响应"""
        cmd_id = data.get('cmd_id')
        cmd_no = data.get('cmd_no')
        result = data.get('result')
        
        print(f"命令响应: 命令ID={cmd_id}, 序号={cmd_no}, 结果={result}")
        
        # 特殊处理急停命令
        if cmd_id == ImmediateCommand.EMERGENCY_STOP:
            if result == ErrorHandler.ERROR_MAP[0]:
                print("急停命令已成功执行")
                # 更新所有任务状态为停止
                self.task_executor.emergency_stop()
            else:
                print("急停命令执行失败!")
                self._handle_error(result)
        
    # def _handle_data_frame(self, data):
    #     """处理数据帧"""
    #     # 这里可以添加对特定数据类型的处理逻辑
    #     data_type = data.get('data_type')
    #     payload = data.get('payload', {})
        
    #     if data_type == RESProtocol.DataType.PALLET_INFO:
    #         print(f"载货信息: 状态={payload.get('status')}, 重量={payload.get('weight')}kg")
    #     else:
    #         print(f"收到数据帧: 类型={data_type}, 内容={payload}")
            
    def _handle_error(self, error_code):
        """统一错误处理"""
        error_name, solution = ErrorHandler.get_error_info(error_code)
        
        print(f"\n⚠️ 错误发生: [{error_name}]")
        # print(f"错误描述: {error_description}")
        print(f"建议解决方案: {solution}\n")
        
        # 这里可以添加根据错误代码的自动处理逻辑
        # if error_code in [RESProtocol.ErrorCode.POWER_LOW, 
        #                  RESProtocol.ErrorCode.POWER_CRITICAL]:
        #     self._handle_low_battery()
            
    def _handle_low_battery(self):
        """低电量处理逻辑"""
        print("检测到低电量，执行安全程序...")
        # 1. 停止所有任务
        self.task_executor.emergency_stop()
        
        # 2. 导航到充电站
        charge_segments = [
            (1, 1, 1, 0),  # 前往充电站坐标
            (255, 255, 255, 0)   # 停止
        ]
        charge_task_id = self.task_executor.queue_task(charge_segments)
        self.task_executor.start_task(charge_task_id, charge_segments)
        print(f"已创建充电任务: ID={charge_task_id}")
        
    async def _receive_task(self):
        """后台接收任务"""
        while self.running:
            try:
                # 接收数据包
                data = await self.network.receive()  # 添加await等待异步方法
                if data:
                    # 解析数据包
                    parsed = self.parser.parse(data)
                    # 处理解析结果
                    await self._process_parsed_data(parsed)
            except Exception as e:
                print(f"接收任务异常: {str(e)}")
                await asyncio.sleep(5)
