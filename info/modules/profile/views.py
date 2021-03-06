from flask import g, redirect, render_template, request, jsonify, current_app, session

from info.models import Category, News
from . import profile_blue
# 导入登录验证装饰器
from info.utils.commons import login_required
from info.utils.response_code import RET
from info import db, constants
# 导入七牛云
from info.utils.image_storage import storage


@profile_blue.route('/info')
@login_required
def user_info():
    """
    个人中心基本页面展示
    1、获取用户id
    2、如果用户未登录，重定向到项目首页
    3、如果用户登录，获取用户信息，返回给模板


    :return:
    """
    user = g.user
    # 如果用户未登录
    if not user:
        return redirect('/')

    data = {
        'user': user.to_dict()
    }
    # 返回数据给模板
    return render_template('news/user.html', data=data)


@profile_blue.route('/base_info', methods=['GET', 'POST'])
@login_required
def base_info():
    """
    基本信息展示和修改
    1、获取参数，nick_name,signature,gender
    2、检查参数的完整性
    3、检查性别必须是MAN/WOMAN
    4、保存用户信息
    5、提交数据

    :return:
    """
    user = g.user
    # 如果是get请求，展示用户信息，用户昵称、签名、性别
    if request.method == 'GET':
        data = {
            'user': user.to_dict()
        }
        # 返回数据给模板
        return render_template('news/user_base_info.html', data=data)
    # 获取参数
    nick_name = request.json.get('nick_name')
    signature = request.json.get('signature')
    gender = request.json.get('gender')
    # 检查参数的完整性
    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')
    # 检查性别参数
    if gender not in ['MAN', 'WOMAN']:
        return jsonify(errno=RET.PARAMERR, errmsg='参数格式错误')
    # 保存用户信息
    user.nick_name = nick_name
    user.signature = signature
    user.gender = gender
    # 提交数据
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')
    # 需要修改redis缓存中的nick_name
    session['nick_name'] = nick_name
    # 返回结果
    return jsonify(errno=RET.OK, errmsg='OK')


@profile_blue.route('/pic_info', methods=['GET', 'POST'])
@login_required
def save_avatar():
    """
    保存用户头像
        如果是get请求加载模板
    1、获取参数，
    avatar = request.files.get()
    avatar是文件对象，上传的是二进制文件。
    avatar.read()
    2、校验参数的存在
    3、读取图片数据，
    4、调用七牛云，上传图片
    5、保存七牛云返回的图片名称
        七牛外链域名 + 七牛云返回的图片名称
        七牛云返回的图片名称
    6、在mysql中存储图片的相对路径，即：七牛云返回的图片名称
    7、提交数据
    8、拼接图片的绝对路径，返回前端
    :return:
    """
    user = g.user

    if request.method == 'GET':
        data = {
            'user': user.to_dict()
        }
        return render_template('news/user_pic_info.html', data=data)

    # 获取参数
    avatar = request.files.get('avatar')

    if not avatar:
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 读取图片数据,转成bytes类型
    try:
        image_data = avatar.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数类型错误')

    # 调用七牛云，上传头像,保存七牛云返回的图片名称
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='上传头像异常')

    # 保存用户头像名称到mysql数据库
    user.avatar_url = image_name

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')

    # 拼接图片的绝对路径，返回前端
    avatar_url = constants.QINIU_DOMIN_PREFIX + image_name
    # 返回结果
    data = {
        'avatar_url': avatar_url
    }
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


@profile_blue.route("/news_release", methods=['GET', 'POST'])
@login_required
def news_release():
    """
    新闻发布
    1、如果是get请求，加载新闻分类数据，必须要移除'最新'，渲染模板
    :return:
    """
    user = g.user

    if request.method == 'GET':

        # 查询新闻分类数据
        try:
            category_list = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg='查询数据失败')

        # 判断查询结果
        if not category_list:
            return jsonify(errno=RET.NODATA, errmsg='无新闻数据')

        # 定义容器存储查询结果
        categoryies = []
        for category in category_list:
            categoryies.append(category.to_dict())

        # 移除最新分类
        categoryies.pop(0)

        data = {
            'categories': categoryies
        }
        return render_template('news/user_news_release.html', data=data)

    # 获取参数，title、category_id,digest,index_image,content
    title = request.form.get('title')
    category_id = request.form.get('category_id')
    digest = request.form.get('digest')
    index_image = request.files.get('index_image')
    content = request.form.get('content')

    print('内容是是身上测试一下', content)
    # 检查参数的完整性
    # if not all([title,category_id,digest,index_image,content]):
    #     return jsonify(errno=RET.PARAMERR,errmsg='参数缺失')
    # 检查新闻分类的数据类型
    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数类型错误')
    # 读取图片数据
    try:
        image_data = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数格式错误')

    # 调用七牛云，上传新闻图片
    try:
        image_name = storage(image_data)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='上传图片失败')

    # 构造新闻模型类对象，存储新闻数据
    news = News()
    news.category_id = category_id
    news.user_id = user.id
    news.source = '个人发布'
    news.title = title
    news.digest = digest
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + image_name
    news.content = content

    news.status = 1

    # 提交数据
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')

    # 返回结果
    return jsonify(errno=RET.OK, errmsg='OK')


# ----------------------个人这中心修改密码-------------------------------
@profile_blue.route('/pass_info', methods=['POST', 'GET'])
@login_required
def pass_info():
    """
    个人中心:修改密码
    1. 判断请求方法，如果get请求，默认选惹我你模板页面
    2. 获取参数。old_password,new_password
    3.减产参数的完整性，
    4. 获取用户的信息，用来对旧密码进行教研是否正确
    5. 更巡用户的密码
    6. 返回结果i
    :return:
    """

    if request.method == 'GET':
        return render_template('news/user_pass_info.html')

    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')

    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数确实')

    user = g.user

    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg='用户未登录')

    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR, errmsg='就密码错误')

    user.password = new_password

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')

    # 返回结果
    return jsonify(errno=RET.OK, errmsg='ok')


# -----------------------------用户收藏喀开始---------------------------
@profile_blue.route('/news_list')
@login_required
def user_news_list():
    """
    新闻列表
    1. 获取参数，页数，默认1
    2. 判断参数，整形
    3. 获取用户用户信息，定义容器存储查询结果，总页数默认1，当前页默认1
    4. 查询数据库，查询新闻数据进行分页‘
    5. 获取总页数，当前页，新闻数据u
    6. 定义字典列表，遍历查询结果，添加到列表中
    7. 返回模板new/user_news_list.html   'total_page. current_page, news_dict_list'
    :return:
    """

    page = request.args.get('p', 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    user = g.user
    news_list = []
    current_page = 1
    total_page = 1

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages

    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='查询数据错误')

    news_dict_list = []

    for news in news_list:
        news_dict_list.append(news.to_review_dict())

    # 准备数据
    data = {
        'news_list': news_dict_list,
        'total_page': total_page,
        'current_page': current_page
    }

    return render_template('news/user_news_list.html', data=data)


# ------------------------------用户收藏-----------------------------------
@profile_blue.route('/collection')
@login_required
def user_collection():
    # 获取页数
    p = request.args.get('p', 1)

    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user
    collections = []
    current_page = 1
    total_page = 1

    try:
        # 分页数据查询
        paginate = user.collection_news.paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取分页数据
        collections = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg='保存数据失败')

    # 收藏列表
    collection_dict_list = []

    for news in collections:
        collection_dict_list.append(news.to_basic_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "collections": collection_dict_list
    }

    return render_template('news/user_collection.html', data=data)
