#!/usr/bin/env python
"""功能说明：Django 项目命令行入口。"""
import os
import sys


def main() -> None:
    """功能说明：执行 Django 命令行任务。"""
    # 指定默认配置模块，保证命令行工具加载项目配置。
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travel_route.settings')

    # 调用 Django 内置命令执行器。
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
