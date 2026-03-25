## 6. 项目排期（优化版）

> **排期原则（严格对齐本 DEV_SPEC 的架构分层与目录结构）**
> 
> - **只按本文档设计落地**：以第 5.2 节目录树为“交付清单”，每一步都要在文件系统上产生可见变化。
> - **1 小时一个可验收增量**：每个小阶段（≈1h）都必须同时给出“验收标准 + 测试方法”，尽量做到 TDD。
> - **先打通主闭环，再补齐默认实现**：优先做“可跑通的端到端路径（问诊对话 → Agent 规划 → 工具调用 → 返回结果）”，并在 Libs 层补齐可运行的默认后端实现，避免出现“只有接口没有实现”的空转。
> - **外部依赖可替换/可 Mock**：LLM/Embedding/Vision/VectorStore/HIS 的真实调用在单元测试中一律用 Fake/Mock，集成测试再开真实后端（可选）。
> - **工具实现先于大脑构建**：确保 Router（路由）开发时，所需调用的具体工具（RAG、HIS、病历生成）已具备可运行的实现，避免全部硬 Mock 增加联调成本。

---

### 阶段总览（大阶段 → 目的）

| 阶段 | 名称 | 核心目标 | 依赖关系 |
|------|------|---------|---------|
| **A** | 工程骨架与测试基座 | 建立可运行、可配置、可测试的工程骨架 | 无 |
| **B** | Libs 可插拔层 | 把“可替换”变成代码事实，补齐默认后端实现 | A |
| **C** | Ingestion Pipeline（医疗知识库摄取） | 离线摄取链路跑通，支持增量更新 | B |
| **D** | 核心工具箱实现（RAG/HIS/Case） | **提前实现 Router 所需调用的具体工具**，确保大脑构建时有“武器”可用 | B |
| **E** | Agent 认知核心（Planner + Memory） | 实现意图识别、状态机、记忆系统，让 Agent 具备“大脑”和“记忆”能力 | D |
| **F** | API 网关与业务集成 | 实现 FastAPI 服务入口，整合完整业务流程 | E |
| **G** | 记忆系统完整实现 | 完成三层记忆的持久化与检索，支持跨会话记忆唤醒 | E |
| **H** | 医疗安全基线与红线测试 | 实现红线拦截、阈值熔断、幻觉防御等安全机制 | D, E |
| **I** | HIS 业务闭环与并发保障 | 实现完整的挂号业务流程，支持并发锁号 | D |
| **J** | 可观测性与 Dashboard | 搭建 Streamlit 医疗专用 Dashboard | A, F |
| **K** | 评估体系与双轨门禁 | 实现 RagasEvaluator + 黄金测试集，建立 CI/Release 门禁 | D, E, H |
| **L** | 端到端验收与文档收口 | 补齐 E2E 测试，完善 README，全链路验收 | A-K |

---

### 📊 进度跟踪表 (Progress Tracking)

> **状态说明**：`[ ]` 未开始 | `[~]` 进行中 | `[x]` 已完成

---

#### 阶段 A：工程骨架与测试基座

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| A1 | 初始化目录树与最小可运行入口 | [x] | 按 5.2 节目录树创建所有 `__init__.py`、`main.py`、`pyproject.toml` |
| A2 | 引入 pytest 并建立测试目录约定 | [x] | `tests/unit/`、`tests/integration/`、`tests/e2e/`、`tests/fixtures/` |
| A3 | 配置加载与校验（Settings） | [x] | 读取 `config/settings.yaml`，解析为 `Settings`，必填字段校验 |

---

#### 阶段 B：Libs 可插拔层

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| B1 | LLM 抽象接口与工厂（Qwen/OpenAI/Ollama） | [x] | `BaseLLM` + `LLMFactory`，支持 Qwen-Max 默认实现 |
| B2 | Vision LLM 抽象接口与工厂（Qwen-VL/GPT-4V） | [x] | `BaseVisionLLM` + `VisionLLMFactory`，支持 Qwen-VL-Max |
| B3 | Embedding 抽象接口与工厂（通义/OpenAI/Ollama） | [x] | `BaseEmbedding` + `EmbeddingFactory`，通义文本向量默认 |
| B4 | VectorStore 抽象接口与工厂（Chroma/Qdrant） | [x] | `BaseVectorStore` + `VectorStoreFactory`，Chroma 默认 |
| B5 | Splitter 抽象接口与工厂（Recursive/Semantic） | [x] | `BaseSplitter` + `SplitterFactory`，RecursiveSplitter 默认 |
| B6 | Reranker 抽象接口与工厂（BGE/LLM/None） | [x] | `BaseReranker` + `RerankerFactory`，BGE reranker 默认 |
| B7 | Memory 抽象接口与工厂 | [x] | `BaseMemory`（短期/长期/情景），支持 SQLite + Chroma 默认 |
| B8 | HIS 抽象接口与工厂（Mock/HTTP） | [x] | `BaseHISClient` + `HISFactory`，MockHISClient 默认（SQLite） |

---

#### 阶段 C：Ingestion Pipeline（医疗知识库摄取）

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| C1 | 定义核心数据类型（Document/Chunk/ChunkRecord） | [x] | `src/core/types.py`，包含医疗元数据字段 |
| C2 | 文件完整性检查（SHA256） | [x] | `SQLiteIntegrityChecker`，增量摄取 |
| C3 | Loader 抽象基类与纯文本 Loader | [x] | 优先 `.txt`/`.md`，支持 FHIR 解析预留 |
| C4 | MedicalChunker（医疗语义切分） | [x] | 调用 `libs.splitter`，配置医疗分隔符 |
| C5 | Transform 基类 + ChunkRefiner | [x] | 规则去噪 + LLM 智能重组 |
| C6 | MetadataEnricher（疾病标签/权威等级） | [x] | 为 Chunk 注入医疗元数据 |
| C7 | ImageCaptioner（医疗图像描述） | [x] | 调用 Vision LLM 生成化验单/影像描述（依赖 B2） |
| C8 | DenseEncoder + SparseEncoder | [x] | 双路编码，支持差量计算 |
| C9 | BatchProcessor（批处理优化） | [x] | 批量调用 Embedding API |
| C10 | BM25Indexer（倒排索引构建） | [x] | 计算 IDF，持久化 |
| C11 | VectorUpserter（幂等 upsert） | [x] | 稳定 chunk_id 生成 |
| C12 | ImageStorage（图片存储 + SQLite 索引） | [x] | 支持 WAL 模式 |
| C13 | Pipeline 编排 | [x] | 串行执行，支持 `on_progress` 回调 |
| C14 | 脚本入口 ingest_medical.py | [x] | CLI 支持 `--path`、`--collection`、`--force` |

---

#### 阶段 D：核心工具箱实现（提前实现，供 Router 调用）

> **设计说明**：本阶段提前实现 Router 所需调用的具体工具，确保 Agent 大脑构建时已有可用的“武器”，避免全部硬 Mock。

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| D1 | RAG Engine 完整实现 | [ ] | QueryProcessor、HybridSearch、Reranker 集成（依赖 B3,B4,B6） |
| D2 | HIS Orchestrator 基础实现 | [ ] | DepartmentService、ScheduleService（依赖 B8） |
| D3 | Case Generator 基础实现 | [ ] | EntityExtractor、RecordBuilder、SchemaValidator |
| D4 | BookingService 框架（事务预留） | [ ] | 挂号服务框架，并发锁号逻辑后续细化 |

---

