import re

def _format_collection_name(name: str) -> str:
    """Format string to valid Qdrant collection name using regex."""
    # Replace spaces and special chars with underscore
    formatted = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Replace multiple underscores with single underscore
    formatted = re.sub(r'_+', '_', formatted)
    # Remove leading/trailing underscores
    formatted = formatted.strip('_')
    # Convert to lowercase for consistency
    formatted = formatted.lower()
    # Ensure name starts with letter (Qdrant requirement)
    if not formatted[0].isalpha():
        formatted = 'collection_' + formatted
    return formatted

def print_evaluation_results(metrics_df, quality_details, rag_metrics=None):
    """Print comprehensive evaluation results with formatting."""
    
    print("\n" + "="*50)
    print("📊 EVALUATION RESULTS SUMMARY")
    print("="*50)
    
    # 1. Transcript Quality Metrics
    print("\n🎯 TRANSCRIPT METRICS")
    print("-"*30)
    print(f"Total Videos: {metrics_df['total_videos'].iloc[0]}")
    print(f"Coverage Rate: {metrics_df['coverage_rate'].iloc[0]:.1f}%")
    print(f"Average Quality: {metrics_df['avg_quality_score'].iloc[0]:.1f}/5")
    print(f"Quality Pass Rate: {metrics_df['quality_rate'].iloc[0]:.1f}%")
    print(f"Processing Time: {metrics_df['evaluation_time'].iloc[0]:.2f}s")
    
    # 2. Quality Details
    print("\n📝 TRANSCRIPT QUALITY DETAILS")
    print("-"*30)
    failed_transcripts = quality_details[quality_details['failed']]
    passed_transcripts = quality_details[~quality_details['failed']]
    
    print("\nPassed Quality Check:")
    for _, row in passed_transcripts.iterrows():
        print(f"✅ Video {row['video_id']}: {row['quality_score']}/5 - {row['quality_reason']}")
    
    if not failed_transcripts.empty:
        print("\nFailed Quality Check:")
        for _, row in failed_transcripts.iterrows():
            print(f"❌ Video {row['video_id']}: {row['quality_score']}/5 - {row['quality_reason']}")
    
    # 3. RAG Metrics (if available)
    if rag_metrics is not None:
        print("\n🤖 RAG PIPELINE PERFORMANCE")
        print("-"*30)
        
        # Overall averages
        print("\nOverall Performance:")
        print(f"Context Precision: {rag_metrics['context_precision'].mean():.1%}")
        print(f"Context Recall: {rag_metrics['context_recall'].mean():.1%}")
        print(f"Factual Consistency: {rag_metrics['factual_consistency'].mean():.1%}")
        print(f"Answer Relevance: {rag_metrics['answer_relevance'].mean():.1%}")
        
        # Per-query details
        print("\nPer-Query Performance:")
        for _, row in rag_metrics.iterrows():
            print(f"\nQuery: {row['query']}")
            print(f"├─ Precision: {row['context_precision']:.1%} ({row['precision_reason']})")
            print(f"├─ Recall: {row['context_recall']:.1%} ({row['recall_reason']})")
            print(f"├─ Consistency: {row['factual_consistency']:.1%} ({row['consistency_reason']})")
            print(f"└─ Relevance: {row['answer_relevance']:.1%} ({row['relevance_reason']})")
    
    print("\n" + "="*50)