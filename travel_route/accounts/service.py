from typing import Any, Optional

from django.core.files.uploadedfile import UploadedFile
from django.db.models import QuerySet

from guides.services import build_guide_queryset
from travel.models import AttractionFavorite


MAX_AVATAR_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


def clean_profile_form(
    user: Any,
    post_data: dict[str, Any],
    uploaded_avatar: Optional[UploadedFile],
) -> tuple[dict[str, Any], list[str]]:
    """功能说明：清洗并校验个人中心资料编辑表单。"""
    # 读取用户提交的基础资料。
    username = str(post_data.get('username', '')).strip()
    email = str(post_data.get('email', '')).strip()
    cleaned_data = {'username': username, 'email': email, 'avatar': uploaded_avatar}
    errors = []

    # 校验用户名必填、长度和唯一性。
    if not username:
        errors.append('请输入用户名。')
    elif len(username) > 150:
        errors.append('用户名不能超过 150 个字符。')
    elif user.__class__.objects.exclude(pk=user.pk).filter(username=username).exists():
        errors.append('用户名已存在。')

    # 校验邮箱长度，邮箱格式使用模型层 EmailField 基础能力保存。
    if len(email) > 254:
        errors.append('邮箱不能超过 254 个字符。')

    # 校验头像大小和类型，避免非图片文件写入媒体目录。
    if uploaded_avatar:
        if uploaded_avatar.content_type not in ALLOWED_AVATAR_TYPES:
            errors.append('头像仅支持 JPG、PNG、WEBP 或 GIF 图片。')
        if uploaded_avatar.size > MAX_AVATAR_SIZE:
            errors.append('头像文件不能超过 3MB。')

    return cleaned_data, errors


def update_profile(user: Any, cleaned_data: dict[str, Any]) -> None:
    """功能说明：更新当前用户的个人资料。"""
    # 更新基础字段。
    user.username = cleaned_data['username']
    user.email = cleaned_data['email']
    update_fields = ['username', 'email']

    # 用户上传头像时替换头像文件。
    if cleaned_data.get('avatar'):
        user.avatar = cleaned_data['avatar']
        update_fields.append('avatar')

    # 只保存变更字段，减少不必要数据库写入。
    user.save(update_fields=update_fields)


def get_user_favorites(user: Any) -> QuerySet[AttractionFavorite]:
    """功能说明：查询当前用户收藏的景点列表。"""
    # 预加载景点数据，避免模板循环中重复查询。
    return (
        AttractionFavorite.objects.select_related('attraction')
        .filter(user=user)
        .order_by('-created_at', '-id')
    )


def get_user_guides(user: Any) -> QuerySet:
    """功能说明：查询当前用户发布的旅游攻略列表。"""
    # 复用攻略查询集构造函数，预加载图片和关联景点。
    return build_guide_queryset().filter(author=user).order_by('-created_at', '-id')