#### 阶段 E：Agent 认知核心（Planner + Memory）

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| E1 | IntentClassifier（意图识别） | [ ] | 问诊/挂号/科普/确认/红线拦截，规则 + LLM |
| E2 | StateManager（对话状态机） | [ ] | 状态转移图：症状收集→科室推荐→病历确认→挂号 |
| E3 | Router（工具路由） | [ ] | **根据意图和状态调度 D 阶段已实现的工具**（RAG/HIS/CaseGenerator） |
| E4 | WorkingMemory（短期工作记忆） | [ ] | 维护 `PatientState`（symptom_tree、message_history） |
| E5 | SemanticMemory（长期语义记忆） | [ ] | SQLite 患者档案，Upsert 更新 |
| E6 | EpisodicMemory（历史情景记忆） | [ ] | 向量检索 + SQLite 元数据 |
| E7 | MemoryFactory（记忆工厂） | [ ] | 支持配置切换后端 |

---

#### 阶段 F：API 网关与业务集成

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| F1 | FastAPI 应用入口（app.py） | [ ] | 注册路由、中间件、生命周期管理 |
| F2 | 会话管理路由（session.py） | [ ] | 创建/获取/删除会话，session_id 生成 |
| F3 | 对话接口（chat.py） | [ ] | POST /chat，WebSocket 支持 |
| F4 | 患者档案接口（patient.py） | [ ] | 查询/更新患者信息（脱敏） |
| F5 | 认证中间件（auth.py） | [ ] | JWT 验证，患者身份绑定 |
| F6 | 主链路联调 | [ ] | 模拟患者从“问诊→查号→挂号确认”全流程 |

---

#### 阶段 G：记忆系统完整实现

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| G1 | WorkingMemory 持久化（可选 Redis） | [ ] | 支持内存/Redis 切换 |
| G2 | SemanticMemory 完整 CRUD | [ ] | 支持按 patient_id 查询、合并更新 |
| G3 | EpisodicMemory 向量检索 | [ ] | 复诊时按 patient_id 过滤 + 相似度召回 |
| G4 | 会话结束时的记忆提炼 | [ ] | 调用 LLM 生成摘要，存入情景记忆 |
| G5 | 新会话时记忆注入 | [ ] | 自动加载长期档案 + 检索相似历史 |

---

#### 阶段 H：医疗安全基线与红线测试

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| H1 | 紧急症状关键词库 | [ ] | 胸痛放射、大出血、意识模糊等 |
| H2 | 红线拦截器（EmergencyInterceptor） | [ ] | 在 IntentClassifier 前置执行 |
| H3 | 越界建议阻断（PrescriptionRefusal） | [ ] | 拒绝开药/确诊请求，输出免责声明 |
| H4 | Reranker 阈值熔断 | [ ] | 最高分低于 0.7 时触发 Fallback |
| H5 | 幻觉防御（Faithfulness 校验） | [ ] | 生成病历后与原文对比 |
| H6 | 红线对抗测试集构建 | [ ] | `tests/fixtures/red_team_test_set.json` |
| H7 | 红线测试自动化 | [ ] | `pytest -m red_team` 回归验证 |

---

#### 阶段 I：HIS 业务闭环与并发保障

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| I1 | Mock HIS 数据库初始化 | [ ] | departments、doctors、schedules、appointments 表 |
| I2 | SQLite WAL 模式配置 | [ ] | `PRAGMA journal_mode=WAL`，timeout 设置 |
| I3 | BookingService 完整事务实现 | [ ] | 扣减号源 + 插入订单，原子操作 |
| I4 | 并发锁号测试 | [ ] | `asyncio.gather` 模拟 10 并发抢占同一号源 |
| I5 | 挂号完整流程集成测试 | [ ] | 选科室 → 选医生 → 选时间 → 锁号 → 返回凭证 |

---

#### 阶段 J：可观测性与 Dashboard

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| J1 | TraceContext 实现 | [ ] | trace_id 生成，阶段记录，finish 汇总 |
| J2 | 结构化日志（JSON Lines） | [ ] | `logs/traces.jsonl`、`logs/audit_logs.jsonl` |
| J3 | 在 Agent 链路打点 | [ ] | 意图识别、状态转移、工具调用各阶段 |
| J4 | 在 Ingestion 链路打点 | [ ] | load/split/transform/embed/upsert 各阶段 |
| J5 | Dashboard 基础架构（Streamlit） | [ ] | `app.py` 多页面导航 |
| J6 | 系统总览页（Overview） | [ ] | 组件配置、数据统计 |
| J7 | 知识库浏览器（Data Browser） | [ ] | 文档列表、Chunk 详情、图片预览 |
| J8 | 记忆查看器（Memory Viewer） | [ ] | 患者档案、历史就诊记录（脱敏） |
| J9 | 问诊追踪页（Query Traces） | [ ] | 历史列表、耗时瀑布图、工具调用链 |
| J10 | 知识库质量面板（Medical KB Quality） | [ ] | 检索命中率、Faithfulness 趋势 |
| J11 | 审计日志页（Audit Logs） | [ ] | 按患者 ID、操作类型筛选，决策溯源 |

---

#### 阶段 K：评估体系与双轨门禁

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| K1 | 黄金测试集构建（Golden Test Set） | [ ] | 医疗知识问答、症状到科室、病历生成、挂号场景 |
| K2 | RagasEvaluator 实现 | [ ] | Faithfulness、Answer Relevancy、Context Precision |
| K3 | CompositeEvaluator 实现 | [ ] | 多评估器并行，结果汇总 |
| K4 | EvalRunner 实现 | [ ] | 加载黄金测试集，输出指标报告 |
| K5 | LLM-as-Judge 幻觉检测 | [ ] | 使用强模型计算 Faithfulness，阈值 ≥ 0.95 |
| K6 | CI 自动化门禁 | [ ] | PR 阶段自动运行评估，低于阈值阻断 |
| K7 | Release 人工门禁 | [ ] | 提取低置信度 Edge Cases，人工签署 |
| K8 | 评估面板页面（Evaluation Panel） | [ ] | 指标趋势图、历史对比 |

---

#### 阶段 L：端到端验收与文档收口

| 任务编号 | 任务名称 | 状态 | 备注 |
|---------|---------|------|------|
| L1 | E2E：完整问诊流程 | [ ] | 从输入症状到生成病历 |
| L2 | E2E：复诊记忆唤醒流 | [ ] | 验证情景记忆检索 |
| L3 | E2E：急症红线拦截 | [ ] | 输入“胸痛放射至左肩”，验证强制拦截 |
| L4 | E2E：挂号完整闭环 | [ ] | 从科室选择到锁号成功 |
| L5 | E2E：隐私数据隔离 | [ ] | 多会话并发，验证数据隔离 |
| L6 | E2E：Dashboard 冒烟测试 | [ ] | 所有页面可加载、不抛异常 |
| L7 | 完善 README | [ ] | 快速开始、配置说明、API 文档、Dashboard 使用 |
| L8 | 全链路验收 | [ ] | `pytest` 全绿 + 手动走通完整流程 |

---

### 📈 总体进度

| 阶段 | 总任务数 | 已完成 | 进度 |
|------|---------|--------|------|
| 阶段 A | 3 | 0 | 0% |
| 阶段 B | 8 | 0 | 0% |
| 阶段 C | 14 | 0 | 0% |
| 阶段 D | 5 | 0 | 0% |
| 阶段 E | 7 | 0 | 0% |
| 阶段 F | 6 | 0 | 0% |
| 阶段 G | 5 | 0 | 0% |
| 阶段 H | 7 | 0 | 0% |
| 阶段 I | 5 | 0 | 0% |
| 阶段 J | 11 | 0 | 0% |
| 阶段 K | 8 | 0 | 0% |
| 阶段 L | 8 | 0 | 0% |
| **总计** | **87** | **0** | **0%** |

---

### 交付里程碑

