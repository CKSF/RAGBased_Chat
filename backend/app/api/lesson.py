from flask import Blueprint, request, jsonify
from backend.app.services import rag_service, llm_service

lesson_bp = Blueprint('lesson', __name__)

@lesson_bp.route('/generate', methods=['POST'])
def generate_lesson_plan():
    """
    Generate a lesson plan.
    Payload: { "topic": "高质量发展", "grade": "小学" }
    """
    data = request.json
    if not data or 'topic' not in data:
        return jsonify({"error": "Topic is required"}), 400
        
    topic = data['topic']
    grade = data.get('grade', '不限')
    
    try:
        # 1. RAG Retrieval (Deeper search)
        # We search for the topic + grade to get specific info
        query = f"{grade} {topic}"
        print(f"🔍 Searching abundant context for lesson plan: {query}")
        
        # Retrieve more docs for lesson planning (e.g., k=6)
        # Since our query method in RAGService uses ParentDocumentRetriever via .invoke(),
        # passing 'k' might not be directly supported unless we modified query logic.
        # But let's rely on standard search for now.
        documents = rag_service.query(query, k=5)
        
        context_text = ""
        sources = []
        for doc in documents:
            src = doc.metadata.get('source', 'Unknown')
            if src not in sources: sources.append(src)
            context_text += f"\n---\n{doc.page_content}\n"

        # 2. Construct Prompt
        # DeepSeek-R1 (Reasoning) is excellent at structured tasks.
        system_prompt = (
            "你是一名资深的大中小学思政课骨干教师。\n"
            "任务：请基于提供的背景资料，为一节45分钟的思政课设计一份详细的教案。\n"
            "要求：\n"
            "1. 结构完整（教学目标、重难点、教学方法、教学过程、板书设计）。\n"
            "2. 教学过程要设计具体的互动环节（如提问、讨论）。\n"
            "3. 必须充分融合背景资料中的核心观点和案例。\n"
            "4. 语言生动，符合学生认知水平。\n\n"
            f"### 背景资料:\n{context_text}"
        )
        
        user_prompt = f"请以《{topic}》为主题，设计一份针对【{grade}】学生的教案。"
        
        # 3. Call LLM
        response_text = llm_service.get_response(
            user_prompt,
            system_prompt=system_prompt
        )
        
        return jsonify({
            "lesson_plan": response_text,
            "sources": sources
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        
        # Log to file
        with open("backend_errors.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{request.remote_addr}] Lesson Error:\n{error_trace}\n{'='*50}\n")

        print(f"❌ Lesson Plan Error:\n{error_trace}", flush=True)
        return jsonify({"error": f"{str(e)}\n\nTraceback:\n{error_trace}"}), 500
