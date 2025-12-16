from flask import Blueprint, request, jsonify
from backend.app.services import rag_service, llm_service

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/send', methods=['POST'])
def send_message():
    """
    Handle chat messages.
    Payload: { "message": "什么是思政课?", "history": [...] }
    """
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
        
    user_message = data['message']
    history = data.get('history', [])
    
    try:
        # 1. RAG
        print(f"DEBUG: Entering RAG query for '{user_message}'", flush=True)
        documents = rag_service.query(user_message, k=3)
        print(f"DEBUG: RAG query complete. Found {len(documents)} docs", flush=True)

        context_text = ""
        sources = []
        for doc in documents:
            source_name = doc.metadata.get('source', 'Unknown')
            if source_name not in sources:
                sources.append(source_name)
            context_text += f"\n---\n[Source: {source_name}]\n{doc.page_content}\n"

        # 2. Prompt
        system_prompt = (
            "你是一个专业的思政课助教大模型。请根据提供的背景资料（Context）回答用户的问题。\n"
            "如果资料中没有答案，请诚实说明，并尝试用你的通用知识补充，但要明确区分。\n"
            "回答风格：严谨、准确、积极正向。\n\n"
            f"### 背景资料 (Context):\n{context_text}"
        )
        
        # 3. LLM
        print(f"DEBUG: Preparing to call LLM...", flush=True)
        response_text = llm_service.get_response(
            user_message, 
            system_prompt=system_prompt,
            history=history
        )
        print(f"DEBUG: LLM returned response length: {len(response_text)}", flush=True)
        
        return jsonify({
            "reply": response_text,
            "sources": sources,
            "context_used": context_text[:200] + "..." 
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        # Log to file
        with open("backend_errors.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{request.remote_addr}] Chat Error:\n{error_trace}\n{'='*50}\n")
            
        print(f"❌ Chat Error:\n{error_trace}", flush=True)
        return jsonify({"error": f"{str(e)}\n\nTraceback:\n{error_trace}"}), 500
