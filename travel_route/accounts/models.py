from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """功能说明：保存系统用户账号和头像信息。"""

    username_validator = UnicodeUsernameValidator()

    password = models.CharField('密码', max_length=128, db_comment='密码哈希')
    last_login = models.DateTimeField('最后登录时间', blank=True, null=True, db_comment='最后登录时间')
    is_superuser = models.BooleanField(
        '超级管理员状态',
        default=False,
        help_text='表示该用户拥有所有权限。',
        db_comment='是否为超级管理员',
    )
    username = models.CharField(
        '用户名',
        max_length=150,
        unique=True,
        help_text='必填，长度不超过 150 个字符，可包含字母、数字和 @/./+/-/_。',
        validators=[username_validator],
        error_messages={'unique': '用户名已存在。'},
        db_comment='用户名',
    )
    first_name = models.CharField('名', max_length=150, blank=True, db_comment='名')
    last_name = models.CharField('姓', max_length=150, blank=True, db_comment='姓')
    email = models.EmailField('邮箱', blank=True, db_comment='邮箱')
    is_staff = models.BooleanField(
        '后台权限状态',
        default=False,
        help_text='表示该用户是否可以登录 Django 后台。',
        db_comment='是否可以登录后台',
    )
    is_active = models.BooleanField(
        '启用状态',
        default=True,
        help_text='表示该用户是否启用。',
        db_comment='是否启用',
    )
    date_joined = models.DateTimeField('注册时间', default=timezone.now, db_comment='注册时间')
    avatar = models.ImageField(
        '头像',
        upload_to='avatars/',
        blank=True,
        null=True,
        db_comment='用户头像',
    )
    groups = models.ManyToManyField(
        Group,
        verbose_name='用户组',
        blank=True,
        help_text='用户所属的权限组。',
        related_name='user_set',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='用户权限',
        blank=True,
        help_text='用户单独拥有的权限。',
        related_name='user_set',
        related_query_name='user',
    )

    class Meta:
        db_table = 'user'
        db_table_comment = '用户信息'
        verbose_name = '用户信息'
        verbose_name_plural = '用户信息'
