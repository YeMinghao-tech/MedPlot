## 5. 系统架构与模块设计

### 5.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    客户端接入层                                              │
│                                                                                             │
│    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐                        │
│    │   患者微信小程序  │    │    医生工作站    │    │   Web 管理后台   │                        │
│    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘                        │
│             │                      │                      │                                 │
│             └──────────────────────┼──────────────────────┘                                 │
│                                    │  HTTPS / WebSocket                                     │
└────────────────────────────────────┼────────────────────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              API 网关层 (FastAPI)                                           │
│                                                                                             │
│    ┌─────────────────────────────────────────────────────────────────────────────────┐      │
│    │                         RESTful API / WebSocket 服务                            │      │
│    │   会话管理 | 用户认证 | 请求路由 | 流式响应 | 限流熔断                          │      │
│    └─────────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                             │
│    ┌─────────────────────────────────────────────────────────────────────────────────┐      │
│    │                         Agent 入口适配器                                         │      │
│    │   请求解析 → 会话加载 → 调用 Agent → 响应封装                                   │      │
│    └─────────────────────────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              Agent 核心层 (认知架构)                                         │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           Planner (规划与决策器)                                     │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Intent Classifier (意图识别)                           │    │    │
│  │  │         问诊 | 挂号 | 科普 | 确认 | 红线紧急拦截                            │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  │                                       │                                             │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      State Manager (状态机)                                 │    │    │
│  │  │         症状收集 → 科室推荐 → 病历确认 → 挂号决策 → 结束                    │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  │                                       │                                             │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Router (工具路由)                                      │    │    │
│  │  │         根据意图和状态，调度底层工具/服务                                    │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              Memory (记忆系统)                                       │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Working Memory (短期工作记忆)                          │    │    │
│  │  │         当前会话状态 | 已收集实体 | 待追问问题                              │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Semantic Memory (长期语义记忆)                         │    │    │
│  │  │         患者健康档案 | 既往史 | 过敏史 | 基础信息                          │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  │  ┌─────────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                      Episodic Memory (历史情景记忆)                         │    │    │
│  │  │         历史就诊摘要向量 | 相似病情检索 | 复诊上下文唤醒                   │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────┬────────────────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              工具层 (可插拔执行单元)                                         │
│                                                                                             │
│  ┌──────────────────────────────────┐    ┌──────────────────────────────────┐             │
│  │        Medical RAG Engine        │    │        HIS Orchestrator         │             │
│  │                                  │    │                                  │             │
│  │  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │             │
│  │  │  Query Processor           │  │    │  │  Department Service       │  │             │
│  │  │  (口语化→医学术语映射)     │  │    │  │  (科室查询)               │  │             │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │             │
│  │  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │             │
│  │  │  Hybrid Search             │  │    │  │  Schedule Service         │  │             │
│  │  │  (Dense + Sparse + RRF)    │  │    │  │  (排班/号源查询)          │  │             │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │             │
│  │  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │             │
│  │  │  Reranker                  │  │    │  │  Booking Service          │  │             │
│  │  │  (阈值熔断 + 重排)         │  │    │  │  (挂号事务 + 并发锁号)    │  │             │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │             │
│  └──────────────────────────────────┘    └──────────────────────────────────┘             │
│                                                                                             │
│  ┌──────────────────────────────────┐    ┌──────────────────────────────────┐             │
│  │       Case Generator             │    │       Vision Processor          │             │
│  │                                  │    │                                  │             │
│  │  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │             │
│  │  │  Entity Extractor          │  │    │  │  Image Preprocess         │  │             │
│  │  │  (症状/时间/药物/过敏)     │  │    │  │  (压缩/格式转换)          │  │             │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │             │
│  │  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │             │
│  │  │  Record Builder            │  │    │  │  Vision LLM Call          │  │             │
│  │  │  (结构化 JSON 生成)        │  │    │  │  (Qwen-VL / GPT-4V)       │  │             │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │             │
│  │  ┌────────────────────────────┐  │    │  ┌────────────────────────────┐  │             │
│  │  │  Schema Validator          │  │    │  │  Abnormal Indicator       │  │             │
│  │  │  (医疗规范校验)            │  │    │  │  Extractor                │  │             │
│  │  └────────────────────────────┘  │    │  └────────────────────────────┘  │             │
│  └──────────────────────────────────┘    └──────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                  存储层 (持久化)                                             │
│                                                                                             │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐                │
│  │        Vector Store              │  │        Relational Store          │                │
│  │  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │                │
│  │  │  Chroma DB                 │  │  │  │  SQLite / PostgreSQL       │  │                │
│  │  │  - 医疗知识库 (Dense+      │  │  │  │  - 患者档案                │  │                │
│  │  │    Sparse)                 │  │  │  │  - HIS 数据                │  │                │
│  │  │  - 情景记忆向量            │  │  │  │  - 挂号记录                │  │                │
│  │  └────────────────────────────┘  │  │  └────────────────────────────┘  │                │
│  └──────────────────────────────────┘  └──────────────────────────────────┘                │
│                                                                                             │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐                │
│  │        BM25 Index                │  │        File Storage              │                │
│  │  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │                │
│  │  │  倒排索引 | IDF 统计       │  │  │  │  化验单图片 | 医疗图表     │  │                │
│  │  └────────────────────────────┘  │  │  └────────────────────────────┘  │                │
│  └──────────────────────────────────┘  └──────────────────────────────────┘                │
│                                                                                             │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐                │
│  │        Trace & Audit             │  │        Processing Cache          │                │
│  │  ┌────────────────────────────┐  │  │  ┌────────────────────────────┐  │                │
│  │  │  JSON Lines (traces.jsonl) │  │  │  │  文件哈希 | 内容哈希      │  │                │
│  │  │  JSON Lines (audit_logs)   │  │  │  │  增量更新状态             │  │                │
│  │  └────────────────────────────┘  │  │  └────────────────────────────┘  │                │
│  └──────────────────────────────────┘  └──────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              Ingestion Pipeline (离线数据摄取)                               │
│                                                                                             │
│    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐   │
│    │   Loader   │───►│  Splitter  │───►│ Transform  │───►│  Embedding │───►│   Upsert   │   │
│    │ (医疗文档) │    │ (语义切分) │    │ (增强处理) │    │ (双路编码) │    │ (原子存储) │   │
│    └────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘   │
│         │                  │                  │                  │                │         │
│         ▼                  ▼                  ▼                  ▼                ▼         │
│    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐   │
│    │纯文本优先   │    │Recursive   │    │LLM重写     │    │Dense:      │    │Chroma      │   │
│    │MD/TXT     │    │Character   │    │元数据注入  │    │通义/BGE    │    │BM25        │   │
│    │FHIR解析   │    │TextSplitter│    │图片描述    │    │Sparse:BM25 │    │图片存储    │   │
│    └────────────┘    └────────────┘    └────────────┘    └────────────┘    └────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 目录结构

