# tests/test_models.py

# 系统路径
import os
import sys
from pathlib import Path
# 调试输出路径信息
print("当前工作目录:", os.getcwd())
print("sys.path:", sys.path)
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from sqlalchemy.orm import sessionmaker

from models.base_enum import TaskStatus, TaskType, LocationStatus
from models.base_model import OrderList, TaskList, LocationList
from models.init_db import init_db


# 核心业务逻辑
class WarehouseSystem:
    def __init__(self, session):
        self.session = session
    
    def generate_task_id(self):
        """生成任务ID (年月日时分秒)"""
        return datetime.now().strftime("%Y%m%d%H%M%S")
    
    def create_task(self, pallet_id, location, task_type, priority=0):
        """创建新任务"""
        task_id = self.generate_task_id()
        creation_time = datetime.now().strftime("%Y%m%d%H%M%S")
        
        task = TaskList(
            id=task_id,
            pallet_id=pallet_id,
            location=location,
            task_type=task_type,
            priority=priority,
            creation_time=creation_time
        )
        
        self.session.add(task)
        self.session.commit()
        return task
    
    def create_order(self, task_id, material_code, material_num, **kwargs):
        """创建新订单"""
        # 获取关联的任务
        task = self.session.get(TaskList, task_id)
        if not task:
            raise ValueError(f"任务ID {task_id} 不存在")
        
        order = OrderList(
            task_id=task_id,
            material_code=material_code,
            material_num=material_num,
            pallet_id=task.pallet_id,
            location=task.location,
            task_type=task.task_type,
            task_status=task.task_status,
            **kwargs
        )
        
        self.session.add(order)
        self.session.commit()
        return order
    
    def update_task_status(self, task_id, new_status):
        """更新任务状态"""
        task = self.session.get(TaskList, task_id)
        if task:
            task.task_status = new_status
            self.session.commit()
            
            # 同时更新关联订单的状态
            for order in task.orders:
                order.task_status = new_status
            self.session.commit()
            return True
        return False
    
    def update_location_status(self, location_id, new_status, pallet_id=None):
        """更新库位状态"""
        location = self.session.get(LocationList, location_id)
        if location:
            location.status = new_status
            if pallet_id is not None:
                location.pallet_id = pallet_id
            self.session.commit()
            return True
        return False
    
    def assign_pallet_to_location(self, pallet_id, location_id):
        """分配托盘到库位"""
        # 检查库位是否可用
        location = self.session.get(LocationList, location_id)
        if not location or location.status != LocationStatus.FREE:
            return False
        
        # 更新库位状态
        location.status = LocationStatus.OCCUPIED
        location.pallet_id = pallet_id
        self.session.commit()
        return True
    
    def free_location(self, location_id):
        """释放库位"""
        location = self.session.get(LocationList, location_id)
        if location and location.status == LocationStatus.OCCUPIED:
            location.status = LocationStatus.FREE
            location.pallet_id = None
            self.session.commit()
            return True
        return False
    
    def process_inbound(self, pallet_id, material_code, material_num, location_id):
        """处理入库流程"""
        # 检查库位是否可用
        location = self.session.get(LocationList, location_id)
        if not location or location.status != LocationStatus.FREE:
            raise ValueError("指定库位不可用")
        
        # 创建入库任务
        task = self.create_task(
            pallet_id=pallet_id,
            location=location.location,
            task_type=TaskType.PUTAWAY,
            priority=5  # 入库优先级
        )
        
        # 创建订单
        order = self.create_order(
            task_id=task.id,
            material_code=material_code,
            material_num=material_num
        )
        
        # 分配托盘到库位
        self.assign_pallet_to_location(pallet_id, location_id)
        
        # 更新任务状态为完成
        self.update_task_status(task.id, TaskStatus.COMPLETED)
        
        return task, order
    
    def process_outbound(self, location_id):
        """处理出库流程"""
        # 检查库位是否有托盘
        location = self.session.get(LocationList, location_id)
        if not location or location.status != LocationStatus.OCCUPIED or not location.pallet_id:
            raise ValueError("指定库位无托盘")
        
        # 获取托盘上的物料信息（实际系统中应从库存获取）
        # 这里简化为从订单中获取最新相关订单
        orders = self.session.query(OrderList).filter_by(
            pallet_id=location.pallet_id,
            location=location.location
        ).all()
        
        if not orders:
            raise ValueError("未找到相关订单信息")
        
        # 创建出库任务
        task = self.create_task(
            pallet_id=location.pallet_id,
            location=location.location,
            task_type=TaskType.PICKING,
            priority=3  # 出库优先级
        )
        
        # 创建出库订单（使用最后一条入库订单的信息）
        last_order = orders[-1]
        order = self.create_order(
            task_id=task.id,
            material_code=last_order.material_code,
            material_num=last_order.material_num
        )
        
        # 释放库位
        self.free_location(location_id)
        
        # 更新任务状态为完成
        self.update_task_status(task.id, TaskStatus.COMPLETED)
        
        return task, order


