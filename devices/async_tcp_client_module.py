import asyncio

class AsyncTCPClient:
    def __init__(self, host='127.0.0.1', port=8888):
        """
        初始化TCP客户端
        :param host: 服务器主机地址
        :param port: 服务器端口
        """
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.connected = False
    
    async def connect(self):
        """
        连接到TCP服务器
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            print(f"[CLIENT] 已连接到服务器 {self.host}:{self.port}")
        except ConnectionRefusedError:
            print("[CLIENT] 无法连接到服务器")
            self.connected = False
        return self.connected
    
    async def send_message(self, message):
        """
        发送消息到服务器
        :param message: 要发送的消息内容
        """
        if not self.connected:
            return False
        
        self.writer.write(message)
        await self.writer.drain()
        print(f"[CLIENT] 已发送: {message}")
        return True
    
    async def receive_message(self):
        """
        接收服务器响应
        :return: 服务器返回的消息
        """
        if not self.connected:
            return None
        
        data = await self.reader.read(1024)
        if not data:
            return None
        
        # response = data.decode()
        response = data
        print(f"[CLIENT] 收到服务端回复: {response}")
        return response
    
    async def close(self):
        """
        关闭连接
        """
        if self.connected and self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.connected = False
            print("[CLIENT] 连接已关闭")
        return True

async def main():
    """主函数用于测试"""
    client = AsyncTCPClient()
    if await client.connect():
        # 发送消息并接收响应
        await client.send_message("第一次测试")
        response = await client.receive_message()
        
        # 再次发送消息
        await client.send_message("第二次测试")
        response = await client.receive_message()
        
        # 关闭连接
        await client.close()

if __name__ == '__main__':
    asyncio.run(main())