```
medical-agent-hub/
│
├── config/                              # 配置文件目录
│   ├── settings.yaml                    # 主配置文件 (LLM/Embedding/VectorStore/记忆/HIS)
│   └── prompts/                         # Prompt 模板目录
│       ├── medical_knowledge.txt        # 医疗问答 Prompt
│       ├── case_generation.txt          # 病历生成 Prompt
│       ├── symptom_elicitation.txt      # 症状追问 Prompt
│       ├── image_captioning.txt         # 化验单/影像描述 Prompt
│       └── rerank.txt                   # LLM Rerank Prompt
│
├── src/                                 # 源代码主目录
│   │
│   ├── api/                             # API 网关层 (FastAPI)
│   │   ├── __init__.py
│   │   ├── app.py                       # FastAPI 应用入口
│   │   ├── dependencies.py              # 依赖注入 (会话、认证)
│   │   ├── routers/                     # 路由模块
│   │   │   ├── __init__.py
│   │   │   ├── chat.py                  # 对话接口 (POST /chat, WebSocket)
│   │   │   ├── session.py               # 会话管理 (创建/获取/删除)
│   │   │   └── patient.py               # 患者档案接口
│   │   ├── models/                      # Pydantic 请求/响应模型
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   └── patient.py
│   │   └── middleware/                  # 中间件
│   │       ├── auth.py                  # 认证中间件
│   │       └── logging.py               # 请求日志中间件
│   │
│   ├── agent/                           # Agent 核心层 (认知架构)
│   │   ├── __init__.py
│   │   ├── planner/                     # 规划与决策器
│   │   │   ├── __init__.py
│   │   │   ├── intent_classifier.py     # 意图识别
│   │   │   ├── state_manager.py         # 对话状态机
│   │   │   └── router.py                # 工具路由决策
│   │   │
│   │   └── memory/                      # 记忆系统
│   │       ├── __init__.py
│   │       ├── working_memory.py        # 短期工作记忆
│   │       ├── semantic_memory.py       # 长期语义记忆 (患者档案)
│   │       ├── episodic_memory.py       # 历史情景记忆
│   │       └── memory_factory.py        # 记忆工厂 (可插拔后端)
│   │
│   ├── tools/                           # 工具层 (可插拔执行单元)
│   │   ├── __init__.py
│   │   │
│   │   ├── rag_engine/                  # 医疗 RAG 引擎
│   │   │   ├── __init__.py
│   │   │   ├── query_processor.py       # 查询预处理 (口语化转医学术语)
│   │   │   ├── hybrid_search.py         # 混合检索 (Dense + Sparse + RRF)
│   │   │   ├── dense_retriever.py       # 稠密检索
│   │   │   ├── sparse_retriever.py      # 稀疏检索 (BM25)
│   │   │   ├── fusion.py                # RRF 融合
│   │   │   ├── reranker.py              # 精排重排 (带阈值熔断)
│   │   │   └── vector_store_adapter.py  # 向量库适配器
│   │   │
│   │   ├── his_orchestrator/            # HIS 工具编排器
│   │   │   ├── __init__.py
│   │   │   ├── dept_service.py          # 科室服务
│   │   │   ├── schedule_service.py      # 排班服务
│   │   │   ├── booking_service.py       # 挂号服务 (事务管理)
│   │   │   └── his_client.py            # HIS 客户端抽象
│   │   │
│   │   ├── case_generator/              # 病历生成器
│   │   │   ├── __init__.py
│   │   │   ├── entity_extractor.py      # 实体抽取
│   │   │   ├── record_builder.py        # 结构化病历构建
│   │   │   └── schema_validator.py      # JSON Schema 校验
│   │   │
│   │   └── vision_processor/            # 多模态处理
│   │       ├── __init__.py
│   │       ├── image_preprocessor.py    # 图片预处理 (压缩/格式转换)
│   │       ├── vision_llm_client.py     # Vision LLM 调用
│   │       └── indicator_extractor.py   # 异常指标提取
│   │
│   ├── ingestion/                       # Ingestion Pipeline (离线数据摄取)
│   │   ├── __init__.py
│   │   ├── pipeline.py                  # Pipeline 主流程编排
│   │   ├── document_manager.py          # 文档生命周期管理
│   │   │
│   │   ├── chunking/                    # 切分模块
│   │   │   ├── __init__.py
│   │   │   └── medical_chunker.py       # 医疗文档切分
│   │   │
│   │   ├── transform/                   # 增强处理模块
│   │   │   ├── __init__.py
│   │   │   ├── base_transform.py
│   │   │   ├── chunk_refiner.py         # 智能重组
│   │   │   ├── metadata_enricher.py     # 元数据注入 (疾病标签、权威等级)
│   │   │   └── image_captioner.py       # 医疗图像描述
│   │   │
│   │   ├── embedding/                   # 向量化模块
│   │   │   ├── __init__.py
│   │   │   ├── dense_encoder.py
│   │   │   ├── sparse_encoder.py
│   │   │   └── batch_processor.py
│   │   │
│   │   └── storage/                     # 存储模块
│   │       ├── __init__.py
│   │       ├── vector_upserter.py
│   │       ├── bm25_indexer.py
│   │       └── image_storage.py
│   │
│   ├── libs/                            # 可插拔抽象层 (基础设施)
│   │   ├── __init__.py
│   │   │
│   │   ├── llm/                         # LLM 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_llm.py
│   │   │   ├── llm_factory.py
│   │   │   ├── qwen_llm.py              # 通义千问实现 (推荐)
│   │   │   ├── openai_llm.py
│   │   │   ├── ollama_llm.py
│   │   │   ├── base_vision_llm.py
│   │   │   └── qwen_vl_llm.py           # Qwen-VL 实现
│   │   │
│   │   ├── embedding/                   # Embedding 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_embedding.py
│   │   │   ├── embedding_factory.py
│   │   │   ├── dashscope_embedding.py   # 通义文本向量
│   │   │   ├── openai_embedding.py
│   │   │   └── ollama_embedding.py
│   │   │
│   │   ├── vector_store/                # VectorStore 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_vector_store.py
│   │   │   ├── vector_store_factory.py
│   │   │   └── chroma_store.py
│   │   │
│   │   ├── reranker/                    # Reranker 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_reranker.py
│   │   │   ├── reranker_factory.py
│   │   │   ├── bge_reranker.py          # BGE 重排实现 (支持中文)
│   │   │   └── llm_reranker.py
│   │   │
│   │   ├── splitter/                    # Splitter 抽象
│   │   │   ├── __init__.py
│   │   │   ├── base_splitter.py
│   │   │   ├── splitter_factory.py
│   │   │   └── recursive_splitter.py
│   │   │
│   │   └── his/                         # HIS 集成抽象
│   │       ├── __init__.py
│   │       ├── base_his.py
│   │       ├── his_factory.py
│   │       ├── mock_his.py              # Mock 实现 (SQLite)
│   │       └── http_his.py              # 真实 HIS HTTP 适配器
│   │
│   └── observability/                   # Observability 层
│       ├── __init__.py
│       ├── logger.py                    # 结构化日志
│       ├── trace/                       # 追踪模块
│       │   ├── __init__.py
│       │   ├── trace_context.py
│       │   └── trace_collector.py
│       ├── dashboard/                   # Web Dashboard (Streamlit)
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── pages/
│       │   │   ├── overview.py          # 系统总览
│       │   │   ├── data_browser.py      # 知识库浏览器
│       │   │   ├── ingestion_manager.py # 摄取管理
│       │   │   ├── query_traces.py      # 问诊追踪
│       │   │   ├── memory_viewer.py     # 记忆查看器
│       │   │   ├── medical_kb_quality.py# 知识库质量面板
│       │   │   └── audit_logs.py        # 审计日志
│       │   └── services/
│       │       ├── trace_service.py
│       │       ├── data_service.py
│       │       └── config_service.py
│       └── evaluation/                  # 评估模块
│           ├── __init__.py
│           ├── eval_runner.py
│           ├── ragas_evaluator.py
│           └── composite_evaluator.py
│
├── data/                                # 数据目录
│   ├── medical_knowledge/               # 医疗知识库原始文档
│   │   └── {collection}/
│   ├── images/                          # 化验单/影像图片
│   │   └── {collection}/
│   └── db/                              # 数据库目录
│       ├── ingestion_history.db         # 摄取历史
│       ├── image_index.db               # 图片索引
│       ├── patient_profiles.db          # 患者档案 (长期语义记忆)
│       ├── episodic_metadata.db         # 情景记忆元数据
│       ├── his_mock.db                  # Mock HIS 数据库
│       ├── chroma/                      # Chroma 向量库
│       └── bm25/                        # BM25 索引
│
├── cache/                               # 缓存目录
│   ├── embeddings/
│   ├── captions/
│   └── processing/
│
├── logs/                                # 日志目录
│   ├── traces.jsonl                     # 追踪日志
│   ├── audit_logs.jsonl                 # 审计日志
│   └── app.log
│
├── tests/                               # 测试目录
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│       ├── medical_documents/           # 医疗测试文档
│       ├── golden_test_set.json         # 黄金测试集
│       └── red_team_test_set.json       # 红线对抗测试集
│
├── scripts/                             # 脚本目录
│   ├── ingest_medical.py                # 医疗知识摄取脚本
│   ├── seed_his.py                      # 初始化 HIS Mock 数据
│   ├── query.py                         # 测试查询脚本
│   ├── evaluate.py                      # 评估运行脚本
│   └── start_dashboard.py               # Dashboard 启动脚本
│
├── main.py                              # FastAPI 应用启动入口
├── pyproject.toml
├── requirements.txt
└── README.md
```

