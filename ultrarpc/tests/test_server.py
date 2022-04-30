import os
os.sys.path.append(os.path.abspath('./'))
from ultrarpc import RpcServer


rpcserver = RpcServer(host='127.0.0.1',prot=8808)

@rpcserver.register_function
def double(x:int,y:int)->int:
    """乘方"""
    return x**y


global value
value=100

@rpcserver.register_function()
def sub(x:int):
    """操作一个本地变量"""
    global value
    value=value-x
    return value


@rpcserver.register_function(name='hello')
def hi(string:str):
    """返回字符串"""
    return string



@rpcserver.register_function
def get_dict()->dict:
    """返回一个字典"""
    return {'name':'ikale','sex':1,'age':18}



@rpcserver.register_function
def get_func():
    """###目前还无法返回函数。测试返回一个函数"""
    return sub


if __name__ == '__main__':
    rpcserver.run()