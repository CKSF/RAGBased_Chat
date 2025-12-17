from openai import OpenAI
from backend.config import Config
from typing import List, Optional, Generator

class LLMService:
    def __init__(self):
        """Initialize the Volcengine client using OpenAI SDK."""
        self.client = OpenAI(
            api_key=Config.VOLC_API_KEY,
            base_url=Config.VOLC_BASE_URL
        )
        self.model = Config.VOLC_MODEL
        self.lite_model = Config.VOLC_LITE_MODEL  # Fast model for simple tasks
        
    def stream_response(self, user_prompt: str, system_prompt: str = None, history: List[dict] = None) -> Generator[str, None, None]:
        """
        Stream response token by token.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            # Sanitize history: Volcengine strict mode only allows 'role' and 'content'
            clean_history = [{"role": m["role"], "content": m["content"]} for m in history if m["role"] in ["user", "assistant"]]
            messages.extend(clean_history)
            
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7 
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"[LLM ERROR: {str(e)}]"

    def get_response(self, user_prompt: str, system_prompt: str = None, history: List[dict] = None) -> str:
        """
        Get a simple response from the LLM.
        """
        messages = []
        
        # 1. Add System Prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # 2. Add History (Context)
        if history:
            messages.extend(history)
            
        # 3. Add Current User Prompt
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            print(f"🤖 Calling Volcengine API [{self.model}]...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                # temperature=0.7, 
            )
            
            # Extract content
            answer = completion.choices[0].message.content
            return answer
            
        except Exception as e:
            print(f"❌ LLM API Error: {e}")
            return f"Error calling LLM: {str(e)}"
    
    def rewrite_query(self, user_query: str, history: List[dict]) -> str:
        """
        Rewrite user query based on conversation history to make it self-contained.
        Uses lightweight model for speed.
        
        Args:
            user_query: Original user question
            history: List of previous messages [{"role": "user/assistant", "content": "..."}]
            
        Returns:
            Rewritten query (or original if no rewriting needed)
        """
        # Quick check: Does query need rewriting?
        needs_rewrite = self._should_rewrite(user_query, history)
        
        if not needs_rewrite:
            print(f"ℹ️  Query is complete, no rewriting needed: {user_query}")
            return user_query
        
        # Extract recent context (last 2 turns = 4 messages)
        recent_turns = history[-4:] if len(history) >= 4 else history
        
        if not recent_turns:
            return user_query
        
        # Build context string (truncate long messages)
        context_lines = []
        for msg in recent_turns:
            role = "用户" if msg['role'] == 'user' else "助手"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            context_lines.append(f"{role}: {content}")
        context_str = "\n".join(context_lines)
        
        # Construct rewrite prompt
        rewrite_prompt = f"""基于以下对话历史，将用户的最新问题改写为一个独立完整的检索查询。

要求：
1. 如果问题已经完整独立，直接返回原问题
2. 如果问题依赖上文（如使用"它"、"这个"、"那个"、"呢"、"还有"等指代词），补充主语和背景
3. 保持原问题的核心意图
4. 输出：直接返回改写后的查询，不要任何解释或标点

对话历史：
{context_str}

用户最新问题：{user_query}

改写后的独立查询："""

        try:
            print(f"🔄 Query rewriting: {user_query}")
            
            # Use lightweight model for fast rewriting
            completion = self.client.chat.completions.create(
                model=self.lite_model,
                messages=[
                    {"role": "system", "content": "你是查询改写专家。将不完整的问题改写为独立完整的检索查询。"},
                    {"role": "user", "content": rewrite_prompt}
                ],
                max_tokens=100,  # Limit output length
                temperature=0.3   # Low temperature for consistent rewrites
            )
            
            rewritten = completion.choices[0].message.content.strip()
            print(f"✅ Rewritten query: {rewritten}")
            return rewritten
            
        except Exception as e:
            print(f"❌ Query rewrite failed: {e}, using original query")
            return user_query
    
    def _should_rewrite(self, query: str, history: List[dict]) -> bool:
        """
        Determine if query needs rewriting based on simple heuristics.
        
        Returns:
            True if query appears to depend on context
        """
        if not history:
            return False
        
        # Indicators that query is incomplete or context-dependent
        indicators = [
            len(query) < 15,  # Very short query
            any(word in query for word in ["它", "这个", "那个", "呢", "还有", "这", "那"]),  # Pronouns/references
            query.strip().endswith("？") and len(query) < 10,  # Short question
            any(phrase in query for phrase in ["详细", "举例", "为什么", "怎么", "如何"])  # Follow-up keywords
        ]
        
        return any(indicators)

