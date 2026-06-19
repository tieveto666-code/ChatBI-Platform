# ChatBI API 规范文档

> **文档类型**：技术设计文档  
> **版本**：v0.3  
> **更新日期**：2026-05-10  
> **对应 PRD**：ChatBI-PRD.md v0.6

---

## 1. 通用约定

### 1.1 基础 URL

```
http://localhost:8000/api
```

### 1.2 认证方式

所有需要鉴权的 API 在 Header 中携带 JWT Token：

```
Authorization: Bearer <token>
```

### 1.3 标准响应信封

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 1.4 错误响应

```json
{
  "code": 3001,
  "message": "SQL execution failed",
  "detail": "no such table: orders"
}
```

### 1.5 错误码表

| 区间 | 分类 | 错误码 | 说明 |
|------|------|--------|------|
| 0 | 成功 | 0 | 请求成功 |
| 1000-1999 | 认证错误 | 1001 | TOKEN_EXPIRED — Token 过期 |
| | | 1002 | INVALID_CREDENTIALS — 用户名或密码错误 |
| | | 1003 | TOKEN_INVALID — Token 无效 |
| | | 1004 | REGISTRATION_FAILED — 注册失败（用户名已存在） |
| 2000-2999 | 参数错误 | 2001 | VALIDATION_ERROR — 请求参数校验失败 |
| | | 2002 | MISSING_FIELD — 缺少必填字段 |
| 3000-3999 | 业务错误 | 3001 | SQL_EXECUTION_ERROR — SQL 执行失败 |
| | | 3002 | LLM_CALL_FAILED — LLM 调用失败 |
| | | 3003 | FILE_TOO_LARGE — 文件超过大小限制 |
| | | 3004 | FILE_PARSE_ERROR — 文件解析失败 |
| | | 3005 | UNSUPPORTED_FILE_TYPE — 不支持的文件类型 |
| | | 3006 | MEMORY_LIMIT_EXCEEDED — 超出内存限制 |
| 4000-4999 | 权限错误 | 4001 | FORBIDDEN — 无权限 |
| | | 4002 | INSUFFICIENT_PERMISSION — 权限不足 |
| 5000-5999 | 系统错误 | 5001 | INTERNAL_ERROR — 服务器内部错误 |
| | | 5002 | DATABASE_ERROR — 数据库错误 |

---

## 2. 认证模块

### POST /auth/register

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "Abc123!@#",
  "email": "zhangsan@example.com"
}
```

**成功响应** (201)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "user_id": 1,
    "username": "zhangsan",
    "role": "user"
  }
}
```

**失败响应** (409)：

```json
{
  "code": 1004,
  "message": "用户名已存在",
  "detail": "username 'zhangsan' already exists"
}
```

### POST /auth/login

**请求体**：

```json
{
  "username": "zhangsan",
  "password": "Abc123!@#"
}
```

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 86400,
    "user": {
      "id": 1,
      "username": "zhangsan",
      "email": "zhangsan@example.com",
      "role": "analyst"
    }
  }
}
```

### POST /auth/refresh

**请求头**：`Authorization: Bearer <current_token>`

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 86400
  }
}
```

### POST /auth/logout

**请求头**：`Authorization: Bearer <token>`

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

### GET /auth/me

