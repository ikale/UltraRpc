from dataclasses import dataclass
import sys
import warnings
from functools import partial
from importlib import import_module
import types,inspect 
from xmlrpc.client import ServerProxy
from xmlrpc.server import SimpleXMLRPCServer,DocXMLRPCServer,resolve_dotted_attribute

from datetime import datetime

from .utils import is_port_open,get_funcs_info

@dataclass
class ResultError:
    res:str

KEEPWORD = ['results','clear_results','clear_calltasks','sys']


def _add_multicall_funcinfo__(localproxy_instance,func,_locals):
    """为multicall增加一条调用信息"""
    _ = dict(
        methodName=localproxy_instance._class+func.__name__,
        params=[]
        )
    for i in inspect.signature(func).parameters.keys():            
        _val = _locals[i]
        if type(_val) is LocalProxy: continue
        _['params'].append(_val)
    # print("增加一条调用",_)
    localproxy_instance._calltasks.append(_)



class Update_Localproxy:
    last_update = 0

    rpcfunc_localproxy_instances = None
    multicall_localproxy_instances = None

    @classmethod
    def update_rpcfunc(cls,localproxy_instances=None,localproxy_instance2=None,funcs_info=None)->datetime.timestamp:
        """
        远程rpc函数本地化更新
        更新时机：
            1.初始化化客户端的时候会被调用,默认会被调用两次(rpcfunc和multicall)
            2.当本地不存某个函数时,会先执行本方法进行更新
        """                
        if localproxy_instances is None and localproxy_instance2 is None:
            if  cls.rpcfunc_localproxy_instances ==None or cls.multicall_localproxy_instances == None:
                raise RuntimeError("The localproxy instance is not specified")
            else:
                localproxy_instances  = cls.rpcfunc_localproxy_instances
                localproxy_instance2 = cls.multicall_localproxy_instances
                funcs_info = localproxy_instances._sever_proxy.sys.get_rpc_funcs_info()['result']
       
       
        localproxy_instances._all_rpcfuncs = []
        for f in funcs_info.values():
            name= f['name']
            localproxy_instances._all_rpcfuncs.append(name)
            doc = f['doc']
            params = f['params']
            default_values = f['default_values']
            annotations = f['annotations']
            _arr = name.split(".")

            if len(_arr)==1:
                _rpc_func = cls.create_local_rpcfunc(name,doc,params,default_values,annotations)
                setattr(localproxy_instances,name,types.MethodType(_rpc_func,localproxy_instances))
                setattr(localproxy_instance2,name,types.MethodType(_rpc_func,localproxy_instance2))
            elif len(_arr)>1:
                _class = _arr[0]
                _name = '.'.join(_arr[1:])

                # print("带点的实例操作",_class,_name)

                new_rpcfunc = localproxy_instances._child.get(_class)
                if new_rpcfunc:
                    new_multicall = localproxy_instance2._child.get(_class)
                else:
                    p_class = localproxy_instances._class
                    new_rpcfunc = LocalProxy(localproxy_instances._sever_proxy,_class=p_class+_class)
                    new_multicall = create_multicall_proxy_instance(localproxy_instances._sever_proxy,_class=p_class+_class)
                    setattr(localproxy_instances,_class,new_rpcfunc)
                    setattr(localproxy_instance2,_class,new_multicall)
                    localproxy_instances._child[_class] = new_rpcfunc
                    localproxy_instance2._child[_class] = new_multicall
                
                f['name'] = _name
                cls.update_rpcfunc(new_rpcfunc,new_multicall,{_name:f})

        # print('already updated rpcfuncs')
        cls.last_update = datetime.now().timestamp()
        return cls.last_update


    @classmethod
    def create_local_rpcfunc(cls,name,doc,params,default_values,annotations):
        """为LocalProxy类,创建/映射本地rpc函数"""
        args = ""
        for param in params:
            args+=param
            args+=','
        
        # add to LocalProxy instance
        code = f"""def {name}(self,{args}):
                '''{doc}'''
                __l__ = locals()
                for __kk__,__tt__ in {annotations}.items():
                    __t__ = type(__l__[__kk__]).__name__
                    if __t__!=__tt__:
                        raise TypeError('parameter "'+__kk__+'" need an '+__tt__+', but it is an '+__t__+'.')

                if self._is_multicall:
                    _add_multicall_funcinfo__(self,self.{name},locals())
                    return self
                else: 
                    __res__ = eval("self._sever_proxy."+self._class+"{name}")({args})
                    if __res__.get("isfunc"):
                        return eval(__res__["result"])
                    else:
                        return __res__["result"]
        """
        module_code = compile(code, '', 'exec')
        function_code = [c for c in module_code.co_consts if isinstance(c, types.CodeType)][0]
        default_values = tuple(default_values) if default_values else None
        func = types.FunctionType(function_code,globals(),name,default_values)
        for an in annotations.keys():
            annotations[an] = eval(annotations[an])
        func.__annotations__ = annotations
        return func



