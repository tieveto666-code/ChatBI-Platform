# ChatBI

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](backend/requirements.txt)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](frontend/package.json)

基于大语言模型的对话式数据分析平台：**自然语言问数 → NL2SQL → 查询执行 → 表格 / 图表 / 文字总结**。

## 功能概览

| 模块 | 能力 |
|------|------|
| 对话问数 | SSE 流式回复、查看 SQL、结果表格与 ECharts 图表（柱状/折线/柱线复合/表格，左上角可切换） |
| 数据源 | SQLite 连接、Excel/CSV 上传、表结构同步、表数据预览 |
| 智能体 | 固定 9 步问数工作流，各 LLM 节点可配 Prompt 与模型 |
| 字段术语 | 数据表级标准词 / 同义词，注入 NL2SQL Prompt |
| 权限 | 用户 / 角色 / 菜单 RBAC，数据源与智能体按角色授权 |

## 环境要求

- Python 3.9+
- Node.js 18+
- **DeepSeek API Key**（OpenAI 兼容 Chat Completions 接口）

> 运行应用必须配置 `DEEPSEEK_API_KEY`。后端单元测试使用内部 `mock` Provider，无需真实 Key。

## 快速开始

```bash
# 1. 配置密钥
cp .env.example backend/.env
# 编辑 backend/.env，填入 DEEPSEEK_API_KEY

# 2. 安装依赖
cd backend && python3 -m pip install -r requirements.txt
cd ../frontend && npm install

# 3. 一键启动（项目根目录）
cd .. && chmod +x dev-start.sh && ./dev-start.sh
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |

首次启动会自动执行 `seed.py`，创建演示 SQLite、样例 Excel、默认智能体。

### 默认登录（仅本地演示）

| 账号 | 密码 |
|------|------|
| `admin` | `admin123` |

**部署到生产环境前务必修改密码与 `JWT_SECRET`。**

## LLM 配置

问数模型由 **智能体** 与 **工作流节点** 的 `model_provider` / `model_name` 决定。

| 环境变量 | 说明 |
|----------|------|
| `LLM_PROVIDER` | 生产环境使用 `deepseek` |
| `DEEPSEEK_API_KEY` | **必填** |
| `DEEPSEEK_API_BASE` | 默认 `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | 默认 `deepseek-chat` |

字段术语（同义词）在 **数据源管理 → 管理表 → 字段术语** 中配置，不在智能体页配置。

## 项目结构

```
chatbi-open-source/
├── backend/           # FastAPI + SQLAlchemy
│   ├── data/samples/  # 演示 SQLite 与样例 Excel
│   ├── llm/           # DeepSeek Provider
│   ├── services/      # 问数引擎、SQL 校验等
│   └── tests/         # pytest（114+）
├── frontend/          # React + Vite + MUI
├── docs/              # PRD、API 规范、架构说明
├── dev-start.sh       # 本地开发启动脚本
└── .github/workflows/ # CI
```

## 测试

```bash
cd backend
python3 -m pytest -q
```

```bash
cd frontend
npm run build
```

## 文档

- [产品需求（PRD）](docs/PRD.md)
- [API 规范](docs/API-Spec.md)
- [后端架构](docs/Architecture.md)
- [贡献指南](CONTRIBUTING.md)
- [安全说明](SECURITY.md)

## 发布到 GitHub

```bash
cd chatbi-open-source
git init
git add .
git commit -m "Initial open-source release"
git remote add origin git@github.com:YOUR_USER/chatbi.git
git push -u origin main
```

## License

[MIT](LICENSE)
