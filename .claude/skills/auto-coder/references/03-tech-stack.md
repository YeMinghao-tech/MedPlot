## 3. 技术选型与记忆架构

### 3.1 核心认知与动态记忆流 (Cognitive & Memory Architecture)

**目标**：构建一个具有真实“临床时间线”感知的多层记忆引擎。突破单纯依赖 LLM Context Window 的局限，将短期会话状态、静态健康档案与历史就诊事件（Episodic Events）分离存储与调度。该架构不仅支撑业务，也为深入研究 Agent 认知机制（如探索更高效的存储结构优化）提供了理想的实验底座。

#### 3.1.1 记忆分层设计与持久化方案

| 记忆层级 | 存储介质 | 检索方式 | 生命周期 | 核心用途 |
|---------|---------|---------|---------|---------|
| **短期工作记忆** | 内存字典 / Redis | 按 Session ID 直接存取 | 单次会话 | 追踪当前对话状态、待追问问题、已收集的医疗实体 |
| **长期语义记忆（健康档案）** | SQLite | 按患者 ID 直接查询 | 跨会话持久 | 存储患者基本信息、既往史、过敏史、家族史等结构化数据 |
| **历史情景记忆** | Chroma (向量) + SQLite | 向量检索（基于当前对话摘要） | 跨会话持久 | 检索相似历史对话片段，用于唤醒复诊记忆 |

**① 短期工作记忆 (Working Memory - Session State)**

- **定位**：维护当前一次门诊咨询的上下文，是 Agent 进行意图规划（Planner）的直接输入。
- **数据结构**：维护一个结构化的 `PatientState` 对象，包含：
  - `symptom_tree`: 收集到的主诉、伴随症状、持续时间（用于判断是否满足分诊/病历生成条件）。
  - `message_history`: 当前 Session 的前 N 轮原始对话。
  - `state`: 当前状态机阶段（symptom_collection / dept_recommend / record_confirmation / booking）。
- **存储选型**：运行时内存（单机）或 Redis（分布式）。
- **生命周期**：随患者挂号完成或会话超时而冻结，随后触发记忆提炼 (Memory Consolidation)，将核心要素下沉至长期与情景记忆。

**② 长期语义记忆 (Semantic Memory - Patient Profile)**

- **定位**：存储患者确定的、静态的健康档案与身份信息。这部分作为高优上下文，在每次 LLM 思考时强制注入 System Prompt。
- **表结构** (`patient_profiles`)：
```sql
CREATE TABLE patient_profiles (
    patient_id TEXT PRIMARY KEY,
    name TEXT,
    age INTEGER,
    gender TEXT,
    chronic_conditions TEXT,   -- JSON 列表，如 ["高血压", "2型糖尿病"]
    allergies TEXT,            -- 如 ["青霉素", "阿司匹林"]
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_last_updated ON patient_profiles(last_updated);
```
- **更新机制**：在对话中通过 LLM 的 Entity Extraction 工具实时抽取，采用 Upsert 逻辑更新 SQLite。

**③ 历史情景记忆 (Episodic Memory - Past Visits)**

- **定位**：记录患者过去发生的就医事件。当患者提到“上次那个胃病”时，系统能通过语义向量找回当时的上下文。
- **存储选型**：Chroma 向量数据库，独立 Collection (`episodic_memory`)。
- **数据流转**：
  - 就诊结束时，调用 LLM 将当前 Working Memory 提炼为一段摘要（如：“2025年10月，因饮食不当引发急性胃炎，伴随呕吐，挂消化内科专家号”）。
  - 将摘要文本进行 Embedding。
  - Metadata 结构：`{"patient_id": "P123", "date": "2025-10-12", "dept": "消化内科", "diagnosis_tags": ["急性胃炎"]}`。
- **检索机制**：复诊时，结合 `patient_id` 进行硬过滤 (Pre-filter)，再通过当前 Query 的 Dense Embedding 召回历史相似病情，作为上下文注入 System Prompt。

### 3.2 医疗知识 RAG 核心流水线设计

#### 3.2.1 数据摄取流水线 (Ingestion Pipeline)

**目标**：构建统一、可配置且可观测的数据摄取流水线，覆盖医疗文档加载、格式解析、语义切分、多模态增强、嵌入计算与存储。该能力应作为可重用库，便于在 `ingest_medical.py`、Dashboard 管理面板、离线批处理中调用。

- **自研 Pipeline 框架**：采用自定义抽象接口（`BaseLoader`/`BaseSplitter`/`BaseTransform`/`BaseEmbedding`/`BaseVectorStore`），实现完全可控的可插拔架构。

