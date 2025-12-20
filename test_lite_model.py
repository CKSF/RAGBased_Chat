import os
import sys

# Ensure backend modules can be imported
sys.path.append(os.getcwd())

from backend.config import Config
from backend.app.services.llm_service import LLMService

def test_lite_model():
    print("--------------------------------------------------")
    print("🧪 Testing Volcengine Lite Model Configuration")
    print("--------------------------------------------------")
    
    # Check Config
    try:
        Config.validate()
        print(f"✅ Configuration Valid")
    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        return

    print(f"📋 Configured Lite Model: '{Config.VOLC_LITE_MODEL}'")
    
    # Initialize Service
    try:
        service = LLMService()
        print("✅ LLMService Initialized")
    except Exception as e:
        print(f"❌ LLMService Init Failed: {e}")
        return

    # Test Call
    print("\n🔄 Sending simple test request...")
    try:
        # Manually calling the client to test the specific model
        response = service.client.chat.completions.create(
            model=Config.VOLC_LITE_MODEL,
            messages=[
                {"role": "user", "content": "Hello! Reply with 'Lite model is working'."}
            ],
            max_tokens=20
        )
        
        reply = response.choices[0].message.content
        print(f"✅ Success! Response: {reply}")
        
    except Exception as e:
        print(f"\n❌ FAILED to call model '{Config.VOLC_LITE_MODEL}'")
        print(f"   Error: {e}")
        print("\n💡 Troubleshooting Tips:")
        print("   1. Check if 'doubao-lite-4k' is the correct Endpoint ID in your Volcengine console.")
        print("   2. It might be 'doubao-lite-32k' or a specific ID like 'ep-2024...'.")

if __name__ == "__main__":
    test_lite_model()
