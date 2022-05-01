# UltraRpc
极致简洁的rpc,只需安心的写你的python代码，其他都不需要关心

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
3.  运行服务端
```
rpcserver.run()
```


#### RpcServer

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

