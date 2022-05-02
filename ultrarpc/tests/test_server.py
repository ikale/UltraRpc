import os
os.sys.path.append(os.path.abspath('./'))
from ultrarpc import RpcServer


rpcserver = RpcServer(host='127.0.0.1',prot=8808)

@rpcserver.register_function
def double(x:int,y:int)->int:
    """乘方"""
    return x**y



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


@rpcserver.register_function(name='hello')
def hi2(string:str):
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



# 注册类的实例
class TestClass:

    def __init__(self) -> None:
        self.data = 1

    def add(self,x:int)->int:
        """操作类中的变量"""
        self.data+=x
        return self.data

    def say(self,name:str)->str:
        """测试输出"""
        return f'hello {name}'

rpcserver.register_class(TestClass(),'testclass')



# 使用装饰起注册类，将在内部自动实例化
@rpcserver.register_class('testclass2',data=50)
class TestClass2:

    def __init__(self,data) -> None:
        self.data = data

    def add(self,x:int)->int:
        """操作类中的变量"""
        self.data+=x
        return self.data

    def say(self,name:str)->str:
        """测试输出"""
        return f'hello {name}'







if __name__ == '__main__':
    rpcserver.run()