**请求头**：`Authorization: Bearer <token>`

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "role": {
      "id": 2,
      "name": "数据分析师",
      "code": "analyst"
    },
    "is_active": true
  }
}
```

---

## 3. 对话模块

### POST /chat/stream

> SSE (Server-Sent Events) 流式接口。客户端通过 EventSource 或 fetch 连接。

**请求头**：`Authorization: Bearer <token>`

**请求体**：

```json
{
  "conversation_id": null,
  "message": "上个月的销售额Top10是哪些？",
  "data_source_type": "db",
  "db_connection_id": 1,
  "file_upload_id": null,
  "agent_config_id": 1
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| conversation_id | integer/null | ✅ | null 表示新建对话，非 null 追加到已有对话 |
| message | string | ✅ | 用户输入的纯文本问题 |
| data_source_type | string | 条件 | conversation_id 为 null 时必填；取值 `db` / `excel` / `csv` |
| db_connection_id | integer/null | 条件 | data_source_type=db 时必填 |
| file_upload_id | integer/null | 条件 | data_source_type=excel/csv 时必填 |
| agent_config_id | integer/null | ❌ | 指定数据智能体配置；不传使用默认配置 |

> 契约约束：前端不得传 `datasource_ids`。数据库和文件数据源必须用 `data_source_type + db_connection_id/file_upload_id` 表达，避免同一数组同时承载两类 ID。

**响应**：SSE 流式响应（Content-Type: text/event-stream）

**SSE 事件协议**：

```
event: token
data: {"text": "2025年4月销售额Top10的商品如下："}

event: sql
data: {"sql": "SELECT product_name, SUM(amount) as total FROM orders WHERE strftime('%Y-%m', created_at) = '2025-04' GROUP BY product_name ORDER BY total DESC LIMIT 10"}

event: chart
data: {"default_type": "bar", "available_types": ["table", "bar", "line"], "type": "bar", "x_axis": ["商品A", "商品B"], "options": {"bar": {"series": [{"name": "销售额", "type": "bar", "data": [12345, 9876]}]}, "line": {"series": [{"name": "销售额", "type": "line", "data": [12345, 9876]}]}}, "config": {"x_label": "商品", "y_label": "销售额(元)"}}

event: table
data: {"columns": ["商品名", "销售额"], "rows": [["商品A", 12345], ...], "total_rows": 10}

event: done
data: {"conversation_id": 5, "message_id": 23, "token_usage": {"prompt": 1200, "completion": 350, "total": 1550}}

event: error
data: {"code": 3001, "message": "SQL 执行失败", "detail": "表 'orders' 不存在"}
```

**事件说明**：

| 事件名 | 触发时机 | data 字段 |
|--------|---------|-----------|
| token | LLM 流式输出每个文本片段 | `{"text": "..."}` |
| sql | SQL 生成完毕；**管线固定发出该事件**（便于审计与调试）。PRD 所述「可选展示」指**前端/权限是否向最终用户展示**，非服务端省略事件。 | `{"sql": "SELECT ..."}` |
| chart | 查询结果生成图表数据（含多种可用类型，前端左上角可切换） | `{"default_type": "bar|line|bar_line", "available_types": ["table","bar","line",...], "x_axis": [...], "options": {...}, "config": {...}}` |
| table | 查询结果原始表格 | `{"columns": [...], "rows": [...], "total_rows": N}` |
| done | 回答结束 | `{"conversation_id": N, "message_id": N, "token_usage": {...}}` |
| error | 管线任意步骤出错 | `{"code": N, "message": "...", "detail": "..."}` |

### GET /conversations

**请求头**：`Authorization: Bearer <token>`

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|:-----:|------|
| page | integer | ❌ | 1 | 页码 |
| page_size | integer | ❌ | 20 | 每页数量 |

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 5,
        "title": "上个月的销售额分析",
        "data_source": {"type": "db", "name": "sales.db"},
        "message_count": 12,
        "last_message_at": "2026-05-08T10:30:00Z",
        "created_at": "2026-05-08T10:00:00Z"
      }
    ],
    "total": 23,
    "page": 1,
    "page_size": 20
  }
}
```

### POST /conversations

**请求头**：`Authorization: Bearer <token>`

**请求体**：

```json
{
  "title": "2025年销售数据分析",
  "data_source_type": "db",
  "db_connection_id": 1,
  "agent_config_id": 1
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| title | string | ❌ | 对话标题，不传则由系统自动生成 |
| data_source_type | string | ✅ | "db" / "excel" / "csv" |
| db_connection_id | integer | 条件 | data_source_type=db 时必填 |
| file_upload_id | integer | 条件 | data_source_type=excel/csv 时必填 |
| agent_config_id | integer | ❌ | 指定数据智能体配置 |

**成功响应** (201)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 6,
    "title": "2025年销售数据分析",
    "data_source": {"type": "db", "name": "sales.db"},
    "status": "active",
    "created_at": "2026-05-08T11:00:00Z"
  }
}
```

### GET /conversations/{id}

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5,
    "title": "上个月的销售额分析",
    "data_source": {"type": "db", "name": "sales.db"},
    "status": "active",
    "message_count": 12,
    "created_at": "2026-05-08T10:00:00Z",
    "updated_at": "2026-05-08T10:30:00Z"
  }
}
```

