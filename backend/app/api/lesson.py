import json
import traceback
from flask import Blueprint, request, Response, stream_with_context
from backend.app.services import rag_service, llm_service

lesson_bp = Blueprint('lesson', __name__)

def format_sse(event_type: str, data: dict):
    """Helper to format Server-Sent Events."""
    return f"data: {json.dumps({'type': event_type, 'data': data}, ensure_ascii=False)}\n\n"

@lesson_bp.route('/generate', methods=['POST'])
def generate_lesson_plan():
    """
    Generate a lesson plan via Streaming.
    Payload: { "topic": "高质量发展", "grade": "小学" }
    """
    req_data = request.json
    topic = req_data.get('topic', '')
    grade = req_data.get('grade', '不限')

    # --- 1. Construct RAG Filters based on Grade ---
    # We must map the user's input grade to the specific tags used in build_db.py
    # Valid tags: "小学", "初中", "高中", "大学", "硕士", "博士"
    rag_filters = {}
    
    if grade and grade != '不限':
        # Simple substring matching ensures that "小学五年级" -> filter: "小学"
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
        # Note: If no match (e.g. "成人教育"), filters remains empty, relying on semantic search only.

    def generate():
        try:
            # --- STEP 1: ANALYSIS ---
            yield format_sse('thought', f"🎯 正在解析教学需求：【{grade}】{topic}...")
            
            # --- STEP 2: RAG SEARCH ---
            # We keep grade in the text query for semantic reinforcement, 
            # but the heavy lifting is done by 'rag_filters'
            query = f"{grade} {topic}"
            yield format_sse('thought', f"📚 正在检索相关思政课标与素材: '{query}' (Filter: {rag_filters})...")
            
            # Retrieve docs with Metadata Filtering
            # This ensures University content NEVER leaks into Primary School queries
            documents = rag_service.query(query, k=8, filters=rag_filters)
            
            if not documents:
                yield format_sse('thought', "⚠️ 未找到特定素材，将基于通用教学理论设计。")
                context_text = ""
                sources = []
            else:
                sources = list(set([doc.metadata.get('source', 'Unknown') for doc in documents]))
                yield format_sse('thought', f"✅ 找到 {len(documents)} 份参考资料，正在提取核心观点...")
                yield format_sse('thought', f"📄 参考来源: {', '.join(sources)}")
                
                context_text = ""
                for doc in documents:
                    # Append source and grade info to context for LLM visibility
                    doc_grade = doc.metadata.get('grade', '通用')
                    context_text += f"\n---\n[Source: {doc.metadata.get('source')} | 适用年级: {doc_grade}]\n{doc.page_content}\n"

            # --- STEP 3: PROMPT CONSTRUCTION ---
            yield format_sse('thought', "🏗️ 正在构建教学目标、重难点与互动环节...")
            
            # The prompt you provided:
            system_prompt = (
                "你是一名资深的大中小学思政课骨干教师。请根据背景资料设计教案。\n"
                "任务：请基于提供的背景资料，为一节45分钟的思政课设计一份详细的教案。\n"
                "### 严禁项(Negative Constraints)\n"
                f"1. 年级严格限制：当前目标年级为【{grade}】"
                "   - 如果是小学：**严禁**出现初中/高中/大学/研究生/博士的复杂的政治术语、哲学概念或过深的理论分析。\n"
                "   - 如果是大学：**严禁**使用低幼化的语言或简单的生活案例。\n"
                "   - **绝对禁止**发生“年级泄漏”（如：明明是五年级教案，却引用了六年级或初中的课标要求）。低年级教案禁止使用一切来源自高年级的资料，包括概念、教案、案例、演示等一切模态的信息。\n"
                "2. **严禁捏造引用**：教案中的引用必须来自背景资料。如果没有，就不要写引用。\n\n"
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
                "3. **严禁捏造直接引用**：如果要加入直接引用，必须确认引用内容是背景资料中的原文，严禁出现任何使用通用知识补充、自由发挥和自行捏造的引用。引用必须带有信息来源的标注（如：根据《...》）。\n"
                "4. **风格要求**：严谨、准确、积极正向。\n"
                "5. **引用说明**：回答中注明信息的来源（如：根据《...》）。\n\n"
                "要求：\n"
                "1. 结构完整（教学目标、重难点、教学方法、教学过程、板书设计）。\n"
                "2. 教学过程要设计具体的互动环节（如提问、讨论）。\n"
                "3. 必须充分融合背景资料中的核心观点和案例。\n"
                "4. 语言生动，符合学生认知水平。\n"
                "5. 格式使用标准 Markdown（列表、表格），**严禁使用 Mermaid、Graphviz 或 ASCII 字符画**。\n"
                "   - 板书设计请务必使用 **Markdown 表格** 或 **列表** 呈现，不要用键盘字符拼凑框图。\n\n"
                f"### 背景资料:\n{context_text}"
            )
            
            user_prompt = f"请以《{topic}》为主题，设计一份针对【{grade}】学生的教案。"

            # --- STEP 4: LLM STREAMING ---
            yield format_sse('thought', "✍️ 开始撰写教案...")
            
            # Reusing the existing stream_response method from llm_service
            for token in llm_service.stream_response(user_prompt, system_prompt, history=[]):
                yield format_sse('token', token)
            
            # --- STEP 5: FINISH ---
            yield format_sse('done', {"sources": sources})

        except Exception as e:
            traceback.print_exc()
            yield format_sse('error', str(e))

    return Response(stream_with_context(generate()), mimetype='text/event-stream')