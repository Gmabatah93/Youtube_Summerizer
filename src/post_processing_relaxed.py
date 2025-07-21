"""
Relaxed version of post-processing for debugging and initial testing.
"""

import re
from typing import List, Tuple
from collections import defaultdict
from langchain_core.documents import Document

# Relaxed configuration
RELAXED_CONFIG = {
    'min_view_count': 10,          # Much lower threshold
    'max_similarity_distance': 1.0, # More lenient similarity
    'min_content_length': 20,       # Shorter content OK
    'max_noise_count': 10,          # Allow more noise
}

def post_process_documents_relaxed(raw_docs_with_scores, query):
    """Relaxed post-processing for debugging."""
    processed_docs = []
    seen_content = set()
    
    print(f"🔄 Starting relaxed post-processing with {len(raw_docs_with_scores)} documents")
    
    for i, (doc, score) in enumerate(raw_docs_with_scores):
        print(f"  Processing doc {i+1}: score={score:.3f}")
        
        # Relaxed score filter
        if score > RELAXED_CONFIG['max_similarity_distance']:
            print(f"    ❌ Filtered by score: {score:.3f} > {RELAXED_CONFIG['max_similarity_distance']}")
            continue
        
        # Clean content
        cleaned_content = clean_document_content_relaxed(doc.page_content)
        
        # Skip duplicates (same as before)
        content_hash = hash(cleaned_content[:200])
        if content_hash in seen_content:
            print(f"    ❌ Filtered as duplicate")
            continue
        seen_content.add(content_hash)
        
        # Relaxed quality check
        if is_high_quality_content_relaxed(doc, cleaned_content):
            doc.page_content = cleaned_content
            processed_docs.append((doc, score))
            print(f"    ✅ Passed all filters")
        else:
            print(f"    ❌ Filtered by quality check")
    
    print(f"🎯 Relaxed filtering result: {len(processed_docs)} documents passed")
    return processed_docs

def clean_document_content_relaxed(content):
    """More gentle content cleaning."""
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Only remove the most obvious noise (keep more content)
    content = re.sub(r'\[Music\]', '', content)
    content = re.sub(r'\[Applause\]', '', content)
    
    # Remove URLs (same as before)
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
    
    return content.strip()

def is_high_quality_content_relaxed(doc, content):
    """More lenient quality assessment."""
    # Relaxed minimum length
    if len(content) < RELAXED_CONFIG['min_content_length']:
        return False
    
    # Allow more noise
    transcript_noise = ['[Music]', '[Applause]', 'inaudible', 'unclear']
    noise_count = sum(1 for noise in transcript_noise if noise.lower() in content.lower())
    if noise_count > RELAXED_CONFIG['max_noise_count']:
        return False
    
    # Much lower view count threshold
    view_count = int(doc.metadata.get('view_count', 0))
    if view_count < RELAXED_CONFIG['min_view_count']:
        return False
    
    return True

# Import the relaxed functions in the main module
from src.rag_post_processing import rerank_documents, aggregate_and_compress, calculate_chunk_relevance

def post_process_pipeline_relaxed(raw_docs_with_scores, query):
    """Complete relaxed pipeline."""
    # Step 1: Relaxed post-processing
    processed_docs = post_process_documents_relaxed(raw_docs_with_scores, query)
    
    if not processed_docs:
        print("⚠️  No documents passed relaxed filtering - returning empty list")
        return []
    
    # Step 2: Rerank (same as before)
    reranked_docs = rerank_documents(processed_docs, query)
    
    # Step 3: Aggregate (same as before)
    final_context = aggregate_and_compress(reranked_docs[:5], query)
    
    return final_context