# 从开发目录同步到本开源包

本目录 `chatbi-open-source/` 是从上级开发工程整理出的 **GitHub 发布包**，与开发目录并列存放，**不会修改开发目录中的任何文件**。

开发目录：`../`（ChatBI_vibe coding）  
开源包：`./`（chatbi-open-source）

## 何时需要同步

开发目录有功能更新、Bug 修复或文档变更，需要刷新 GitHub 仓库内容时，在本目录执行下方脚本。

## 一键同步脚本

在项目根目录（`ChatBI_vibe coding/`）执行：

```bash
./chatbi-open-source/scripts/sync-from-dev.sh
```

或在 `chatbi-open-source/` 内执行：

```bash
./scripts/sync-from-dev.sh
```

## 同步范围

| 会同步 | 不会同步（保留开源包自有文件） |
|--------|-------------------------------|
| `backend/` 源码与测试 | `README.md`、`LICENSE` |
| `frontend/` 源码 | `CONTRIBUTING.md`、`SECURITY.md` |
| `backend/data/samples/` 演示数据 | `.github/` CI 与模板 |
| `dev-start.sh`、根目录 `.env.example` | 本文件 `SYNC.md` |
| `docs/` 下 PRD / API / 架构文档 | `backend/.env.example`（开源专用版） |

**永不复制：** `.env`、`backend/.env`、`node_modules`、`dist`、`__pycache__`、运行时数据库与上传文件。

## 同步后建议检查

```bash
cd chatbi-open-source/backend && python3 -m pytest -q
cd ../frontend && npm run build
git status
git diff
```

确认无 `.env` 或 API Key 被误加入后再 commit / push。

## 首次推送到 GitHub

```bash
cd chatbi-open-source
git init
git add .
git commit -m "Initial open-source release"
git branch -M main
git remote add origin git@github.com:YOUR_USER/chatbi.git
git push -u origin main
```

## 后续更新

```bash
# 1. 从开发目录同步
./scripts/sync-from-dev.sh

# 2. 提交
git add -A
git commit -m "Sync from dev: <简要说明>"
git push
```
