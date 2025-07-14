# tests/test_car.py
# RES+3.1 穿梭车控制系统 - 使用示例

# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

from res_protocol_system import RESProtocol, PacketBuilder, PacketParser, NetworkManager, HeartbeatManager, TaskExecutor, DataReceiver
import time
import threading

def main():
    # =========================================================================
    # 步骤1: 系统初始化
    # =========================================================================
    
    # 1.1 创建网络管理器
    CAR_IP = "192.168.8.30"  # 小车的IP地址
    CAR_PORT = 2504           # 小车通信端口
    # CAR_IP = "localhost"      # 小车的IP地址
    # CAR_PORT = 65432            # 小车通信端口
    network = NetworkManager(CAR_IP, CAR_PORT)
    
    # 1.2 创建协议组件
    builder = PacketBuilder(device_id=2)  # 设备ID为1
    parser = PacketParser()
    
    # 1.3 创建心跳管理器
    heartbeat_mgr = HeartbeatManager(network, builder)
    
    # 1.4 创建任务执行器
    task_executor = TaskExecutor(network, builder)

    data_rec = DataReceiver(network, parser, task_executor, heartbeat_mgr)
    
    # 1.5 启动心跳管理
    heartbeat_mgr.start()

    
    print("系统初始化完成，心跳已启动")

    print(data_rec)
    
    # =========================================================================
    # 步骤2: 连接小车
    # =========================================================================
    
    # 尝试连接小车
    if not network.connect():
        print("连接失败，请检查网络设置")
        return
    
    # 等待连接建立
    time.sleep(0.5)
    print(heartbeat_mgr.is_connected())
    # print(f"已连接小车 {CAR_IP}:{CAR_PORT}")
    
    # =========================================================================
    # 步骤3: 定义任务处理函数
    # =========================================================================
    
    def handle_task_response(data):
        """任务响应处理函数"""
        print(f"\n收到任务响应: 任务ID={data.get('task_id', '未知')}, 结果={data.get('result', '未知')}")
        
        if data.get('result') != 0:
            print("任务执行失败!")
            error_info = RESProtocol.ErrorHandler.get_error_info(data.get('result'))
            print(f"错误信息: {error_info[0]}")
            print(f"建议解决方案: {error_info[1]}")
    
    # =========================================================================
    # 步骤4: 创建并发送任务
    # =========================================================================
    
    # 4.1 定义路径段 (格式: (x, y, z, 动作))
    # 动作: 0-直行, 1-左转, 2-右转, 3-提升, 4-下降, 5-停止
    warehouse_segments = [
        (1, 1, 1, 0),    # 从(10,20)到下一个点的直行
        (2, 1, 1, 0),    # 直行到(10,50)
        (3, 5, 1, 0),    # 左转到(30,50)
        (3, 6, 1, 0),    # 提升货物
        (3, 8, 1, 0),    # 直行到(30,80)楼层1
        (3, 8, 1, 0),    # 下降货物
        (3, 8, 1, 0)     # 停止
    ]

    # 获取当前位置信息
    isconnected = heartbeat_mgr.is_connected()
    print(f'是否连接: {isconnected}')

    currentStatus = heartbeat_mgr.current_status
    print(f'小车当前状态: {currentStatus}')

    # # 4.2 将任务加入队列并获取任务ID
    # task_id = task_executor.queue_task(warehouse_segments)
    # print(f"\n任务{task_id}已加入队列，包含{len(warehouse_segments)}个路径段")
    
    # # 4.3 启动任务执行
    # print(f"正在发送任务{task_id}到小车...")
    # if task_executor.start_task(task_id, warehouse_segments):
    #     print(f"任务{task_id}已成功下发到小车")
    # else:
    #     print(f"任务{task_id}下发失败，请检查网络连接")
    
    # =========================================================================
    # 步骤5: 处理命令响应 (模拟)
    # =========================================================================
    
    # # 在实际系统中，这里是响应处理线程
    # time.sleep(1.5)  # 模拟处理延迟
    
    # # 5.1 模拟小车响应数据
    # # 注意: 实际应用中，这里是真实的网络数据
    # mock_response = {
    #     'device_id': 1,
    #     'life': 42,
    #     'frame_type': RESProtocol.FrameType.TASK,
    #     'task_id': task_id,
    #     'result': 0,  # 成功代码
    #     'current_segment': 3
    # }
    
    # # 5.2 处理响应
    # handle_task_response(mock_response)
    
    # =========================================================================
    # 步骤6: 发送紧急停止命令
    # =========================================================================
    
    # def emergency_stop():
    #     """紧急停止命令"""
    #     print("\n正在发送紧急停止命令...")
    #     cmd_packet = builder.build_command(
    #         cmd_id=RESProtocol.CommandID.EMERGENCY_STOP,
    #         task_no=task_id,
    #         cmd_no=1
    #     )
    #     if network.send(cmd_packet):
    #         print("紧急停止命令已发送")
    #     else:
    #         print("紧急停止命令发送失败")
    
    # # 模拟紧急情况触发急停
    # time.sleep(2)
    # emergency_stop()
    
    # =========================================================================
    # 步骤7: 监控和状态报告
    # =========================================================================
    
    # print("\n===== 系统状态报告 =====")
    # print(f"心跳状态: {'连接正常' if heartbeat_mgr.is_connected() else '连接断开'}")
    
    # # 模拟小车状态数据
    # if heartbeat_mgr.current_status:
    #     status = heartbeat_mgr.current_status
    #     print(f"小车位置: X={status.get('x', 0)}, Y={status.get('y', 0)}, Z={status.get('z', 0)}")
    #     print(f"电量: {status.get('battery', '未知')}%")
    #     print(f"载货状态: {'有货物' if status.get('have_pallet') else '无货物'}")
    
    # =========================================================================
    # 步骤8: 系统清理
    # =========================================================================
    
    print("\n正在停止系统...")
    heartbeat_mgr.stop()
    network.close()
    print("系统已安全关闭")

if __name__ == "__main__":
    
    main()