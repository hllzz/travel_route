from typing import List
from django.views.decorators.http import require_POST
from travel.models import AttractionFavorite, AttractionComment
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.http import HttpRequest
from travel.models import Attraction
def build_pagination_items(current_page: int, total_pages:int,window_size:int=2) -> List[int]:
    if total_pages <= 1:
        return [1]
    start_page=max(1,current_page-window_size)
    end_page=min(total_pages,current_page+window_size)
    return list(range(start_page,end_page+1))
@login_required
def attraction_list_view(request: HttpRequest) -> HttpResponse:
    """功能说明：展示旅游景点列表并支持关键词、城市和免费条件筛选。"""
    # 读取查询参数并清理空白字符。
    keyword = request.GET.get('keyword', '').strip()
    city = request.GET.get('city', '').strip()
    is_free = request.GET.get('is_free', '').strip()
    page_number = request.GET.get('page', 1)

    # 构建景点查询集，按热度、评分、评论数量综合排序。
    attractions = Attraction.objects.all()
    if keyword:
        attractions = attractions.filter(
            Q(name__icontains=keyword) | Q(tags__icontains=keyword) | Q(area__icontains=keyword)
        )
    if city:
        attractions = attractions.filter(city_name=city)
    if is_free in {'0', '1'}:
        attractions = attractions.filter(is_free=(is_free == '1'))
    attractions = attractions.order_by('-heat_score', '-score', '-comment_count', 'id')

    # 准备城市筛选项和分页数据。
    city_options = Attraction.objects.values_list('city_name', flat=True).distinct().order_by('city_name')
    paginator = Paginator(attractions, 12)
    page_obj = paginator.get_page(page_number)
    pagination_items = build_pagination_items(page_obj.number, paginator.num_pages)

    # 构建分页链接前缀，保证翻页时保留当前筛选条件。
    page_query = request.GET.copy()
    page_query.pop('page', None)
    encoded_page_query = page_query.urlencode()
    page_query_prefix = f'?{encoded_page_query}&' if encoded_page_query else '?'

    # 渲染旅游景点列表页面。
    return render(
        request,
        'accounts/attraction_list.html',
        {
            'page_obj': page_obj,
            'paginator': paginator,
            'keyword': keyword,
            'city': city,
            'is_free': is_free,
            'city_options': city_options,
            'total_count': paginator.count,
            'pagination_items': pagination_items,
            'page_query_prefix': page_query_prefix,
        },
    )
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages


@login_required
def attraction_detail_view(request: HttpRequest, poi_id: int) -> HttpResponse:
    """功能说明：展示站内旅游景点详情页。"""
    # 根据携程景点唯一标识查询站内景点数据。
    attraction = get_object_or_404(Attraction, poi_id=poi_id)

    # 查询当前用户收藏状态、收藏总数和评论列表。
    is_favorited = AttractionFavorite.objects.filter(user=request.user, attraction=attraction).exists()
    favorite_count = AttractionFavorite.objects.filter(attraction=attraction).count()
    comments = (
        AttractionComment.objects.select_related('user')
        .filter(attraction=attraction)
        .order_by('-created_at')
    )

    # 渲染景点详情页面。
    return render(
        request,
        'accounts/attraction_detail.html',
        {
            'attraction': attraction,
            'is_favorited': is_favorited,
            'favorite_count': favorite_count,
            'comments': comments,
        },
    )

@login_required
@require_POST
def toggle_favorite_view(request: HttpRequest, poi_id: int) -> HttpResponse:
    """功能说明：切换当前用户对指定景点的收藏状态。"""
    # 根据携程景点唯一标识查询站内景点数据。
    attraction = get_object_or_404(Attraction, poi_id=poi_id)
    favorite = AttractionFavorite.objects.filter(user=request.user, attraction=attraction)

    # 仅接受 POST 请求，已收藏则取消，未收藏则添加。
    if favorite:
        favorite.delete()
        messages.success(request, '已取消收藏')
    else:
        AttractionFavorite.objects.create(user=request.user, attraction=attraction)
        messages.success(request, '已加入收藏')
    return redirect('travel:attraction_detail', poi_id=attraction.poi_id)
# Create your views here.
@login_required
@require_POST
def add_comment_view(request: HttpRequest, poi_id: int) -> HttpResponse:
    """功能说明：添加景点评论。"""
    attraction = get_object_or_404(Attraction, poi_id=poi_id)
    content = request.POST.get('content', '').strip()
    if not content:
        messages.error(request,'请输入评论内容')
        return redirect('travel:attraction_detail', poi_id=attraction.poi_id)
    if len(content) >500:
        messages.error(request,'评论内容不能超过500个字符')
        return redirect('travel:attraction_detail', poi_id=attraction.poi_id)
    AttractionComment.objects.create(user=request.user, attraction=attraction, content=content)
    messages.success(request,'评论发布成功')
    return redirect('travel:attraction_detail', poi_id=attraction.poi_id)