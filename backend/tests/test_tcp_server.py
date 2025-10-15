import socket
import sys

HOST = 'localhost'
PORT = 65432

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"TCP服务已启动，监听 {HOST}:{PORT}")
        print("按 Ctrl+C 停止服务")

        while True:  # 持续监听循环
            conn, addr = s.accept()  # 接受新连接
            with conn:
                print(f"\n新连接来自 {addr}")
                try:
                    while True:
                        data = conn.recv(2048)
                        if not data:
                            print("连接已关闭")
                            break
                        print(f"接收到数据: {data}")
                        # conn.sendall(b"Server received: Message Received!")
                        conn.sendall(data)
                except Exception as e:
                    print(f"连接异常：{e}")

except KeyboardInterrupt:
    print("\n正在停止TCP服务...")
    sys.exit(0)