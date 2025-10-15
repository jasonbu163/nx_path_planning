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
├── api/                 # REST API interfaces
│   ├── v1/              # API version 1
│   └── v2/              # API version 2
├── data/                # Map configuration data
├── devices/             # Device control modules
├── map_core/            # Map and path core algorithms
├── models/              # Database models
├── res_protocol_system/ # Communication protocol processing
├── task_scheduler/      # Task scheduling module
├── tests/               # Test code
├── ui/                  # User interface
│   ├── v1/              # UI version 1
│   └── v2/              # UI version 2
├── config.py            # System configuration file
└── main.py              # System entry file
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
Edit the `config.py` file to modify device IP addresses and other configuration items

### Start Services

1. Start the API service:
```bash
python main.py
```

2. Start the visualization interface (new terminal window):
```bash
streamlit run ui/v2/main.py
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
- `car_controller.py` - Shuttle car controller
- `plc_controller.py` - PLC controller
- `service_asyncio.py` - Asynchronous communication service

### API Interface Module (api)
Provides RESTful API interfaces:
- `v1/` - First version of API interfaces
- `v2/` - Second version of API interfaces (recommended)

### User Interface Module (ui)
Visualization operation interface based on Streamlit:
- Provides device debugging functions
- Supports manual operation and task scheduling
- Visual path display

## Configuration Description

The main system configuration items are in the `config.py` file:

```python
PLC_IP = "192.168.8.10"           # PLC IP address
CAR_IP = "192.168.8.20"           # Shuttle car IP address
CAR_PORT = 2504                   # Shuttle car port
SQLITE_DB = "wcs.db"              # SQLite database filename
USE_MOCK_PLC = True               # Whether to use mock PLC (development mode)
```

## Development Guide

### Adding New Features
1. Create new files in the corresponding module directory
2. Follow existing code style and specifications
3. Write unit tests
4. Update API documentation

### Extending Maps
1. Modify the `data/map_config.json` file
2. Add new node and edge definitions
3. Restart the service for the configuration to take effect

## Contributing

1. Fork the repository
2. Create a Feat_xxx branch
3. Commit your code
4. Create a Pull Request

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.