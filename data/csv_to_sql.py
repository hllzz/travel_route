"""功能说明：将清洗后的景点数据 clean.csv 导入 Attraction 数据表。"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_route.settings')
from pathlib import Path
import pandas as pd
import django
django.setup()
from travel.models import Attraction
df = pd.read_csv('clean.csv', encoding='utf-8-sig')
attractions = []
for _, row in df.iterrows():
    attractions.append(
        Attraction(
            poi_id=int(float(row['景点ID'])),
            area=row.get('所在区域') if pd.notna(row.get('所在区域')) else None,
            name=row['景点名称'],
            comment_count=float(row['评论数量']) if pd.notna(row['评论数量']) else None,
            score=float(row['评分']) if pd.notna(row['评分']) else 0,
            is_advertisement=str(row['是否广告']).lower() == 'true',
            is_recommend=str(row['是否推荐']).lower() == 'true',
            city_name=row['城市名称'],
            image=row.get('图片链接') if pd.notna(row.get('图片链接')) else None,
            distance=row.get('距离市中心距离') if pd.notna(row.get('距离市中心距离')) else None,
            tags=row.get('标签列表') if pd.notna(row.get('标签列表')) else None,
            detail_url=row['详情页链接'],
            market_price=float(row['市场票价']) if pd.notna(row['市场票价']) else None,
            preferential_price=float(row['优惠价格']) if pd.notna(row['优惠价格']) else None,
            preferential_desc=row.get('优惠描述') if pd.notna(row.get('优惠描述')) else None,
            actual_price=str(row.get('实际票价', '')) if pd.notna(row.get('实际票价')) else '',
            price_type=int(float(row['价格类型'])) if pd.notna(row['价格类型']) else None,
            price_type_desc=row.get('价格类型描述') if pd.notna(row.get('价格类型描述')) else None,
            is_free=str(row['是否免费']).lower() == 'true',
            longitude=float(row['经度']) if pd.notna(row['经度']) else None,
            latitude=float(row['维度']) if pd.notna(row['维度']) else None,
            heat_score=float(row['热度评分']) if pd.notna(row['热度评分']) else None,
        )
    )
Attraction.objects.all().delete()
Attraction.objects.bulk_create(attractions, batch_size=1000)
print(f'共读取 {len(df)} 条数据，提交 {len(attractions)} 条景点记录导入完成。')