### DELETE /conversations/{id}

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

### PATCH /conversations/{id}

> 切换对话绑定的数据源，保留对话上下文。前端在用户通过 DataSourceSelector 切换数据源时调用此接口。

**请求头**：`Authorization: Bearer <token>`

**请求体**：

```json
{
  "data_source_type": "db",
  "db_connection_id": 2,
  "file_upload_id": null,
  "agent_config_id": 1
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| title | string | ❌ | 修改对话标题 |
| data_source_type | string | 条件 | 切换数据源时必填；"db" / "excel" / "csv" |
| db_connection_id | integer | 条件 | data_source_type=db 时必填 |
| file_upload_id | integer | 条件 | data_source_type=excel/csv 时必填 |
| agent_config_id | integer | ❌ | 切换数据智能体配置 |

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 5,
    "data_source": {"type": "db", "name": "生产数据库", "id": 2},
    "updated_at": "2026-05-08T12:00:00Z"
  }
}
```

### GET /conversations/{id}/messages

**查询参数**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|:-----:|------|
| page | integer | ❌ | 1 | 页码 |
| page_size | integer | ❌ | 50 | 每页数量 |

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 22,
        "role": "user",
        "content_type": "text",
        "content": "上个月的销售额Top10是哪些？",
        "created_at": "2026-05-08T10:00:05Z"
      },
      {
        "id": 23,
        "role": "assistant",
        "content_type": "mixed",
        "content": {
          "text": "2025年4月销售额Top10的商品如下：",
          "sql": "SELECT ...",
          "chart": {"type": "bar", "data": [...]},
          "table": {"columns": [...], "rows": [...]}
        },
        "token_count": 350,
        "created_at": "2026-05-08T10:00:08Z"
      }
    ],
    "total": 12,
    "page": 1,
    "page_size": 50
  }
}
```

---

## 4. 数据源模块

### POST /datasources/upload

> 上传 Excel/CSV 文件（multipart/form-data）。后端必须完成“保存原始文件 → 解析多 Sheet → 导入文件查询库 SQLite → 写入元数据和 Schema 缓存”的完整链路，上传成功后该文件即可被对话绑定查询。

**请求头**：`Authorization: Bearer <token>`

**请求体**：multipart/form-data

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| file | file | ✅ | .xlsx 或 .csv 文件，最大 20MB |

**成功响应** (201)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 3,
    "name": "2025销售报表.xlsx",
    "source_type": "excel",
    "file_size_bytes": 1048576,
    "query_db_ready": true,
    "sheet_count": 3,
    "total_rows": 1234,
    "sheets": [
      {"sheet_name": "订单数据", "table_name": "tbl_orders", "column_count": 8, "row_count": 500},
      {"sheet_name": "用户信息", "table_name": "tbl_users", "column_count": 5, "row_count": 200},
      {"sheet_name": "产品目录", "table_name": "tbl_products", "column_count": 6, "row_count": 534}
    ],
    "created_at": "2026-05-08T12:00:00Z"
  }
}
```

**处理要求**：

