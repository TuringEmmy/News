# author        TuringEmmy 
# createtime    18-10-8  下午6:27
# coding=utf-8
# doc           PyCharm

import logging
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

from config import config_dict

from redis import StrictRedis
from config import Config

from flask_wtf import CSRFProtect, csrf

# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG)  # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)

# 先实例化sqlqlchemy程序实例
db = SQLAlchemy()
# 实例化redis对象,用来存储业务相关的
# decode_responses是为了获取参数不是二进制，相关的只是可以查阅redisde 使用能手册
rb = StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


def create_app(config__name):
    app = Flask(__name__)
    # 加载配置文件
    app.config.from_object(config_dict[config__name])
    db.init_app(app)
    Session(app)

    # 项目开启csrf保护
    CSRFProtect(app)
    # 生成csrf_token
    # 因为每次都要使用，所以使用请求钩子,在每次请求后，往客户端的cookie中设置csrt_token
    @app.after_request
    def after_request(response):
        # response = make_response()
        csrf_token =csrf.generate_csrf()
        response.set_cookie('csrf_token',csrf_token)
        return response

   # 添加过滤器给模板，必须给程序实例
    from app.static.util.comments import index_filter
    app.add_template_filter(index_filter,'index_filter')


    # 导入蓝图对象
    from app.news import news
    app.register_blueprint(news)
    from app.passport import passport
    app.register_blueprint(passport)
    from app.profile import profile
    app.register_blueprint(profile)
    return app
