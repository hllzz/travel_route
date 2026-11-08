from django.db import models
from django.conf import settings


class Attraction(models.Model):
    """功能说明：保存携程景点清洗数据。"""

    poi_id = models.BigIntegerField('唯一标识', unique=True, db_comment='景点唯一标识')
    area = models.CharField('所在区域', max_length=100, blank=True, null=True, db_comment='所在区域')
    name = models.CharField('景点名称', max_length=120, db_comment='景点名称')
    comment_count = models.FloatField('评论数量', blank=True, null=True, db_comment='评论数量')
    score = models.FloatField('评分', default=0, db_comment='评分')
    is_advertisement = models.BooleanField(
        '是否为广告内容',
        default=False,
        db_comment='是否为广告内容',
    )
    is_recommend = models.BooleanField('是否被推荐', default=False, db_comment='是否被推荐')
    city_name = models.CharField('城市名称', max_length=50, db_comment='城市名称')
    image = models.URLField('图片', max_length=500, blank=True, null=True, db_comment='图片')
    distance = models.CharField(
        '与市中心的距离',
        max_length=50,
        blank=True,
        null=True,
        db_comment='与市中心的距离',
    )
    tags = models.CharField('标签', max_length=120, blank=True, null=True, db_comment='标签')
    detail_url = models.URLField('详情页链接', max_length=500, db_comment='详情页链接')
    market_price = models.FloatField('市场票价', blank=True, null=True, db_comment='市场票价')
    preferential_price = models.FloatField(
        '优惠价格',
        blank=True,
        null=True,
        db_comment='优惠价格',
    )
    preferential_desc = models.CharField(
        '优惠描述',
        max_length=50,
        blank=True,
        null=True,
        db_comment='优惠描述',
    )
    actual_price = models.CharField('实际票价', max_length=50, db_comment='实际票价')
    price_type = models.IntegerField('价格类型', blank=True, null=True, db_comment='价格类型')
    price_type_desc = models.CharField(
        '价格类型描述',
        max_length=50,
        blank=True,
        null=True,
        db_comment='价格类型描述',
    )
    is_free = models.BooleanField('是否免费', default=False, db_comment='是否免费')
    longitude = models.FloatField('经度', db_comment='经度')
    latitude = models.FloatField('纬度', db_comment='纬度')
    heat_score = models.FloatField('热度评分', blank=True, null=True, db_comment='热度评分')

    class Meta:
        db_table = 'attraction'
        db_table_comment = '旅游景点信息'
        verbose_name = '旅游景点信息'
        verbose_name_plural = '旅游景点信息'
        indexes = [
            models.Index(fields=['city_name'], name='idx_attraction_city'),
            models.Index(fields=['name'], name='idx_attraction_name'),
            models.Index(fields=['score'], name='idx_attraction_score'),
        ]

    def __str__(self) -> str:
        """功能说明：返回景点名称作为后台展示文本。"""
        return self.name

    @property
    def tags_display(self) -> str:
        """功能说明：清洗标签文本，去掉爬虫入库残留的引号并用顿号拼接。"""
        # 标签为空时直接返回空字符串。
        if not self.tags:
            return ''

        # 按逗号拆分后去除每段两端空白和残留引号，再用顿号拼接。
        parts = [part.strip().strip("'\"") for part in self.tags.split(',')]
        return '、'.join(part for part in parts if part)

    @property
    def tags_list(self) -> list[str]:
        """功能说明：返回清洗后的标签列表，供详情页渲染标签胶囊。"""
        # 标签为空时返回空列表。
        if not self.tags:
            return []

        # 按逗号拆分后去除残留引号和空白，过滤空值。
        parts = [part.strip().strip("'\"").strip() for part in self.tags.split(',')]
        return [part for part in parts if part]

class AttractionFavorite(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户', on_delete=models.CASCADE,related_name='attraction_favorites'
                           ,db_column='收藏用户')
    attraction = models.ForeignKey(Attraction, verbose_name='景点', on_delete=models.CASCADE,
                             related_name='favorites', db_column='收藏景点')
    created_at=models.DateTimeField('收藏时间',auto_now_add=True,db_comment='收藏时间')
    class Meta:
        db_table = 'attraction_favorite'
        db_table_comment='景点收藏信息'
        constraints=[
            models.UniqueConstraint(fields=['user','attraction'], name='unique_attraction_favorite'),  # 唯一约束
        ]
        indexes = [
            models.Index(fields=['user'], name='idx_favorite_user'),
            models.Index(fields=['attraction'], name='idx_favorite_attraction')
        ]
    def __str__(self) -> str:
        return f'{self.user.username}收藏{self.attraction.name}'
class AttractionComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户', on_delete=models.CASCADE,
                             related_name='attraction_comments', db_column='评论用户')
    attraction = models.ForeignKey(Attraction, verbose_name='景点', on_delete=models.CASCADE,
                                   related_name='comments', db_column='评论景点')
    content = models.TextField('评论内容', max_length=500, db_comment='评论内容')
    created_at = models.DateTimeField('评论时间', auto_now_add=True, db_comment='评论时间')
    class Meta:
        db_table = 'attraction_comment'
        db_table_comment='景点评论信息'
        indexes = [
            models.Index(fields=['user'], name='idx_comment_user'),
            models.Index(fields=['attraction','-created_at'], name='idx_comment_attraction_time')
        ]
    def __str__(self) -> str:
        return f'{self.user.username}评论{self.attraction.name}'
