from src.youtube import search_videos, get_video_details
from src.vectorstore import process_documents_recursive, process_documents_semantic
from src.evaluation import evaluate_transcripts
from langchain_openai import OpenAIEmbeddings
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def process_youtube_topic(topic: str, max_results: int = 5):
    """Process a YouTube topic through the complete pipeline."""
    print(f"\n=== Processing Topic: {topic} ===")
    
    # 1. Fetch Videos from YouTube API
    print("\n1. Fetching videos...")
    video_ids = search_videos(
        topic=topic,
        api_key=os.environ['YOUTUBE_API_KEY'],
        max_results=max_results
    )
    
    # 2. Get Video Details and Transcripts
    print("\n2. Getting video details and transcripts...")
    video_df = get_video_details(
        video_ids=video_ids,
        api_key=os.environ['YOUTUBE_API_KEY']
    )
    
    # 3. Evaluate Transcript Quality
    print("\n3. Evaluating transcript quality...")
    metrics = evaluate_transcripts(video_df)
    
    # 4. Filter and Process High-Quality Transcripts
    quality_threshold = 3
    high_quality_df = video_df[
        video_df['video_id'].isin([
            vid for vid, score in metrics.quality_scores.items() 
            if score >= quality_threshold
        ])
    ]
    
    print(f"\nFound {len(high_quality_df)} high-quality transcripts out of {len(video_df)} total videos")
    
    # 5. Create Vector Store (only with quality content)
    if not high_quality_df.empty:
        print("\n5. Creating vector store...")
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_semantic(high_quality_df, embedding)
        print(f"Created {len(chunks)} chunks from high-quality transcripts")
    else:
        print("\nWarning: No high-quality transcripts found for vector store")
    
    return metrics, high_quality_df

# Run the pipeline
if __name__ == "__main__":
    topic = "What is an AI Agent"
    metrics, quality_df = process_youtube_topic(topic)
    
    # Save results
    quality_df.to_csv("data/aiAgent_quality.csv", index=False)