| 里程碑 | 达成条件 | 关键依赖 |
|--------|---------|---------|
| **M1（阶段 A+B）** | 工程骨架 + 可插拔抽象层就绪，后续实现可并行推进 | 无 |
| **M2（阶段 C）** | 离线医疗知识摄取链路可用，能构建本地索引 | B |
| **M3（阶段 D）** | 核心工具箱（RAG/HIS/Case/Vision）实现完成，Router 有“武器”可调用 | B |
| **M4（阶段 E+F）** | Agent 认知核心 + API 网关可用，可通过 HTTP 进行问诊对话 | D |
| **M5（阶段 G+H+I）** | 记忆系统完整 + 医疗安全基线 + HIS 并发锁号，红线测试通过 | E, D |
| **M6（阶段 J+K）** | Dashboard 医疗专用面板 + 双轨评估门禁就绪 | A, F |
| **M7（阶段 L）** | E2E 验收通过 + 文档完善，形成可交付的医疗导诊 Agent | A-K |

---
## 各阶段详细任务说明

> **说明**：本章节严格对齐项目排期中的阶段划分，为每个子任务提供详细的实现目标、修改文件、验收标准与测试方法，确保开发过程可追踪、可验收。

---

### 阶段 A：工程骨架与测试基座

#### A1：初始化目录树与最小可运行入口
- **目标**：在 repo 根目录创建第 5.2 节所述目录骨架与空模块文件，确保所有包可导入。
- **修改文件**：
  - `main.py`（FastAPI 入口占位）
  - `pyproject.toml`（项目配置）
  - `README.md`
  - `.gitignore`
  - `src/**/__init__.py`（按目录树补齐）
  - `config/settings.yaml`（最小配置）
  - `config/prompts/medical_knowledge.txt`、`case_generation.txt`、`symptom_elicitation.txt`、`image_captioning.txt`、`rerank.txt`（占位文件）
- **实现类/函数**：无（仅骨架）
- **验收标准**：
  - 目录结构与 5.2 节一致
  - 所有 `__init__.py` 存在，`python -c "import src"` 成功
  - 能读取 `config/settings.yaml`（即使内容为空）
- **测试方法**：运行 `python -m compileall src`

#### A2：引入 pytest 并建立测试目录约定
- **目标**：建立 `tests/unit|integration|e2e|fixtures` 目录与 pytest 运行基座。
- **修改文件**：
  - `pyproject.toml`（添加 pytest 配置）
  - `tests/unit/test_smoke_imports.py`
  - `tests/fixtures/sample_documents/`（放置一个样例 `.txt` 文件）
- **实现类/函数**：无
- **验收标准**：
  - `pytest -q` 可运行并通过（至少一个冒烟测试）
  - 测试目录结构符合约定
- **测试方法**：`pytest -q tests/unit/test_smoke_imports.py`

#### A3：配置加载与校验（Settings）
- **目标**：实现读取 `config/settings.yaml` 的配置加载器，并在启动时校验关键字段存在。
- **修改文件**：
  - `main.py`（启动时调用 `load_settings()`）
  - `src/core/settings.py`（新增）
  - `src/observability/logger.py`（占位）
  - `config/settings.yaml`（补齐字段：llm, embedding, vector_store, retrieval, memory, his, api, observability）
  - `tests/unit/test_config_loading.py`
- **实现类/函数**：
  - `Settings`（dataclass / pydantic）
  - `load_settings(path: str) -> Settings`
  - `validate_settings(settings: Settings) -> None`
- **验收标准**：
  - 成功加载配置，缺失必填字段时抛出明确错误
  - 环境变量可覆盖配置项
- **测试方法**：`pytest -q tests/unit/test_config_loading.py`

---

### 阶段 B：Libs 可插拔层

#### B1：LLM 抽象接口与工厂
- **目标**：定义 `BaseLLM` 与 `LLMFactory`，支持 Qwen、OpenAI、Ollama 等 Provider。
- **修改文件**：
  - `src/libs/llm/base_llm.py`
  - `src/libs/llm/llm_factory.py`
  - `src/libs/llm/qwen_llm.py`
  - `src/libs/llm/openai_llm.py`
  - `src/libs/llm/ollama_llm.py`
  - `tests/unit/test_llm_factory.py`
- **实现类/函数**：
  - `BaseLLM.chat(messages: List[Dict]) -> str`
  - `LLMFactory.create(settings) -> BaseLLM`
- **验收标准**：
  - Factory 根据配置正确创建对应实现
  - 单元测试中使用 Fake 验证路由逻辑
- **测试方法**：`pytest -q tests/unit/test_llm_factory.py`

#### B2：Vision LLM 抽象接口与工厂
- **目标**：定义 `BaseVisionLLM`，支持 Qwen-VL、GPT-4V 等。
- **修改文件**：
  - `src/libs/llm/base_vision_llm.py`
  - `src/libs/llm/qwen_vl_llm.py`
  - `src/libs/llm/llm_factory.py`（扩展 `create_vision_llm`）
  - `tests/unit/test_vision_llm_factory.py`
- **实现类/函数**：
  - `BaseVisionLLM.chat_with_image(text: str, image: Union[str, bytes]) -> str`
- **验收标准**：
  - 工厂正确创建 Vision LLM
  - 支持图片路径或 base64 输入
- **测试方法**：`pytest -q tests/unit/test_vision_llm_factory.py`

#### B3：Embedding 抽象接口与工厂
- **目标**：定义 `BaseEmbedding`，支持通义、OpenAI、Ollama。
- **修改文件**：
  - `src/libs/embedding/base_embedding.py`
  - `src/libs/embedding/embedding_factory.py`
  - `src/libs/embedding/dashscope_embedding.py`
  - `src/libs/embedding/openai_embedding.py`
  - `src/libs/embedding/ollama_embedding.py`
  - `tests/unit/test_embedding_factory.py`
- **实现类/函数**：
  - `BaseEmbedding.embed(texts: List[str]) -> List[List[float]]`
- **验收标准**：
  - 批量 embed 返回向量维度一致
- **测试方法**：`pytest -q tests/unit/test_embedding_factory.py`

#### B4：VectorStore 抽象接口与工厂
- **目标**：定义 `BaseVectorStore`，支持 Chroma、Qdrant。
- **修改文件**：
  - `src/libs/vector_store/base_vector_store.py`
  - `src/libs/vector_store/vector_store_factory.py`
  - `src/libs/vector_store/chroma_store.py`
  - `tests/unit/test_vector_store_contract.py`
- **实现类/函数**：
  - `BaseVectorStore.upsert(records: List[Dict])`
  - `BaseVectorStore.query(vector, top_k, filters) -> List[Dict]`
  - `BaseVectorStore.get_by_ids(ids) -> List[Dict]`
  - `BaseVectorStore.delete_by_metadata(filter)`
- **验收标准**：契约测试确保接口输入输出 shape 稳定。
- **测试方法**：`pytest -q tests/unit/test_vector_store_contract.py`

#### B5：Splitter 抽象接口与工厂
- **目标**：定义 `BaseSplitter`，支持 Recursive、Semantic 等策略。
- **修改文件**：
  - `src/libs/splitter/base_splitter.py`
  - `src/libs/splitter/splitter_factory.py`
  - `src/libs/splitter/recursive_splitter.py`
  - `tests/unit/test_splitter_factory.py`
- **实现类/函数**：
  - `BaseSplitter.split_text(text: str) -> List[str]`
- **验收标准**：Factory 根据配置返回正确 splitter 实例。
- **测试方法**：`pytest -q tests/unit/test_splitter_factory.py`

#### B6：Reranker 抽象接口与工厂
- **目标**：定义 `BaseReranker`，支持 BGE、LLM、None。
- **修改文件**：
  - `src/libs/reranker/base_reranker.py`
  - `src/libs/reranker/reranker_factory.py`
  - `src/libs/reranker/bge_reranker.py`
  - `src/libs/reranker/llm_reranker.py`
  - `src/libs/reranker/none_reranker.py`
  - `tests/unit/test_reranker_factory.py`
- **实现类/函数**：
  - `BaseReranker.rerank(query: str, candidates: List[Dict]) -> List[Dict]`
