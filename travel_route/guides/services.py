import re
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db.models.query import QuerySet, Prefetch
from django.db.models import Q,F
from django.db import transaction
from django.http.request import QueryDict
from django.shortcuts import get_object_or_404

from guides.models import TravelGuide, TravelGuideAttraction, TravelGuideImage
from travel.models import Attraction

MAX_GUIDE_IMAGE_COUNT=9
MAX_GUIDE_IMAGE_SIZE=5 * 1024 * 1024
ALLOWED_GUIDE_IMAGE_TYPES=['image/jpeg', 'image/png','image/webp','image/gif']
ATTRACTION_SEARCH_LIMIT=12
#功能说明：攻略应用路由配置（基础架构版本）。
def build_guide_queryset():
  return TravelGuide.objects.prefetch_related('images',
       Prefetch('guide_attractions',
                queryset=TravelGuideAttraction.objects.select_related('attraction').order_by('id')
           ))
def search_guides(keyword:str='', city:str='')->QuerySet[TravelGuide]:#根据关键词和城市查询攻略列表。
    guides = build_guide_queryset().order_by('-created_at','-id')
    if keyword:
        guides = guides.filter(Q(title__icontains=keyword)
        | Q(city__icontains=keyword)
        | Q(summary__icontains=keyword)
        | Q(content__icontains=keyword)
        | Q(guide_attractions__attraction__name__icontains=keyword) )
    if city:
        guides = guides.filter(Q(city=city))
    return guides.distinct()
def get_city_options() -> QuerySet[str]:#查询已有攻略的筛选项
    return TravelGuide.objects.values_list('city',flat=True).distinct().order_by('city')
def get_guide_detail(guide_id:int)->TravelGuide:
    #查询旅游攻略并添加浏览量
    guide=get_object_or_404(build_guide_queryset(), pk=guide_id)
    TravelGuide.objects.filter(pk=guide.pk).update(view_count=F('view_count') + 1)
    guide.refresh_from_db(fields=['view_count'])
    return guide
def parse_attractions_ids(raw_ids:list[str])->list[int]:
    #解析页面提交的景点id列表
    attraction_ids=[]
    for raw_id in raw_ids:
        if not raw_id.isdigit():
            continue
        if not raw_id:
            continue
        attraction_id=int(raw_id)
        if attraction_id not in attraction_ids:
            attraction_ids.append(attraction_id)
    return attraction_ids


def split_attraction_names(raw_names:str)->list[str]:
    #按中文和英文拆分景点名称
    names=[]
    for item in re.split(r'[，,、：;\n\r]+',raw_names):
        name=item.strip()
        if name and name not in names:
            names.append(name)
    return names
def resolve_related_attraction_ids(selected_ids: list[int], raw_names: str, city: str) -> tuple[list[int], list[str]]:
    """功能说明：根据多选 ID 和输入名称解析攻略关联景点。"""
    # 先校验多选景点 ID 是否真实存在。
    resolved_ids = []
    if selected_ids:
        selected_attractions = Attraction.objects.filter(id__in=selected_ids)
        resolved_ids.extend(selected_attractions.values_list('id', flat=True))

    # 再按用户输入的景点名称匹配景点库。
    missing_names = []
    name_list = split_attraction_names(raw_names)
    if name_list:
        name_queryset = Attraction.objects.filter(name__in=name_list)
        if city:
            city_queryset = name_queryset.filter(city_name=city)
            if city_queryset.exists():
                name_queryset = city_queryset
        matched_names = set(name_queryset.values_list('name', flat=True))
        resolved_ids.extend(name_queryset.values_list('id', flat=True))
        missing_names = [name for name in name_list if name not in matched_names]

    # 去重并保持提交顺序。
    unique_ids = []
    for attraction_id in resolved_ids:
        if attraction_id not in unique_ids:
            unique_ids.append(attraction_id)
    return unique_ids, missing_names


def get_attractions_by_ids(attraction_ids: list[int]) -> list[Attraction]:
    """功能说明：根据景点 ID 列表查询景点并保持原提交顺序。"""
    # 空列表直接返回，避免无意义数据库查询。
    if not attraction_ids:
        return []

    # 使用字典保存查询结果，再按原 ID 顺序返回。
    attraction_map = {
        attraction.id: attraction
        for attraction in Attraction.objects.filter(id__in=attraction_ids)
    }
    return [attraction_map[attraction_id] for attraction_id in attraction_ids if attraction_id in attraction_map]


