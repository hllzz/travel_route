"""功能说明：账号登录、注册和首页视图（基础架构版本）。"""
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.service import clean_profile_form, get_user_favorites, update_profile, get_user_guides
from travel.models import Attraction, AttractionFavorite


def home_view(request: HttpRequest) -> HttpResponse:
    """功能说明：渲染登录后的系统首页。"""
    # 未登录用户跳转到登录页面，已登录用户展示首页。
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    # 查询首页轮播图景点，优先展示热度高且有图片的数据。
    carousel_attractions = (
        Attraction.objects.filter(image__isnull=False)
        .exclude(image='')
        .order_by('-heat_score', '-score', '-comment_count')[:4]
    )

    # 查询猜你喜欢景点，优先展示评分和热度较高的数据。
    recommend_attractions = (
        Attraction.objects.filter(image__isnull=False)
        .exclude(image='')
        .order_by('-score', '-heat_score', '-comment_count')[:8]
    )

    # 渲染当前登录用户的首页。
    return render(
        request,
        'accounts/home.html',
        {
            'carousel_attractions': carousel_attractions,
            'recommend_attractions': recommend_attractions,
        },
    )

def login_view(request: HttpRequest) -> HttpResponse:
    """功能说明：处理用户登录页面展示和登录提交。"""
    # 已登录用户直接进入首页。
    if request.user.is_authenticated:
        return redirect('accounts:home')

    # 准备模板上下文，保留安全的跳转地址。
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    safe_next_url = ''
    if url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):#原来的网址，白名单，是否https安全
        safe_next_url = next_url
    context = {'error': '', 'username': '', 'next': safe_next_url}

    # GET 请求直接展示登录页面。
    if request.method != 'POST':
        return render(request, 'accounts/login.html', context)

    # 读取账号密码并执行基础校验。
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    context['username'] = username
    if not username or not password:
        context['error'] = '请输入用户名和密码。'
        return render(request, 'accounts/login.html', context)

    # 使用 Django 认证后端校验用户身份。
    user = authenticate(request, username=username, password=password)
    if user is None:
        context['error'] = '用户名或密码错误。'
        return render(request, 'accounts/login.html', context)

    # 写入登录会话并跳转到目标页面。
    auth_login(request, user)
    if safe_next_url:
        return redirect(safe_next_url)
    return redirect('accounts:home')


def register_view(request: HttpRequest) -> HttpResponse:
    """功能说明：处理用户注册页面展示和注册提交。"""
    # 已登录用户直接进入首页。
    if request.user.is_authenticated:
        return redirect('accounts:home')

    # 准备模板上下文，用于回显用户已输入的数据。
    context = {'errors': [], 'username': ''}
    if request.method != 'POST':
        return render(request, 'accounts/register.html', context)

    # 从 POST 中读取注册数据。
    user_model = get_user_model()
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    password_confirm = request.POST.get('password_confirm', '')
    errors = []
    context.update({'username': username})

    # 校验用户名和密码的基础规则。
    if not username:
        errors.append('请输入用户名。')
    elif user_model.objects.filter(username=username).exists():
        errors.append('用户名已存在。')
    if not password:
        errors.append('请输入密码。')
    if password != password_confirm:
        errors.append('两次输入的密码不一致。')

    # 调用 Django 密码校验器，只校验密码长度不少于 6 位。
    if password and password == password_confirm:
        temporary_user = user_model(username=username)
        try:
            validate_password(password, temporary_user)
        except ValidationError as exc:
            errors.extend(exc.messages)

    # 存在错误时返回注册页面并展示错误信息。
    if errors:
        context['errors'] = errors
        return render(request, 'accounts/register.html', context)

    # 创建用户账号。
    user = user_model.objects.create_user(username=username, password=password)

    # 注册成功后自动登录并进入首页。
    auth_login(request, user)
    return redirect('accounts:home')


def logout_view(request: HttpRequest) -> HttpResponse:
    """功能说明：退出当前登录用户并返回登录页。"""
    # 清理当前用户登录会话。
    auth_logout(request)

    # 跳转回登录页面。
    return redirect('accounts:login')
@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    """功能说明：展示个人中心并处理基础资料更新。"""
    # 准备个人中心基础上下文。
    context = {
        'errors': [],
        'form_data': {'username': request.user.username, 'email': request.user.email},
    }
    if request.method != 'POST':
        return render(request, 'accounts/profile.html', context)

    # POST 请求清洗和校验表单数据。
    uploaded_avatar = request.FILES.get('avatar')
    cleaned_data, errors = clean_profile_form(request.user, request.POST, uploaded_avatar)
    if errors:
        context.update({'errors': errors, 'form_data': cleaned_data})
        return render(request, 'accounts/profile.html', context)

    # 更新用户资料。
    update_profile(request.user, cleaned_data)
    messages.success(request, '个人资料更新成功。')
    return redirect('accounts:profile')


@login_required
def my_favorites_view(request: HttpRequest) -> HttpResponse:
    """功能说明：展示当前用户收藏的旅游景点。"""
    # 查询收藏列表并分页展示。
    favorites = get_user_favorites(request.user)
    paginator = Paginator(favorites, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # 渲染我的收藏页面。
    return render(
        request,
        'accounts/my_favorites.html',
        {
            'page_obj': page_obj,
            'total_count': paginator.count,
        },
    )


@login_required
@require_POST
def remove_favorite_view(request: HttpRequest, favorite_id: int) -> HttpResponse:
    """功能说明：从我的收藏页面取消指定景点收藏。"""
    # 只允许删除当前用户自己的收藏记录。
    favorite = AttractionFavorite.objects.filter(id=favorite_id, user=request.user).first()
    if favorite:
        favorite.delete()
        messages.success(request, '已取消收藏。')
    else:
        messages.error(request, '收藏记录不存在。')

    # 操作完成后回到我的收藏页面。
    return redirect('accounts:my_favorites')
@login_required
def my_guides_view(request: HttpRequest) -> HttpResponse:
    """功能说明：展示当前用户发布的旅游攻略。"""
    # 查询发布列表并分页展示。
    favorites = get_user_guides(request.user)
    paginator = Paginator(favorites, 12)#分页器
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # 渲染我的发布页面。
    return render(
        request,
        'accounts/my_guides.html',
        {
            'page_obj': page_obj,
            'total_count': paginator.count,
        },
    )

