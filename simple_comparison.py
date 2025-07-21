import sys
sys.path.append('/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer')

from src.workflow import run_rag_chain
from src.youtube import load_video_details
from src.vectorstore import process_documents_recursive, create_chroma_vectorstore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def simple_comparison():
    print("🔍 Simple Comparison Test")
    
    # Try to load your existing data
    try:
        video_df = load_video_details(
            base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
        )
        print(f"📊 Loaded {len(video_df)} videos")
        
        # Create vectorstore
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_recursive(video_df)
        vectorstore = create_chroma_vectorstore(chunks, embedding, topic="test_enhanced")
        
        # Test the enhanced system
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        query = "machine learning tutorial from youtube"
        print(f"\n🔍 Testing query: '{query}'")
        
        result = run_rag_chain(
            query=query,
            vectorstore=vectorstore,
            llm=llm
        )
        
        print(f"✅ Action taken: {result['action']}")
        print(f"✅ Documents retrieved: {len(result['context'])}")
        
        if result['context']:
            print("\n📄 Retrieved documents:")
            for i, doc in enumerate(result['context'][:3]):  # Show first 3
                title = doc.metadata.get('title', 'Unknown')
                author = doc.metadata.get('author', 'Unknown')
                aggregated = " [AGGREGATED]" if doc.metadata.get('aggregated') else ""
                print(f"  {i+1}. {title} by {author}{aggregated}")
        
        print(f"\n💬 Response preview:")
        print(result['response'][:200] + "...")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print("💡 Make sure you have some YouTube data in your data/youtube_data folder")

if __name__ == "__main__":
    simple_comparison()