- **验收标准**：BGE 模型打分可 mock；None 模式保持原序。
- **测试方法**：`pytest -q tests/unit/test_reranker_factory.py`

#### B7：Memory 抽象接口与工厂
- **目标**：定义 `BaseWorkingMemory`、`BaseSemanticMemory`、`BaseEpisodicMemory` 及其工厂。
- **修改文件**：
  - `src/libs/memory/base_memory.py`
  - `src/libs/memory/memory_factory.py`
  - `src/libs/memory/sqlite_memory.py`（长期档案）
  - `src/libs/memory/chroma_memory.py`（情景记忆）
  - `tests/unit/test_memory_factory.py`
- **实现类/函数**：
  - `BaseSemanticMemory.get(patient_id) -> Dict`、`upsert(patient_id, data)`
  - `BaseEpisodicMemory.add(patient_id, summary, metadata)`、`search(patient_id, query_vector, top_k)`
- **验收标准**：工厂可创建默认实现，单元测试验证 CRUD。
- **测试方法**：`pytest -q tests/unit/test_memory_factory.py`

#### B8：HIS 抽象接口与工厂
- **目标**：定义 `BaseHISClient`，支持 Mock 和 HTTP 实现。
- **修改文件**：
  - `src/libs/his/base_his.py`
  - `src/libs/his/his_factory.py`
  - `src/libs/his/mock_his.py`
  - `tests/unit/test_his_factory.py`
- **实现类/函数**：
  - `BaseHISClient.query_departments(keyword) -> List[Dept]`
  - `BaseHISClient.query_doctor_schedule(dept_name, date) -> List[Schedule]`
  - `BaseHISClient.book_appointment(patient_id, schedule_id) -> AppointmentResult`
- **验收标准**：Mock 实现使用 SQLite，支持 WAL 模式。
- **测试方法**：`pytest -q tests/unit/test_his_factory.py`


#### B9：Vision Processor 基础组件
- **目标**：实现图片预处理、Vision LLM 调用封装、异常指标提取的基础接口。
- **修改文件**：
  - `src/libs/vision/base_vision_processor.py`
  - `src/libs/vision/image_preprocessor.py`
  - `src/libs/vision/vision_llm_client.py`
  - `src/libs/vision/indicator_extractor.py`
  - `tests/unit/test_vision_processor.py`
- **实现类/函数**：
  - `ImagePreprocessor.compress(image_bytes, max_size) -> bytes`
  - `VisionLLMClient.describe(image, prompt) -> str`
  - `IndicatorExtractor.extract(description) -> List[str]`
- **验收标准**：
  - 支持图片压缩至指定尺寸
  - Vision LLM 调用支持 Qwen-VL/GPT-4V
  - 异常指标提取仅输出超标项目，避免上下文溢出
- **测试方法**：`pytest -q tests/unit/test_vision_processor.py`
---

### 阶段 C：Ingestion Pipeline（医疗知识库摄取）

#### C1：定义核心数据类型
- **目标**：定义全链路共用的 `Document`、`Chunk`、`ChunkRecord` 等类型。
- **修改文件**：
  - `src/core/types.py`
  - `tests/unit/test_core_types.py`
- **实现类/函数**：
  - `Document(id, text, metadata)`
  - `Chunk(id, text, metadata, source_ref, chunk_index)`
  - `ChunkRecord(...)`（含向量字段）
- **验收标准**：类型可序列化，元数据包含医疗专用字段（如 `authority_level`）。
- **测试方法**：`pytest -q tests/unit/test_core_types.py`

#### C2：文件完整性检查（SHA256）
- **目标**：实现基于 SQLite 的增量摄取检查。
- **修改文件**：
  - `src/libs/loader/file_integrity.py`
  - `tests/unit/test_file_integrity.py`
- **实现类/函数**：
  - `SQLiteIntegrityChecker.compute_sha256(path) -> str`
  - `should_skip(file_hash) -> bool`
  - `mark_success(file_hash, file_path, ...)`
- **验收标准**：同一文件标记成功后再调用返回 True；支持 WAL。
- **测试方法**：`pytest -q tests/unit/test_file_integrity.py`

#### C3：Loader 抽象基类与纯文本 Loader
- **目标**：实现 `BaseLoader` 及纯文本 Loader（优先 `.txt`/`.md`）。
- **修改文件**：
  - `src/libs/loader/base_loader.py`
  - `src/libs/loader/text_loader.py`
  - `tests/unit/test_text_loader.py`
- **实现类/函数**：
  - `BaseLoader.load(path) -> Document`
- **验收标准**：能读取文本文件，提取元数据（文件名、路径、标题）。
- **测试方法**：`pytest -q tests/unit/test_text_loader.py`

#### C4：MedicalChunker（医疗语义切分）
- **目标**：实现 `MedicalChunker`，调用 libs.splitter，并配置医疗分隔符。
- **修改文件**：
  - `src/ingestion/chunking/medical_chunker.py`
  - `tests/unit/test_medical_chunker.py`
- **实现类/函数**：
  - `MedicalChunker.split_document(document: Document) -> List[Chunk]`
- **验收标准**：确保“疾病概述”“临床表现”“治疗原则”等不被切分；Chunk 携带 `chunk_index`、`source_ref`。
- **测试方法**：`pytest -q tests/unit/test_medical_chunker.py`

#### C5：Transform 基类 + ChunkRefiner
- **目标**：定义 `BaseTransform`，实现 `ChunkRefiner`（规则去噪 + LLM 增强）。
- **修改文件**：
  - `src/ingestion/transform/base_transform.py`
  - `src/ingestion/transform/chunk_refiner.py`
  - `config/prompts/chunk_refinement.txt`
  - `tests/fixtures/noisy_chunks.json`
  - `tests/unit/test_chunk_refiner.py`
  - `tests/integration/test_chunk_refiner_llm.py`
- **实现类/函数**：
  - `BaseTransform.transform(chunks, trace) -> List[Chunk]`
  - `ChunkRefiner._rule_based_refine(text) -> str`
  - `ChunkRefiner._llm_refine(text, trace) -> str | None`
- **验收标准**：规则去噪有效；LLM 失败时回退规则；集成测试使用真实 LLM 验证效果。
- **测试方法**：`pytest -q tests/unit/test_chunk_refiner.py`；`pytest tests/integration/test_chunk_refiner_llm.py`（可选）

#### C6：MetadataEnricher（疾病标签/权威等级）
- **目标**：为 Chunk 注入医疗元数据。
- **修改文件**：
  - `src/ingestion/transform/metadata_enricher.py`
  - `tests/unit/test_metadata_enricher.py`
- **实现类/函数**：
  - `MetadataEnricher.transform(chunks, trace) -> List[Chunk]`
- **验收标准**：LLM 增强时生成疾病标签；降级时使用规则。
- **测试方法**：`pytest -q tests/unit/test_metadata_enricher.py`

#### C7：ImageCaptioner（医疗图像描述）
- **目标**：为 Chunk 中引用的图片生成描述。
- **修改文件**：
  - `src/ingestion/transform/image_captioner.py`
  - `config/prompts/image_captioning.txt`
  - `tests/unit/test_image_captioner.py`
- **实现类/函数**：
  - `ImageCaptioner.transform(chunks, trace) -> List[Chunk]`
- **验收标准**：存在 `image_refs` 时调用 Vision LLM 生成描述，失败时标记 `has_unprocessed_images`。
- **测试方法**：`pytest -q tests/unit/test_image_captioner.py`

#### C8：DenseEncoder + SparseEncoder
- **目标**：实现双路编码。
- **修改文件**：
  - `src/ingestion/embedding/dense_encoder.py`
  - `src/ingestion/embedding/sparse_encoder.py`
  - `tests/unit/test_dense_encoder.py`
  - `tests/unit/test_sparse_encoder.py`