def clean_guide_form(post_data:QueryDict,uploaded_images:list[UploadedFile],)->tuple[dict[str,Any],list[str]]:
    #清洗并校验旅游攻略发布表单
    raw_attractions_ids=post_data.getlist('attraction_ids')
    cleaned_data={
        'title': str(post_data.get('title')).strip(),
        'city': str(post_data.get('city')).strip(),
        'summary': str(post_data.get('summary')).strip(),
        'content': str(post_data.get('content')).strip()    ,
        'attraction_names':str(post_data.get('attraction_names')).strip(),
        'attraction_ids': parse_attractions_ids(raw_attractions_ids),
    }
    errors = []
    if not cleaned_data['title']:
        errors.append('请输入攻略标题。')
    if not cleaned_data['city']:
        errors.append('请输入目的地城市。')
    if not cleaned_data['summary']:
        errors.append('请输入攻略摘要。')
    if not cleaned_data['content']:
        errors.append('请输入攻略正文。')

    if len(cleaned_data['title']) > 120:
        errors.append('攻略标题不能超过120个字符。')
    if len(cleaned_data['city']) > 50:
        errors.append('目的地城市不能超过50个字符。')
    if len(cleaned_data['summary']) > 240:
        errors.append('攻略摘要不能超过240个字符。')
    if len(cleaned_data['content']) > 1000:
        errors.append('攻略正文不能超过1000个字符。')
    # 校验上传图片数量和文件类型
    if not uploaded_images:
        errors.append('请上传至少一张攻略图片')
    if len(uploaded_images) > MAX_GUIDE_IMAGE_COUNT:
        errors.append(f'攻略图片最多上传 {MAX_GUIDE_IMAGE_COUNT} 张。')
    for uploaded_image in uploaded_images:
        if uploaded_image.content_type not in ALLOWED_GUIDE_IMAGE_TYPES:
            errors.append(f'{uploaded_image.name} 不是支持的图片格式。')
        if uploaded_image.size > MAX_GUIDE_IMAGE_SIZE:
            errors.append(f'{uploaded_image.name} 不能超过 5MB。')
    # 校验并解析关联景点
    attraction_ids, missing_names = resolve_related_attraction_ids(
        cleaned_data['attraction_ids'],
        cleaned_data['attraction_names'],
        cleaned_data['city'],
    )
    cleaned_data['attraction_ids'] = attraction_ids
    if missing_names:
        errors.append(f'未找到{"、".join(missing_names)}.')
    return cleaned_data, errors


def create_guide(author: Any, cleaned_data: dict[str, Any], uploaded_images: list[UploadedFile], ) -> TravelGuide:
    """
    功能说明：创建一篇用户旅游攻略
    """
    attraction_ids = cleaned_data.pop('attraction_ids', [])
    cleaned_data.pop('attraction_names', None)
    with transaction.atomic():#一起成功输出，否者都补输出
        guide = TravelGuide.objects.create(author=author, **cleaned_data)

        for index, uploaded_image in enumerate(uploaded_images, start=1):
            TravelGuideImage.objects.create(
                guide=guide,
                image=uploaded_image,
                sort_order=index
            )

        if attraction_ids:
            TravelGuideAttraction.objects.bulk_create(
                [
                    TravelGuideAttraction(guide=guide, attraction_id=attraction_id)
                    for attraction_id in attraction_ids
                ],
                ignore_conflicts=True,
            )

    return guide


def search_attractions_for_guide(keyword: str) -> QuerySet[Attraction]:
    """
    功能说明：根据关键词，搜索可关联景点
    """
    keyword = keyword.strip()
    if not keyword:
        return Attraction.objects.none()
    return Attraction.objects.filter(
        Q(name__icontains=keyword)#忽略大小写等于
        | Q(city_name__icontains=keyword)
        | Q(area__icontains=keyword)
        | Q(tags__icontains=keyword)
    ).order_by('city_name', '-score', 'name')[:ATTRACTION_SEARCH_LIMIT]