# app/protocols/__init__.py

"""
protocols/            # 【协议实现层】各通信协议的具体实现，同步/异步在此区分
   ├── modbus/
   │   ├── __init__.py
   │   ├── constants.py  # Modbus特定常量
   │   ├── connection.py # 包含SyncModbusConnection和AsyncModbusConnection
   │   └── client.py     # 包含ModbusClient的同步和异步实现
   ├── snap7/
   ├── socket_tcp/       # 自定义Socket TCP协议
   └── ...               # 其他协议（如Profibus, CC-Link等[2,5](@ref)）
"""