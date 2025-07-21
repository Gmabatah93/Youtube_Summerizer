import os
from src.workflow import run_rag_chain
from src.vectorstore import create_chroma_vectorstore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def test_post_processing():
    """Test the enhanced post-processing pipeline."""
    
    # Load your existing vectorstore
    embedding = OpenAIEmbeddings(model="text-embedding-3-small")
    # You'll need to load your actual vectorstore here
    
    test_queries = [
        "How do I implement RAG systems?",
        "What are the best practices for vector databases?",
        "Explain machine learning concepts for beginners"
    ]
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print(f"{'='*50}")
        
        # Test with enhanced retrieval
        result = run_rag_chain(
            query=query,
            vectorstore=None,  # Your vectorstore here
            chat_history=[],
            llm=llm
        )
        
        print("Enhanced Response:")
        print(result.get("response", "No response"))
        print("\nContext Sources:")
        for i, doc in enumerate(result.get("context", [])):
            print(f"{i+1}. {doc.metadata.get('title', 'Unknown')} by {doc.metadata.get('author', 'Unknown')}")

if __name__ == "__main__":
    test_post_processing()