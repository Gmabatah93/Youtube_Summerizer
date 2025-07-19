from dataclasses import dataclass
from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
import pandas as pd
import time
from datetime import datetime

@dataclass
class EvaluationMetrics:
    """Stores comprehensive evaluation metrics for transcripts."""
    # Coverage metrics
    total_videos: int
    videos_with_transcripts: int
    coverage_rate: float
    
    # Quality metrics
    quality_scores: Dict[str, int]
    quality_reasons: Dict[str, str]
    avg_quality_score: float
    high_quality_count: int
    quality_rate: float
    
    # Performance metrics
    evaluation_time: float
    timestamp: str
    
    # Failed videos tracking
    failed_videos: List[str]
    failure_reasons: Dict[str, str]

def evaluate_transcripts(
    df: pd.DataFrame,
    quality_threshold: int = 3,
    model_name: str = "gpt-3.5-turbo"
) -> EvaluationMetrics:
    """
    Comprehensive evaluation of transcript coverage and quality.
    
    Args:
        df: DataFrame with video_id and transcript columns
        quality_threshold: Minimum acceptable quality score (1-5)
        sample_size: Number of characters to analyze per transcript
        model_name: LLM model to use for quality analysis
    """
    start_time = time.time()
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.0,
        max_tokens=10
    )
    
    # Initialize tracking
    quality_scores: Dict[str, int] = {}
    quality_reasons: Dict[str, str] = {}
    failed_videos: List[str] = []
    failure_reasons: Dict[str, str] = {}

    # Evaluate each transcript
    for _, row in df.iterrows():
        video_id = row['video_id']
        transcript = row.get('transcript')

        if pd.isna(transcript):
            failed_videos.append(video_id)
            failure_reasons[video_id] = "Missing transcript"
            quality_scores[video_id] = 1
            quality_reasons[video_id] = "No transcript available"
            continue

        # Quality check prompt
        prompt = f"""You are a transcript quality analyst. Evaluate this full video transcript for coherence, formatting, and usability.

        Rate on these criteria:
        - Text coherence and readability
        - Proper formatting and structure
        - Content completeness
        - Overall transcript quality

        Score (1-5):
        1=Unusable (gibberish/nonsense)
        2=Poor (major formatting/coherence issues)
        3=Fair (some issues but usable)
        4=Good (minor issues)
        5=Excellent (clean, coherent text)

        Format:
        SCORE: [number]
        REASON: [brief explanation, max 10 words]

        Text to analyze:
        {transcript}
        """

        try:
            response = llm.invoke(prompt).content
            score_line, reason_line = response.split('\n')[:2]
            
            score = int(score_line.split(':')[1].strip())
            reason = reason_line.split(':')[1].strip()
            
            quality_scores[video_id] = score
            quality_reasons[video_id] = reason
            
            if score < quality_threshold:
                failed_videos.append(video_id)
                failure_reasons[video_id] = f"Low quality score: {score}/5"
                
        except Exception as e:
            failed_videos.append(video_id)
            failure_reasons[video_id] = str(e)
            quality_scores[video_id] = 1
            quality_reasons[video_id] = "Error during quality check"

    # Calculate metrics
    total_videos = len(df)
    videos_with_transcripts = df['transcript'].notna().sum()
    coverage_rate = (videos_with_transcripts / total_videos * 100) if total_videos > 0 else 0
    
    scores = list(quality_scores.values())
    avg_quality = sum(scores) / len(scores) if scores else 0
    high_quality = sum(1 for s in scores if s >= quality_threshold)
    quality_rate = (high_quality / len(scores) * 100) if scores else 0

    return EvaluationMetrics(
        total_videos=total_videos,
        videos_with_transcripts=videos_with_transcripts,
        coverage_rate=coverage_rate,
        quality_scores=quality_scores,
        quality_reasons=quality_reasons,
        avg_quality_score=avg_quality,
        high_quality_count=high_quality,
        quality_rate=quality_rate,
        evaluation_time=time.time() - start_time,
        timestamp=datetime.now().isoformat(),
        failed_videos=failed_videos,
        failure_reasons=failure_reasons
    )


# Test
# from youtube import load_video_details

# def analyze_stored_videos(topic: str = "how_to_make_mayonnaise", timestamp: str = "20231001_120000"):
#     """Analyze stored video data for quality and coverage metrics."""
    
#     # Load the stored data
#     video_df = load_video_details(
#         topic=topic,
#         timestamp=timestamp,
#         base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
#     )
    
#     print("\n=== Running Quality Analysis ===")
#     metrics = evaluate_transcripts(
#         df=video_df,
#         quality_threshold=3,
#         sample_size=200
#     )
    
#     # Print comprehensive analysis
#     print("\n=== Video Content Analysis Report ===")
#     print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
#     print(f"Topic: {topic}")
    
#     print("\nCoverage Metrics:")
#     print(f"- Total Videos: {metrics.total_videos}")
#     print(f"- Videos with Transcripts: {metrics.videos_with_transcripts}")
#     print(f"- Coverage Rate: {metrics.coverage_rate:.1f}%")
    
#     print("\nQuality Metrics:")
#     print(f"- Average Quality Score: {metrics.avg_quality_score:.1f}/5")
#     print(f"- High Quality Videos: {metrics.high_quality_count}")
#     print(f"- Quality Pass Rate: {metrics.quality_rate:.1f}%")
    
#     print("\nDetailed Quality Analysis:")
#     for video_id in video_df['video_id']:
#         score = metrics.quality_scores.get(video_id, 0)
#         reason = metrics.quality_reasons.get(video_id, "N/A")
#         title = video_df[video_df['video_id'] == video_id]['title'].iloc[0]
#         print(f"\nVideo: {title}")
#         print(f"- Quality Score: {score}/5")
#         print(f"- Reason: {reason}")
#         if video_id in metrics.failed_videos:
#             print(f"- Status: ❌ Failed - {metrics.failure_reasons[video_id]}")
#         else:
#             print(f"- Status: ✅ Passed")
    
#     return metrics

# metrics = analyze_stored_videos()