# NetworkX Path Planning System

## Project Introduction

An open-source path planning project based on NetworkX, focusing on providing efficient and flexible graph algorithm support for various path optimization problems. This project is mainly applied to shuttle car path planning and task scheduling in automated storage systems.

## Core Features

### 1. Path Planning
- Shortest path calculation based on NetworkX graph algorithms
- Multi-layer warehouse map modeling (supports up to 4-layer立体 warehouses)
- Visual map display and path drawing

### 2. Device Control
- Shuttle car (Car) control module
- PLC (Programmable Logic Controller) communication module
- Supports real device connection and simulation mode

### 3. Task Scheduling
- WCS (Warehouse Control System) task management
- WMS (Warehouse Management System) order processing
- Task priority scheduling mechanism

### 4. System Interface
- RESTful API interface (provides v1 and v2 versions)
- Supports Swagger UI documentation
- Database operation interface

### 5. User Interface
- Visual operation interface based on Streamlit
- Provides debugging tool pages
- Supports manual and automated operation modes

## Technical Architecture

### Core Technology Stack
- Python 3.10+
- FastAPI - Web framework
- NetworkX - Graph algorithm processing
- SQLAlchemy - Database ORM
- Matplotlib - Data visualization
- Streamlit - Frontend interface

### System Architecture
```
┌─────────────────┐    ┌────────────────┐    ┌──────────────────┐
│   Streamlit UI  │    │   FastAPI API  │    │  Device Communication │
│  (Visualization) │◄──►│   (REST API)   │◄──►│   (PLC/Shuttle Control)│
└─────────────────┘    └────────────────┘    └──────────────────┘
                              │                        │
                    ┌─────────▼─────────┐    ┌─────────▼─────────┐
                    │   Task Scheduler  │    │  Path Planning   │
                    │  (TaskScheduler)  │    │ (NetworkX Algorithms)│
                    └───────────────────┘    └───────────────────┘
                              │                        │
                    ┌─────────▼─────────┐    ┌─────────▼─────────┐
                    │   Database Layer  │    │   Map Data Layer │
                    │ (SQLite/SQLAlchemy)│    │ (JSON Config Files)│
                    └───────────────────┘    └───────────────────┘
```

## Project Structure

```
nx_path_planning/
├── backend/                 # Backend application
│   ├── app/                 # Main application directory
│   │   ├── api/             # REST API interfaces
│   │   │   ├── v1/          # API version 1
│   │   │   └── v2/          # API version 2
│   │   ├── core/            # Core application components
│   │   ├── data/            # Database files
│   │   ├── devices/         # Device control modules
│   │   ├── map_core/        # Map and path core algorithms
│   │   │   └── data/        # Map configuration data
│   │   ├── models/          # Database models
│   │   ├── plc_system/      # PLC communication system
│   │   ├── protocols/       # Communication protocols
│   │   ├── res_system/      # RES communication system
│   │   ├── task_scheduler/  # Task scheduling module
│   │   ├── utils/           # Utility functions
│   │   └── main.py          # Application entry point
│   ├── tests/               # Test files
│   ├── build.py             # Build script
│   └── run.py               # Run script
├── frontend/                # Frontend application
│   ├── v1/                  # Frontend version 1
│   └── v2/                  # Frontend version 2
├── tests/                   # Additional test files
├── README.md                # English documentation
├── README.zh.md             # Chinese documentation
├── LICENSE                  # License file
└── .gitignore               # Git ignore file
```

## Installation and Deployment

### Requirements
- Python 3.10 or higher
- pip package manager

### Installation Steps

1. Clone the project code:
```bash
git clone <project_url>
cd nx_path_planning
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure system parameters (optional):
Edit the configuration files to modify device IP addresses and other configuration items

### Start Services

1. Start the API service:
```bash
cd backend
python run.py
```

2. Start the visualization interface (new terminal window):
```bash
cd frontend/v2
streamlit run main.py
```

### Access the System
- API Documentation: http://localhost:8765/api/v2/docs
- Visualization Interface: http://localhost:8501

## Core Module Description

### Map and Path Planning Module (map_core)
This module is responsible for warehouse map construction and path planning algorithm implementation:
- `MapBase.py` - Map base class, responsible for reading map configuration and building NetworkX graph
- `PathBase.py` - Path planning base class, provides shortest path calculation functionality
- `PathCustom.py` - Custom path planning extensions

### Device Control Module (devices)
Responsible for communication with physical devices:
- `async_devices_controller.py` - Asynchronous device controller
- `devices_controller.py` - Device controller
- `fsm_devices_controller.py` - Finite state machine device controller
- `service_asyncio.py` - Asynchronous communication service

### API Interface Module (api)
Provides RESTful API interfaces:
- `v1/` - First version of API interfaces
- `v2/` - Second version of API interfaces (recommended)

### Task Scheduler Module (task_scheduler)
Responsible for task scheduling and management:
- `TaskScheduler.py` - Main task scheduler implementation
- `models.py` - Task data models

## Configuration Description

The main system configuration items are in the `backend/app/core/config.py` file.

## Development Guide

### Adding New Features
1. Create new files in the corresponding module directory
2. Follow existing code style and specifications
3. Write unit tests
4. Update API documentation

### Extending Maps
1. Modify the map configuration files in `backend/app/map_core/data/`
2. Add new node and edge definitions
3. Restart the service for the configuration to take effect

## Contributing

1. Fork the repository
2. Create a Feat_xxx branch
3. Commit your code
4. Create a Pull Request

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.