| 步骤 | 要求 |
|------|------|
| 文件校验 | 限制 .csv/.xlsx，最大 20MB；CSV 优先 UTF-8，失败回退 GBK |
| Schema 清洗 | 表名、列名必须转换为 SQLite 安全标识符，并记录原始名称映射 |
| 数据导入 | 每个 Sheet 导入文件查询库中的独立表；批量写入失败时回滚并删除临时文件 |
| 生命周期 | 删除 `/datasources/files/{id}` 时，必须同步删除原始文件、查询库和 `file_sheets` |

### GET /datasources/files

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 3,
        "name": "2025销售报表.xlsx",
        "source_type": "excel",
        "file_size_bytes": 1048576,
        "sheet_count": 3,
        "total_rows": 1234,
        "created_at": "2026-05-08T12:00:00Z"
      }
    ],
    "total": 1
  }
}
```

### DELETE /datasources/files/{id}

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

### GET /datasources/connections

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "生产数据库",
        "db_type": "sqlite",
        "db_path": "/data/sales.db",
        "is_active": true,
        "created_at": "2026-05-01T00:00:00Z"
      }
    ],
    "total": 1
  }
}
```

### POST /datasources/connections

**请求体**：

```json
{
  "name": "测试数据库",
  "db_type": "sqlite",
  "db_path": "/Users/xxx/data/test.db"
}
```

**成功响应** (201)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 2,
    "name": "测试数据库",
    "db_type": "sqlite",
    "db_path": "/Users/xxx/data/test.db",
    "is_active": true,
    "created_at": "2026-05-08T13:00:00Z"
  }
}
```

### PUT /datasources/connections/{id}

**请求体**（支持部分更新）：

```json
{
  "name": "生产数据库-正式环境",
  "db_path": "/data/production/sales.db"
}
```

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "生产数据库-正式环境",
    "db_type": "sqlite",
    "db_path": "/data/production/sales.db",
    "is_active": true,
    "updated_at": "2026-05-08T14:00:00Z"
  }
}
```

### DELETE /datasources/connections/{id}

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

### GET /datasources/connections/{id}/schema
> 获取数据库连接的 Schema。
>
> **路径说明**：`{id}` 对应 `db_connections` 表的主键。

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "source_type": "db",
    "tables": [...]

### GET /datasources/files/{id}/schema
> 获取上传文件的 Schema（多 Sheet Excel 将返回所有 Sheet 的 Schema）。
>
> **路径说明**：`{id}` 对应 `file_uploads` 表的主键。

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "source_type": "file",
    "file_name": "2025销售报表.xlsx",
    "tables": [...]

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "tables": [
      {
        "table_name": "orders",
        "columns": [
          {"name": "id", "type": "INTEGER", "nullable": false, "pk": true},
          {"name": "user_id", "type": "INTEGER", "nullable": true, "fk": {"table": "users", "column": "id"}},
          {"name": "product_name", "type": "TEXT", "nullable": true},
          {"name": "amount", "type": "REAL", "nullable": true},
          {"name": "created_at", "type": "TEXT", "nullable": true}
        ],
        "row_count": 10000
      }
    ]
  }
}
```

---

## 5. 用户/角色/菜单管理

### GET /admin/users

**查询参数**：page, page_size, keyword（用户名/邮箱搜索）

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "role": {"id": 1, "name": "超级管理员", "code": "admin"},
        "is_active": true,
        "created_at": "2026-05-01T00:00:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "page_size": 20
  }
}
```

### POST /admin/users

**请求体**：

```json
{
  "username": "lisi",
  "password": "Pass123!@#",
  "email": "lisi@example.com",
  "role_id": 2
}
```

### PUT /admin/users/{id}

**请求体**（支持部分更新）：

```json
{
  "email": "newemail@example.com",
  "role_id": 3
}
```

### DELETE /admin/users/{id}

**注意**：系统内置管理员（role=admin 且 is_system=True）不可删除。

### PUT /admin/users/{id}/status

**请求体**：