- **实现类/函数**：
  - `DenseEncoder.encode(chunks) -> List[List[float]]`
  - `SparseEncoder.encode(chunks) -> List[Dict]`（词频统计）
- **验收标准**：输出向量数量与 chunks 一致，稀疏结构可用于 BM25。
- **测试方法**：`pytest -q tests/unit/test_dense_encoder.py`

#### C9：BatchProcessor（批处理优化）
- **目标**：批量调用 Embedding API。
- **修改文件**：
  - `src/ingestion/embedding/batch_processor.py`
  - `tests/unit/test_batch_processor.py`
- **实现类/函数**：
  - `BatchProcessor.process(items, batch_size, processor_func) -> List`
- **验收标准**：正确分批，顺序不变。
- **测试方法**：`pytest -q tests/unit/test_batch_processor.py`

#### C10：BM25Indexer（倒排索引构建）
- **目标**：构建 BM25 倒排索引并持久化。
- **修改文件**：
  - `src/ingestion/storage/bm25_indexer.py`
  - `tests/unit/test_bm25_indexer.py`
- **实现类/函数**：
  - `BM25Indexer.build(chunks)`
  - `BM25Indexer.save(path)`
  - `BM25Indexer.load(path)`
- **验收标准**：对已知语料能计算稳定 IDF，查询返回正确 top_ids。
- **测试方法**：`pytest -q tests/unit/test_bm25_indexer.py`

#### C11：VectorUpserter（幂等 upsert）
- **目标**：将 Dense 向量写入向量库，保证幂等。
- **修改文件**：
  - `src/ingestion/storage/vector_upserter.py`
  - `tests/unit/test_vector_upserter.py`
- **实现类/函数**：
  - `VectorUpserter.upsert(chunks, vectors, metadata)`
- **验收标准**：相同 chunk_id 重复写入不产生重复记录。
- **测试方法**：`pytest -q tests/unit/test_vector_upserter.py`

#### C12：ImageStorage（图片存储 + SQLite 索引）
- **目标**：保存图片到本地，建立 SQLite 索引。
- **修改文件**：
  - `src/ingestion/storage/image_storage.py`
  - `tests/unit/test_image_storage.py`
- **实现类/函数**：
  - `ImageStorage.save(image_id, image_data, collection) -> path`
  - `ImageStorage.get_path(image_id) -> str`
- **验收标准**：保存后文件存在，索引可查询。
- **测试方法**：`pytest -q tests/unit/test_image_storage.py`

#### C13：Pipeline 编排
- **目标**：串行执行摄取流程，支持进度回调。
- **修改文件**：
  - `src/ingestion/pipeline.py`
  - `tests/integration/test_ingestion_pipeline.py`
- **实现类/函数**：
  - `IngestionPipeline.run(source_path, collection, on_progress) -> IngestionResult`
- **验收标准**：对样例文档能完整跑通，输出向量库和 BM25 索引。
- **测试方法**：`pytest -q tests/integration/test_ingestion_pipeline.py`

#### C14：脚本入口 ingest_medical.py
- **目标**：提供命令行摄取脚本。
- **修改文件**：
  - `scripts/ingest_medical.py`
  - `tests/e2e/test_data_ingestion.py`
- **验收标准**：`python scripts/ingest_medical.py --path ./data/medical_knowledge` 可执行，重复运行跳过未变更文件。
- **测试方法**：`pytest -q tests/e2e/test_data_ingestion.py`

---

### 阶段 D：核心工具箱实现

#### D1：RAG Engine 完整实现
- **目标**：实现 `QueryProcessor`、`HybridSearch`、`Reranker` 的集成。
- **修改文件**：
  - `src/tools/rag_engine/query_processor.py`
  - `src/tools/rag_engine/hybrid_search.py`
  - `src/tools/rag_engine/reranker.py`
  - `tests/unit/test_rag_engine.py`
- **实现类/函数**：
  - `QueryProcessor.process(query) -> ProcessedQuery`
  - `HybridSearch.search(query, top_k, filters) -> List[RetrievalResult]`
- > **验收标准**：
    > - 支持口语化→医学术语映射
    > - RRF 融合算法正确实现
    > - Cross-Encoder 精排打分（使用 BGE reranker）返回相关性分数
- **测试方法**：`pytest -q tests/unit/test_rag_engine.py`

#### D2：HIS Orchestrator 基础实现
- **目标**：实现科室和排班查询。
- **修改文件**：
  - `src/tools/his_orchestrator/dept_service.py`
  - `src/tools/his_orchestrator/schedule_service.py`
  - `tests/unit/test_his_services.py`
- **实现类/函数**：
  - `DepartmentService.query(keyword) -> List[Dept]`
  - `ScheduleService.query(dept_name, date) -> List[Schedule]`
- **验收标准**：按关键词匹配科室；按日期/医生过滤排班。
- **测试方法**：`pytest -q tests/unit/test_his_services.py`

#### D3：Case Generator 基础实现
- **目标**：实现实体抽取、病历构建、Schema 校验。
- **修改文件**：
  - `src/tools/case_generator/entity_extractor.py`
  - `src/tools/case_generator/record_builder.py`
  - `src/tools/case_generator/schema_validator.py`
  - `tests/unit/test_case_generator.py`
- **实现类/函数**：
  - `EntityExtractor.extract(conversation) -> Dict`
  - `RecordBuilder.build(entities, memory) -> MedicalRecord`
  - `SchemaValidator.validate(record) -> bool`
- **验收标准**：输出 JSON 符合预设 schema；必填字段非空。
- **测试方法**：`pytest -q tests/unit/test_case_generator.py`


#### D4：BookingService 框架（事务预留）
- **目标**：实现挂号服务的基础框架，预留并发锁号接口。
- **修改文件**：
  - `src/tools/his_orchestrator/booking_service.py`
  - `tests/unit/test_booking_service.py`
- **实现类/函数**：
  - `BookingService.book(patient_id, schedule_id) -> AppointmentResult`
- **验收标准**：目前可 mock 返回成功，后续细化事务逻辑。
- **测试方法**：`pytest -q tests/unit/test_booking_service.py`

---

### 阶段 E：Agent 认知核心

#### E1：IntentClassifier（意图识别）
- **目标**：识别问诊/挂号/科普/确认/红线拦截五类意图。
- **修改文件**：
  - `src/agent/planner/intent_classifier.py`
  - `tests/unit/test_intent_classifier.py`
- **实现类/函数**：
  - `IntentClassifier.classify(user_input, memory) -> Intent`
- **验收标准**：紧急关键词优先；规则 + LLM 分类。
- **测试方法**：`pytest -q tests/unit/test_intent_classifier.py`

#### E2：StateManager（对话状态机）
- **目标**：实现状态转移图。
- **修改文件**：
  - `src/agent/planner/state_manager.py`
  - `tests/unit/test_state_manager.py`
- **实现类/函数**：
  - `StateManager.transition(current_state, intent, context) -> new_state`
- **验收标准**：状态转移符合业务规则（症状收集→科室推荐→病历确认→挂号）。
- **测试方法**：`pytest -q tests/unit/test_state_manager.py`

#### E3：Router（工具路由）
- **目标**：根据意图和状态调度底层工具。
- **修改文件**：
  - `src/agent/planner/router.py`
  - `tests/unit/test_router.py`
- **实现类/函数**：
  - `Router.route(intent, state, memory) -> ToolCall`
- **验收标准**：科普意图→RAG；挂号意图且信息充分→CaseGenerator；科室咨询→HIS。
- **测试方法**：`pytest -q tests/unit/test_router.py`


#### E4：WorkingMemory（短期工作记忆）
- **目标**：维护当前会话的 `PatientState`，并在每次交互后触发长期档案的实时更新。
- **修改文件**：
  - `src/agent/memory/working_memory.py`
  - `tests/unit/test_working_memory.py`
