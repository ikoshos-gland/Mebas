"""
MEB RAG Sistemi - Azure AI Search Index Şemaları
Sentetik sorular ve görseller için Hybrid Search index tanımları
"""
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)


def create_question_index_schema(index_name: str = "meb-sentetik-sorular-index") -> SearchIndex:
    """
    Create index schema for synthetic questions.
    
    Features:
    - Turkish analyzer for keyword search
    - Vector search with HNSW algorithm
    - Semantic reranker for improved accuracy
    - Grade and subject filters for pedagogical correctness
    """
    return SearchIndex(
        name=index_name,
        fields=[
            # Key field
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            # Question content - searchable with Turkish analyzer
            SearchField(
                name="question_text",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"
            ),
            # Metadata - filterable/facetable
            SearchField(
                name="difficulty",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="question_type",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            # Parent kazanım - for grouping
            SearchField(
                name="parent_kazanim_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SearchField(
                name="parent_kazanim_code",
                type=SearchFieldDataType.String,
                filterable=True,
                searchable=True
            ),
            SearchField(
                name="parent_kazanim_desc",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            # Parent kazanim title - provides context for sub-items
            SearchField(
                name="kazanim_title",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"
            ),
            # Filters for pedagogical correctness - CRITICAL!
            SearchField(
                name="grade",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="subject",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            # Semester - 1 or 2 (dönem)
            SearchField(
                name="semester",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True
            ),
            # Vector embedding for semantic search
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=3072,
                vector_search_profile_name="question-profile"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-algo",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="question-profile",
                    algorithm_configuration_name="hnsw-algo"
                )
            ]
        ),
        # Semantic reranker - 20-30% accuracy improvement!
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="question_text"),
                        content_fields=[
                            SemanticField(field_name="kazanim_title"),
                            SemanticField(field_name="parent_kazanim_desc")
                        ]
                    )
                )
            ]
        )
    )


def create_image_index_schema(index_name: str = "meb-images-index") -> SearchIndex:
    """
    Create index schema for textbook images.

    Images are searchable by:
    - Caption text (GPT-4o generated)
    - Image type (diagram, graph, photo, etc.)
    - Related kazanım
    """
    return SearchIndex(
        name=index_name,
        fields=[
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            # Caption from GPT-4o Vision
            SearchField(
                name="caption",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"
            ),
            # Image classification
            SearchField(
                name="image_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            # Location
            SearchField(
                name="page_number",
                type=SearchFieldDataType.Int32,
                filterable=True
            ),
            SearchField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            # Related content - links image to surrounding text context
            SearchField(
                name="related_text",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"  # Turkish analyzer for better search
            ),
            # Document hierarchy for navigation (e.g., "Ünite 1/Konu 2/Alt Başlık")
            SearchField(
                name="hierarchy_path",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True  # Allow filtering by hierarchy prefix
            ),
            # File path for retrieval
            SearchField(
                name="image_path",
                type=SearchFieldDataType.String
            ),
            SearchField(
                name="width",
                type=SearchFieldDataType.Int32
            ),
            SearchField(
                name="height",
                type=SearchFieldDataType.Int32
            ),
            # Grade/Subject for filtering - CRITICAL for pedagogical correctness
            SearchField(
                name="grade",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="subject",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="textbook_id",
                type=SearchFieldDataType.Int32,
                filterable=True
            ),
            # Vector embedding of caption
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=3072,
                vector_search_profile_name="image-profile"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-algo",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="image-profile",
                    algorithm_configuration_name="hnsw-algo"
                )
            ]
        ),
        # Semantic search for improved image retrieval
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="caption"),
                        content_fields=[
                            SemanticField(field_name="related_text"),
                            SemanticField(field_name="hierarchy_path")
                        ]
                    )
                )
            ]
        )
    )


def create_kazanim_index_schema(index_name: str = "meb-kazanimlar-index") -> SearchIndex:
    """
    Create index schema for MEB kazanımları (learning objectives).

    This is the PRIMARY index for curriculum alignment.
    Kazanımlar are the official MEB learning objectives that define
    what students should learn at each grade level.

    Features:
    - Turkish analyzer for keyword search
    - Vector search with HNSW algorithm
    - Semantic reranker for improved accuracy
    - Grade/subject/semester filters for curriculum alignment
    """
    return SearchIndex(
        name=index_name,
        fields=[
            # Key field
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            # Kazanım code - e.g., "BİY.9.1.1.a"
            SearchField(
                name="code",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True,
                sortable=True
            ),
            # Parent code for sub-items - e.g., "BİY.9.1.1" for "BİY.9.1.1.a"
            SearchField(
                name="parent_code",
                type=SearchFieldDataType.String,
                filterable=True,
                searchable=True
            ),
            # Kazanım description - the actual learning objective text
            SearchField(
                name="description",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"
            ),
            # Parent kazanım title (for sub-items)
            SearchField(
                name="title",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"
            ),
            # Grade level - CRITICAL for pedagogical correctness
            SearchField(
                name="grade",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True,
                sortable=True
            ),
            # Subject code - e.g., "BİY", "M", "F"
            SearchField(
                name="subject",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            # Semester - 1 or 2 (dönem)
            SearchField(
                name="semester",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True
            ),
            # Vector embedding for semantic search
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=3072,
                vector_search_profile_name="kazanim-profile"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-algo",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="kazanim-profile",
                    algorithm_configuration_name="hnsw-algo"
                )
            ]
        ),
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="title"),
                        content_fields=[
                            SemanticField(field_name="description"),
                            SemanticField(field_name="code")
                        ]
                    )
                )
            ]
        )
    )


def create_textbook_chunk_index_schema(index_name: str = "meb-kitaplar-index") -> SearchIndex:
    """
    Create index schema for textbook chunks.
    
    For direct textbook content search (not via synthetic questions).
    """
    return SearchIndex(
        name=index_name,
        fields=[
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            # Content
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True,
                analyzer_name="tr.microsoft"
            ),
            # Metadata
            SearchField(
                name="chunk_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="hierarchy_path",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="page_range",
                type=SearchFieldDataType.String
            ),
            SearchField(
                name="is_sidebar",
                type=SearchFieldDataType.Boolean,
                filterable=True
            ),
            # Textbook info
            SearchField(
                name="textbook_id",
                type=SearchFieldDataType.Int32,
                filterable=True
            ),
            SearchField(
                name="textbook_name",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True,
                analyzer_name="tr.microsoft"
            ),
            SearchField(
                name="chapter_id",
                type=SearchFieldDataType.Int32,
                filterable=True
            ),
            SearchField(
                name="grade",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True
            ),
            SearchField(
                name="subject",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            # Semester - 1 or 2 (dönem) - critical for curriculum alignment
            SearchField(
                name="semester",
                type=SearchFieldDataType.Int32,
                filterable=True,
                facetable=True
            ),
            # Vector
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=3072,
                vector_search_profile_name="chunk-profile"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-algo",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="chunk-profile",
                    algorithm_configuration_name="hnsw-algo"
                )
            ]
        ),
        semantic_search=SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="hierarchy_path"),
                        content_fields=[
                            SemanticField(field_name="content")
                        ]
                    )
                )
            ]
        )
    )
