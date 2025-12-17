import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.rag_service import RAGService

print("🔍 RAG 诊断工具")
print("="*60)

# 初始化
print("\n1️⃣ 初始化 RAG Service...")
try:
    rag = RAGService(persist_directory="chroma_db", parent_store_directory="doc_store")
    print("   ✅ RAG Service 初始化成功")
except Exception as e:
    print(f"   ❌ 初始化失败: {e}")
    sys.exit(1)

# 检查向量存储
print("\n2️⃣ 检查向量存储...")
if rag.vector_store is None:
    print("   ❌ 向量存储未初始化")
    sys.exit(1)
else:
    print("   ✅ 向量存储已初始化")

# 检查文档数量
print("\n3️⃣ 检查数据库文档数量...")
try:
    count = rag.vector_store._collection.count()
    print(f"   📊 子块数量: {count}")
    if count == 0:
        print("   ⚠️  数据库为空！请运行 'python build_db.py'")
except Exception as e:
    print(f"   ❌ 无法获取数量: {e}")

# 检查doc_store
print("\n4️⃣ 检查父文档存储...")
doc_store_files = os.listdir("doc_store") if os.path.exists("doc_store") else []
print(f"   📄 父块文件数量: {len(doc_store_files)}")
if len(doc_store_files) == 0:
    print("   ⚠️  父文档存储为空！")

# 测试查询
print("\n5️⃣ 测试查询...")
test_queries = [
    "高质量发展",
    "新时代",
    "五大发展理念"
]

for query in test_queries:
    print(f"\n   查询: '{query}'")
    try:
        results = rag.query(query, k=3)
        print(f"   ✅ 返回 {len(results)} 个文档")
        
        if len(results) > 0:
            print(f"   📝 首个结果预览: {results[0].page_content[:100]}...")
            print(f"   📚 来源: {results[0].metadata.get('source', 'Unknown')}")
        else:
            print("   ⚠️  返回空数组")
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")

print("\n" + "="*60)
print("🏁 诊断完成")
print("\n💡 如果发现数据库为空，请运行:")
print("   python build_db.py")