- **实现类/函数**：
  - `WorkingMemory.update(session_id, user_input, response) -> PatientState`
  - `WorkingMemory._trigger_semantic_update(patient_id, new_entities)`
- **验收标准**（新增）：
  - 每次对话轮次后，后台调用 `EntityExtractor` 抽取新增实体（如过敏史、既往史）
  - 若检测到新增的长期档案信息（如“我对青霉素过敏”），立即调用 `SemanticMemory.upsert` 更新患者档案
  - 更新操作在后台异步执行，不阻塞主对话流程
  - 测试用例：模拟对话中途告知过敏史，验证档案被实时更新
- **测试方法**：`pytest -q tests/unit/test_working_memory.py`

#### E5：SemanticMemory（长期语义记忆）
- **目标**：读写患者健康档案。
- **修改文件**：
  - `src/agent/memory/semantic_memory.py`
  - `tests/unit/test_semantic_memory.py`
- **实现类/函数**：
  - `SemanticMemory.get(patient_id) -> PatientProfile`
  - `SemanticMemory.upsert(patient_id, profile)`
- **验收标准**：Upsert 合并更新，不产生脏数据。
- **测试方法**：`pytest -q tests/unit/test_semantic_memory.py`

#### E6：EpisodicMemory（历史情景记忆）
- **目标**：存储历史就诊摘要，支持相似检索。
- **修改文件**：
  - `src/agent/memory/episodic_memory.py`
  - `tests/unit/test_episodic_memory.py`
- **实现类/函数**：
  - `EpisodicMemory.add(patient_id, summary, metadata)`
  - `EpisodicMemory.search(patient_id, query_vector, top_k) -> List[Episode]`
- **验收标准**：复诊时能召回相似历史。
- **测试方法**：`pytest -q tests/unit/test_episodic_memory.py`

#### E7：MemoryFactory（记忆工厂）
- **目标**：根据配置创建记忆实例。
- **修改文件**：
  - `src/agent/memory/memory_factory.py`
  - `tests/unit/test_memory_factory.py`
- **实现类/函数**：
  - `MemoryFactory.create_working(settings)`
  - `MemoryFactory.create_semantic(settings)`
  - `MemoryFactory.create_episodic(settings)`
- **验收标准**：可切换后端（如 Redis）。
- **测试方法**：`pytest -q tests/unit/test_memory_factory.py`

---

### 阶段 F：API 网关与业务集成

#### F1：FastAPI 应用入口
- **目标**：创建 FastAPI 应用，注册路由、中间件。
- **修改文件**：
  - `src/api/app.py`
  - `main.py`
  - `tests/unit/test_app.py`
- **实现类/函数**：
  - `create_app() -> FastAPI`
- **验收标准**：应用可启动，`/docs` 可访问。
- **测试方法**：`pytest -q tests/unit/test_app.py`

#### F2：会话管理路由
- **目标**：提供会话创建、获取、删除接口。
- **修改文件**：
  - `src/api/routers/session.py`
  - `tests/unit/test_session_routes.py`
- **实现类/函数**：
  - `POST /sessions` 创建会话
  - `GET /sessions/{session_id}` 获取会话信息
- **验收标准**：会话 ID 唯一，支持超时管理。
- **测试方法**：`pytest -q tests/unit/test_session_routes.py`

#### F3：对话接口
- **目标**：实现 POST `/chat` 和 WebSocket 接口。
- **修改文件**：
  - `src/api/routers/chat.py`
  - `tests/unit/test_chat_routes.py`
- **实现类/函数**：
  - `POST /chat` 同步对话
  - `WebSocket /ws` 流式对话
- **验收标准**：支持 SSE 流式输出，整合 Agent 调用。
- **测试方法**：`pytest -q tests/unit/test_chat_routes.py`

#### F4：患者档案接口
- **目标**：提供患者信息查询/更新接口（脱敏）。
- **修改文件**：
  - `src/api/routers/patient.py`
  - `tests/unit/test_patient_routes.py`
- **实现类/函数**：
  - `GET /patients/{patient_id}` 返回脱敏信息
  - `PUT /patients/{patient_id}` 更新档案
- **验收标准**：敏感字段脱敏；权限校验。
- **测试方法**：`pytest -q tests/unit/test_patient_routes.py`

#### F5：认证中间件
- **目标**：JWT 验证，绑定患者身份。
- **修改文件**：
  - `src/api/middleware/auth.py`
  - `tests/unit/test_auth_middleware.py`
- **实现类/函数**：
  - `AuthMiddleware`，依赖注入 `get_current_patient`
- **验收标准**：未认证请求返回 401。
- **测试方法**：`pytest -q tests/unit/test_auth_middleware.py`

#### F6：主链路联调
- **目标**：模拟患者从问诊到挂号的完整流程。
- **修改文件**：
  - `tests/e2e/test_main_flow.py`
- **验收标准**：能通过 API 完成“症状收集→病历生成→科室查询→挂号”闭环。
- **测试方法**：`pytest -q tests/e2e/test_main_flow.py`

---

### 阶段 G：记忆系统完整实现

#### G1：WorkingMemory 持久化（Redis 可选）
- **目标**：支持将短期记忆持久化到 Redis。
- **修改文件**：
  - `src/agent/memory/working_memory.py`（增加 Redis 实现）
  - `tests/unit/test_working_memory_redis.py`
- **验收标准**：配置切换后正常工作。
- **测试方法**：`pytest -q tests/unit/test_working_memory_redis.py`

#### G2：SemanticMemory 完整 CRUD
- **目标**：实现合并更新、历史版本查询等。
- **修改文件**：
  - `src/agent/memory/semantic_memory.py`（扩展）
  - `tests/unit/test_semantic_memory_crud.py`
- **验收标准**：多次更新后字段合并正确。
- **测试方法**：`pytest -q tests/unit/test_semantic_memory_crud.py`

#### G3：EpisodicMemory 向量检索
- **目标**：完善情景记忆的向量检索能力。
- **修改文件**：
  - `src/agent/memory/episodic_memory.py`（完善 search 方法）
  - `tests/unit/test_episodic_memory_search.py`
- **验收标准**：按 patient_id 预过滤后，相似度排序。
- **测试方法**：`pytest -q tests/unit/test_episodic_memory_search.py`

#### G4：会话结束时的记忆提炼
- **目标**：调用 LLM 生成摘要，存入情景记忆。
- **修改文件**：
  - `src/agent/memory/memory_consolidator.py`
  - `tests/unit/test_memory_consolidator.py`
- **实现类/函数**：
  - `MemoryConsolidator.consolidate(session_id, conversation, working_memory)`
- **验收标准**：会话结束后自动触发，摘要非空。
- **测试方法**：`pytest -q tests/unit/test_memory_consolidator.py`

#### G5：新会话时记忆注入
- **目标**：自动加载长期档案和相似情景。
- **修改文件**：
  - `src/agent/memory/memory_manager.py`
  - `tests/unit/test_memory_manager.py`
- **实现类/函数**：
  - `MemoryManager.load_context(patient_id, current_query) -> str`
- **验收标准**：注入的上下文包含既往史、相似病情。
- **测试方法**：`pytest -q tests/unit/test_memory_manager.py`

---

### 阶段 H：医疗安全基线与红线测试

#### H1：紧急症状关键词库
- **目标**：构建危急重症关键词库。
- **修改文件**：
  - `config/emergency_keywords.json`
  - `src/agent/planner/emergency_interceptor.py`（引入）
  - `tests/unit/test_emergency_keywords.py`
- **验收标准**：关键词列表覆盖常见急症。
- **测试方法**：`pytest -q tests/unit/test_emergency_keywords.py`

#### H2：红线拦截器
- **目标**：在意图识别前检测紧急症状并拦截。
- **修改文件**：
  - `src/agent/planner/emergency_interceptor.py`
  - `tests/unit/test_emergency_interceptor.py`
