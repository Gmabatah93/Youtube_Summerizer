import sys
sys.path.append('/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer')

from src.youtube import load_video_details
from src.vectorstore import process_documents_recursive, create_chroma_vectorstore
from src.rag_post_processing import post_process_documents, is_high_quality_content, clean_document_content
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def debug_filtering():
    print("🔍 Debugging Post-Processing Filters")
    print("=" * 50)
    
    try:
        # Load your data
        video_df = load_video_details(
            base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
        )
        print(f"📊 Loaded {len(video_df)} videos")
        
        # Create vectorstore
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_recursive(video_df)
        vectorstore = create_chroma_vectorstore(chunks, embedding, topic="debug_test")
        
        # Get raw similarity results
        query = "machine learning"
        raw_docs = vectorstore.similarity_search_with_score(query, k=15)
        print(f"\n🔍 Raw similarity search returned {len(raw_docs)} documents")
        
        # Analyze each document and why it might be filtered
        print("\n📊 Analyzing each document:")
        for i, (doc, score) in enumerate(raw_docs[:5]):  # Check first 5
            print(f"\n--- Document {i+1} ---")
            print(f"Score: {score:.3f}")
            print(f"Title: {doc.metadata.get('title', 'Unknown')}")
            print(f"Author: {doc.metadata.get('author', 'Unknown')}")
            print(f"View Count: {doc.metadata.get('view_count', 0)}")
            print(f"Content Length: {len(doc.page_content)} chars")
            print(f"Content Preview: {doc.page_content[:100]}...")
            
            # Test each filter individually
            print("\n🧪 Filter Tests:")
            
            # 1. Score filter
            score_pass = score <= 0.8
            print(f"  Score filter (≤0.8): {score_pass} (score: {score:.3f})")
            
            # 2. Content cleaning
            try:
                cleaned_content = clean_document_content(doc.page_content)
                content_length_pass = len(cleaned_content) >= 50
                print(f"  Content length (≥50): {content_length_pass} ({len(cleaned_content)} chars)")
            except Exception as e:
                print(f"  Content cleaning failed: {e}")
                continue
            
            # 3. Quality check
            try:
                quality_pass = is_high_quality_content(doc, cleaned_content)
                print(f"  Quality check: {quality_pass}")
                
                # Break down quality check
                view_count = int(doc.metadata.get('view_count', 0))
                view_pass = view_count >= 100
                print(f"    View count (≥100): {view_pass} ({view_count} views)")
                
                # Check for noise
                transcript_noise = ['[Music]', '[Applause]', 'inaudible', 'unclear']
                noise_count = sum(1 for noise in transcript_noise if noise.lower() in cleaned_content.lower())
                noise_pass = noise_count <= 3
                print(f"    Noise level (≤3): {noise_pass} ({noise_count} noise indicators)")
                
            except Exception as e:
                print(f"  Quality check failed: {e}")
            
            # Overall pass/fail
            overall_pass = score_pass and content_length_pass and quality_pass
            print(f"  🎯 OVERALL: {'✅ PASS' if overall_pass else '❌ FAIL'}")
        
        # Show what the current filters are doing
        print(f"\n🔄 Running post_process_documents...")
        try:
            processed_docs = post_process_documents(raw_docs, query)
            print(f"Result: {len(processed_docs)} documents passed filtering")
            
            if len(processed_docs) == 0:
                print("❌ All documents were filtered out!")
                print("💡 Possible issues:")
                print("   - View count threshold too high (current: ≥100)")
                print("   - Score threshold too strict (current: ≤0.8)")
                print("   - Content too noisy")
                print("   - Transcripts too short after cleaning")
            
        except Exception as e:
            print(f"❌ post_process_documents failed: {e}")
    
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")

if __name__ == "__main__":
    debug_filtering()