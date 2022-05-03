
from setuptools import Extension, find_packages, setup,find_packages
# from distutils.core import  setup

setup(
    name="ultrarpc",  
    version="0.5", 
    author="ikale", 
    author_email="ikale@qq.com", 
    # 最重要的就是py_modules和packages
    # py_modules=["major.test1","major.test2"],  # py_modules : 打包的.py文件
    # packages=["major.major1"],  # packages: 打包的python文件夹
    packages=find_packages(), # 需要处理的包目录（包含__init__.py的文件夹）
    keywords=("RPC", "ultrarpc"),  # 程序的关键字列表
    description="ultrarpc for python",                 # 简单描述
    long_description="Acme concise RPC, just peace of mind of write your python code", # 详细描述
    license="Apache-2.0",  # 授权信息
    url="https://utran.cn",  # 官网地址       
    platforms="any",  # 适用的软件平台列表
    # install_requires=[],  # 需要安装的依赖包
    # 项目里会有一些非py文件,比如html和js等,这时候就要靠include_package_data和package_data来指定了。
    # scripts=[],  # 安装时需要执行的脚本列表
    # entry_points={     # 动态发现服务和插件
    #     'console_scripts': [
    #         'jsuniv_sllab = jsuniv_sllab.help:main'
    #     ]
    # }

)