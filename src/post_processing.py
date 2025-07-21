"""
Post-processing functions for document retrieval and context optimization.

This module contains functions for:
- Document filtering and cleaning
- Metadata-aware reranking
- Content aggregation and compression
- Quality assessment

These functions are used in the enhanced retrieval pipeline to transform
raw similarity search results into high-quality, compressed context.
"""

from typing import List, Tuple, Dict, Any
from langchain_core.documents import Document
from collections import defaultdict
import re


def post_process_documents(raw_docs_with_scores: List[Tuple[Document, float]], query: str) -> List[Tuple[Document, float]]:
    """
    Post-process documents: filter, clean, deduplicate.
    
    Args:
        raw_docs_with_scores: List of (Document, similarity_score) tuples
        query: The search query
        
    Returns:
        List of processed (Document, score) tuples
    """
    processed_docs = []
    seen_content = set()
    
    for doc, score in raw_docs_with_scores:
        # Filter by relevance score
        if score > 0.8:  # Too dissimilar
            continue
            
        # Clean content
        cleaned_content = clean_document_content(doc.page_content)
        
        # Skip duplicates
        content_hash = hash(cleaned_content[:200])
        if content_hash in seen_content:
            continue
        seen_content.add(content_hash)
        
        # Filter by quality indicators
        if is_high_quality_content(doc, cleaned_content):
            doc.page_content = cleaned_content
            processed_docs.append((doc, score))
    
    return processed_docs


def rerank_documents(docs_with_scores: List[Tuple[Document, float]], query: str) -> List[Document]:
    """
    Rerank documents using metadata and content quality.
    
    Args:
        docs_with_scores: List of (Document, similarity_score) tuples
        query: The search query
        
    Returns:
        List of Documents sorted by enhanced relevance score
    """
    def calculate_rerank_score(doc: Document, original_score: float) -> float:
        metadata = doc.metadata
        
        # Start with similarity score (lower is better, so invert)
        score = 1 - original_score
        
        # Boost by view count (popularity)
        view_count = int(metadata.get('view_count', 0))
        if view_count > 10000:
            score += 0.2
        elif view_count > 1000:
            score += 0.1
        
        # Boost educational channels
        educational_channels = [
            "3Blue1Brown", "Khan Academy", "Crash Course", 
            "MIT OpenCourseWare", "Stanford", "Harvard"
        ]
        author = metadata.get('author', '').lower()
        if any(edu.lower() in author for edu in educational_channels):
            score += 0.3
        
        # Penalize music/entertainment content for technical queries
        technical_keywords = ['code', 'programming', 'tutorial', 'learn', 'how to']
        if any(keyword in query.lower() for keyword in technical_keywords):
            entertainment_indicators = ['music', 'song', 'funny', 'meme', 'reaction']
            title = metadata.get('title', '').lower()
            if any(indicator in title for indicator in entertainment_indicators):
                score -= 0.4
        
        return score
    
    # Rerank documents
    reranked = []
    for doc, original_score in docs_with_scores:
        new_score = calculate_rerank_score(doc, original_score)
        reranked.append((doc, new_score))
    
    # Sort by new score (descending)
    return [doc for doc, score in sorted(reranked, key=lambda x: x[1], reverse=True)]


def aggregate_and_compress(docs: List[Document], query: str, max_tokens: int = 4000) -> List[Document]:
    """
    Aggregate and compress document content for optimal context.
    
    Args:
        docs: List of Documents to aggregate
        query: The search query
        max_tokens: Maximum token limit for context
        
    Returns:
        List of compressed Documents grouped by video source
    """
    # Group by video source
    video_groups = defaultdict(list)
    for doc in docs:
        video_id = doc.metadata.get('video_id', 'unknown')
        video_groups[video_id].append(doc)
    
    compressed_context = []
    current_tokens = 0
    
    for video_id, video_docs in video_groups.items():
        # Get video metadata
        video_title = video_docs[0].metadata.get('title', 'Unknown')
        video_author = video_docs[0].metadata.get('author', 'Unknown')
        video_url = video_docs[0].metadata.get('url', '')
        
        # Merge chunks from same video
        merged_content = merge_video_chunks(video_docs, query)
        
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(merged_content) // 4
        
        if current_tokens + estimated_tokens > max_tokens:
            # Compress if too long
            compressed_content = compress_content(merged_content, query)
            estimated_tokens = len(compressed_content) // 4
        else:
            compressed_content = merged_content
        
        if current_tokens + estimated_tokens <= max_tokens:
            context_doc = Document(
                page_content=compressed_content,
                metadata={
                    'video_id': video_id,
                    'title': video_title,
                    'author': video_author,
                    'url': video_url,
                    'aggregated': True
                }
            )
            compressed_context.append(context_doc)
            current_tokens += estimated_tokens
        else:
            break  # Stop if we'd exceed token limit
    
    return compressed_context


