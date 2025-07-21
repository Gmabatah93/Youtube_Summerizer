"""
Unit tests for post-processing functions.
Run this to verify the post-processing module works correctly.
"""

import sys
sys.path.append('/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer')

from src.rag_post_processing import (
    clean_document_content,
    is_high_quality_content,
    calculate_chunk_relevance,
    post_process_documents,
    rerank_documents,
    aggregate_and_compress,
    compress_content
)
from langchain_core.documents import Document


def test_clean_document_content():
    """Test content cleaning function."""
    print("🧹 Testing clean_document_content...")
    
    dirty_content = """
    [Music] This is a test transcript with [Applause] noise.
    Visit our website at https://example.com for more info.
    (inaudible) We also have    excessive    whitespace.
    """
    
    cleaned = clean_document_content(dirty_content)
    print(f"Original: {dirty_content.strip()}")
    print(f"Cleaned: {cleaned}")
    
    # Check if artifacts were removed
    assert "[Music]" not in cleaned
    assert "[Applause]" not in cleaned
    assert "(inaudible)" not in cleaned
    assert "https://example.com" not in cleaned
    assert "    " not in cleaned  # No excessive whitespace
    print("✅ Content cleaning works!")


def test_is_high_quality_content():
    """Test quality assessment function."""
    print("\n📏 Testing is_high_quality_content...")
    
    # High quality document
    good_doc = Document(
        page_content="This is a comprehensive tutorial on machine learning algorithms with detailed explanations.",
        metadata={'view_count': 5000}
    )
    
    # Low quality document
    bad_doc = Document(
        page_content="[Music] [Music] [Music] inaudible unclear [Applause]",
        metadata={'view_count': 50}
    )
    
    # Short document
    short_doc = Document(
        page_content="Too short",
        metadata={'view_count': 1000}
    )
    
    assert is_high_quality_content(good_doc, good_doc.page_content) == True
    assert is_high_quality_content(bad_doc, bad_doc.page_content) == False
    assert is_high_quality_content(short_doc, short_doc.page_content) == False
    
    print("✅ Quality assessment works!")


def test_calculate_chunk_relevance():
    """Test relevance calculation."""
    print("\n🎯 Testing calculate_chunk_relevance...")
    
    doc = Document(
        page_content="This tutorial covers machine learning algorithms and neural networks in detail."
    )
    
    query1 = "machine learning tutorial"
    query2 = "cooking recipes"
    
    relevance1 = calculate_chunk_relevance(doc, query1)
    relevance2 = calculate_chunk_relevance(doc, query2)
    
    print(f"Relevance to '{query1}': {relevance1:.2f}")
    print(f"Relevance to '{query2}': {relevance2:.2f}")
    
    assert relevance1 > relevance2  # Should be more relevant to ML query
    print("✅ Relevance calculation works!")


def test_rerank_documents():
    """Test document reranking."""
    print("\n📊 Testing rerank_documents...")
    
    # Create test documents
    edu_doc = Document(
        page_content="Educational content about programming",
        metadata={
            'title': 'Python Programming Tutorial',
            'author': 'Khan Academy',
            'view_count': 15000
        }
    )
    
    music_doc = Document(
        page_content="This is a music video",
        metadata={
            'title': 'Funny Music Video',
            'author': 'MusicChannel',
            'view_count': 100000
        }
    )
    
    docs_with_scores = [(edu_doc, 0.3), (music_doc, 0.2)]
    query = "programming tutorial"
    
    reranked = rerank_documents(docs_with_scores, query)
    
    print(f"Reranked order:")
    for i, doc in enumerate(reranked):
        print(f"  {i+1}. {doc.metadata['title']} by {doc.metadata['author']}")
    
    # Educational content should rank higher for technical query
    assert reranked[0].metadata['author'] == 'Khan Academy'
    print("✅ Document reranking works!")


def test_compress_content():
    """Test content compression."""
    print("\n🗜️ Testing compress_content...")
    
    long_content = """
    Machine learning is a subset of artificial intelligence. 
    It involves training algorithms on data. 
    Neural networks are a popular approach. 
    They can learn complex patterns. 
    This is unrelated content about cooking recipes. 
    Deep learning uses multiple layers. 
    It's very effective for image recognition.
    """
    
    query = "machine learning neural networks"
    compressed = compress_content(long_content, query, target_ratio=0.5)
    
    print(f"Original length: {len(long_content)} chars")
    print(f"Compressed length: {len(compressed)} chars")
    print(f"Compressed content: {compressed}")
    
    # Should keep ML-related sentences
    assert "machine learning" in compressed.lower()
    assert "neural networks" in compressed.lower()
    # Should remove unrelated content
    assert "cooking recipes" not in compressed.lower()
    
    print("✅ Content compression works!")


def test_aggregate_and_compress():
    """Test document aggregation."""
    print("\n📦 Testing aggregate_and_compress...")
    
    # Create documents from same video
    doc1 = Document(
        page_content="Part 1: Introduction to machine learning",
        metadata={'video_id': 'vid123', 'title': 'ML Tutorial', 'author': 'EduChannel'}
    )
    
    doc2 = Document(
        page_content="Part 2: Neural network basics",
        metadata={'video_id': 'vid123', 'title': 'ML Tutorial', 'author': 'EduChannel'}
    )
    
    doc3 = Document(
        page_content="Different video about cooking",
        metadata={'video_id': 'vid456', 'title': 'Cooking Tutorial', 'author': 'FoodChannel'}
    )
    
    docs = [doc1, doc2, doc3]
    query = "machine learning"
    
    aggregated = aggregate_and_compress(docs, query)
    
    print(f"Original docs: {len(docs)}")
    print(f"Aggregated docs: {len(aggregated)}")
    
    for doc in aggregated:
        print(f"  Video: {doc.metadata['title']} (aggregated: {doc.metadata.get('aggregated', False)})")
    
    # Should group docs by video
    assert len(aggregated) <= 2  # Max 2 videos
    assert all(doc.metadata.get('aggregated', False) for doc in aggregated)
    
    print("✅ Document aggregation works!")


def run_all_tests():
    """Run all post-processing tests."""
    print("🧪 Running Post-Processing Function Tests")
    print("=" * 50)
    
    try:
        test_clean_document_content()
        test_is_high_quality_content()
        test_calculate_chunk_relevance()
        test_rerank_documents()
        test_compress_content()
        test_aggregate_and_compress()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Post-processing module is working correctly.")
        print("\n💡 The enhanced retrieval pipeline should now work properly!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
