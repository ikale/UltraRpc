# UltraRpc
ultrarpc是轻量快速的rpc服务，对第三方库零依赖，速度比zerorpc快20%.
<!-- ultrarpc is ultra light-weight and faster，which take no  dependency to the third  library .
it's 20% faster than zerorpc. -->

### 安装
```
pip install ultrarpc
```

### 使用说明

#### RpcServer

1.  创建服务端
```
from ultrarpc import RpcServer
rpcserver = RpcServer(host='127.0.0.1',prot=8808,usedoc=True)
```
2.  注册rpc函数
```
@rpcserver.register_function
def double(x:int,y:int)->int:
    """乘方"""
    return x**y

```
3. 注册类或实例
```
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

    
tc = TestClass()    
rpcserver.register_class(tc,'testclass')



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

```

4.  运行服务端
```
rpcserver.run()
```


#### RpcClient

1.  连接服务端
```
from ultrarpc import RpcClient
c = RpcClient('127.0.0.1','8808')
c.init_localproxy()
```
2.  单次调用rpc函数
```
c.rpcfunc.double(y=2,x=2)
```
3.  多次调用rpc函数（把多次单用合并为一个请求）
```
c.multicall.double(2,3)
c.multicall.double(3,2)
c.multicall.double(5,2)

c.multicall.results()
```

