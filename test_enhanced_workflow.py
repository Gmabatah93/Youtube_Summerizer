"""
Test script for the enhanced workflow with post-processing.
This will help you verify that the new retrieval pipeline is working correctly.
"""

import os
import sys
sys.path.append('/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer')

from src.workflow import run_rag_chain
from src.youtube import load_video_details
from src.vectorstore import process_documents_semantic, create_chroma_vectorstore
from src.utils import _format_collection_name
from src.rag_post_processing import (
    post_process_documents, 
    rerank_documents, 
    aggregate_and_compress
)
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def test_enhanced_workflow():
    """Test the enhanced workflow with post-processing."""
    
    print("🚀 Testing Enhanced Workflow with Post-Processing")
    print("=" * 60)
    
    try:
        # Load existing data
        print("📊 Loading existing video data...")
        video_df = load_video_details(
            base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
        )
        print(f"Loaded {len(video_df)} videos")
        
        # Process documents and create vectorstore
        print("📝 Processing documents...")
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_semantic(video_df=video_df, embedding_model=embedding)
        
        print("🗂️ Creating vectorstore...")
        topic = "test_enhanced_workflow"
        vectorstore = create_chroma_vectorstore(chunks, embedding, topic=topic)
        
        # Initialize LLM
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Test queries to see the difference
        test_queries = [
            "youtube how to learn programming effectively",
            "youtube best practices for machine learning",
            "youtube explain neural networks for beginners"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'='*60}")
            print(f"🔍 Test Query {i}: '{query}'")
            print("="*60)
            
            # Run the enhanced workflow
            result = run_rag_chain(
                query=query,
                vectorstore=vectorstore,
                chat_history=[],
                llm=llm
            )
            
            # Display results
            print(f"\n📝 Response Preview:")
            response = result.get("response", "No response")
            print(response[:300] + "..." if len(response) > 300 else response)
            
            print(f"\n📊 Context Analysis:")
            context_docs = result.get("context", [])
            print(f"Number of context documents: {len(context_docs)}")
            
            for j, doc in enumerate(context_docs, 1):
                title = doc.metadata.get('title', 'Unknown Title')
                author = doc.metadata.get('author', 'Unknown Author')
                view_count = doc.metadata.get('view_count', 'N/A')
                aggregated = doc.metadata.get('aggregated', False)
                content_length = len(doc.page_content)
                
                print(f"  📄 Doc {j}:")
                print(f"    Title: {title[:60]}...")
                print(f"    Author: {author}")
                print(f"    Views: {view_count}")
                print(f"    Content Length: {content_length} chars")
                print(f"    Aggregated: {aggregated}")
            
            print(f"\n🎯 Action Taken: {result.get('action', 'Unknown')}")
            if result.get('error'):
                print(f"❌ Error: {result.get('error')}")
            
            print("\n" + "-"*60)
        
        print("\n✅ Enhanced workflow testing completed!")
        print("\n💡 What to look for:")
        print("- Documents should be cleaned (no [Music], [Applause], etc.)")
        print("- Higher quality videos should be prioritized")
        print("- Content should be aggregated by video source")
        print("- Educational channels should get boosted")
        print("- Entertainment content should be filtered for technical queries")
        
    except FileNotFoundError:
        print("❌ No stored video data found!")
        print("Please run your app first to collect some YouTube data:")
        print("1. Start your Streamlit app: streamlit run app.py")
        print("2. Search for a topic to collect YouTube videos")
        print("3. Then run this test script")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure you have:")
        print("1. OpenAI API key in .env file")
        print("2. Required packages installed")
        print("3. YouTube data in data/youtube_data/")

def compare_basic_vs_enhanced():
    """Compare basic vs enhanced retrieval side by side."""
    print("\n" + "="*60)
    print("🔬 COMPARISON: Basic vs Enhanced Retrieval")
    print("="*60)
    
    # This would require modifying the workflow to support both modes
    # For now, just showing what the comparison would look like
    print("📊 Metrics to compare:")
    print("- Response relevance")
    print("- Context quality")
    print("- Source diversity")
    print("- Token efficiency")
    print("- Content cleanliness")

if __name__ == "__main__":
    test_enhanced_workflow()
    compare_basic_vs_enhanced()
