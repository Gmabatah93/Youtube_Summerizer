import sys
sys.path.append('/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer')

from src.youtube import load_video_details
from src.vectorstore import process_documents_recursive, create_chroma_vectorstore
from src.post_processing_relaxed import post_process_pipeline_relaxed
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def test_relaxed_processing():
    print("🧪 Testing with Relaxed Post-Processing")
    print("=" * 50)
    
    try:
        # Load data
        video_df = load_video_details(
            base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
        )
        print(f"📊 Loaded {len(video_df)} videos")
        
        # Create vectorstore
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_recursive(video_df)
        vectorstore = create_chroma_vectorstore(chunks, embedding, topic="relaxed_test")
        
        # Test relaxed pipeline
        query = "machine learning"
        print(f"\n🔍 Testing query: '{query}'")
        
        # Get raw docs
        raw_docs = vectorstore.similarity_search_with_score(query, k=15)
        print(f"Step 1: Got {len(raw_docs)} initial candidates")
        
        # Apply relaxed processing
        final_context = post_process_pipeline_relaxed(raw_docs, query)
        print(f"Step 2: Relaxed processing returned {len(final_context)} documents")
        
        if final_context:
            print("\n📄 Final documents:")
            for i, doc in enumerate(final_context):
                title = doc.metadata.get('title', 'Unknown')
                author = doc.metadata.get('author', 'Unknown')
                view_count = doc.metadata.get('view_count', 0)
                aggregated = " [AGGREGATED]" if doc.metadata.get('aggregated') else ""
                print(f"  {i+1}. {title}")
                print(f"      Author: {author} | Views: {view_count}{aggregated}")
        else:
            print("❌ Still no documents after relaxed processing")
            print("💡 Your data might need custom filtering rules")
    
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_relaxed_processing()