### 5.3 模块说明

#### 5.3.1 API 网关层

| 模块 | 职责 | 关键技术点 |
|-----|-----|----------|
| `app.py` | FastAPI 应用入口，注册路由、中间件 | FastAPI，生命周期管理 |
| `routers/chat.py` | 对话接口，支持 HTTP 和 WebSocket | 流式响应 (SSE)，会话管理 |
| `routers/session.py` | 会话创建、获取、删除 | 会话 ID 生成，超时管理 |
| `models/` | Pydantic 请求/响应模型 | 数据校验，自动文档生成 |
| `middleware/auth.py` | 认证与鉴权 | JWT，患者身份验证 |

#### 5.3.2 Agent 核心层

| 模块 | 职责 | 关键技术点 |
|-----|-----|----------|
| **Planner (规划器)** | | |
| `intent_classifier.py` | 意图识别（问诊/挂号/科普/确认/红线拦截） | 规则 + LLM 分类，紧急关键词优先 |
| `state_manager.py` | 对话状态机 | 状态转移图，超时重置 |
| `router.py` | 工具路由决策 | 根据状态和意图调度底层工具 |
| **Memory (记忆系统)** | | |
| `working_memory.py` | 短期工作记忆 | 维护当前会话 `PatientState`，支持序列化 |
| `semantic_memory.py` | 长期语义记忆 | SQLite 读写患者档案，Upsert 合并更新 |
| `episodic_memory.py` | 历史情景记忆 | 向量检索相似历史，按 patient_id 过滤 |

