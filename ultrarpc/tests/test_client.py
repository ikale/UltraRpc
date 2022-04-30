import os
os.sys.path.append(os.path.abspath('./'))


from ultrarpc import RpcClient

client = RpcClient('127.0.0.1','8808')
rpcfunc = client.rpcfunc

[f for f in dir(rpcfunc) if not f.startswith("_")]
