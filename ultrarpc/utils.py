import socket

def is_port_open(port,ip='127.0.0.1')->bool:
    """检测端口是否被占用"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(socket.SHUT_RDWR)
        return True
    except Exception as e:
        pass

    return False