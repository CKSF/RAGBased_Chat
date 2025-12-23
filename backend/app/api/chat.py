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
    # Get grade, default to '不限' (No Filter)
    grade = req_data.get('grade', '不限')

    # --- FILTER LOGIC (Copied from Lesson BP) ---
    rag_filters = {}
    if grade and grade != '不限':
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
                
                context_text = ""
                for doc in documents:
                    # Display Grade in Context so LLM sees it
                    doc_grade = doc.metadata.get('grade', '通用')
                    context_text += f"\n---\n[Source: {doc.metadata.get('source')} | 适用: {doc_grade}]\n{doc.page_content}\n"

            # --- STEP 4: LLM GENERATION ---
            yield format_sse('thought', "🧠 正在整理答案...")
            

            
            system_prompt = (
    "你是一个专业的思政课助教大模型。请根据提供的【背景资料】(Context) 客观、严谨地回答用户的问题。\n\n"
    "在回答之前，请先判断提供的【背景资料】是否能回答用户的问题：\n\n"
    "**情况一：资料高度相关**\n"
    "- 必须**优先**引用资料中的原文、观点或案例。\n"
    "- 严禁脱离资料进行不必要的发挥。\n\n"
    "**情况二：资料不相关、相关度低 或 无法回答核心问题**\n"
    "- **必须**在回答的最开始，**加粗**输出以下免责声明：\n"
    "  > **【注：知识库中未匹配到高相关度资料，以下内容基于通用知识补充，仅供参考。】**\n"
    "### 核心原则：\n"
    "1. **优先原文**：回答必须基于 背景资料(Context) 内容。如果 背景资料(Context) 包含确切答案，请直接引用。\n"
    "2. **严禁编造**：如果资料中没有答案，必须诚实说明。如果用户问“红军长征”，而资料里全是“改革开放”，请直接按【情况二】处理，绝对不要强行把改革开放的内容套用到长征上。如果不确定，就说不知道。\n"
    "3. **严禁捏造直接引用**：如果要加入直接引用，必须确认引用内容是背景资料中的原文，严禁出现任何使用通用知识补充、自由发挥和自行捏造的引用。直接引用在回答中最多出现三次，且根据你确定发生过的可验证的直接引用排序。引用必须带有信息来源的标注（如：根据《...》）。\n"
    "4. **风格要求**：严谨、准确、积极正向。\n"
    "5. **引用说明**：回答中注明信息的来源（如：根据《...》）。\n\n"
    f"6. 年级严格限制：当前设定的目标用户年级为【{grade}】。或者如果用户提到了目标年级（例如“大学生”、“小学生”、或者“小学四年级”时）"
                "   - 如果是小学：**严禁**出现初中/高中/大学/研究生/博士的复杂的政治术语、哲学概念或过深的理论分析。\n"
                "   - 如果是大学：**严禁**使用低幼化的语言或简单的生活案例。\n"
                "   - **绝对禁止**发生“年级泄漏”（如：明明是五年级教案，却引用了六年级或初中的课标要求）。低年级教案禁止使用一切来源自高年级的资料，包括概念、教案、案例、演示等一切模态的信息。\n"
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
    f"\n\n### 背景资料 (Context):\n{context_text}"
)

            # Stream the actual text token-by-token
            for token in llm_service.stream_response(user_message, system_prompt, history):
                yield format_sse('token', token)
            
            yield format_sse('done', {"sources": sources})

        except Exception as e:
            traceback.print_exc()
            yield format_sse('error', str(e))

    return Response(stream_with_context(generate()), mimetype='text/event-stream')