#### 5.3.3 工具层

| 模块 | 职责 | 关键技术点 |
|-----|-----|----------|
| **RAG Engine** | | |
| `query_processor.py` | 查询预处理 | 口语化→医学术语映射，同义词扩展 |
| `hybrid_search.py` | 混合检索编排 | 并行 Dense/Sparse，RRF 融合 |
| `reranker.py` | 精排重排 | CrossEncoder (bge-reranker-v2-m3)，阈值熔断 |
| **HIS Orchestrator** | | |
| `dept_service.py` | 科室查询 | 按关键词匹配科室 |
| `schedule_service.py` | 排班查询 | 日期/医生过滤，余号统计 |
| `booking_service.py` | 挂号服务 | 事务管理，并发锁号，回滚 |
| **Case Generator** | | |
| `entity_extractor.py` | 实体抽取 | 症状、持续时间、药物、过敏史 |
| `record_builder.py` | 病历构建 | 汇总记忆和抽取结果，调用 LLM 生成 JSON |
| `schema_validator.py` | Schema 校验 | 确保输出符合医疗规范 |
| **Vision Processor** | | |
| `image_preprocessor.py` | 图片预处理 | 压缩、格式转换 |
| `vision_llm_client.py` | Vision LLM 调用 | Qwen-VL / GPT-4V 适配 |
| `indicator_extractor.py` | 异常指标提取 | 仅提取超出正常范围指标 |

