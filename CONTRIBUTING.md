# 贡献指南

感谢你对 ChatBI 的关注！

## 开发环境

1. Fork 本仓库并 clone 到本地
2. 配置环境变量：`cp .env.example backend/.env`，填入 `DEEPSEEK_API_KEY`
3. 安装依赖并启动：

```bash
cd backend && python3 -m pip install -r requirements.txt
cd ../frontend && npm install
cd .. && ./dev-start.sh
```

## 提交前检查

```bash
# 后端测试（使用 mock LLM，无需 API Key）
cd backend && python3 -m pytest -q

# 前端构建
cd frontend && npm run build
```

## Pull Request

- 一个 PR 聚焦一类改动，便于 review
- 如涉及 API 变更，请同步更新 `docs/API-Spec.md`
- 不要提交 `.env`、数据库文件、上传目录内容

## 代码风格

- 后端：与现有 FastAPI / SQLAlchemy 结构保持一致
- 前端：TypeScript + MUI，与现有组件风格一致
- 避免无关重构
