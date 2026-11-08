from django.conf import settings
from django.db import models

from travel.models import Attraction


class RoutePlan(models.Model):
    """功能说明：保存用户提交的 AI 路线规划结果。"""

    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_RUNNING, '规划中'),
        (STATUS_SUCCESS, '规划成功'),
        (STATUS_FAILED, '规划失败'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='用户',
        on_delete=models.CASCADE,
        related_name='route_plans',
        db_comment='提交规划的用户',
    )
    city = models.CharField('目的地城市', max_length=50, db_comment='目的地城市')
    budget = models.CharField('预算', max_length=80, db_comment='用户输入的旅行预算')
    travel_time = models.CharField('出行时间', max_length=80, db_comment='用户输入的出行时间')
    preferences = models.CharField('旅行偏好', max_length=300, db_comment='用户输入的旅行偏好')
    intent_data = models.JSONField('意图数据', default=dict, blank=True, db_comment='AI 识别出的结构化意图')
    process_steps = models.JSONField('规划过程', default=list, blank=True, db_comment='LangGraph 规划过程步骤')
    final_plan = models.TextField('路线说明', blank=True, db_comment='AI 生成的最终路线说明')
    status = models.CharField(
        '规划状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
        db_comment='规划任务状态',
    )
    error_message = models.CharField('错误信息', max_length=300, blank=True, db_comment='规划失败原因')
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_comment='创建时间')

    class Meta:
        db_table = 'route_plan'
        db_table_comment = 'AI 路线规划结果'
        verbose_name = 'AI 路线规划结果'
        verbose_name_plural = 'AI 路线规划结果'
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_route_plan_user_time'),
            models.Index(fields=['city'], name='idx_route_plan_city'),
        ]

    def __str__(self) -> str:
        """功能说明：返回路线规划记录的展示文本。"""
        return f'{self.user.username} 的 {self.city} 路线规划'


class RoutePlanStop(models.Model):
    """功能说明：保存 AI 路线规划中的单个景点站点。"""

    plan = models.ForeignKey(
        RoutePlan,
        verbose_name='路线规划',
        on_delete=models.CASCADE,
        related_name='stops',
        db_comment='所属路线规划',
    )
    attraction = models.ForeignKey(
        Attraction,
        verbose_name='景点',
        on_delete=models.SET_NULL,
        related_name='route_plan_stops',
        null=True,
        blank=True,
        db_comment='关联景点',
    )
    day_index = models.PositiveSmallIntegerField('天数序号', db_comment='第几天')
    sequence = models.PositiveSmallIntegerField('当日序号', db_comment='当天第几个')
    name = models.CharField('景点名称', max_length=120, db_comment='景点名称')
    city_name = models.CharField('城市名称', max_length=50, db_comment='城市名称')
    longitude = models.FloatField('经度', db_comment='经度')
    latitude = models.FloatField('纬度', db_comment='纬度')
    intro = models.TextField('站点介绍', blank=True, db_comment='站点介绍')
    created_at = models.DateTimeField('创建时间', auto_now_add=True, db_comment='创建时间')

    class Meta:
        db_table = 'route_plan_stop'
        db_table_comment = 'AI 路线规划站点'
        verbose_name = 'AI 路线规划站点'
        verbose_name_plural = 'AI 路线规划站点'
        ordering = ['day_index', 'sequence']
        indexes = [
            models.Index(fields=['plan', 'day_index', 'sequence'], name='idx_route_stop_plan_day_seq'),
        ]

    def __str__(self) -> str:
        """功能说明：返回站点展示文本。"""
        return f'第{self.day_index}天第{self.sequence}站：{self.name}'