**设计要点**：

| 阶段 | 职责 | 医疗场景关键实现 |
|------|------|------------------|
| **Loader** | 将原始文件解析为统一 `Document` 对象 | **纯文本优先**：明确弃用通用 PDF 解析以规避复杂表格导致的数据污染，优先摄取高质量的医疗指南 .txt 或 .md 文本资料。**电子病历（FHIR/HL7）**：解析结构化字段映射为文本。 |
| **Splitter** | 基于 Markdown 结构切分 | 使用 LangChain `RecursiveCharacterTextSplitter`，并针对医疗文档调整分隔符（如“疾病概述”、“临床表现”、“治疗原则”），确保疾病知识完整性。 |
| **Transform** | 可插拔的增强步骤 | ① **智能重组**：LLM 合并被切断的医疗段落，剔除页眉页脚；② **语义元数据注入**：为 Chunk 生成疾病名称、适应症、禁忌症等标签；③ **图像描述生成**：调用 Vision LLM 对医学图表、化验单图片生成文本描述。 |
| **Embedding** | 双路向量化 | **Dense**：调用通义文本向量或 OpenAI Embedding；**Sparse**：BM25 编码。支持差量计算（基于内容哈希复用）。 |
| **Upsert** | 原子化存储 | 同时写入 Dense Vector、Sparse Vector、Chunk 文本及 Metadata 到 Chroma，并更新 BM25 索引。 |

**关键实现要素**：

- **前置去重与增量摄取**：在解析文件前计算 SHA256 哈希，查询 SQLite 表（`ingestion_history`），若已成功处理则直接跳过，实现零成本增量更新。
- **医疗元数据注入**：为每个 Chunk 标注来源权威等级（如“国家卫健委指南”）、适用人群（儿童/成人/老年人），便于检索时加权。
- **图片处理**：Loader 阶段提取图片，生成 `image_id`，在文本中插入占位符 `[IMAGE: {image_id}]`，并将图片保存至 `data/images/`。Transform 阶段调用 Vision LLM 生成描述，写入 Chunk 正文，实现“以文搜图”。

#### 3.2.2 检索流水线 (Retrieval Pipeline)

**目标**：实现多阶段过滤与精排，精准召回 Top-K 最相关医疗知识。

- **Query 预处理**：
  - **口语化转医学术语**：将患者输入（如“胃烧心”）映射为专业术语（“上腹烧灼感”）。
  - **关键词提取**：去停用词，提取核心症状、药品名。
  - **查询扩展**：为稀疏检索增加同义词、别名（如“布洛芬”→“芬必得”）。

- **混合检索执行**：
  - **稠密召回**：Query Embedding 检索向量库，返回 Top-N 语义候选。
  - **稀疏召回**：BM25 检索倒排索引，返回 Top-N 关键词候选。
  - **融合**：采用 RRF 算法融合两路排名：`Score = 1 / (k + Rank_Dense) + 1 / (k + Rank_Sparse)`。

- **精排重排 (Rerank)**：
  - 默认使用支持中文语境的**高性能重排模型**（如 BAAI/bge-reranker-v2-m3）对候选集进行深度打分。坚决弃用纯英文的 PubMed 模型以防止 Tokenizer 在中文场景下崩溃。
  - 当 Reranker 不可用或超时时，回退到融合后的排序。
  - **医疗专属策略**：根据 `metadata.authority_level` 字段对来自权威指南的 Chunk 给予更高权重。
  - **阈值熔断机制**：如果 Rerank 最高分低于设定的安全阈值（如 0.7），直接触发 Fallback 回复（“抱歉，超出系统医学知识库范围，建议尽快线下就诊”），绝对禁止 LLM 根据自身参数内化知识编造医疗建议。

- **质量保障**：
  - 集成 Ragas `faithfulness` 指标，当检索到的知识不足以支撑回答时，系统明确提示“当前知识库暂无相关信息，建议咨询医生”。
  - 所有回答附带来源文档及段落引用。

### 3.3 全链路可插拔与算力架构设计

定义清晰的抽象层（如 `BaseLLM`、`BaseEmbedding`、`BaseVectorStore`），通过 `settings.yaml` 工厂模式动态路由。

