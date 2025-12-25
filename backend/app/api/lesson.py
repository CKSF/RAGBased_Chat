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
    grade = req_data.get('grade', '通用')

    # --- 1. Construct RAG Filters based on Grade ---
    # We must map the user's input grade to the specific tags used in build_db.py
    # Valid tags: "小学", "初中", "高中", "大学", "硕士", "博士"
    rag_filters = {}
    
    if grade and grade != '通用':
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
                
                # --- GROUP DOCUMENTS BY SOURCE ---
                grouped_docs = {}
                for doc in documents:
                    src = doc.metadata.get('source', 'Unknown')
                    if src not in grouped_docs:
                        grouped_docs[src] = []
                    grouped_docs[src].append(doc)
                
                context_text = ""
                for i, (source_name, docs) in enumerate(grouped_docs.items()):
                    doc_grade = docs[0].metadata.get('grade', '通用')
                    context_text += f"\n【资料 {i+1}】《{source_name}》 (适用: {doc_grade})\n"
                    for sub_doc in docs:
                        sub_page = sub_doc.metadata.get('page', '?')
                        context_text += f"   - [第 {sub_page} 页]: {sub_doc.page_content}\n"
                    context_text += "\n"

            # --- STEP 3: PROMPT CONSTRUCTION ---
            yield format_sse('thought', "🏗️ 正在构建教学目标、重难点与互动环节...")
            
            system_prompt = (
                "你是一名资深的大中小学思政课骨干教师。请根据背景资料设计教案。\n"
                "任务：请基于提供的背景资料，为一节45分钟的思政课设计一份详细的教案。\n"
                "### 严禁项(Negative Constraints)\n"
                f"1. 年级严格限制：当前目标年级为【{grade}】"
                "   - 如果是小学：**严禁**出现初中/高中/大学/研究生/博士的复杂的政治术语、哲学概念或过深的理论分析。\n"
                "   - 如果是大学：**严禁**使用低幼化的语言或简单的生活案例。\n"
                "   - **绝对禁止**发生“年级泄漏”。\n"
                "2. **严禁捏造引用**：教案中的引用必须来自背景资料。\n\n"
                "### 🖊️ 输出结构强制要求 (必须完全遵守):\n"
                "请将你的回答严格划分为两个部分：\n\n"
                "#### 第一部分：📚 知识库精准依据 (Evidence Base)\n"
                "**必须按来源书籍分组展示**，格式如下：\n"
                "**《书籍名称 A》【1】**:\n"
                "1. \"...引用原文片段...\" (第 5 页)\n"
                "2. \"...引用原文片段...\" (第 12 页)\n\n"
                "#### 第二部分：📝 教案主体 (Lesson Plan)\n"
                "1. 结构完整（教学目标、重难点、教学方法、教学过程、板书设计）。\n"
                "2. 在【教学过程】中引用资料时，使用 `【1】` 标注来源。\n"
                "3. **引用位置**：引用编号必须放在**句号之后** (e.g. ...教学内容。【1】)。\n"
                
                f"### 背景资料 (Indexed Context):\n{context_text}"
            )
            
            user_prompt = f"请以《{topic}》为主题，设计一份针对【{grade}】学生的教案。"

            # --- STEP 4: LLM STREAMING ---
            yield format_sse('thought', "✍️ 开始撰写教案...")
            
            # Reusing the existing stream_response method from llm_service
            for token in llm_service.stream_response(user_prompt, system_prompt, history=[]):
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
                        "content": doc.page_content[:300] + "..." # Snippet
                    })

            yield format_sse('done', {"sources": rich_citations})

        except Exception as e:
            traceback.print_exc()
            yield format_sse('error', str(e))

    return Response(stream_with_context(generate()), mimetype='text/event-stream')