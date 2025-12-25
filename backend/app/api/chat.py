import json
import traceback
from flask import Blueprint, request, jsonify, stream_with_context, Response
from backend.app.services import rag_service, llm_service

chat_bp = Blueprint('chat', __name__)

def format_sse(event_type: str, data: dict):
    """Helper to format Server-Sent Events (SSE)."""
    return f"data: {json.dumps({'type': event_type, 'data': data}, ensure_ascii=False)}\n\n"

@chat_bp.route('/send', methods=['POST'])
def send_message():
    # 1. Parse Request
    req_data = request.json
    user_message = req_data.get('message', '')
    history = req_data.get('history', [])
    grade = req_data.get('grade', '通用')

    # --- FILTER LOGIC (Copied from Lesson BP) ---
    rag_filters = {}
    if grade and grade != '通用':
        if "小学" in grade:
            rag_filters = {"grade": "小学"}
        elif "初中" in grade:
            rag_filters = {"grade": "初中"}
        elif "高中" in grade:
            rag_filters = {"grade": "高中"}
        elif "大学" in grade or "本科" in grade:
            rag_filters = {"grade": "大学"}
        elif "硕士" in grade or "研究生" in grade:
            rag_filters = {"grade": "硕士"}
        elif "博士" in grade:
            rag_filters = {"grade": "博士"}

    def generate():
        try:
            # --- STEP 1: QUERY REWRITING ---
            # We append the grade to the query context so the rewriter knows the level
            rewrite_context_msg = f"{user_message} (Target Audience: {grade})"
            
            yield format_sse('thought', "🤔 正在理解您的问题上下文...")
            rewritten_query = llm_service.rewrite_query(rewrite_context_msg, history)
            
            # If rewrite failed/skipped, ensure we still search for the user message
            final_query = rewritten_query if rewritten_query else user_message

            if final_query != user_message:
                yield format_sse('thought', f"🔄 优化查询为: “{final_query}”")

            # --- STEP 2: RAG RETRIEVAL ---
            yield format_sse('thought', f"📚 正在检索思政知识库 (Filter: {rag_filters})...")
            
            # Perform Query with FILTERS
            documents = rag_service.query(final_query, k=8, filters=rag_filters)
            
            # --- STEP 3: INTERMEDIATE DATA ---
            doc_count = len(documents)
            if doc_count == 0:
                yield format_sse('thought', "⚠️ 未找到相关资料，将基于通用知识回答。")
                context_text = ""
                sources = []
            else:
                sources = list(set([doc.metadata.get('source', 'Unknown') for doc in documents]))
                yield format_sse('thought', f"✅ 检索完成：找到 {doc_count} 份相关文档。")
                yield format_sse('thought', f"📄 参考来源: {', '.join(sources)}")
                
                # --- GROUP DOCUMENTS BY SOURCE ---
                # Key: source_name, Value: list of docs
                grouped_docs = {}
                for doc in documents:
                    src = doc.metadata.get('source', 'Unknown')
                    if src not in grouped_docs:
                        grouped_docs[src] = []
                    grouped_docs[src].append(doc)
                
                context_text = ""
                # Iterate through unique sources (giving each a Book ID)
                for i, (source_name, docs) in enumerate(grouped_docs.items()):
                    # Take metadata from first doc of the group
                    first_meta = docs[0].metadata
                    doc_grade = first_meta.get('grade', '通用')
                    
                    # Header for the Book
                    context_text += f"\n【资料 {i+1}】《{source_name}》 (适用: {doc_grade})\n"
                    
                    # List content for each page/chunk in this book
                    for sub_doc in docs:
                        sub_page = sub_doc.metadata.get('page', '?')
                        # Format: [第 5 页]: Content
                        context_text += f"   - [第 {sub_page} 页]: {sub_doc.page_content}\n"
                    
                    context_text += "\n"

            # --- STEP 4: LLM GENERATION ---
            print(f"\n[DEBUG] Context Sent to LLM:\n{context_text}\n[END DEBUG]\n")
            yield format_sse('thought', "🧠 正在进行事实核查与答案生成...")
            
            
            system_prompt = (
    "你是一个极其严谨的思政课助教大模型（专注问答与概念解析）。\n"
    "你的核心任务是基于【背景资料】直接回答用户的问题，提供清晰、流畅的解释。\n\n"
    "### ⚠️ 身份与格式严格限制 (Identity & Format Constraints)\n"
    "1. **角色定义**：你现在是**问答助手**，不是教案生成器。\n"
    "2. **严禁输出教案结构**：**绝对禁止**使用“教学目标”、“教学重难点”、“教学过程”、“板书设计”、“课后作业”等教案专用格式。\n"
    "3. **文风要求**：请使用通顺的段落进行说明（Explanatory Paragraphs）。不要罗列过多的知识点大纲，而是要把逻辑讲清楚。\n\n"
    "为了确保信息的绝对准确性，你必须**严格区分**“资料库内容”与“通用推理内容”。\n\n"
    "在回答之前，请先判断提供的【背景资料】是否能回答用户的问题：\n\n"
    "**情况一：资料高度相关**\n"
    "- 必须**优先**引用资料中的原文、观点或案例。\n"
    "- 严禁脱离资料进行不必要的发挥。\n\n"
    "**情况二：资料不相关、相关度低 或 无法回答核心问题**\n"
    "- **必须**在回答的最开始，**加粗**输出以下免责声明：\n"
    "  > **【注：知识库中未匹配到高相关度资料，以下内容基于通用知识补充，仅供参考。】**\n"
    "### 核心铁律（违反即视为严重错误）：\n"
    "1. **优先原文**：回答必须基于 背景资料(Context) 内容。如果 背景资料(Context) 包含确切答案，请直接引用。\n"
    "2. **严禁编造**：如果资料中没有答案，必须诚实说明。如果用户问“红军长征”，而资料里全是“改革开放”，请直接按【情况二】处理，绝对不要强行把改革开放的内容套用到长征上。如果不确定，就说不知道。\n"
    "3. **强制索引引用 (Strict Indexing)**：这是最重要的规则。\n"
    "   - 当你引用背景资料中的内容时，**必须**在句末标注来源索引，格式为 `[1]` 或 `[2]`。\n"
    "3. **强制索引引用 (Strict Indexing)**：\n"
    "   - 在正文回答中，请使用 **`《文件名》[ID](第X页)`** 或者 **简单的 `[ID]`** (如果该ID在第一部分Evidence Base已明确列出)。\n"
    "   - 推荐在正文综合分析时，使用简单的 `[ID]` 来保持流畅度，但第一次引用某书时最好带上书名。\n"
    
    "### 🖊️ 输出结构强制要求 (必须完全遵守):\n"
    "请将你的回答严格划分为两个部分：\n\n"
    
    "#### 第一部分：📚 知识库精准依据 (Evidence Base)\n"
    "**必须按来源书籍分组展示**，格式如下 (严禁错乱)：\n"
    "**《书籍名称 A》【1】**:\n"
    "1. \"...引用原文片段...\" (第 5 页)\n"
    "2. \"...引用原文片段...\" (第 12 页)\n\n"
    "**《书籍名称 B》【2】**:\n"
    "1. \"...引用原文片段...\" (第 8 页)\n\n"
    "- 必须完全基于提供的【资料 1】、【资料 2】上下文来生成此部分。\n"
    "- 每一条引用必须精确到页码。\n\n"
    
    "#### 第二部分：💡 综合解答与助教解析 (Analysis & Answer)\n"
    "- 在此部分，基于第一部分的证据，结合你的教学逻辑，回答用户的问题。\n"
    "- **使用引用索引**：当用到上述证据时，使用 `【1】` 或 `【2】` 标注。\n"
    "- **引用位置**：引用编号必须放在**句号之后**。\n"
    "  - ✅ 正确：...促进人的全面发展。【1】\n"
    "  - ❌ 错误：...促进人的全面发展[1]。\n"
    "- 语言风格：严谨、积极、符合目标年级认知。\n"
    "### 格式强制规范 (Critical Output Rules)：\n"
    "由于前端显示限制，**系统无法渲染任何图表代码**。你必须严格遵守以下规则：\n"
    "1. **结构化降级处理**：\n"
    "   - 当你想画“流程图”时，**必须**改写为【带序号的步骤列表】(1. -> 2. -> 3.)。\n"
    "   - 当你想画“思维导图”或“层级结构”时，**必须**改写为【多级缩进列表】(- 第一层 \n  - 第二层)。\n"
    "   - 当你想画“饼图”或“表格”时，**必须**使用标准的 Markdown 表格 (| header | ...)。\n"
    "2. **绝对禁止**：\n"
    "   - 严禁输出任何 ```mermaid, ```flowchart, ```graph, ```pie 等代码块。\n"
    "   - 严禁输出 `<svg>` 标签。\n"
    "   - 输出内容必须是直接可读的纯文本 Markdown。"
    f"\n\n### 背景资料 (Indexed Context):\n{context_text}"
)

            # Stream the actual text token-by-token
            for token in llm_service.stream_response(user_message, system_prompt, history):
                yield format_sse('token', token)
            
            # Construct Rich Citations
            rich_citations = []
            if documents:
                 for doc in documents:
                    meta = doc.metadata
                    rich_citations.append({
                        "source": meta.get('source', 'Unknown'),
                        "page": meta.get('page', '?'),
                        "grade": meta.get('grade', '通用'),
                        "content": doc.page_content[:300] + "..." # Snippet for preview
                    })

            yield format_sse('done', {"sources": rich_citations})

        except Exception as e:
            traceback.print_exc()
            yield format_sse('error', str(e))

    return Response(stream_with_context(generate()), mimetype='text/event-stream')