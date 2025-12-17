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

    def generate():
        try:
            # --- STEP 1: QUERY REWRITING ---
            yield format_sse('thought', "🤔 正在理解您的问题上下文...")
            rewritten_query = llm_service.rewrite_query(user_message, history)
            
            if rewritten_query != user_message:
                yield format_sse('thought', f"🔄 优化查询为: “{rewritten_query}”")

            # --- STEP 2: RAG RETRIEVAL ---
            yield format_sse('thought', "📚 正在检索思政知识库...")
            
            # Perform Query
            documents = rag_service.query(rewritten_query, k=3)
            
            # --- STEP 3: INTERMEDIATE DATA (THE COLLAPSIBLE INFO) ---
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
                    context_text += f"\n---\n[Source: {doc.metadata.get('source')}]\n{doc.page_content}\n"

            # --- STEP 4: LLM GENERATION ---
            yield format_sse('thought', "🧠 正在整理答案...")
            
            system_prompt = (
                "你是一个专业的思政课助教大模型。请根据提供的背景资料（Context）回答用户的问题。\n"
                "如果资料中没有答案，请诚实说明，并尝试用你的通用知识补充，但要明确区分。\n"
                "回答风格：严谨、准确、积极正向。\n\n"
                f"### 背景资料 (Context):\n{context_text}"
            )

            # Stream the actual text token-by-token
            for token in llm_service.stream_response(user_message, system_prompt, history):
                yield format_sse('token', token)
            
            # --- STEP 5: FINISH ---
            # Send the sources one last time so the UI can lock them in
            yield format_sse('done', {"sources": sources})

        except Exception as e:
            traceback.print_exc()
            yield format_sse('error', str(e))

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
