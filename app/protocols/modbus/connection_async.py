# # protocols/modbus/async_connection.py
# import asyncio
# from app.core.connection import BaseConnection
# from aioModbus import AsyncModbusTcpClient

# class AsyncModbusTcpConnection(BaseConnection):
#     """Modbus TCP协议的异步连接实现。"""
    
#     def __init__(self, host: str, port: int = 502, unit_id: int = 1):
#         self._host = host
#         self._port = port
#         self._unit_id = unit_id
#         self._client: Optional[AsyncModbusTcpClient] = None
#         self._connected = False
    
#     async def connect(self) -> bool:  # 注意这里是异步方法
#         try:
#             self._client = AsyncModbusTcpClient()
#             await self._client.connect(self._host, self._port)
#             self._connected = True
#             return True
#         except Exception as e:
#             print(f"异步Modbus连接失败: {e}")
#             self._connected = False
#             return False
    
#     async def read(self, address: str, length: int) -> bytes:
#         starting_address = int(address)
#         result = await self._client.read_holding_registers(
#             self._unit_id, starting_address, length
#         )
#         return bytes(result)
    
#     async def write(self, address: str, data: bytes) -> bool:
#         starting_address = int(address)
#         values = list(data)
#         await self._client.write_multiple_registers(
#             self._unit_id, starting_address, values
#         )
#         return True
    
#     async def disconnect(self) -> None:
#         if self._client:
#             await self._client.close()
#         self._connected = False
    
#     @property
#     def is_connected(self) -> bool:
#         return self._connected