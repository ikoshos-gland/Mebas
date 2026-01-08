"""
MEB RAG System - Index Oluşturma Script
Bu script Azure AI Search'te gerekli indexleri oluşturur.

Kullanım:
    python scripts/create_indexes.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

from config.settings import get_settings
from src.vector_store.index_schema import (
    create_question_index_schema,
    create_image_index_schema,
    create_textbook_chunk_index_schema
)


def main():
    print("=" * 50)
    print("MEB RAG - Azure AI Search Index Oluşturucu")
    print("=" * 50)
    
    # Get settings
    settings = get_settings()
    
    print(f"\n📍 Endpoint: {settings.azure_search_endpoint}")
    print(f"📦 API Version: 2024-07-01")
    
    # Create index client
    client = SearchIndexClient(
        endpoint=settings.azure_search_endpoint,
        credential=AzureKeyCredential(settings.azure_search_api_key)
    )
    
    # Define indexes to create
    indexes = [
        {
            "name": settings.azure_search_index_questions,
            "schema": create_question_index_schema(settings.azure_search_index_questions),
            "description": "Sentetik Sorular (Hybrid Search)"
        },
        {
            "name": settings.azure_search_index_kitap,
            "schema": create_textbook_chunk_index_schema(settings.azure_search_index_kitap),
            "description": "Ders Kitabı Chunk'ları"
        },
        {
            "name": settings.azure_search_index_images,
            "schema": create_image_index_schema(settings.azure_search_index_images),
            "description": "Ders Kitabı Görselleri"
        }
    ]
    
    print(f"\n🔧 {len(indexes)} index oluşturulacak:\n")
    
    for idx_info in indexes:
        name = idx_info["name"]
        schema = idx_info["schema"]
        desc = idx_info["description"]
        
        try:
            # Check if exists
            existing = list(client.list_index_names())
            
            if name in existing:
                print(f"⚠️  {name}")
                print(f"   └─ Zaten mevcut. Silip yeniden oluşturulsun mu? (y/n): ", end="")
                response = input().strip().lower()
                
                if response == 'y':
                    client.delete_index(name)
                    print(f"   └─ Silindi.")
                    client.create_index(schema)
                    print(f"   └─ ✅ Yeniden oluşturuldu!")
                else:
                    print(f"   └─ Atlandı.")
                    continue
            else:
                client.create_index(schema)
                print(f"✅ {name}")
                print(f"   └─ {desc}")
            
            # Print schema info
            fields = [f.name for f in schema.fields]
            print(f"   └─ Fields: {', '.join(fields[:5])}...")
            
        except Exception as e:
            print(f"❌ {name}")
            print(f"   └─ Hata: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Index oluşturma tamamlandı!")
    print("=" * 50)
    
    # Show verification command
    print("\n📋 Doğrulama için Azure CLI:")
    print(f"   az search index list --service-name <search-name> --resource-group <rg>")


if __name__ == "__main__":
    main()
