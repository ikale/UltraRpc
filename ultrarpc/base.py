from functools import partial
import types
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer

from .utils import is_port_open


class BoRpcClient:
    def __init__(self,host='127.0.0.1',prot=8808) -> None:
        self._host = host
        self._prot = prot
        self._sever_proxy  = ServerProxy(f'http://{host}:{prot}')
        

    @property
    def rpcfunc(self):
        if not self._rpcfunc:
            self.update_rpcfunc()
        return self._rpcfunc


    def update_rpcfunc(self):
        """远程rpc函数本地化"""
        _dict = {'_severproxy':self._sever_proxy}
        
        funcs_info = self._sever_proxy.rpc_funcs()
        for f in funcs_info.values():
            name= f['name']
            doc = f['doc']
            params = f['params']
            default_values = f['default_values']
            annotations = f['annotations']
            _dict[name] = self.__create_local_rpcfunc(name,doc,params,default_values,annotations)

        self._rpcfunc = type('RpcFunc',(object,),_dict)()


    def __create_local_rpcfunc(self,name,doc,params,default_values,annotations):
        args = ""
        for param in params:
            args+=param
            args+=','
            
        code = f"""def {name}(self,{args}):
                '''{doc}'''
                return self._severproxy.{name}({args})
        """
        module_code = compile(code, '', 'exec')
        function_code = [c for c in module_code.co_consts if isinstance(c, types.CodeType)][0]
        default_values = tuple(default_values) if default_values else None
        func = types.FunctionType(function_code,globals(),name,default_values)
        for an in annotations.keys():
            annotations[an] = eval(annotations[an])
        func.__annotations__ = annotations
        return func



class BoRpcServer:

    def __init__(self,host='127.0.0.1',prot=8808) -> None:
        assert not is_port_open(prot),f'<BoRpcServer>: init faild,Prot "{prot}" already in use!'
        self._server = SimpleXMLRPCServer((host,prot),allow_none=True)
        self._host = host
        self._prot = prot
        self._rpc_funcs = {}
        self._server.register_function(partial(BoRpcServer.__rpc_funcs,self),name="rpc_funcs")


    @property
    def host(self):
        return self._host

    @property
    def prot(self):
        return self._prot

    @property
    def rpc_funcs(self):
        return self._rpc_funcs


    @staticmethod
    def __rpc_funcs(rpcsever_instance):
        """
        用于在远程调用
        返回rpc服务器上注册得 所有可调用函数得信息
        """
        return rpcsever_instance.rpc_funcs


    def __save_rpc_funcs_info(self,f:callable,name=None):
        name = f.__name__ if name is None else name
        params= f.__code__.co_varnames
        default_values= f.__defaults__
        doc = f.__doc__
        annotations = f.__annotations__
        for an in annotations.keys():
            annotations[an] = annotations[an].__name__
        
        self._rpc_funcs[f.__name__] = {'name':name,'doc':doc,'params':params,'default_values':default_values,'annotations':annotations}



    def register_function(self,f=None,name=None):
        """将函数注册为 rpc函数"""
        # decorator factory
        if f is None:
            return partial(self.register_function, name=name)

        if not name:
            name = f.__name__

        if name not in self._server.funcs:
            self._server.register_function(f,name)
            self.__save_rpc_funcs_info(f,name)
        return f



    def run(self):
        print(f"start rpc server on http://{self.host}:{self.prot}")
        self._server.serve_forever()