#### 5.3.4 Ingestion Pipeline 层

| 模块 | 职责 | 关键技术点 |
|-----|-----|----------|
| `pipeline.py` | Pipeline 流程编排 | 支持 `on_progress` 回调，增量更新 |
| `document_manager.py` | 文档生命周期管理 | list/delete/stats，跨存储协调 |
| `medical_chunker.py` | 医疗文档切分 | 医疗分隔符（疾病概述/临床表现/治疗原则） |
| `transform/` | 增强处理 | LLM 重组、元数据注入、图像描述生成 |
| `embedding/` | 双路编码 | Dense + Sparse，批处理优化 |
| `storage/` | 存储 | 向量库 Upsert，BM25 索引，图片存储 |

#### 5.3.5 Libs 层 (可插拔抽象)

| 抽象接口 | 当前默认实现 | 可替换选项 |
|---------|------------|----------|
| `LLMClient` | Qwen-Max (DashScope) | Azure OpenAI / OpenAI / Ollama / DeepSeek |
| `VisionLLMClient` | Qwen-VL-Max | GPT-4o / Claude 3.5 Sonnet |
| `EmbeddingClient` | 通义文本向量 | OpenAI Embedding / BGE / Ollama |
| `Splitter` | RecursiveCharacterTextSplitter | Semantic / FixedLen |
| `VectorStore` | Chroma | Qdrant / Milvus |
| `Reranker` | BAAI/bge-reranker-v2-m3 | LLM Rerank / None |
| `Memory` (短期) | 内存字典 | Redis |
| `Memory` (长期档案) | SQLite | PostgreSQL |
| `Memory` (情景) | Chroma + SQLite | 其他向量库 + 关系库 |
| `HISClient` | MockHISClient (SQLite) | 真实 HIS HTTP API |

