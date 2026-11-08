from django.conf import settings
from django.db import models

from travel.models import Attraction


class TravelGuide(models.Model):
    """功能说明：保存用户发布的旅游攻略。"""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='作者',
        on_delete=models.CASCADE,
        related_name='travel_guides',
        db_comment='攻略作者',
    )
    title = models.CharField('攻略标题', max_length=120, db_comment='攻略标题')
    city = models.CharField('目的地城市', max_length=50, db_comment='目的地城市')
    summary = models.CharField('攻略摘要', max_length=240, db_comment='攻略摘要')
    content = models.TextField('攻略正文', db_comment='攻略正文')
    view_count = models.PositiveIntegerField('浏览量', default=0, db_comment='浏览量')
    created_at = models.DateTimeField('发布时间', auto_now_add=True, db_comment='发布时间')
    updated_at = models.DateTimeField('更新时间', auto_now=True, db_comment='更新时间')

    class Meta:
        db_table = 'travel_guide'
        db_table_comment = '旅游攻略'
        verbose_name = '旅游攻略'
        verbose_name_plural = '旅游攻略'
        indexes = [
            models.Index(fields=['city', '-created_at'], name='idx_guide_city_time'),
            models.Index(fields=['author', '-created_at'], name='idx_guide_author_time'),
            models.Index(fields=['-created_at'], name='idx_guide_created_time'),
        ]

    def __str__(self) -> str:
        """功能说明：返回攻略标题作为后台展示文本。"""
        return self.title


class TravelGuideImage(models.Model):
    """功能说明：保存旅游攻略上传的多张图片。"""

    guide = models.ForeignKey(
        TravelGuide,
        verbose_name='所属攻略',
        on_delete=models.CASCADE,
        related_name='images',
        db_comment='所属攻略',
    )
    image = models.ImageField(
        '攻略图片',
        upload_to='guide_images/%Y/%m/',
        max_length=255,
        db_comment='攻略图片',
    )
    sort_order = models.PositiveSmallIntegerField('排序序号', default=0, db_comment='排序序号')
    created_at = models.DateTimeField('上传时间', auto_now_add=True, db_comment='上传时间')

    class Meta:
        db_table = 'travel_guide_image'
        db_table_comment = '旅游攻略图片'
        verbose_name = '旅游攻略图片'
        verbose_name_plural = '旅游攻略图片'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['guide', 'sort_order'], name='idx_guide_image_order'),
        ]

    def __str__(self) -> str:
        """功能说明：返回攻略图片的后台展示文本。"""
        return f'{self.guide.title} 图片 {self.sort_order}'


class TravelGuideAttraction(models.Model):
    """功能说明：保存旅游攻略关联的景点。"""

    guide = models.ForeignKey(
        TravelGuide,
        verbose_name='所属攻略',
        on_delete=models.CASCADE,
        related_name='guide_attractions',
        db_comment='所属攻略',
    )
    attraction = models.ForeignKey(
        Attraction,
        verbose_name='关联景点',
        on_delete=models.CASCADE,
        related_name='guide_attractions',
        db_comment='关联景点',
    )
    created_at = models.DateTimeField('关联时间', auto_now_add=True, db_comment='关联时间')

    class Meta:
        db_table = 'travel_guide_attraction'
        db_table_comment = '旅游攻略关联景点'
        verbose_name = '旅游攻略关联景点'
        verbose_name_plural = '旅游攻略关联景点'
        constraints = [
            models.UniqueConstraint(fields=['guide', 'attraction'], name='uniq_guide_attraction'),
        ]
        indexes = [
            models.Index(fields=['guide'], name='idx_guide_attr_guide'),
            models.Index(fields=['attraction'], name='idx_guide_attr_spot'),
        ]

    def __str__(self) -> str:
        """功能说明：返回攻略和景点的关联展示文本。"""
        return f'{self.guide.title} 关联 {self.attraction.name}'