def _call_in_global_env(server_instance,f,params):
    """处理执行结果"""
    res = f(*params)
    if callable(res):
        # print("服务器实例",server_instance)
        # print("返回了一个函数：",res)
        # env_vars = vars(import_module(f.__module__))
        # print("返回了一个函数：",env_vars[res.__name__])
        registed_funcnames = [name for name,value in server_instance.funcs.items() if value==res]
        if registed_funcnames:
            # print(f"{res.__name__}函数已经注册")
            return dict(
                result=f'self.{registed_funcnames[0]}',
                isfunc = True
            )
        elif isinstance(res,partial):
            registed_funcnames = [name for name,value in server_instance.funcs.items() if value==res.func]
            if registed_funcnames:
                return dict(
                result=f'partial(self.{registed_funcnames[0]},res.args)',
                isfunc = True
                )
            else:
                pass
        else:
            pass
    else:
        return dict(
            result=res,
        )



def _dispatch(self, method, params):
    """处理远程调用，执行并返回结果"""
    try:
        # call the matching registered function
        func = self.funcs[method]
    except KeyError:
        pass
    else:
        if func is not None:            
            return _call_in_global_env(self,func,params)
        raise Exception('method "%s" is not supported' % method)

    if self.instance is not None:
        if hasattr(self.instance, '_dispatch'):
            # call the `_dispatch` method on the instance
            return self.instance._dispatch(method, params)

        # call the instance's method directly
        try:
            func = resolve_dotted_attribute(
                self.instance,
                method,
                self.allow_dotted_names
            )
        except AttributeError:
            pass
        else:
            if func is not None:
                return _call_in_global_env(self,func,params)

    raise Exception('method "%s" is not supported' % method)



def register_function(self, function=None, name=None):
    """
    可以注册函数和实例
    Registers a function to respond to XML-RPC requests.
    The optional name argument can be used to set a Unicode name
    for the function.
    """
    # decorator factory
    if function is None:
        return partial(self.register_function, name=name)

    if name is None:
        name = function.__name__

    if name in KEEPWORD:
        raise ValueError(f"can't set {name},it's keep words!")

    self.funcs[name] = function
    self.rpc_funcs_info[name] = get_funcs_info(function,name)
    return function



def syx_get_rpc_funcs_info(self):
    """返回rpc服务器上注册得 所有可调用函数得信息"""
    return self.rpc_funcs_info



SimpleXMLRPCServer._dispatch = _dispatch
DocXMLRPCServer._dispatch = _dispatch

SimpleXMLRPCServer.register_function = register_function
DocXMLRPCServer.register_function = register_function

SimpleXMLRPCServer.rpc_funcs_info = {}
DocXMLRPCServer.rpc_funcs_info = {}

SimpleXMLRPCServer.syx_get_rpc_funcs_info = syx_get_rpc_funcs_info
DocXMLRPCServer.syx_get_rpc_funcs_info = syx_get_rpc_funcs_info




