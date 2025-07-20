from dataclasses import dataclass
from typing import Dict, List
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
        model_name: LLM model to use for quality analysis
    """
    start_time = time.time()
    
    # Initialize LLM
    llm = ChatOpenAI(
        model=model_name,
        temperature=0.0,
        max_tokens=50
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

        if len(transcript) < 100:  # Too short
            quality_scores[video_id] = 1
            quality_reasons[video_id] = "Transcript too short"
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
        total_videos=total_videos,                          # How many videos we tried to evaluate
        videos_with_transcripts=videos_with_transcripts,    # How many actually had transcripts
        coverage_rate=coverage_rate,                        # Percentage success rate
        quality_scores=quality_scores,                      # {video_id: score} for each video
        quality_reasons=quality_reasons,                    # {video_id: reason} AI explanations
        avg_quality_score=avg_quality,                      # Overall quality average
        high_quality_count=high_quality,                    # Count of good videos (score >= threshold)
        quality_rate=quality_rate,                          # Percentage of high-quality videos
        evaluation_time=time.time() - start_time,           # How long evaluation took
        timestamp=datetime.now().isoformat(),               # When evaluation was run
        failed_videos=failed_videos,
        failure_reasons=failure_reasons
    )