| 组件类别 | 抽象接口 | 默认实现 | 可替换选项 |
|---------|---------|---------|---------|
| **LLM** | `BaseLLM` | **Qwen-Max (DashScope)** | Azure OpenAI / OpenAI / Ollama / DeepSeek |
| **Vision LLM** | `BaseVisionLLM` | Qwen-VL-Max | GPT-4o / Claude 3.5 Sonnet |
| **Embedding** | `BaseEmbedding` | 通义文本向量 | OpenAI Embedding / BGE / Ollama |
| **Vector Store** | `BaseVectorStore` | Chroma | Qdrant / Milvus |
| **Reranker** | `BaseReranker` | CrossEncoder (BiomedNLP) | LLM Rerank / None |
| **Memory (短期)** | `BaseWorkingMemory` | 内存字典 | Redis |
| **Memory (长期档案)** | `BaseSemanticMemory` | SQLite | PostgreSQL |
| **Memory (情景)** | `BaseEpisodicMemory` | Chroma + SQLite | 其他向量库 + 关系库 |
| **HIS 集成** | `BaseHISClient` | MockHISClient | 真实 HIS HTTP API |

#### 3.3.1 模型调度层 (LLM Engine)

系统原生提供多种 LLM Provider 适配，针对指令遵循、Tool Calling 稳定性和医疗数据隐私，采用如下推荐部署方案：

- **主推云端基座：Qwen (通义千问) API**
  - **选型理由**：Qwen 的 API 在长文本处理、中文医疗语境对齐以及 JSON 格式化输出（生成结构化病历的关键）上极具优势，且成本可控。系统的主体研发与 Prompt 调优均以 Qwen API 为基准。

- **隐私级本地算力部署 (Local Private Deployment)**
  - **场景**：医院内网环境对患者数据隐私有严苛的物理隔离要求，数据不可出内网。
  - **硬件与框架适配**：架构底层设计全面兼容 OpenAI 接口协议。在具备专有算力（如 8 张昇腾 910B 计算卡）的环境下，可通过 MindIE 推理引擎或基于 NPU 优化的 vLLM 框架，分布式部署 Qwen2.5-72B-Instruct 等千亿级旗舰开源模型。
  - **无缝切换**：只需在配置文件中将 `provider` 设为 `openai_compatible`，更改 `base_url` 指向本地昇腾集群暴露的服务端口，无需修改任何上层 Agent 调度与工具调用逻辑。

### 3.4 Agent 核心工具与 HIS 模拟集成 (Tools & HIS Mock)

系统封装了标准化的工具集供认知规划器 (Planner) 调用，实现“导诊→查号→挂号”闭环。

#### 3.4.1 模拟医院信息系统 (SQLite Mock HIS)

在 `data/db/his_mock.db` 中建立以下表：
- `departments`：科室表（`dept_id`, `name`, `introduction`）。
- `doctors`：医生表（`doctor_id`, `name`, `dept_id`, `title`, `specialty`）。
- `schedules`：排班号源表（`schedule_id`, `doctor_id`, `date`, `time_slot`, `total_slots`, `remaining_slots`）。
- `appointments`：挂号订单表（`appointment_id`, `patient_id`, `schedule_id`, `status`, `booked_at`）。
工程规范与并发保障：
在初始化 SQLite 数据库连接时，必须强制执行 PRAGMA journal_mode=WAL; 并设置合理的超时时间（如 timeout=5000）。这是利用 SQLite 锁机制安全模拟多并发扣减号源（book_appointment）的底层前提，可有效防止 Python 异步环境下的 database is locked 崩溃。

#### 3.4.2 核心机制划分与 Tool 定义
- **A. LLM 可调用的业务 Tools (Function Calling)**

    | 工具名称 | 输入参数 | 输出 | 调用时机 |
    |---------|---------|------|---------|
    | `query_departments` | `keyword?: string` | 科室列表及介绍 | 患者询问科室信息时 |
    | `query_doctor_schedule` | `dept_name: str`, `target_date: str` | 医生排班表及余号状态 | 患者决定挂号科室后 |
    | `book_appointment` | `patient_id: str`, `schedule_id: str` | 挂号凭证（成功/失败/候补） | 患者确认后 |

- **B. 状态机内置服务 (Built-in Services)**
注：不对 LLM 暴露为工具，由 Agent 工作流底层引擎自动触发：

    - `ask_medical_knowledge()`：作为 RAG 的独立意图路由，当判断用户为咨询科普时，系统自动切入该检索流。

    - `generate_structured_case()`：在满足症状收集条件、准备进行挂号前，后台自动汇总工作记忆，生成病历草案供患者确认。

### 3.5 多模态处理：检验报告解析 (Vision Pipeline)

无缝复用纯文本 RAG 链路，通过“图转文”策略处理患者上传的医疗影像与单据。