class LocalProxy:
    def __init__(self,
        sever_proxy,
        minimum_update_interval=2,
        is_multicall = False,
        _class=''
        ) -> None:
        self._class= _class+'.' if _class else ''
        self._sever_proxy = sever_proxy
        self._all_rpcfuncs = []

        self._minimum_update_interval = minimum_update_interval

        self._is_multicall = is_multicall
        self._calltasks = []
        self._results = []

        self._child={}


    def __notfound_func(self,methodName,*arg,**kwarg):
        res = getattr(self,methodName)(*arg,**kwarg)
        return res


    def __getattr__(self, name: str):
        """本地不存在该函数，首先进行一次更新同步"""
        curtimestamp = datetime.now().timestamp()
        if curtimestamp- Update_Localproxy.last_update >self._minimum_update_interval:      
            Update_Localproxy.update_rpcfunc()
            if hasattr(self,name):
                return partial(self.__notfound_func,name)
            else:
                raise AttributeError(f"'LocalProxy' object has no attribute '{name}'")
        else:
            raise AttributeError(f"'LocalProxy' object has no attribute '{name}'")



def create_multicall_proxy_instance(sever_proxy,_class='')->LocalProxy:
    muticall = LocalProxy(sever_proxy,is_multicall=True,_class=_class)

    def results(self,clear=True):
        if len(self._calltasks)>0:
            self._results = self._sever_proxy.sys.multicall(self._calltasks)
            self._calltasks = []
            res = []
            for a in self._results['result']:
                if type(a) == dict:
                    res.append(ResultError(res=a['faultString']))
                else:
                    res.append(a[0]['result'])
            self._results = res

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


    def init_localproxy(self) -> None:
        if self.__init:
            return
        self.__init = True
        self._multicall:LocalProxy = create_multicall_proxy_instance(self._sever_proxy)
        self.__rpcfunc:LocalProxy = LocalProxy(self._sever_proxy)
        Update_Localproxy.rpcfunc_localproxy_instances = self.__rpcfunc
        Update_Localproxy.multicall_localproxy_instances =self._multicall
        Update_Localproxy.update_rpcfunc()


    @property
    def all_rpcfuncs(self)->list:
        if not self.__init:
            raise RuntimeError('localproxy is not init!')
        Update_Localproxy.update_rpcfunc()
        return self.__rpcfunc._all_rpcfuncs

    @property
    def rpcfunc(self)->LocalProxy:
        if not self.__init:
            raise RuntimeError('localproxy is not init!')
        return self.__rpcfunc

    @property
    def multicall(self)->LocalProxy:
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

        self._server.funcs.update({
            'sys.get_rpc_funcs_info' : self._server.syx_get_rpc_funcs_info,
            'sys.multicall':self._server.system_multicall
            })

        # self._server.register_multicall_functions()


    def register_function(self,f=None,name=None):
        """将函数注册为 rpc函数"""
        # decorator factory
        if f is None:
            return partial(self.register_function, name=name)

        if not name:
            name = f.__name__

        if name in self._server.funcs:
            funcs = {}
            for k,v in self._server.funcs.items():
                if name == k or name+'.' in k:
                    continue
                funcs[k] = v
            self._server.funcs = funcs            
            msg = f'Registered name "{name}" already exists, and has been covered'
            warnings.warn(msg,UserWarning)
        self._server.register_function(f,name)
        return f


    def register_class(self,class_or_ins=None,name_=None,**options):
        """
        将注册类为远程rpc        

        ## 使用装饰器注册类，在内部自动实例化
        @register_class_or_ins('name',k1='df',k2=12)
        class Testclass:
            def __init__(self,k1,k2):
                pass
        """

        if class_or_ins is None:
            raise ValueError(f"{class_or_ins} is not an class_or_ins!")
                
        if type(class_or_ins) is str: 
            return partial(self.register_class,name_=class_or_ins,**options)
            
        if name_ is None:
            raise ValueError(f"name {name_} is not a string!")

        if inspect.isclass(class_or_ins):
            _instance = class_or_ins(**options)
        else:
            _instance = class_or_ins

        for i in dir(_instance):
            if i.startswith("_"):
                continue

            f = getattr(_instance,i)
            if not inspect.ismethod(f):
                continue
            method_name = f'{name_}.{i}'
            self.register_function(f,method_name)
        
        return class_or_ins


    def run(self):
        print(f"start rpc server on http://{self._host}:{self._prot}")
        self._server.serve_forever()