# 演示功能
if __name__ == "__main__":
    # 初始化数据库和会话
    engine = init_db(echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 创建系统实例
    warehouse = WarehouseSystem(session)
    
    # 添加初始库位数据
    locations = [
        LocationList(location="1,1,1", status=LocationStatus.FREE),
        LocationList(location="1,1,2", status=LocationStatus.FREE),
        LocationList(location="1,1,3", status=LocationStatus.HIGHWAY),
        LocationList(location="1,2,1", status=LocationStatus.FREE),
    ]
    session.add_all(locations)
    session.commit()
    
    # print("===== 模拟入库操作 =====")
    # # 托盘P1001携带物料M001(数量50)入库到库位1
    # task_in, order_in = warehouse.process_inbound(
    #     pallet_id="P1001",
    #     material_code="M001",
    #     material_num=50,
    #     location_id=1  # 对应location="1,1,1"
    # )
    # print(f"入库任务创建: ID={task_in.id}, 托盘={task_in.pallet_id}, 库位={task_in.location}")
    # print(f"入库订单创建: ID={order_in.id}, 物料={order_in.material_code}, 数量={order_in.material_num}")
    
    # # 查看库位状态
    # location1 = session.get(LocationList, 1)
    # print(f"库位1状态: {location1.status}, 托盘: {location1.pallet_id}")
    
    # print("\n===== 模拟出库操作 =====")
    # # 从库位1出库
    # task_out, order_out = warehouse.process_outbound(location_id=1)
    # print(f"出库任务创建: ID={task_out.id}, 托盘={task_out.pallet_id}, 库位={task_out.location}")
    # print(f"出库订单创建: ID={order_out.id}, 物料={order_out.material_code}, 数量={order_out.material_num}")
    
    # # 查看库位状态
    # location1 = session.get(LocationList, 1)
    # print(f"库位1状态: {location1.status}, 托盘: {location1.pallet_id}")
    
    # print("\n===== 数据库状态查询 =====")
    # # 查询所有任务
    # tasks = session.query(TaskList).all()
    # print("\n任务列表:")
    # for task in tasks:
    #     print(f"{task.id} | {task.task_type} | {task.task_status} | {task.pallet_id} | {task.location}")
    
    # # 查询所有订单
    # orders = session.query(OrderList).all()
    # print("\n订单列表:")
    # for order in orders:
    #     print(f"{order.id} | 任务{order.task_id} | {order.material_code}x{order.material_num} | {order.task_status}")
    
    # # 查询所有库位
    # locations = session.query(LocationList).all()
    # print("\n库位状态:")
    # for loc in locations:
    #     print(f"库位{loc.id}: {loc.location} | {loc.status} | 托盘: {loc.pallet_id or '无'}")
    
    # 关闭会话
    session.close()