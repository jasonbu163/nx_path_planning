import asyncio

async def send_messages(writer: asyncio.StreamWriter):
    """发送消息到服务器"""
    while True:
        message = input("输入要发送的消息 (输入 'exit' 退出): ")
        if message.lower() == 'exit':
            break
            
        # 异步发送数据
        writer.write(message.encode())
        await writer.drain()
        print(f"[CLIENT] 已发送: {message}")

async def receive_messages(reader: asyncio.StreamReader):
    """接收服务器响应"""
    while True:
        # 异步接收数据
        data = await reader.read(1024)
        if not data:
            break
            
        response = data.decode()
        print(f"[CLIENT] 收到服务端回复: {response}")

async def start_async_client(host='127.0.0.1', port=8888):
    """启动异步TCP客户端"""
    reader, writer = await asyncio.open_connection(host, port)
    print(f"[CLIENT] 已连接到服务器 {host}:{port}")
    
    # 创建并发任务
    send_task = asyncio.create_task(send_messages(writer))
    receive_task = asyncio.create_task(receive_messages(reader))
    
    # 等待任意任务完成
    await asyncio.wait([send_task, receive_task], 
                        return_when=asyncio.FIRST_COMPLETED)
    
    # 清理资源
    writer.close()
    await writer.wait_closed()
    print("[CLIENT] 连接已关闭")

if __name__ == '__main__':
    try:
        HOST = "192.168.123.188"
        PORT = 8888
        asyncio.run(start_async_client(HOST, PORT))
    except ConnectionRefusedError:
        print("[CLIENT] 无法连接到服务器")
    except KeyboardInterrupt:
        print("\n[CLIENT] 客户端已关闭")