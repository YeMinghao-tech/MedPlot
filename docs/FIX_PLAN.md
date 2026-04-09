# MedPilot 问题修复计划

**创建日期**: 2026-04-09
**更新日期**: 2026-04-09

---

## 一、已解决问题

### Critical (3/3 完成)

| # | 问题 | 修复方案 | 状态 |
|---|------|----------|------|
| C-1 | API Key 明文硬编码 | `config/settings.yaml` 中 `api_key` 改为 `${DASHSCOPE_API_KEY}` 环境变量注入 | ✅ 已完成 |
| C-2 | Auth 中间件是空壳 | 实现基于 `MEDPILOT_API_KEY` 环境变量的 Bearer Token 验证 | ✅ 已完成 |
| C-3 | 无容器化配置 | 添加 Dockerfile、docker-compose.yml、.env.example、.dockerignore | ✅ 已完成 |

### Major (9/13 完成)

| # | 问题 | 修复方案 | 状态 |
|---|------|----------|------|
| M-1 | CORS 全开 | `config/settings.yaml` 中 `cors_origins` 改为 `["http://localhost:3000", "http://localhost:8501"]` | ✅ 已完成 |
| M-3 | LLM 调用无超时 | `qwen_llm.py` 中 `dashscope.Generation.call` 添加 `request_timeout=30` | ✅ 已完成 |
| M-4 | 全局可变单例状态 | Router 初始化移至 app.py lifespan，使用 app.state 管理 | ✅ 已完成 |
| M-5 | 患者列表接口是假实现 | 调用 SemanticMemory.list_patients 实现分页 | ✅ 已完成 |
| M-6 | Bare except 静默吞异常 | 所有 `except Exception: print()` 替换为 `logger.warning/error` + 适当处理 | ✅ 已完成 |
| M-7 | 无输入验证 | 新增 `src/api/models/chat.py` 的 `ChatMessage` Pydantic 模型，添加长度验证 (1-5000) | ✅ 已完成 |
| M-8 | 无外部服务重试 | 新增 `src/libs/utils/retry.py`，QwenLLM 添加指数退避重试 (3次, 2s/4s/8s) | ✅ 已完成 |
| M-9 | Trace 模块为空 | `src/observability/trace/__init__.py` 正确导出 TraceContext 等 | ✅ 已完成 |
| M-10 | 调试 print 残留 | `chat.py` 和 `router.py` 中所有 `print(f"[DEBUG]...")` 替换为 `logger.debug/info/error` | ✅ 已完成 |

---

## 二、新增文件

| 文件 | 说明 |
|------|------|
| `Dockerfile` | Python 3.10-slim 基础镜像，uvicorn 启动 |
| `docker-compose.yml` | API + Dashboard 服务编排 |
| `.env.example` | 环境变量示例 |
| `.dockerignore` | Docker 构建忽略文件 |
| `src/api/models/chat.py` | Pydantic 请求/响应模型 |
| `src/libs/utils/retry.py` | 重试工具（装饰器 + 配置类） |

---

## 三、未解决问题

### Critical (0/3)

| # | 问题 | 建议方案 |
|---|------|----------|
| C-1 | API Key 轮换 | 需要生成新的 DashScope API Key 并撤销旧的 |
| C-2 | JWT 验证 | 生产环境应实现完整的 JWT 验证逻辑 |
| C-3 | 生产部署 | 需要配置生产级 docker-compose（监控、日志持久化等） |

### Major (4/13)

| # | 问题 | 建议方案 |
|---|------|----------|
| M-2 | 患者 PII 数据未加密 | SQLite 添加 encryption extension 或迁移至加密存储服务 |
| M-2 | LLM/HIS 无重试 | HIS 服务添加重试（需在 HISFactory 中实现） |
| M-6 | 部分异常仍静默 | `router.py` 中 RAG 失败的异常已被日志记录，但不影响响应 |
| M-10 | 其他文件仍有 print | 需要检查 `src/tools/` 等其他目录 |

### Medium (0/9)

| # | 问题 | 建议方案 |
|---|------|----------|
| N-1 | 会话列表无分页 | 实现 offset-based 分页 |
| N-5 | 日志系统未集成 | API 层统一使用 logging 模块 |
| N-6 | Health Check 不检查依赖 | 添加 DB/LLM/VectorStore 就绪检查 |
| N-7 | 无 CI/CD | 添加 GitHub Actions 流水线 |
| N-8 | WorkingMemory 无持久化 | 添加 Redis 或文件持久化 |
| N-9 | SemanticMemory 全量加载 | 实现 SQL WHERE 子句过滤 |

### Minor (1/6)

| # | 问题 | 建议方案 |
|---|------|----------|
| L-1 | StateManager 非线程安全 | 添加 asyncio.Lock |
| L-2 | 无 RequestID 链路追踪 | 实现请求级别 trace_id |
| L-3 | logs/ 未加入 .gitignore | ✅ 已完成 |
| L-4 | 类型注解不完整 | 补充类型注解 |
| L-5 | 无 requirements.lock | 使用 `pip-compile` 生成锁文件 |
| L-6 | 模块导出不一致 | ✅ 已完成（Trace 模块） |

---

## 四、修复文件清单

### 已修改文件

| 文件 | 修改内容 |
|------|----------|
| `config/settings.yaml` | api_key 改为 `${DASHSCOPE_API_KEY}`，CORS 限制 |
| `src/api/middleware/auth.py` | 实现 Bearer Token 验证 |
| `src/libs/llm/qwen_llm.py` | 添加 request_timeout=30，添加重试逻辑 |
| `src/api/routers/chat.py` | 添加 logging，移除 print，添加 Pydantic 模型 |
| `src/agent/planner/router.py` | 移除 print，添加 logging |
| `src/libs/reranker/llm_reranker.py` | 异常处理添加日志 |
| `src/agent/memory/memory_manager.py` | 异常处理添加日志 |
| `src/tools/case_generator/entity_extractor.py` | 添加 logging |

---

## 五、运行方式

### 本地运行

```bash
# 设置环境变量
export DASHSCOPE_API_KEY=your_api_key
export MEDPILOT_API_KEY=your_api_key

# 启动 API 服务
uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port 8000

# 或使用 Docker
docker-compose up --build
```

### 测试验证

```bash
# 无认证 - 应返回 401
curl -X POST http://localhost:8000/sessions

# 正确认证 - 应返回 session
curl -X POST http://localhost:8000/sessions -H "Authorization: Bearer test-key"

# 发送消息
curl -X POST "http://localhost:8000/chat/<session_id>" \
  -H "Authorization: Bearer test-key" \
  -H "Content-Type: application/json" \
  -d '{"content": "我有点咳嗽"}'
```

---

## 六、后续优先级建议

1. **P0 (立即)**: 轮换 API Key（撤销当前 key，生成新 key）
2. **P1 (上线前)**: 患者数据加密、全局单例状态重构、CI/CD 流水线
3. **P2 (稳定后)**: 健康检查完善、分页实现、日志系统统一
