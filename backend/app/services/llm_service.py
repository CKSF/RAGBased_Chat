from openai import OpenAI
from backend.config import Config
from typing import List, Optional

class LLMService:
    def __init__(self):
        """Initialize the Volcengine client using OpenAI SDK."""
        self.client = OpenAI(
            api_key=Config.VOLC_API_KEY,
            base_url=Config.VOLC_BASE_URL
        )
        self.model = Config.VOLC_MODEL

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