```json
{
  "is_active": false
}
```

### GET /admin/roles

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "超级管理员",
        "code": "admin",
        "description": "拥有全部系统权限",
        "is_system": true,
        "sort_order": 1,
        "menu_ids": [1, 2, 3, 4, 5, 6, 7],
        "user_count": 1,
        "created_at": "2026-05-01T00:00:00Z"
      }
    ]
  }
}
```

### POST /admin/roles

**请求体**：

```json
{
  "name": "查看者",
  "code": "viewer",
  "description": "仅可查看对话分析结果",
  "menu_ids": [1, 4]
}
```

### PUT /admin/roles/{id}

**请求体**（支持部分更新）：

```json
{
  "name": "只读用户",
  "menu_ids": [1]
}
```

### DELETE /admin/roles/{id}

**注意**：`is_system=true` 的角色不可删除。

### GET /admin/menus

**成功响应** (200)：返回完整菜单树（含父子层级）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "menus": [
      {
        "id": 1,
        "name": "对话分析",
        "icon": "ChatIcon",
        "path": "/chat",
        "sort_order": 1,
        "children": []
      },
      {
        "id": 3,
        "name": "系统管理",
        "icon": "SettingsIcon",
        "path": "/admin",
        "sort_order": 99,
        "children": [
          {"id": 4, "name": "用户管理", "icon": "PeopleIcon", "path": "/admin/users", "sort_order": 1, "children": []},
          {"id": 5, "name": "角色管理", "icon": "SecurityIcon", "path": "/admin/roles", "sort_order": 2, "children": []},
          {"id": 6, "name": "菜单管理", "icon": "MenuIcon", "path": "/admin/menus", "sort_order": 3, "children": []}
        ]
      }
    ]
  }
}
```

### POST /admin/menus

**请求体**：

```json
{
  "parent_id": 3,
  "name": "操作日志",
  "icon": "HistoryIcon",
  "path": "/admin/logs",
  "sort_order": 4
}
```

### PUT /admin/menus/{id}

**请求体**（支持部分更新）：

```json
{
  "name": "审计日志",
  "sort_order": 5
}
```

### DELETE /admin/menus/{id}

**注意**：删除父菜单时，其子菜单一并删除（CASCADE）。

### GET /menus（获取当前用户可见菜单）

> 根据当前用户的角色过滤返回可见菜单树。

**请求头**：`Authorization: Bearer <token>`

**成功响应** (200)：格式同 GET /admin/menus，但仅包含当前角色有权限的菜单。

---

## 6. 智能体配置

### GET /agents

**成功响应** (200)：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "默认NL2SQL智能体",
        "model_provider": "deepseek",
        "model_name": "deepseek-chat",
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 4096,
        "is_active": true,
        "created_at": "2026-05-01T00:00:00Z"
      }
    ]
  }
}
```

### PUT /agents/{id}

**请求体**：

```json
{
  "temperature": 0.2,
  "system_prompt": "自定义系统提示词...",
  "synonym_map": {"销售额": "amount", "用户数": "user_count"}
}
```

---

*本文档对应 ChatBI PRD v0.6 附录 C（API 路由汇总表）的完整规格版。*

### OpenAPI 规范

| 项目 | 说明 |
|------|------|
| **权威源** | 以 **FastAPI 自动生成的 `/openapi.json`** 为唯一事实源 |
| **生成方式** | 后端 `main.py` 启动后访问 `http://localhost:8000/openapi.json` |
| **前端消费** | 通过 `openapi-typescript` 自动生成 TypeScript 类型：`npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts` |
| **规范同步** | 后端路由变更 → 重启 FastAPI → `/openapi.json` 自动更新 → 前端重新生成类型。**无需手动维护 OpenAPI YAML 文件** |
| **首次生成** | 后端第一个 PR 合并后，由后端开发者执行一次 `curl -o backend/openapi.json http://localhost:8000/openapi.json` 作为基线 |
