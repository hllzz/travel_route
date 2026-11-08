from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from guides.services import search_guides, get_city_options, get_guide_detail, clean_guide_form, get_attractions_by_ids, \
    create_guide, search_attractions_for_guide


@login_required
def guide_list_view(request: HttpRequest) -> HttpResponse:
    """功能说明：展示旅游攻略列表并支持搜索筛选。"""
    # 读取筛选参数。
    keyword = request.GET.get('keyword', '').strip()
    city = request.GET.get('city', '').strip()
    page_number = request.GET.get('page', 1)

    # 查询攻略列表并分页。
    guides = search_guides(keyword=keyword, city=city)
    paginator = Paginator(guides, 9)
    page_obj = paginator.get_page(page_number)

    # 渲染攻略列表页面。
    return render(
        request,
        'guides/guide_list.html',
        {
            'page_obj': page_obj,
            'keyword': keyword,
            'city': city,
            'city_options': get_city_options(),
            'total_count': paginator.count,
        },
    )

@login_required
def guide_detail_view(request: HttpRequest, guide_id: int) -> HttpResponse:
    """功能说明：展示旅游攻略详情。"""
    # 查询攻略详情并增加浏览量。
    guide = get_guide_detail(guide_id)
    return render(
        request,
        'guides/guide_detail.html',
        {
            'guide': guide,
            'guide_images': guide.images.all(),
            'guide_attractions': guide.guide_attractions.all(),
        },
    )

# Create your views here.
# 旅游页面发布攻略并处理请求
@login_required
def guide_create_view(request: HttpRequest) -> HttpResponse:
  context={'form_data':{
      'title': '','city':'','summary':'','content':'','attracion_name':''},
      'selected_attraction_ids': [],
      'selected_attractions': [],
      'errors': [],
  }
  if request.method != 'POST':
      return render(request, 'guides/guide_create.html', context)
  uploaded_images = request.FILES.getlist('images')
  cleaned_data, errors = clean_guide_form(request.POST,uploaded_images)
  if errors:
      context.update(
          {
              'form_data': cleaned_data,
              'selected_attraction_ids': cleaned_data.get('attraction_ids', []),
              'selected_attractions': get_attractions_by_ids(cleaned_data.get('attraction_ids', [])),
              'errors': errors,
          }
      )
      return render(request, 'guides/guide_create.html', context)
  guide=create_guide(request.user,cleaned_data,uploaded_images)
  return redirect( 'guides:guide_detail', guide_id=guide.id)
@login_required
def attraction_search_view(request: HttpRequest) -> JsonResponse:
    #为攻略发布页提供关联景点结果搜索结果
   keyword = request.GET.get('keyword', '').strip()
   attractions=search_attractions_for_guide(keyword)
   results=[{
        'id': attraction.id,
        'name': attraction.name,
        'city_name': attraction.city_name,
        'area': attraction.area,
        'score': attraction.score,
        'image': attraction.image or '',
    } for attraction in attractions
   ]
   return JsonResponse({'results': results})