#### 5.3.6 Observability 层

| 模块 | 职责 | 关键技术点 |
|-----|-----|----------|
| `logger.py` | 结构化日志 | JSON Formatter，JSON Lines 输出 |
| `trace/` | 请求级追踪 | trace_id，trace_type，阶段耗时记录 |
| `dashboard/` | Web Dashboard | Streamlit 多页面，医疗专用面板 |
| `evaluation/` | 评估模块 | Ragas 指标，红线对抗测试，复合评估器 |

### 5.4 数据流说明

#### 5.4.1 在线问诊与挂号流程

```
患者输入 (微信小程序)
      │
      ▼
┌─────────────────┐
│   API Gateway   │  POST /chat
│   (FastAPI)     │  会话验证，加载 session_id
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent 核心层                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Memory Scheduler                                     │    │
│  │  - 从 WorkingMemory 加载当前状态                    │    │
│  │  - 从 SemanticMemory 加载患者档案                   │    │
│  │  - 从 EpisodicMemory 检索相似历史 (复诊场景)        │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Intent Classifier                                    │    │
│  │  - 紧急关键词检测 (红线拦截)                        │    │
│  │  - 意图分类 (问诊/挂号/科普/确认)                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ State Manager                                        │    │
│  │  - 更新状态机                                        │    │
│  │  - 判断信息完整性                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Router                                               │    │
│  │  - 科普意图 → RAG Engine                            │    │
│  │  - 挂号意图且信息充足 → Case Generator              │    │
│  │  - 科室咨询 → HIS Orchestrator                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
         │
         ├─ 科普意图 ──► 触发 RAG Tool ──► 获取医学知识片段
         │                                    │
         │                                    ▼
         │                            回传给 Planner (LLM) ──► 结合上下文拟人化生成回答 ──► 返回给患者
         │
         ├─ 挂号意图且信息充足 ──► Case Generator ──► 生成病历草案 ──► 返回给患者确认
         │                              │
         │                              ▼ (患者确认后)
         │                    HIS Orchestrator (工具箱)
         │                         │
         │                         ├─ query_departments
         │                         ├─ query_doctor_schedule
         │                         └─ book_appointment (事务级锁号)
         │
         └─ 科室咨询 ──► 触发 HIS Tool ──► 回传给 Planner (LLM) ──► 整合为自然语言建议 ──► 返回给患者
```

#### 5.4.2 离线医疗知识摄取流

