# 旅游规划平台（travel_route）

基于 Django + MySQL 的旅游规划平台，集景点浏览、攻略分享与 AI 路线规划于一体：景点数据来自携程清洗数据，AI 规划由 DeepSeek + LangGraph 智能体生成按天行程，后台采用 SimpleUI 中文管理界面。

## 功能模块

| 模块 | 功能 |
| --- | --- |
| 账号（accounts） | 注册 / 登录 / 退出、个人中心与头像上传、我的收藏、我的攻略 |
| 景点（travel） | 景点列表与详情（评分、标签、票价、经纬度等）、景点收藏、景点评论 |
| 攻略（guides） | 攻略发布（多图上传、关联景点）、攻略列表与详情、景点搜索 |
| AI 规划（planner） | 输入城市 / 预算 / 出行时间 / 偏好，LangGraph 智能体调用 DeepSeek 流式生成按天路线，规划过程与结果可查看 |
| 后台管理 | `/admin/`，SimpleUI 界面，含账号权限、景点管理、攻略管理、AI 路线规划 |

## 技术栈

- Python 3.12+ / Django 6.0
- MySQL 8（utf8mb4，mysqlclient 驱动）
- SimpleUI 后台界面、Pillow 图像处理
- AI：LangGraph + LangChain + DeepSeek API（OpenAI 兼容接口）
- 地图：高德地图 JS API（AK 配置于 `travel_route/settings.py`）

## 快速开始

### 1. 创建数据库

```sql
CREATE DATABASE travel_route_base DEFAULT CHARSET utf8mb4;
```

### 2. 配置环境变量

在项目根目录新建 `.env`（已被 `.gitignore` 排除，不会上传）：

```ini
MYSQL_DATABASE=travel_route_base
MYSQL_USER=root
MYSQL_PASSWORD=你的数据库密码
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
DEEPSEEK_API_KEY=你的DeepSeek密钥
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
# AI 规划模块额外依赖（requirements.txt 未包含）
pip install langgraph langchain-openai openai
```

### 4. 初始化数据库

```bash
python manage.py migrate
```

然后导入根目录的 `旅游攻略初始化数据.sql`（攻略示例数据，含部分表结构与数据，可用 Navicat / SQLyog / mysql 命令行导入）。

### 5. 创建管理员并运行

```bash
python manage.py createsuperuser
python manage.py runserver
```

- 前台首页：http://127.0.0.1:8000/
- 管理后台：http://127.0.0.1:8000/admin/

## 目录结构

```
travel_route/
├── travel_route/          # Django 配置（settings / urls / wsgi / asgi）
├── accounts/              # 用户账号模块
├── travel/                # 景点、收藏、评论模块
├── guides/                # 攻略模块
├── planner/               # AI 路线规划模块
│   └── Agent/             # LangGraph 图、景点工具、LLM 与路线 utils
├── templates/             # 前端模板
├── static/                # 静态资源
├── media/                 # 上传文件（头像、攻略图片，不入库）
├── requirements.txt
├── manage.py
└── 旅游攻略初始化数据.sql   # 攻略初始化数据
```

## 环境变量说明

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | 开发用占位值 | 生产环境务必替换 |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | 逗号分隔 |
| `MYSQL_DATABASE` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_HOST` / `MYSQL_PORT` | `travel_route_base` / `root` / `password` / `127.0.0.1` / `3306` | MySQL 连接 |
| `DEEPSEEK_API_KEY` | 无 | AI 规划必需 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 接口地址 |
| `DEEPSEEK_MODEL` | `deepseek-flash` | 模型名称 |

## 注意事项

- `.env`、`.venv`、`media/` 均在 `.gitignore` 中，请勿提交密钥与上传文件。
- `DEBUG = True` 仅适用于开发环境。
- `settings.py` 中的高德 AK 为硬编码，公开仓库前建议移入 `.env` 管理。
- AI 规划需配置 `DEEPSEEK_API_KEY` 后方可使用。
