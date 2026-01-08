"""
MEB RAG - Index İstatistiklerini Görüntüleme
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from config.settings import get_settings

def print_index_stats():
    settings = get_settings()
    
    indexes = [
        ("Images", settings.azure_search_index_images),
        ("Textbooks (Chunks)", settings.azure_search_index_kitap),
        ("Questions", settings.azure_search_index_questions)
    ]
    
    print("\n" + "="*50)
    print("Azure AI Search Index İstatistikleri")
    print("="*50)
    
    credential = AzureKeyCredential(settings.azure_search_api_key)
    
    for label, index_name in indexes:
        try:
            client = SearchClient(
                endpoint=settings.azure_search_endpoint,
                index_name=index_name,
                credential=credential
            )
            count = client.get_document_count()
            print(f"[INFO] {label:<20} : {count} documents ({index_name})")
        except Exception as e:
            print(f"[ERROR] {label:<20} : Erişim Hatası ({e})")
            
    print("="*50 + "\n")

if __name__ == "__main__":
    print_index_stats()