```
医疗指南 (.txt/.md)
      │
      ▼
┌─────────────────┐     未变更则跳过
│ File Integrity  │───────────────────────────► 结束
│   (SHA256)      │
└────────┬────────┘
         │ 新文件/已变更
         ▼
┌─────────────────┐
│     Loader      │  文本读取 + 元数据收集
│  (纯文本优先)   │  (来源、章节标题)
└────────┬────────┘
         │ Document (text + metadata)
         ▼
┌─────────────────┐
│    Splitter     │  按医疗语义边界切分
│ (Recursive)     │  (分隔符: 疾病概述、临床表现、治疗原则)
└────────┬────────┘
         │ Chunks[]
         ▼
┌─────────────────┐
│   Transform     │  LLM 重组 + 元数据注入 (疾病标签、权威等级)
│ (Enrichment)    │
└────────┬────────┘
         │ Enriched Chunks[]
         ▼
┌─────────────────┐
│   Embedding     │  Dense (通义) + Sparse (BM25) 双路编码
│  (Dual Path)    │
└────────┬────────┘
         │ Vectors + Chunks + Metadata
         ▼
┌─────────────────┐
│    Upsert       │  Chroma Upsert + BM25 索引
│   (Storage)     │
└─────────────────┘
```

### 5.5 配置驱动设计

系统通过 `config/settings.yaml` 统一配置各组件实现，支持零代码切换。

```yaml
# config/settings.yaml (医疗导诊 Agent)

# LLM 配置 (主推 Qwen)
llm:
  provider: dashscope           # dashscope | azure | openai | ollama | openai_compatible
  model: qwen-max
  api_key: ${DASHSCOPE_API_KEY}
  # 若使用本地部署
  # base_url: http://192.168.1.100:8000/v1

# Vision LLM (化验单识别)
vision_llm:
  provider: dashscope
  model: qwen-vl-max

# Embedding 配置
embedding:
  provider: dashscope           # dashscope | openai | ollama
  model: text-embedding-v1

# 向量存储配置
vector_store:
  backend: chroma
  persist_path: ./data/db/chroma

# 检索配置
retrieval:
  sparse_backend: bm25
  fusion_algorithm: rrf
  top_k_dense: 20
  top_k_sparse: 20
  top_k_final: 10
  rerank_backend: cross_encoder
  rerank_model: BAAI/bge-reranker-v2-m3
  # 安全阈值，低于此分数触发 fallback
  confidence_threshold: 0.7

# 记忆配置
memory:
  working:
    backend: in_memory          # in_memory | redis
  semantic:
    backend: sqlite
    db_path: ./data/db/patient_profiles.db
  episodic:
    backend: chroma
    collection: episodic_memory
    metadata_db: ./data/db/episodic_metadata.db

# HIS 配置 (底层业务系统)
his:
  backend: mock                 # mock | api
  mock_db_path: ./data/db/his_mock.db
  use_wal: true                 # [CRITICAL] 必须开启以支持挂号事务的高并发锁处理
  api_base: http://localhost:8080/his
  timeout: 5

# API 服务配置
api:
  host: 0.0.0.0
  port: 8000
  cors_origins: ["*"]           # 生产环境需限制
  websocket_enabled: true

# 可观测性
observability:
  enabled: true
  log_file: logs/traces.jsonl
  audit_log_file: logs/audit_logs.jsonl
  detail_level: standard

# Dashboard
dashboard:
  enabled: true
  port: 8501
```

### 5.6 扩展性设计要点

1. **新增 LLM Provider**：实现 `BaseLLM` 接口，在 `libs/llm/llm_factory.py` 注册，配置文件指定 `provider` 即可。

2. **替换记忆后端**：实现 `BaseMemory` 接口（在 `agent/memory/` 下定义），工厂根据配置选择（如从 SQLite 切换到 PostgreSQL）。

3. **接入真实 HIS**：实现 `BaseHISClient` 接口，通过 HTTP 调用医院内部系统，无需修改上层业务逻辑。

4. **新增医疗知识源**：实现 `BaseLoader` 接口，支持其他格式（如 FHIR XML），在 Ingestion Pipeline 中注册。

5. **自定义评估指标**：实现 `BaseEvaluator` 接口，添加到 `evaluation.backends` 列表。

6. **扩展红线测试**：在 `tests/fixtures/red_team_test_set.json` 中添加新的危急重症场景，自动化回归验证。

7. **新增工具**：在 `tools/` 下新建模块，实现统一接口，并在 `agent/planner/router.py` 中注册路由规则。
