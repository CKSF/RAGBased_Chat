"""
Edge Case Testing Suite for Context-Aware Query Rewriting
Tests 7 critical scenarios to validate query rewriting quality
"""

import sys
import os
import requests
import time
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

API_URL = "http://localhost:5000/api/chat/send"

class TestCase:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.history: List[Dict] = []
        self.results = []
    
    def send_message(self, message: str, expect_rewrite: bool = None):
        """Send message and record result"""
        print(f"\n{'='*60}")
        print(f"📤 User: {message}")
        
        try:
            response = requests.post(
                API_URL,
                json={"message": message, "history": self.history},
                timeout=None  # 无超时限制
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get('reply', '')
                sources = data.get('sources', [])
                
                # Add to history
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": reply})
                
                print(f"✅ Bot: {reply[:150]}...")
                print(f"📚 Sources: {sources}")
                
                self.results.append({
                    "message": message,
                    "reply": reply[:200],
                    "status": "success",
                    "sources_count": len(sources)
                })
                
                return True
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                self.results.append({
                    "message": message,
                    "status": "failed",
                    "error": response.text
                })
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            self.results.append({
                "message": message,
                "status": "exception",
                "error": str(e)
            })
            return False
    
    def clear_history(self):
        """Reset conversation history"""
        self.history = []
        print("\n🔄 History cleared")


def test_1_simple_followup():
    """Test 1: 简单追问 - 改写质量"""
    print("\n\n" + "="*80)
    print("TEST 1: 简单追问 - 改写质量")
    print("="*80)
    
    test = TestCase("简单追问", "测试基本的代词引用改写")
    
    # Turn 1
    test.send_message("什么是高质量发展？")
    time.sleep(2)
    
    # Turn 2: 简单代词引用
    test.send_message("它有什么意义？")  # 应该改写为 "高质量发展有什么意义？"
    time.sleep(2)
    
    # Turn 3: 更多追问
    test.send_message("详细说明")  # 应该改写为 "高质量发展的详细说明"
    
    return test


def test_2_rewrite_quality():
    """Test 2: 序号引用 - 改写保留关键信息"""
    print("\n\n" + "="*80)
    print("TEST 2: 序号引用 - 改写保留关键信息")
    print("="*80)
    
    test = TestCase("序号引用", "测试序号引用是否保留主题")
    
    test.send_message("介绍新时代五大发展理念")
    time.sleep(2)
    
    test.send_message("第二个是什么？")  # 应该保留"五大发展理念"
    time.sleep(2)
    
    test.send_message("详细展开第三点")  # 应该保留"五大发展理念"
    
    return test


def test_3_cross_window():
    """Test 3: 跨窗口引用 - 超出5轮限制"""
    print("\n\n" + "="*80)
    print("TEST 3: 跨窗口引用 - 超出5轮限制")
    print("="*80)
    
    test = TestCase("跨窗口引用", "测试历史截断后的引用")
    
    # Turn 1
    test.send_message("什么是高质量发展？")
    time.sleep(1)
    
    # Turn 2-6: 填充窗口
    for i in range(5):
        test.send_message(f"简单问题{i+1}")
        time.sleep(1)
    
    # Turn 7: 引用Turn 1（已被截断）
    test.send_message("回到刚才的高质量发展，它与新发展理念什么关系？")
    
    return test


def test_4_service_failure():
    """Test 4: 改写服务失败 - Fallback机制"""
    print("\n\n" + "="*80)
    print("TEST 4: 改写服务失败 - Fallback机制")
    print("="*80)
    print("ℹ️  Note: 这个测试需要临时修改API key或断网才能完全验证")
    print("ℹ️  当前仅测试正常流程，实际失败场景需手动测试")
    
    test = TestCase("服务失败", "测试改写失败时的fallback")
    
    test.send_message("什么是新时代？")
    time.sleep(1)
    test.send_message("它的特征")  # 如果改写失败，应该用原查询
    
    return test


def test_5_empty_history():
    """Test 5: 空历史或首轮对话"""
    print("\n\n" + "="*80)
    print("TEST 5: 空历史或首轮对话")
    print("="*80)
    
    test = TestCase("空历史", "测试首轮不完整问题")
    
    # 直接发送不完整问题（无上下文）
    test.send_message("它有什么意义？")
    
    return test


def test_6_long_history():
    """Test 6: 超长历史消息 - 教案回复"""
    print("\n\n" + "="*80)
    print("TEST 6: 超长历史消息 - 教案回复")
    print("="*80)
    
    test = TestCase("长历史", "测试教案等长回复的处理")
    
    # 先请求生成教案（会有很长的回复）
    lesson_response = requests.post(
        "http://localhost:5000/api/lesson/generate",
        json={"topic": "高质量发展", "grade": "大学"},
        timeout=None  # 无超时限制
    )
    
    if lesson_response.status_code == 200:
        lesson_data = lesson_response.json()
        lesson_plan = lesson_data.get('lesson_plan', '')
        
        # 手动添加到历史
        test.history.append({"role": "user", "content": "生成关于高质量发展的教案"})
        test.history.append({"role": "assistant", "content": lesson_plan})
        
        print(f"✅ 教案已生成，长度: {len(lesson_plan)} 字符")
        
        # 现在追问
        time.sleep(2)
        test.send_message("加入更多案例")  # 测试长历史下的改写
    else:
        print(f"❌ 教案生成失败: {lesson_response.status_code}")
    
    return test


def test_7_multi_topic():
    """Test 7: 多主题混合引用"""
    print("\n\n" + "="*80)
    print("TEST 7: 多主题混合引用")
    print("="*80)
    
    test = TestCase("多主题", "测试同时引用多个主题")
    
    test.send_message("介绍高质量发展")
    time.sleep(2)
    
    test.send_message("介绍新发展理念")
    time.sleep(2)
    
    test.send_message("对比一下这两个概念")  # 应该同时引用两个主题
    
    return test


def print_summary(test_results: List[TestCase]):
    """打印测试总结"""
    print("\n\n" + "="*80)
    print("📊 测试总结")
    print("="*80)
    
    for test in test_results:
        print(f"\n## {test.name}")
        print(f"描述: {test.description}")
        
        success_count = sum(1 for r in test.results if r['status'] == 'success')
        total_count = len(test.results)
        
        print(f"成功率: {success_count}/{total_count}")
        
        for i, result in enumerate(test.results, 1):
            status_icon = "✅" if result['status'] == 'success' else "❌"
            print(f"  {i}. {status_icon} {result['message'][:50]}...")


if __name__ == "__main__":
    print("🚀 启动边缘情况测试套件")
    print("="*80)
    print("⚠️  确保后端服务运行在 http://localhost:5000")
    print("="*80)
    
    # Check if server is running
    try:
        health = requests.get("http://localhost:5000/health", timeout=2)
        print(f"✅ 服务器状态: {health.json()}")
    except:
        print("❌ 后端服务未运行，请先启动 run.py")
        sys.exit(1)
    
    # Run all tests
    all_tests = []
    
    try:
        all_tests.append(test_1_simple_followup())
        time.sleep(3)
        
        all_tests.append(test_2_rewrite_quality())
        time.sleep(3)
        
        all_tests.append(test_3_cross_window())
        time.sleep(3)
        
        all_tests.append(test_4_service_failure())
        time.sleep(3)
        
        all_tests.append(test_5_empty_history())
        time.sleep(3)
        
        all_tests.append(test_6_long_history())
        time.sleep(3)
        
        all_tests.append(test_7_multi_topic())
        
        # Print summary
        print_summary(all_tests)
        
        print("\n\n✅ 测试完成！请查看后端日志以了解查询改写详情。")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        print_summary(all_tests)
