# TCP 客户端
import socket

HOST = 'localhost'  # The server's hostname or IP address
PORT = 65432        # The port used

# HOST = "192.168.8.30"  # The server's hostname or IP address
# PORT = 2504        # The port used


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))  # 连接到服务器
    print(f"已连接到服务器 {HOST}:{PORT}")
    
    message = b'\x02\xfd\x01\xc3\x10\x00\x0b\x6c\xab\x03\xfc'
    # input_message = input("请输入要发送的消息: ")
    # if input_message:
    #     message = input_message
    s.sendall(message)  # 发送数据
    print(f"发送数据: {message}")
    
    data = s.recv(2048)  # 接收响应
    print(f"接收到响应: {data}")  # 打印接收到的数据

# b'\x02\xfd\x01\xc3\x10\x00\x0b\x6c\xab\x03\xfc'
# '02 fd 02 0a 10 00 0b 17 37 03 fc'