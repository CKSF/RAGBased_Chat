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

    def generate():
        try:
            # --- STEP 1: ANALYSIS ---
            yield format_sse('thought', f"🎯 正在解析教学需求：【{grade}】{topic}...")
            
            # --- STEP 2: RAG SEARCH ---
            query = f"{grade} {topic}"
            yield format_sse('thought', f"📚 正在检索相关思政课标与素材: '{query}'...")
            
            # Retrieve 5 docs (Standard search)
            documents = rag_service.query(query, k=8)
            
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
                    context_text += f"\n---\n[Source: {doc.metadata.get('source')}]\n{doc.page_content}\n"

            # --- STEP 3: PROMPT CONSTRUCTION ---
            yield format_sse('thought', "🏗️ 正在构建教学目标、重难点与互动环节...")
            
            system_prompt = (
                "你是一名资深的大中小学思政课骨干教师。\n"
                "任务：请基于提供的背景资料，为一节45分钟的思政课设计一份详细的教案。\n"
                "要求：\n"
                "1. 结构完整（教学目标、重难点、教学方法、教学过程、板书设计）。\n"
                "2. 教学过程要设计具体的互动环节（如提问、讨论）。\n"
                "3. 必须充分融合背景资料中的核心观点和案例。\n"
                "4. 语言生动，符合学生认知水平。\n"
                "5. 格式使用 Markdown，标题清晰。\n\n"
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