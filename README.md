# TravelMind

TravelMind 是一个基于 FastAPI、LangGraph 和 LangChain 的智能旅行规划系统。

## 功能

- 从自然语言提取旅行需求
- 自动追问缺失信息
- 查询高德天气、景点和步行路线
- 使用 PostgreSQL、pgvector 和知识库增强规划
- 校验日期、预算、费用和活动时间冲突
- 支持人工调整、事件重规划和历史版本恢复
- 使用 LangGraph 检查点保存会话状态

## 环境要求

- Python 3.13+
- uv
- Docker Desktop
- PostgreSQL 16 + pgvector

## 安装依赖

```powershell
uv sync
```

## 配置环境变量

复制配置示例：

```powershell
Copy-Item .env.example .env
```

然后在 `.env` 中填写：

- DeepSeek API Key
- 高德 API Key
- SiliconFlow Embedding API Key
- PostgreSQL 数据库连接地址

不要把 `.env` 提交到 Git。

## 启动 PostgreSQL

```powershell
docker start travel-mind-postgres
```

确认容器状态：

```powershell
docker ps --filter "name=travel-mind-postgres"
```

## 导入知识库

```powershell
uv run python -m travel_mind.rag.ingest
```

## 启动 API

```powershell
uv run travel-mind --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 代码检查

```powershell
uv run ruff check .
uv run ruff format --check .
```

## 运行测试

```powershell
uv run pytest -q
```

查看覆盖率：

```powershell
uv run pytest --cov=travel_mind --cov-report=term-missing
```