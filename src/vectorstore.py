from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import SentenceTransformersTokenTextSplitter

from langchain_chroma import Chroma
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams   

# Documents Recursive Processing
def process_documents_recursive(video_df):
    # Clean and combine content
    video_df = video_df.fillna({"transcript": "", "view_count": 0})
    
    # Create documents with essential metadata
    documents = [
        Document(
            page_content=f"Title: {row['title']}\nTranscript: {row['transcript']}",
            metadata={
                'video_id': str(row['video_id']),
                'title': str(row['title']),
                'url': str(row['url'])
            }
        )
        for _, row in video_df.iterrows()
    ]
    print(f"PROCESS (Recursive): Created {len(documents)} documents")

    # Split into chunks
    chunks = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", " ", ""],
        chunk_size=1000,
        chunk_overlap=200
    ).split_documents(documents)
    
    # Add basic chunk identifiers
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            'chunk_id': f"{chunk.metadata['video_id']}_recursive_chunk_{i}"
        })
 
    print(f"PROCESS (Recursive): Created {len(chunks)} chunks from documents")

    return chunks


# Documents Semantic Processing
def process_documents_semantic(video_df, embedding_model):
    """
    Processes video transcripts using a semantic chunking approach.
    This method aims to create chunks based on semantic coherence.
    
    Args:
        video_df (pd.DataFrame): DataFrame containing video data including 'title' and 'transcript'.
        embedding_model: An initialized embedding model (e.g., GoogleGenerativeAIEmbeddings).
                         This is crucial for semantic chunking.
    """
    # Clean and combine content
    video_df = video_df.fillna({"transcript": "", "view_count": 0})
    
    # Create documents with essential metadata
    documents = [
        Document(
            page_content=f"Title: {row['title']}\nTranscript: {row['transcript']}",
            metadata={
                'video_id': str(row['video_id']),
                'title': str(row['title']),
                'url': str(row['url'])
            }
        )
        for _, row in video_df.iterrows()
    ]
    print(f"PROCESS (Semantic): Created {len(documents)} documents")

    # Semantic chunking requires an embedding model
    # The SemanticChunker will use this model to find semantic boundaries.
    # Note: SemanticChunker is experimental and might require specific Langchain versions.
    # If it causes issues, you might need to implement a more manual semantic splitting logic
    # or use a different library.
    
    # Using SemanticChunker from langchain_experimental
    try:
        from langchain_experimental.text_splitter import SemanticChunker
        text_splitter = SemanticChunker(
            embeddings=embedding_model,
            breakpoint_threshold_type="percentile", # "percentile" or "standard_deviation"
            # You might need to adjust percentile_threshold or standard_deviation_threshold
            # based on your data. Default is 95 for percentile.
        )
        semantic_chunks = text_splitter.split_documents(documents)
    except ImportError:
        print("WARNING: langchain_experimental.text_splitter.SemanticChunker not found.")
        print("Falling back to a simpler sentence-based splitting for demonstration.")
        # Fallback if SemanticChunker is not available or causes issues
        # This is not "true" semantic chunking but a step towards it
        sentence_splitter = SentenceTransformersTokenTextSplitter(chunk_overlap=0, tokens_per_chunk=256)
        semantic_chunks = []
        for doc in documents:
            sentences = sentence_splitter.split_text(doc.page_content)
            # For a basic fallback, we'll just treat each sentence as a "chunk"
            # In a real semantic chunker, you'd then group these sentences based on similarity
            for i, sentence in enumerate(sentences):
                semantic_chunks.append(Document(page_content=sentence, metadata={**doc.metadata, 'chunk_id': f"{doc.metadata['video_id']}_semantic_fallback_chunk_{i}"}))
        print("NOTE: Using a fallback sentence splitter. True semantic chunking requires SemanticChunker.")


    # Add basic chunk identifiers and ensure metadata is copied
    final_semantic_chunks = []
    for i, chunk in enumerate(semantic_chunks):
        # Ensure metadata is properly copied if the chunker creates new Document objects
        new_metadata = chunk.metadata.copy() if chunk.metadata else {}
        new_metadata['chunk_id'] = f"{new_metadata.get('video_id', 'unknown_video')}_semantic_chunk_{i}"
        final_semantic_chunks.append(Document(page_content=chunk.page_content, metadata=new_metadata))
 
    print(f"PROCESS (Semantic): Created {len(final_semantic_chunks)} chunks from documents")
    
    return final_semantic_chunks




# CHROMA -------------------------------------------------------------------------------------------------------------------------------------------
def create_chroma_vectorstore(chunks, embedding, topic="collection"):
    """Create new or connect to existing Chroma vectorstore."""
    persist_dir = "data/chroma_db"

    # First try to connect to existing Chroma vectorstore
    try:
        vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=embedding,
            collection_name=topic
        )
        # Check if collection has documents
        if vectorstore._collection.count() > 0:
            print(f"CHROMA: Connected to existing Chroma collection '{topic}' with {vectorstore._collection.count()} documents")
            return vectorstore
    except Exception as e:
        print(f"CHROMA: No existing collection found: {str(e)}")

    # Create new vectorstore if none exists or is empty     
    print(f"CHROMA: Creating new Chroma collection '{topic}'")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=persist_dir,
        collection_name=topic
    )   
    print(f"Created new collection with {len(chunks)} documents")

    return vectorstore

# QDRANT
def create_qdrant_vectorstore(chunks, embedding, topic="collection"):
    """Create new or connect to existing Qdrant vectorstore."""
    persist_dir = "data/qdrant_db"
    
    # Initialize Qdrant client
    client = QdrantClient(path=persist_dir)
    
    try:
        # Check if collection exists
        collection_info = client.get_collection(topic)
        vectors_count = collection_info.vectors_count
        
        if vectors_count > 0:
            print(f"Connected to existing Qdrant collection '{topic}' with {vectors_count} vectors")
            return QdrantVectorStore(
                client=client,
                collection_name=topic,
                embeddings=embedding
            )
    except Exception as e:
        print(f"No existing collection found: {str(e)}")
    
    # Create new vectorstore if none exists or is empty
    print(f"Creating new Qdrant collection '{topic}'")
    
    # Create collection with vector configuration
    client.recreate_collection(
        collection_name=topic,
        vectors_config=VectorParams(
            size=384,  # Dimension for text-embedding-3-small
            distance=Distance.COSINE
        )
    )
    
    # Create and populate vectorstore
    vectorstore = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embedding,
        collection_name=topic,
        path=persist_dir
    )
    print(f"Created new collection with {len(chunks)} documents")
    
    return vectorstore
