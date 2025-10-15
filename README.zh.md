# NetworkX 路径规划系统

## 项目简介

基于 NetworkX 的路径规划开源项目，专注于提供高效、灵活的图算法支持，适用于各种路径优化问题。本项目主要应用于自动化仓储系统中的穿梭车路径规划与任务调度。

## 核心功能

### 1. 路径规划
- 基于 NetworkX 图算法的最短路径计算
- 多层仓库地图建模（支持最多4层立体仓库）
- 可视化地图展示与路径绘制

### 2. 设备控制
- 穿梭车（Car）控制模块
- PLC（可编程逻辑控制器）通信模块
- 支持真实设备连接和模拟模式

### 3. 任务调度
- WCS（仓库控制系统）任务管理
- WMS（仓库管理系统）订单处理
- 任务优先级调度机制

### 4. 系统接口
- RESTful API 接口（提供 v1 和 v2 两个版本）
- 支持 Swagger UI 文档
- 数据库操作接口

### 5. 用户界面
- 基于 Streamlit 的可视化操作界面
- 提供调试工具页面
- 支持手动操作和自动化操作模式

## 技术架构

### 核心技术栈
- Python 3.10+
- FastAPI - Web 框架
- NetworkX - 图算法处理
- SQLAlchemy - 数据库 ORM
- Matplotlib - 数据可视化
- Streamlit - 前端界面

### 系统架构
```
┌─────────────────┐    ┌────────────────┐    ┌──────────────────┐
│   Streamlit UI  │    │   FastAPI API  │    │  设备通信模块     │
│   (可视化界面)   │◄──►│   (REST接口)    │◄──►│ (PLC/穿梭车控制)  │
└─────────────────┘    └────────────────┘    └──────────────────┘
                              │                        │
                    ┌─────────▼─────────┐    ┌─────────▼─────────┐
                    │   任务调度模块     │    │   路径规划模块     │
                    │  (TaskScheduler)  │    │  (NetworkX算法)    │
                    └───────────────────┘    └───────────────────┘
                              │                        │
                    ┌─────────▼─────────┐    ┌─────────▼─────────┐
                    │    数据库层        │    │    地图数据层      │
                    │  (SQLite/SQLAlchemy)│   │  (JSON配置文件)    │
                    └───────────────────┘    └───────────────────┘
```

## 项目结构

```
nx_path_planning/
├── backend/                 # 后端应用
│   ├── app/                 # 主应用程序目录
│   │   ├── api/             # REST API 接口
│   │   │   ├── v1/          # API 版本 1
│   │   │   └── v2/          # API 版本 2
│   │   ├── core/            # 核心应用组件
│   │   ├── data/            # 数据库文件
│   │   ├── devices/         # 设备控制模块
│   │   ├── map_core/        # 地图与路径核心算法
│   │   │   └── data/        # 地图配置数据
│   │   ├── models/          # 数据库模型
│   │   ├── plc_system/      # PLC 通信系统
│   │   ├── protocols/       # 通信协议
│   │   ├── res_system/      # RES 通信系统
│   │   ├── task_scheduler/  # 任务调度模块
│   │   ├── utils/           # 工具函数
│   │   └── main.py          # 应用程序入口点
│   ├── tests/               # 测试文件
│   ├── build.py             # 构建脚本
│   └── run.py               # 运行脚本
├── frontend/                # 前端应用
│   ├── v1/                  # 前端版本 1
│   └── v2/                  # 前端版本 2
├── tests/                   # 额外的测试文件
├── README.md                # 英文文档
├── README.zh.md             # 中文文档
├── LICENSE                  # 许可证文件
└── .gitignore               # Git 忽略文件
```

## 安装与部署

### 环境要求
- Python 3.10 或更高版本
- pip 包管理器

### 安装步骤

1. 克隆项目代码：
```bash
git clone <项目地址>
cd nx_path_planning
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置系统参数（可选）：
编辑配置文件以修改设备IP地址等配置项

### 启动服务

1. 启动 API 服务：
```bash
cd backend
python run.py
```

2. 启动可视化界面（新终端窗口）：
```bash
cd frontend/v2
streamlit run main.py
```

### 访问系统
- API 文档：http://localhost:8765/docs
- 可视化界面：http://localhost:8501

## 核心模块说明

### 地图与路径规划模块 (map_core)
该模块负责仓库地图的构建和路径规划算法实现：
- `MapBase.py` - 地图基础类，负责读取地图配置并构建 NetworkX 图
- `PathBase.py` - 路径规划基础类，提供最短路径计算功能
- `PathCustom.py` - 自定义路径规划扩展

### 设备控制模块 (devices)
负责与物理设备通信：
- `async_devices_controller.py` - 异步设备控制器
- `devices_controller.py` - 设备控制器
- `fsm_devices_controller.py` - 有限状态机设备控制器
- `service_asyncio.py` - 异步通信服务

### API 接口模块 (api)
提供 RESTful API 接口：
- `v1/` - 第一版 API 接口
- `v2/` - 第二版 API 接口（推荐使用）

### 任务调度模块 (task_scheduler)
负责任务调度和管理：
- `TaskScheduler.py` - 主任务调度器实现
- `models.py` - 任务数据模型

## 配置说明

系统主要配置项在 `backend/app/core/config.py` 文件中。

## 开发指南

### 添加新功能
1. 在对应的模块目录下创建新文件
2. 遵循现有代码风格和规范
3. 编写单元测试
4. 更新 API 文档

### 扩展地图
1. 修改 `backend/app/map_core/data/` 目录下的地图配置文件
2. 添加新的节点和边定义
3. 重启服务使配置生效

## 贡献

1. Fork 本仓库
2. 新建 Feat_xxx 分支
3. 提交代码
4. 新建 Pull Request

## 许可证

本项目采用 Apache License 2.0 许可证，详情请见 [LICENSE](LICENSE) 文件。