- **OCR 与指标提取**：
  - 患者上传化验单/体检报告截图。
  - 核心链路调用 Vision LLM（如 Qwen-VL-Max，其对中文表格与医疗单据的 OCR 具有极高准确度），抽取关键异常指标（如：“白细胞计数偏高，具体数值为 12.5”）。
- **上下文注入**：
  - 避免将全量 OCR 文本塞入内存导致上下文溢出。在调用 Vision LLM（如 Qwen-VL-Max）时，通过 Prompt 严格限制仅提取异常指标。随后，只将生成的精简异常摘要（如：“注意：患者白细胞计数 12.5，超出正常范围；转氨酶偏高”）压入当前会话的 Working Memory，指导 Agent 下一步的分诊规划。

### 3.6 医疗级可观测性与审计日志 (Audit & Observability)

医疗应用的不可解释性是落地的最大阻碍。系统通过 `TraceContext` 提供白盒化的全链路追踪。

#### 3.6.1 追踪数据结构扩展

在原有 Query/Ingestion Trace 基础上，增加医疗专用字段：

- **医疗问答追踪**：记录 `symptom_extracted`（提取的症状）、`department_recommended`（推荐科室）、`citation_authority`（引用来源权威等级）。
- **病历生成追踪**：记录 `record_fields`（生成的字段及内容）、`patient_confirmation`（患者确认状态）。
- **挂号操作追踪**：记录 `doctor_id`、`time_slot`、`booking_status`、`error_code`。

#### 3.6.2 防篡改决策日志 (Decision Trace)

JSON Lines 日志（`logs/traces.jsonl`）中必须包含：
```json
{
  "trace_id": "abc123",
  "timestamp": "2025-03-24T10:30:00Z",
  "user_query": "我胃痛，吃什么药？",
  "retrieved_knowledge": ["《消化性溃疡诊疗指南》中关于胃酸抑制剂的内容..."],
  "injected_memory": {"patient_id": "P123", "allergies": ["青霉素"]},
  "selected_tool": "ask_medical_knowledge",
  "response": "根据您的描述，胃痛可能与胃酸分泌有关，建议... 用药前请确认您无相关禁忌症。"
}
```

#### 3.6.3 Web Dashboard 医疗专用面板

基于 Streamlit 搭建本地面板，增加以下页面：

- **医疗知识库质量面板**：展示不同疾病/药品的覆盖率、检索命中率、用户反馈满意度。
- **病历生成质量监控**：展示生成病历的字段填充率，对“主诉”“现病史”等关键字段进行抽样人工评估。
- **合规审计日志**：单独页面展示所有涉及患者隐私数据访问和修改的操作日志（按患者 ID、时间、操作类型筛选）。
- **决策溯源**：医生或管理员可直接输入 TraceID 还原系统在做出“建议挂心内科急诊”这一决策时，具体参考了哪条记忆、哪段医疗指南，确保责任可追溯。

#### 3.6.4 数据脱敏

- 所有日志中的患者姓名、身份证号等个人可识别信息自动脱敏（如“张**”）。
- 审计日志单独存储（`audit_logs.jsonl`），包含操作人、时间、操作类型、影响记录 ID，确保不可篡改。

### 3.7 配置管理

系统通过 `config/settings.yaml` 统一配置，支持零代码切换组件。

```yaml
# LLM 配置
llm:
  provider: dashscope   # dashscope | azure | openai | ollama | openai_compatible
  model: qwen-max
  api_key: ${DASHSCOPE_API_KEY}
  # 若使用本地部署，启用以下配置
  # base_url: http://192.168.1.100:8000/v1

# Vision LLM
vision_llm:
  provider: dashscope
  model: qwen-vl-max

# Embedding
embedding:
  provider: dashscope
  model: text-embedding-v1

# 向量库
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
  # 安全阈值，低于此分数的结果将被丢弃
  confidence_threshold: 0.7

# 记忆配置
memory:
  working:
    backend: in_memory   # in_memory | redis
  semantic:
    backend: sqlite
    db_path: ./data/db/patient_profiles.db
  episodic:
    backend: chroma
    collection: episodic_memory
    metadata_db: ./data/db/episodic_memory.db

# HIS 配置
his:
  backend: mock   # mock | api
  api_base: http://localhost:8080/his
  timeout: 5

# 可观测性
observability:
  enabled: true
  log_file: logs/traces.jsonl
  audit_log_file: logs/audit_logs.jsonl
  detail_level: standard

dashboard:
  enabled: true
  port: 8501
```