- **实现类/函数**：
  - `EmergencyInterceptor.intercept(user_input) -> Optional[str]`
- **验收标准**：输入“胸痛放射至左肩”直接返回急救指令。
- **测试方法**：`pytest -q tests/unit/test_emergency_interceptor.py`

#### H3：越界建议阻断
- **目标**：拒绝开药、确诊等请求。
- **修改文件**：
  - `src/agent/planner/prescription_refusal.py`
  - `tests/unit/test_prescription_refusal.py`
- **实现类/函数**：
  - `PrescriptionRefusal.refuse(intent, user_input) -> Optional[str]`
- **验收标准**：输入“给我开点头孢”返回免责声明。
- **测试方法**：`pytest -q tests/unit/test_prescription_refusal.py`

#### H4：Reranker 安全熔断
- **目标**：实现医疗安全级别的硬性 Fallback 逻辑。
- **修改文件**：
  - `src/tools/rag_engine/safety_guard.py`
  - `tests/unit/test_safety_guard.py`
- **实现类/函数**：
  - `SafetyGuard.check(rerank_scores, threshold=0.7) -> bool`
  - 若最高分低于阈值，抛出 `MedicalKnowledgeInsufficientError`
- **验收标准**：
  - 最高分 < 0.7 时，直接触发 Fallback 回复：“抱歉，超出系统医学知识库范围，建议尽快线下就诊”
  - 禁止 LLM 根据自身参数编造答案
  - 记录 `safety_guard_triggered` 到 trace
- **测试方法**：`pytest -q tests/unit/test_safety_guard.py`

#### H5：幻觉防御（Faithfulness 校验）
- **目标**：生成病历后与原文对比，检测幻觉。
- **修改文件**：
  - `src/tools/case_generator/hallucination_detector.py`
  - `tests/unit/test_hallucination_detector.py`
- **实现类/函数**：
  - `HallucinationDetector.check(record, conversation) -> bool`
- **验收标准**：检测到幻觉时标记拒绝。
- **测试方法**：`pytest -q tests/unit/test_hallucination_detector.py`

#### H6：红线对抗测试集构建
- **目标**：建立红线对抗测试集 JSON。
- **修改文件**：
  - `tests/fixtures/red_team_test_set.json`
- **验收标准**：包含至少 10 个红线场景（急症、越界等）。
- **测试方法**：手动审核。

#### H7：红线测试自动化
- **目标**：使用 pytest marker 运行红线测试。
- **修改文件**：
  - `tests/e2e/test_red_team.py`
- **验收标准**：`pytest -m red_team` 通过所有红线测试。
- **测试方法**：`pytest -m red_team`

---

### 阶段 I：HIS 业务闭环与并发保障

#### I1：Mock HIS 数据库初始化
- **目标**：创建科室、医生、排班、挂号表。
- **修改文件**：
  - `src/libs/his/mock_his.py`（数据库初始化）
  - `scripts/seed_his.py`
- **验收标准**：表结构完整，预置数据可查询。
- **测试方法**：手动运行 `python scripts/seed_his.py`。

#### I2：SQLite WAL 模式配置
- **目标**：确保 HIS 数据库连接启用 WAL 模式。
- **修改文件**：
  - `src/libs/his/mock_his.py`（在连接时执行 `PRAGMA journal_mode=WAL`）
  - `tests/unit/test_his_wal.py`
- **验收标准**：并发测试时不出现 `database is locked`。
- **测试方法**：`pytest -q tests/unit/test_his_wal.py`

#### I3：BookingService 完整事务实现
- **目标**：实现扣减号源+插入订单的原子操作。
- **修改文件**：
  - `src/tools/his_orchestrator/booking_service.py`
  - `tests/unit/test_booking_service_transaction.py`
- **实现类/函数**：
  - `BookingService.book(patient_id, schedule_id) -> AppointmentResult`
- **验收标准**：使用数据库事务，并发时保证一致。
- **测试方法**：`pytest -q tests/unit/test_booking_service_transaction.py`

#### I4：并发锁号测试
- **目标**：模拟多并发抢占同一号源。
- **修改文件**：
  - `tests/unit/test_booking_concurrency.py`
- **验收标准**：仅一个成功，其余返回号源已满。
- **测试方法**：`pytest -q tests/unit/test_booking_concurrency.py`

#### I5：挂号完整流程集成测试
- **目标**：测试从科室选择到锁号成功。
- **修改文件**：
  - `tests/integration/test_booking_flow.py`
- **验收标准**：通过 HTTP 调用完成挂号全流程。
- **测试方法**：`pytest -q tests/integration/test_booking_flow.py`

---

### 阶段 J：可观测性与 Dashboard

#### J1：TraceContext 实现
- **目标**：实现全链路追踪上下文。
- **修改文件**：
  - `src/observability/trace/trace_context.py`
  - `tests/unit/test_trace_context.py`
- **实现类/函数**：
  - `TraceContext.__init__(trace_type)`
  - `record_stage(name, data)`
  - `finish()`
  - `to_dict()`
- **验收标准**：可记录各阶段耗时，输出 JSON。
- **测试方法**：`pytest -q tests/unit/test_trace_context.py`

#### J2：结构化日志（JSON Lines）
- **目标**：将 trace 写入 `logs/traces.jsonl`。
- **修改文件**：
  - `src/observability/logger.py`
  - `tests/unit/test_jsonl_logger.py`
- **实现类/函数**：
  - `JSONFormatter`
  - `write_trace(trace_dict)`
- **验收标准**：文件每行一个合法 JSON。
- **测试方法**：`pytest -q tests/unit/test_jsonl_logger.py`

#### J3：在 Agent 链路打点
- **目标**：在 Planner、Memory 等关键环节记录 trace。
- **修改文件**：
  - `src/agent/planner/intent_classifier.py`
  - `src/agent/planner/state_manager.py`
  - `src/agent/planner/router.py`
  - `tests/integration/test_agent_trace.py`
- **验收标准**：trace 中包含意图识别、状态转移、工具调用阶段。
- **测试方法**：`pytest -q tests/integration/test_agent_trace.py`

#### J4：在 Ingestion 链路打点
- **目标**：在 Pipeline 各阶段记录 trace。
- **修改文件**：
  - `src/ingestion/pipeline.py`
  - `tests/integration/test_ingestion_trace.py`
- **验收标准**：trace 包含 load/split/transform/embed/upsert 阶段。
- **测试方法**：`pytest -q tests/integration/test_ingestion_trace.py`

#### J5：Dashboard 基础架构
- **目标**：搭建 Streamlit 多页面应用。
- **修改文件**：
  - `src/observability/dashboard/app.py`
  - `scripts/start_dashboard.py`
- **验收标准**：`streamlit run app.py` 可启动，页面可切换。
- **测试方法**：手动运行。

#### J6：系统总览页
- **目标**：展示组件配置和数据统计。
- **修改文件**：
  - `src/observability/dashboard/pages/overview.py`
  - `src/observability/dashboard/services/config_service.py`
- **验收标准**：显示当前 LLM、向量库配置，知识库数量。
- **测试方法**：手动验证。

#### J7：知识库浏览器
- **目标**：展示已摄入文档和 Chunk 详情。
- **修改文件**：
  - `src/observability/dashboard/pages/data_browser.py`
  - `src/observability/dashboard/services/data_service.py`
- **验收标准**：可按集合筛选，查看 Chunk 原文和 metadata。
- **测试方法**：手动验证。

#### J8：记忆查看器
- **目标**：展示患者档案和历史就诊记录（脱敏）。
- **修改文件**：
  - `src/observability/dashboard/pages/memory_viewer.py`
- **验收标准**：按患者 ID 搜索，展示档案和情景记忆。
- **测试方法**：手动验证。

#### J9：问诊追踪页
- **目标**：展示 Query trace 列表和详情。
- **修改文件**：
  - `src/observability/dashboard/pages/query_traces.py`
  - `src/observability/dashboard/services/trace_service.py`
