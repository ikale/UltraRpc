from functools import partial
import types,inspect
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer,DocXMLRPCServer,SimpleXMLRPCRequestHandler

from datetime import datetime

from .utils import is_port_open


FUNC_KEEPWORD = ['results','clear_results','clear_calltasks']


class LocalProxy:
    def __init__(self,
        sever_proxy,
        minimum_update_interval=2,
        is_multicall = False
        ) -> None:
        self._sever_proxy = sever_proxy
        self._all_rpcfuncs = []

        self._last_update = 0
        self._minimum_update_interval = minimum_update_interval

        self._is_multicall = is_multicall
        self._calltasks = []
        self._results = []


    def __notfound_func(self,methodName,*arg,**kwarg):
        res = getattr(self,methodName)(*arg,**kwarg)
        return res


    def __getattr__(self, name: str):
        """本地不存在该函数，首先进行一次更新同步"""
        curtimestamp = datetime.now().timestamp()
        if curtimestamp- self._last_update >self._minimum_update_interval:       
            self._update_rpcfunc()
            self._last_update = curtimestamp
            if hasattr(self,name):
                return partial(self.__notfound_func,name)
            else:
                raise AttributeError(f"'RpcClient' object has no attribute '{name}'")
        else:
            raise AttributeError(f"'RpcClient' object has no attribute '{name}'")


    def _update_rpcfunc(self):
        """远程rpc函数本地化更新"""
        # print('update rpcfunc')
        funcs_info = self._sever_proxy.rpc_funcs()
        self._all_rpcfuncs = []
        for f in funcs_info.values():
            name= f['name']
            self._all_rpcfuncs.append(name)
            doc = f['doc']
            params = f['params']
            default_values = f['default_values']
            annotations = f['annotations']
            setattr(self,name,types.MethodType(
                self.__create_local_rpcfunc(name,doc,params,default_values,annotations),
                self)
            )


    def __create_local_rpcfunc(self,name,doc,params,default_values,annotations):
        args = ""
        for param in params:
            args+=param
            args+=','
            
        # add to LocalProxy instance
        code = f"""def {name}(self,{args}):
                '''{doc}'''
                if self._is_multicall:
                    self._add_multicall_funcinfo(self.{name},locals())
                    return self
                else:
                    return self._sever_proxy.{name}({args})
        """
        module_code = compile(code, '', 'exec')
        function_code = [c for c in module_code.co_consts if isinstance(c, types.CodeType)][0]
        default_values = tuple(default_values) if default_values else None
        func = types.FunctionType(function_code,globals(),name,default_values)
        for an in annotations.keys():
            annotations[an] = eval(annotations[an])
        func.__annotations__ = annotations
        return func


    def _add_multicall_funcinfo(self,func,_locals):        
        _ = dict(methodName=func.__name__,params=[])
        for i in inspect.getfullargspec(func).args:            
            _val = _locals[i]
            if type(_val) is LocalProxy: continue
            _['params'].append(_val)

        self._calltasks.append(_)



def create_multicall_proxy_instance(sever_proxy):
    muticall = LocalProxy(sever_proxy,is_multicall=True)

    def results(self,clear=True):
        if len(self._calltasks)>0:
            self._results = self._sever_proxy.system.multicall(self._calltasks)
            self._calltasks = []
        res = self._results
        if clear:
            self._results = []
        return res

    def clear_results(self):
        self._results = []
        return True

    def clear_calltasks(self):
        self._calltasks = []
        return True

    setattr(muticall,'results',types.MethodType(results,muticall))
    setattr(muticall,'clear_results',types.MethodType(clear_results,muticall))
    setattr(muticall,'clear_calltasks',types.MethodType(clear_calltasks,muticall))

    return muticall


class RpcClient:
    def __init__(self,host='127.0.0.1',prot=8808) -> None:
        self._host = host
        self._prot = prot
        self._sever_proxy  = ServerProxy(f'http://{host}:{prot}')
        self.__init = False


    def init_localproxy(self):
        if self.__init:
            return
        self.__init = True
        self._multicall = create_multicall_proxy_instance(self._sever_proxy)
        self.__rpcfunc = LocalProxy(self._sever_proxy)
        self.__rpcfunc._update_rpcfunc()
        self._multicall._update_rpcfunc()


    @property
    def all_rpcfuncs(self):
        if not self.__init:
            raise RuntimeError('localproxy is not init!')
        self.__rpcfunc._update_rpcfunc()
        return self.__rpcfunc._all_rpcfuncs

    @property
    def rpcfunc(self):
        if not self.__init:
            raise RuntimeError('localproxy is not init!')
        return self.__rpcfunc

    @property
    def multicall(self):
        if not self.__init:
            raise RuntimeError('localproxy is not init!')
        return self._multicall




class RpcServer:

    def __init__(self,
        host='127.0.0.1',
        prot=8808,
        usedoc=True
        ) -> None:
        assert not is_port_open(prot),f'<RpcServer>: init faild,Prot "{prot}" already in use!'

        if usedoc:
            self._server = DocXMLRPCServer((host,prot),allow_none=True)
        else:
            self._server = SimpleXMLRPCServer((host,prot),allow_none=True)

        self._host = host
        self._prot = prot
        self._rpc_funcs = {}
        self._server.register_function(partial(RpcServer.__rpc_funcs,self),name="rpc_funcs")
        self._server.register_multicall_functions()

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
        params= tuple(inspect.getfullargspec(f).args)
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

        if name in FUNC_KEEPWORD:
            raise ValueError(f"can't set {name},it's keep words!")

        if name not in self._server.funcs:
            self._server.register_function(f,name)
            self.__save_rpc_funcs_info(f,name)
        return f



    def run(self):
        print(f"start rpc server on http://{self.host}:{self.prot}")
        self._server.serve_forever()