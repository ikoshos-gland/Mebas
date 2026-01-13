"""
MEB RAG - Sentetik Soruları Görüntüleme
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from config.settings import get_settings

def list_questions(limit: int = 10, kazanim_code: str = None):
    settings = get_settings()
    
    client = SearchClient(
        endpoint=settings.azure_search_endpoint,
        index_name=settings.azure_search_index_questions,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )
    
    # Build filter
    filter_str = None
    if kazanim_code:
        filter_str = f"parent_kazanim_code eq '{kazanim_code}'"
    
    # Search
    results = client.search(
        search_text="*",
        filter=filter_str,
        top=limit,
        select=["id", "question_text", "difficulty", "parent_kazanim_code", "grade", "semester"]
    )
    
    print(f"\n{'='*60}")
    print("Sentetik Sorular")
    print(f"{'='*60}\n")
    
    for i, doc in enumerate(results, 1):
        print(f"[{i}] {doc['parent_kazanim_code']} | Sınıf: {doc.get('grade', '?')} | Dönem: {doc.get('semester', '?')}")
        print(f"    Zorluk: {doc.get('difficulty', '?')}")
        print(f"    Soru: {doc['question_text'][:200]}...")
        print()
    
    # Get total count
    count_result = client.search(search_text="*", filter=filter_str, include_total_count=True)
    print(f"\n📊 Toplam: {count_result.get_count()} soru bulundu")

if __name__ == "__main__":
    import sys
    
    # Usage: python scripts/view_questions.py [limit] [kazanim_code]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    kazanim_code = sys.argv[2] if len(sys.argv) > 2 else None
    
    list_questions(limit, kazanim_code)
