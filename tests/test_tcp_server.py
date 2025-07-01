# TCP 服务器
import socket

HOST = 'localhost'  # The server's hostname or IP address
PORT = 65432        # The port used

socket.AF_INET  # AF_INET 是用于IPv4地址的地址族
# 还有其他地址族，如 AF_INET6 用于IPv6

socket.SOCK_STREAM  # SOCK_STREAM 是用于TCP的套接字类型
# 还有其他类型，如 SOCK_DGRAM 用于UDP
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))  # 绑定套接字到地址
    s.listen()  # 开始监听连接
    print("TCP服务已启动，等待连接...")

    print(f"TCP服务正在监听： {HOST}:{PORT}")
    conn, addr = s.accept()  # 接受连接
    with conn:
        print(f"已连接到 {addr}")
        try:
            while True:
                data = conn.recv(2048)  # 接收数据 1024 字节
                if not data:
                    print("没有接收到数据，连接可能已关闭。")
                    break
                print(f"接收到数据: {data}")
                conn.sendall(b"Server received: Message Recived!")  # 发送响应
        except Exception as e:
            print(f"连接异常：{e}")