def merge_video_chunks(video_docs: List[Document], query: str) -> str:
    """
    Merge chunks from the same video intelligently.
    
    Args:
        video_docs: List of Documents from the same video
        query: The search query
        
    Returns:
        Merged content string
    """
    # Sort chunks by relevance to query
    sorted_chunks = sorted(video_docs, key=lambda x: calculate_chunk_relevance(x, query), reverse=True)
    
    # Take top chunks and merge
    top_chunks = sorted_chunks[:3]  # Max 3 chunks per video
    merged_content = "\n\n".join([doc.page_content for doc in top_chunks])
    
    return merged_content


def compress_content(content: str, query: str, target_ratio: float = 0.6) -> str:
    """
    Compress content while preserving query-relevant information.
    
    Args:
        content: The content to compress
        query: The search query
        target_ratio: Target compression ratio (0.6 = keep 60% of content)
        
    Returns:
        Compressed content string
    """
    sentences = content.split('. ')
    
    # Score sentences by relevance to query
    query_words = set(query.lower().split())
    scored_sentences = []
    
    for sentence in sentences:
        sentence_words = set(sentence.lower().split())
        if len(query_words) > 0:  # Avoid division by zero
            relevance_score = len(query_words.intersection(sentence_words)) / len(query_words)
        else:
            relevance_score = 0
        scored_sentences.append((sentence, relevance_score))
    
    # Keep top sentences
    target_count = max(1, int(len(sentences) * target_ratio))  # At least 1 sentence
    top_sentences = sorted(scored_sentences, key=lambda x: x[1], reverse=True)[:target_count]
    
    # Reconstruct in original order
    selected_sentences = [sentence for sentence, score in top_sentences]
    return '. '.join(selected_sentences)


def clean_document_content(content: str) -> str:
    """
    Clean document content of noise and artifacts.
    
    Args:
        content: Raw document content
        
    Returns:
        Cleaned content string
    """
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Remove common transcript artifacts
    content = re.sub(r'\[.*?\]', '', content)  # Remove [Music], [Applause], etc.
    content = re.sub(r'\(.*?\)', '', content)  # Remove (inaudible), etc.
    
    # Remove URLs
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
    
    return content.strip()


def is_high_quality_content(doc: Document, content: str) -> bool:
    """
    Determine if document content is high quality.
    
    Args:
        doc: The Document object
        content: The document content
        
    Returns:
        True if content meets quality criteria
    """
    # Minimum length check
    if len(content) < 50:
        return False
    
    # Check for transcript quality indicators
    transcript_noise = ['[Music]', '[Applause]', 'inaudible', 'unclear']
    noise_count = sum(1 for noise in transcript_noise if noise.lower() in content.lower())
    
    # Reject if too much noise
    if noise_count > 3:
        return False
    
    # Check view count threshold
    view_count = int(doc.metadata.get('view_count', 0))
    if view_count < 100:  # Very low engagement
        return False
    
    return True


def calculate_chunk_relevance(doc: Document, query: str) -> float:
    """
    Calculate how relevant a chunk is to the query.
    
    Args:
        doc: The Document object
        query: The search query
        
    Returns:
        Relevance score (0.0 to 1.0)
    """
    content = doc.page_content.lower()
    query_words = query.lower().split()
    
    if len(query_words) == 0:
        return 0.0
    
    # Count query word matches
    matches = sum(1 for word in query_words if word in content)
    return matches / len(query_words)


# Configuration constants
DEFAULT_SIMILARITY_THRESHOLD = 0.8
DEFAULT_TOKEN_LIMIT = 4000
DEFAULT_COMPRESSION_RATIO = 0.6
DEFAULT_MIN_VIEW_COUNT = 100
DEFAULT_MAX_NOISE_COUNT = 3
DEFAULT_MAX_CHUNKS_PER_VIDEO = 3

EDUCATIONAL_CHANNELS = [
    "3Blue1Brown", "Khan Academy", "Crash Course", 
    "MIT OpenCourseWare", "Stanford", "Harvard",
    "freeCodeCamp.org", "Coursera", "edX"
]

ENTERTAINMENT_INDICATORS = [
    'music', 'song', 'funny', 'meme', 'reaction',
    'comedy', 'entertainment', 'viral', 'trending'
]

TECHNICAL_KEYWORDS = [
    'code', 'programming', 'tutorial', 'learn', 'how to',
    'algorithm', 'software', 'development', 'engineering'
]
