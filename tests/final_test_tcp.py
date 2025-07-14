import socket
import time
import platform

def test_mac_tcp():
    HOST = '192.168.123.188'
    PORT = 2504
    
    print(f"=== MacOS TCP 诊断工具 ===")
    print(f"系统信息: {platform.platform()}")
    print(f"Python版本: {platform.python_version()}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # 关键套接字选项
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        print(f"\n连接服务器 {HOST}:{PORT}...")
        sock.connect((HOST, PORT))
        print("✅ 连接成功!")
        
        # 测试 1: 单字节发送
        sock.sendall(b'A')
        print("测试 1: 单字节发送成功")
        time.sleep(0.1)
        
        # 测试 2: 小数据包
        sock.sendall(b'B'*128)
        print("测试 2: 128字节发送成功")
        time.sleep(0.1)
        
        # 测试 3: 完整 MTU 包
        sock.sendall(b'C'*1460)
        print("测试 3: 1460字节发送成功")
        time.sleep(0.1)
        
        # 测试 4: 原始协议包
        protocol_msg = bytes.fromhex("02 fd 02 e8 10 00 0b 21 4f 03 fc")
        sock.sendall(protocol_msg)
        print(f"测试 4: {len(protocol_msg)}字节协议包发送成功")
        
        # 检查状态
        print("\n发送状态:")
        print(f" - 套接字状态: {'打开' if sock.fileno() != -1 else '关闭'}")
        print(f" - 待发送队列: {sock.getsockopt(socket.SOL_SOCKET, socket.SO_NWRITE)}字节")
        
    except Exception as e:
        print(f"❌ 测试失败: {type(e).__name__}: {str(e)}")
    finally:
        sock.close()
        print("\n测试完成!")

if __name__ == "__main__":
    test_mac_tcp()