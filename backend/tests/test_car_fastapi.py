# tests/test_car_fastapi.py
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import logging
import sys
from pathlib import Path

# 添加系统路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入穿梭车协议模块
from res_protocol_system import (
    RESProtocol, 
    PacketBuilder, 
    PacketParser, 
    NetworkManager, 
    HeartbeatManager, 
    TaskExecutor,
    DataReceiver
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("car_control")

# 创建 FastAPI 应用
app = FastAPI(
    title="穿梭车控制系统",
    description="基于RES+3.1协议的穿梭车控制API",
    version="1.0.0"
)

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
# car_ip = "192.168.8.30"  # 小车IP地址
# car_port = 2504          # 小车端口
# device_id = 2           # 设备ID

car_ip = "192.168.123.188"  # 小车IP地址
car_port = 2504          # 小车端口
device_id = 2           # 设备ID

# 全局穿梭车组件
network = None
builder = None
parser = None
heartbeat_mgr = None
task_executor = None
data_rec = None

# 定义数据模型
class TaskRequest(BaseModel):
    segments: list
    task_id: int

class CommandRequest(BaseModel):
    cmd_id: int
    param: int = 0
    task_no: int = 0
    cmd_no: int = 1

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化连接"""
    global network, builder, parser, heartbeat_mgr, task_executor, data_rec
    
    logger.info("正在启动穿梭车连接...")
    
    # 初始化组件
    network = NetworkManager(car_ip, car_port)
    builder = PacketBuilder(device_id=device_id)
    parser = PacketParser()
    heartbeat_mgr = HeartbeatManager(network, builder)
    task_executor = TaskExecutor(network, builder)
    data_rec = DataReceiver(network, parser, task_executor, heartbeat_mgr)
    
    # 启动心跳
    heartbeat_mgr.start()
    
    # 连接小车
    if not await network.connect():
        logger.error("无法连接到穿梭车设备")
        return
    
    logger.info(f"已连接到穿梭车 {car_ip}:{car_port}")
    
    # 启动数据接收器
    data_rec.start()
    logger.info("数据接收器已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时断开连接"""
    logger.info("正在关闭系统...")
    
    if data_rec:
        data_rec.stop()
        logger.info("数据接收器已停止")
    
    if heartbeat_mgr:
        heartbeat_mgr.stop()
        logger.info("心跳管理器已停止")
    
    if network:
        await network.close()
        logger.info("网络连接已关闭")
    
    logger.info("系统已安全关闭")

@app.get("/status")
async def get_car_status():
    """获取小车状态"""
    if not heartbeat_mgr or not heartbeat_mgr.is_connected():
        raise HTTPException(
            status_code=503, 
            detail="未连接到小车设备"
        )
    
    # status = heartbeat_mgr.get_current_status()
    status = heartbeat_mgr.current_status
    
    if not status:
        raise HTTPException(
            status_code=503, 
            detail="未获取到小车状态"
        )
    
    # 添加连接状态
    status['connected'] = heartbeat_mgr.is_connected()
    
    return status

@app.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def create_task(task: TaskRequest = Body(...)):
    """
    创建穿梭车任务
    - task_id: 任务ID
    - segments: 路径段列表 [(x, y, z, action), ...]
    """
    if not task_executor:
        raise HTTPException(
            status_code=503, 
            detail="任务执行器未初始化"
        )
    
    # 发送任务
    result = await task_executor.send_task(
        task.task_id, 
        task.segments
    )
    
    if not result:
        raise HTTPException(
            status_code=503, 
            detail="发送任务失败，请检查设备连接"
        )
        
    return {"message": f"任务 {task.task_id} 已接受"}

@app.post("/commands/emergency_stop")
async def emergency_stop():
    """发送紧急停止命令"""
    if not task_executor:
        raise HTTPException(
            status_code=503, 
            detail="任务执行器未初始化"
        )
    
    if not await task_executor.send_emergency_stop():
        raise HTTPException(
            status_code=503, 
            detail="命令发送失败"
        )
    
    return {"message": "紧急停止命令已发送"}

@app.post("/commands/{command_id}")
async def send_command(command_id: int, request: CommandRequest = Body(...)):
    """
    发送控制命令
    - command_id: 命令ID (参考RESProtocol.CommandID)
    - params: 命令参数 {task_no, cmd_no, param}
    """
    if not task_executor:
        raise HTTPException(
            status_code=503, 
            detail="任务执行器未初始化"
        )
    
    # 检查命令ID是否有效
    valid_cmd_ids = [e.value for e in RESProtocol.CommandID]
    if command_id not in valid_cmd_ids:
        raise HTTPException(
            status_code=400, 
            detail="无效的命令ID"
        )
    
    # 发送命令
    if not await task_executor.send_command(
        command_id, 
        request.cmd_no, 
        request.task_no, 
        request.param
    ):
        raise HTTPException(
            status_code=503, 
            detail="命令发送失败"
        )
        
    return {"message": f"命令 {command_id} 已发送"}

@app.get("/health")
async def health_check():
    """健康检查接口"""
    if not heartbeat_mgr:
        return {"status": "uninitialized"}
    
    status = heartbeat_mgr.current_status
    return {
        "connected": heartbeat_mgr.is_connected() if heartbeat_mgr else False,
        "last_update": status.get("last_update") if status else None,
        "car_status": status.get("car_status") if status else -1,
        # "heartbeat_active": heartbeat_mgr.is_running(),  # 新增心跳状态
        "thread_alive": heartbeat_mgr.thread.is_alive() if heartbeat_mgr.thread else False  # 新增线程状态
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)