# res_protocol_system/NetworkManager.py
# -*- coding: utf-8 -*-
"""
RES+3.1 穿梭车通信协议上位机系统 - 模块化设计
按功能划分不同模块，便于团队协作维护
"""

import socket
import time

# ------------------------
# 模块 4: 通信处理器
# 职责: 管理网络连接和数据传输
# 维护者: 网络通信工程师
# ------------------------
class NetworkManager:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.reconnect_attempts = 0
        self.max_reconnect = 5
    
    def connect(self):
        """建TCP连接"""
        try:
            if self.sock:
                self.sock.close()
                
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(3.0)  # 设置超时3秒
            
            # 添加连接目标服务器的步骤
            server_address = (self.host, self.port)  # 需要替换为实际服务器地址
            self.sock.connect(server_address)
            
            self.reconnect_attempts = 0
            return True
        except socket.error as e:
            print(f"连接失败: {str(e)} 错误码: {e.errno}")
            print(f"检查服务器是否运行，防火墙是否开放端口")
            self.reconnect_attempts += 1
            # 添加自动重连机制
            if self.reconnect_attempts < 3:
                time.sleep(1)
                return self.connect()
            return False
        except Exception as ex:
            print(f"未知错误: {str(ex)}")
            return False

    def send(self, packet):
        """发送数据包"""
        try:
            if not self.sock:
                if not self.connect():
                    return False
                    
            # TCP连接使用send方法发送数据
            # 确保sock存在
            assert self.sock is not None, "Socket should be initialized after connect"
            self.sock.sendall(packet)
            return True
        except socket.error as e:
            print(f"发送失败: {str(e)}")
            return False
    
    def receive(self, timeout=1.0):
        """接收数据包"""
        if not self.sock:
            return None
            
        try:
            self.sock.settimeout(timeout)
            # TCP连接使用recv接收数据
            data = self.sock.recv(2048)  # 缓冲区2KB
            if not data:  # 连接关闭
                print("检测到连接断开")
                self.reconnect()
                return None
            print(f"[调试] 收到数据包: {data}")  # 打印收到的数据包
            return data
        except socket.timeout:
            return None
        except socket.error as e:
            print(f"接收错误: {str(e)}")
            self.reconnect()
            return None

    def reconnect(self):
        """重新连接机制"""
        if self.sock:
            self.sock.close()
            self.sock = None
        
        if self.reconnect_attempts < self.max_reconnect:
            print(f"尝试重连... (尝试次数: {self.reconnect_attempts + 1})")
            time.sleep(2)  # 等待2秒后重连
            if self.connect():
                print("重连成功")
                return True
        return False

    def close(self):
        """关闭连接"""
        if self.sock:
            self.sock.close()
            self.sock = None

def main():
    parser = NetworkManager(host="localhost", port=65432)
    parser.connect()
    data = b'\x02\xfd\x01\xc3\x00\x00\x00\x00'
    parser.send(data)
    parser.receive()
    parser.close()

if __name__ == "__main__":
    main()