# 思政领域 RAG 大模型应用 (SiZheng Chatbox)

本项目旨在开发一个基于 RAG (Retrieval-Augmented Generation) 技术的思政教学辅助系统，核心功能包括智能答疑和教案生成。

## 🚀 快速启动

### 前置要求
- Python 3.12+
- Node.js 16+
- `.env` 文件配置（包含 Volcengine API Key）

### 1. 启动后端 (Waitress Server)

```powershell
# 1. 激活虚拟环境
.\.venv\Scripts\activate

# 2. 运行后端服务（使用 Waitress 生产级服务器）
python run.py
```
后端服务将在 `http://localhost:5000` 启动。

### 2. 启动前端 (Next.js)

打开新的终端窗口：

```powershell
# 1. 进入前端目录
cd frontend

# 2. 安装依赖（首次运行）
npm install

# 3. 启动开发服务器
npm run dev
```
前端应用将在 `http://localhost:3000` 启动。

### 3. 构建知识库（首次部署或数据更新时）

```powershell
python build_db.py
```
该脚本会扫描 `data/` 目录下的 PDF 文件，构建向量数据库。

## 🔍 诊断与测试

项目包含自检工具，用于验证 RAG 及其上下文感知功能。

- **RAG 诊断工具**：检查数据库状态和检索功能
  ```powershell
  python diagnose_rag.py
  ```

- **边缘情况测试套件**：测试查询改写、历史窗口、长文本处理等 7 种场景
  ```powershell
  python test_edge_cases.py
  ```

## 🌟 项目功能

### 1. 智能答疑 (Q&A)
- **RAG 检索增强生成**：基于本地文档库精准回答
- **上下文感知 (Context-Aware)**：
  - **滑动窗口历史**：自动保留最近 5 轮对话（10条消息），精准管理 Token
  - **智能查询改写**：识别代词（"它是什么"）和追问，自动改写为独立完整查询
- **双模型驱动**：
  - **轻量模型 (Doubao-lite)**：极速处理查询改写
  - **主力模型 (DeepSeek-R1)**：深度推理生成高质量回答
- **可溯源**：每个回答都标注来源文档

### 2. 教案生成 (Lesson Plan)
- **结构化生成**：自动生成包含教学目标、过程、互动环节的完整教案
- **年级适配**：支持小学、初中、高中、大学分级定制
- **知识融合**：充分利用背景资料中的核心观点和案例

## 💻 技术架构

### 核心技术栈
- **后端**: Flask + Waitress (WSGI Server)
- **AI 框架**: LangChain
- **向量数据库**: ChromaDB (Parent Document Retriever)
- **LLM**: Volcengine DeepSeek-R1 (推理) + Doubao-lite (工具/改写)
- **前端**: Next.js 16 + Tailwind CSS
- **UI 组件**: Lucide React, React Markdown

### 架构设计

```
浏览器 (localhost:3000)
    ↓ (直接 HTTP 请求，启用 CORS)
Waitress Server (localhost:5000)
    ↓
Flask Application
    ├─ /api/chat/send 
    │     ↓
    │   [Context Processing] 
    │   1. Sliding Window (Last 5 turns)
    │   2. Query Rewrite (Lite Model)
    │     ↓
    │   [RAG Retrieval]
    │   Parent Document Retriever
    │     ↓
    │   [Generation]
    │   LLM Service (DeepSeek)
    │
    └─ /api/lesson/generate → Structure Prompt → DeepSeek
```

### 目录结构

```text
SiZhengChatbox/
├── backend/                  # Python Flask 后端
│   ├── app/
│   │   ├── api/              # API 路由 (chat.py, lesson.py)
│   │   ├── services/         # 核心服务 (rag_service, llm_service, pdf_service)
│   │   └── __init__.py       # Flask 应用工厂 (启用 CORS)
│   ├── config.py             # 配置管理
│   └── requirements.txt      # Python 依赖
├── frontend/                 # Next.js 前端
│   ├── src/                  # React 源代码
├── data/                     # PDF 资料库
├── chroma_db/                # 向量数据库（子块索引）
├── doc_store/                # 父文档存储（完整检索结果）
├── build_db.py               # 知识库构建脚本
├── diagnose_rag.py           # RAG 诊断脚本
├── test_edge_cases.py        # 边缘情况测试脚本
├── run.py                    # 后端启动脚本
└── .env                      # 环境变量（API Keys）
```

## 🔧 关键技术决策

### Context-Aware Retrieval (上下文感知检索)
- **智能改写**：解决了多轮对话中指代不清的问题（如"它怎么样"）。系统在检索前使用轻量级模型将用户问题改写为包含必要上下文的完整查询。
- **滑动窗口**：限制历史记录为最后 5 轮，防止 Token 溢出，同时保留足够的近期上下文。

### Parent Document Retriever
- **小块检索，大块生成**：用小粒度的子块（400字符）进行高精度检索，但返回完整的父块（2000字符）作为上下文，确保 LLM 理解完整逻辑。

### Waitress Server
- **生产级稳定性**：替代 Flask 自带的开发服务器，解决 Windows 下多线程/SQLite 冲突导致的连接不稳定问题。

### 直接后端连接
- **跨域请求 (CORS)**：前端直接访问 `http://localhost:5000`，绕过 Next.js 代理层，提升请求稳定性。

## ⚙️ 开发说明

### 添加新文档
1. 将 PDF 文件放入 `data/` 目录
2. 运行 `python build_db.py` 重建索引
3. 重启后端服务

### 环境变量配置 (`.env`)
```env
# 主力模型配置 (用于生成回答)
VOLC_API_KEY=your_volcengine_api_key
VOLC_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
VOLC_MODEL=ep-xxxxx-deepseek-r1

# 轻量级模型配置 (用于查询改写)
VOLC_LITE_MODEL=ep-xxxxx-doubao-lite-4k
```

## 📝 更新日志

- **2025-12-16**: 实现上下文感知检索（智能改写 + 滑动窗口），添加边缘情况测试套件，文档全面更新。
- **2025-12-16**: 完成前后端联调，切换至 Waitress 服务器，实现稳定的统一对话界面。