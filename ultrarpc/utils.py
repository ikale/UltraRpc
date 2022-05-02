import inspect
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



def get_funcs_info(f:callable,name=None):
    """获取函数信息"""
    name = f.__name__ if name is None else name
    _arr = name.split('.')
 
    class_ = _arr[0] if len(_arr)==2 else ''

    params= tuple(inspect.signature(f).parameters.keys())    
    default_values= tuple([i.default for i in tuple(inspect.signature(f).parameters.values()) if i.default is not inspect._empty])
    doc = inspect.getdoc(f)
    annotations = dict([(k,v.annotation) for k,v in  inspect.signature(f).parameters.items() if v.annotation is not inspect._empty])
    for an in annotations.keys():
        annotations[an] = annotations[an].__name__
    return dict(
        class_=class_,
        name = name,
        doc=doc,        
        params=params,
        default_values=default_values,
        annotations=annotations
    )