- **验收标准**：耗时瀑布图、Dense/Sparse 对比、Rerank 变化。
- **测试方法**：手动验证。

#### J10：知识库质量面板
- **目标**：展示 Hit Rate、Faithfulness 趋势。
- **修改文件**：
  - `src/observability/dashboard/pages/medical_kb_quality.py`
- **验收标准**：图表显示历史评估数据。
- **测试方法**：手动验证。

#### J11：审计日志页
- **目标**：按患者 ID、操作类型筛选审计日志。
- **修改文件**：
  - `src/observability/dashboard/pages/audit_logs.py`
- **验收标准**：支持 TraceID 溯源。
- **测试方法**：手动验证。

---

### 阶段 K：评估体系与双轨门禁

#### K1：黄金测试集构建
- **目标**：构建包含医疗知识问答、症状到科室、病历生成、挂号场景的测试集。
- **修改文件**：
  - `tests/fixtures/golden_test_set.json`
- **验收标准**：至少 50 条用例，覆盖核心业务。
- **测试方法**：人工审核。

#### K2：RagasEvaluator 实现
- **目标**：封装 Ragas 评估。
- **修改文件**：
  - `src/observability/evaluation/ragas_evaluator.py`
  - `tests/unit/test_ragas_evaluator.py`
- **实现类/函数**：
  - `RagasEvaluator.evaluate(test_case) -> metrics`
- **验收标准**：输出 Faithfulness、Answer Relevancy 等。
- **测试方法**：`pytest -q tests/unit/test_ragas_evaluator.py`

#### K3：CompositeEvaluator 实现
- **目标**：组合多个评估器。
- **修改文件**：
  - `src/observability/evaluation/composite_evaluator.py`
  - `tests/unit/test_composite_evaluator.py`
- **实现类/函数**：
  - `CompositeEvaluator.evaluate(test_cases) -> dict`
- **验收标准**：并行执行，合并指标。
- **测试方法**：`pytest -q tests/unit/test_composite_evaluator.py`

#### K4：EvalRunner 实现
- **目标**：加载黄金测试集，运行评估。
- **修改文件**：
  - `src/observability/evaluation/eval_runner.py`
  - `scripts/evaluate.py`
  - `tests/unit/test_eval_runner.py`
- **实现类/函数**：
  - `EvalRunner.run(test_set_path) -> EvalReport`
- **验收标准**：`python scripts/evaluate.py` 输出指标报告。
- **测试方法**：`pytest -q tests/unit/test_eval_runner.py`

#### K5：LLM-as-Judge 幻觉检测
- **目标**：使用强模型计算 Faithfulness。
- **修改文件**：
  - `src/observability/evaluation/hallucination_detector.py`
  - `tests/unit/test_hallucination_detector.py`
- **实现类/函数**：
  - `HallucinationDetector.judge(answer, context) -> float`
- **验收标准**：返回 0-1 分数，阈值 ≥ 0.95。
- **测试方法**：`pytest -q tests/unit/test_hallucination_detector.py`

#### K6：CI 自动化门禁
- **目标**：在 PR 阶段自动运行评估，低于阈值阻断。
- **修改文件**：
  - `.github/workflows/ci.yml`（或本地脚本）
- **验收标准**：若 Faithfulness < 0.95 或 Hit Rate < 0.9，流水线失败。
- **测试方法**：手动模拟。

#### K7：Release 人工门禁
- **目标**：发版前提取低置信度案例，人工签署。
- **修改文件**：
  - `scripts/release_checklist.py`
- **验收标准**：生成 Edge Cases 报告，人工审核后放行。
- **测试方法**：手动运行脚本。

#### K8：评估面板页面
- **目标**：在 Dashboard 中展示评估指标趋势。
- **修改文件**：
  - `src/observability/dashboard/pages/evaluation_panel.py`
- **验收标准**：图表显示历史评估结果。
- **测试方法**：手动验证。

---

### 阶段 L：端到端验收与文档收口

#### L1：E2E：完整问诊流程
- **目标**：从输入症状到生成病历。
- **修改文件**：
  - `tests/e2e/test_full_consultation.py`
- **验收标准**：通过 API 完成问诊，病历字段完整。
- **测试方法**：`pytest -q tests/e2e/test_full_consultation.py`

#### L2：E2E：复诊记忆唤醒流
- **目标**：验证情景记忆检索。
- **修改文件**：
  - `tests/e2e/test_follow_up.py`
- **验收标准**：第二次会话能提及历史病情。
- **测试方法**：`pytest -q tests/e2e/test_follow_up.py`

#### L3：E2E：急症红线拦截
- **目标**：输入“胸痛放射至左肩”，验证强制拦截。
- **修改文件**：
  - `tests/e2e/test_emergency_intercept.py`
- **验收标准**：响应包含急救指令，不执行挂号。
- **测试方法**：`pytest -q tests/e2e/test_emergency_intercept.py`

#### L4：E2E：挂号完整闭环
- **目标**：从科室选择到锁号成功。
- **修改文件**：
  - `tests/e2e/test_booking_flow.py`
- **验收标准**：挂号成功后返回凭证。
- **测试方法**：`pytest -q tests/e2e/test_booking_flow.py`

#### L5：E2E：隐私数据隔离
- **目标**：多会话并发，验证数据隔离。
- **修改文件**：
  - `tests/e2e/test_privacy_isolation.py`
- **验收标准**：会话 A 无法读取会话 B 的患者档案。
- **测试方法**：`pytest -q tests/e2e/test_privacy_isolation.py`

#### L6：E2E：Dashboard 冒烟测试
- **目标**：所有页面可加载、不抛异常。
- **修改文件**：
  - `tests/e2e/test_dashboard_smoke.py`
- **验收标准**：使用 Streamlit `AppTest` 框架，6 个页面均正常渲染。
- **测试方法**：`pytest -q tests/e2e/test_dashboard_smoke.py`

#### L7：完善 README
- **目标**：编写完整的项目说明文档。
- **修改文件**：
  - `README.md`
- **验收标准**：包含快速开始、配置说明、API 文档、Dashboard 使用、测试指南。
- **测试方法**：按 README 手动走一遍。

#### L8：全链路验收
- **目标**：执行全部测试并手动走通流程。
- **修改文件**：无
- **验收标准**：`pytest` 全绿，且能成功完成一次问诊→挂号。
- **测试方法**：手动验证。

---

> **交付里程碑总结**：  
> - M1（阶段A+B）：工程骨架 + 可插拔抽象层就绪  
> - M2（阶段C）：离线医疗知识摄取链路可用  
> - M3（阶段D+E）：Agent 认知核心 + API 网关可用  
> - M4（阶段F+G）：记忆系统完整 + 医疗安全基线建立  
> - M5（阶段H）：HIS 业务闭环可用  
> - M6（阶段I+J）：Dashboard 医疗专用面板 + 双轨评估门禁  
> - M7（阶段K+L）：E2E 验收通过 + 文档完善

### 优化说明

| 优化点 | 原排期问题 | 优化后方案 |
|--------|-----------|-----------|
| **工具实现前置** | Router（E3）依赖的工具在阶段 E 才实现，开发时只能硬 Mock | 新增**阶段 D：核心工具箱实现**，提前实现 RAG/HIS/Case/Vision 基础组件，确保 Router 开发时已有可用工具 |
| **Vision 组件提前** | Ingestion Pipeline（C7）依赖 Vision 工具，但工具实现在阶段 E | 将 Vision Processor 基础组件（ImagePreprocessor、VisionLLMClient）纳入阶段 D，支撑 C7 正常运转 |
| **依赖关系清晰** | 阶段间依赖隐晦，联调风险高 | 明确标注各阶段依赖关系，确保“工具先于大脑”、“基础设施先于业务” |

