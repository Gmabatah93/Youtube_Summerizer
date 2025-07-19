import pandas as pd
from src.evaluation import evaluate_transcripts
from src.youtube import store_video_details, load_video_details
from datetime import datetime
import pandas as pd
import json
import os

df = pd.read_csv('data/videos.csv')

path = store_video_details(
    video_df=df,
    topic="How to make mayonnaise",
    base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data",
    timestamp="20231001_120000"  # Example timestamp, can be replaced with current time
)

def run_evaluation_tests():
    """Run comprehensive tests for the evaluation system."""
    
    print("\n=== 🧪 EVALUATION SYSTEM TESTS ===\n")
    
    # 1. Load stored video data
    try:
        video_df = load_video_details(
            topic="how_to_make_mayonnaise",
            timestamp="20231001_120000",
            base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
        )
        print("✅ Successfully loaded video data")
    except Exception as e:
        print(f"❌ Error loading video data: {str(e)}")
        return
    
    # 2. Run evaluation
    print("\n🔄 Running transcript evaluation...")
    metrics = evaluate_transcripts(
        df=video_df,
        quality_threshold=3,
        model_name="gpt-3.5-turbo"
    )
    
    # 3. Print Detailed Results
    print("\n📊 EVALUATION RESULTS")
    print("=" * 50)
    
    # Coverage Statistics
    print("\n🎯 Coverage Metrics:")
    print(f"Total Videos Processed: {metrics.total_videos}")
    print(f"Videos with Transcripts: {metrics.videos_with_transcripts}")
    print(f"Coverage Rate: {metrics.coverage_rate:.1f}%")
    
    # Quality Statistics
    print("\n📈 Quality Metrics:")
    print(f"Average Quality Score: {metrics.avg_quality_score:.2f}/5")
    print(f"High Quality Videos: {metrics.high_quality_count}")
    print(f"Quality Pass Rate: {metrics.quality_rate:.1f}%")
    
    # Performance Metrics
    print("\n⚡ Performance Metrics:")
    print(f"Evaluation Time: {metrics.evaluation_time:.2f} seconds")
    print(f"Timestamp: {metrics.timestamp}")
    
    # Detailed Analysis
    print("\n🔍 Per-Video Analysis:")
    for video_id in video_df['video_id']:
        title = video_df[video_df['video_id'] == video_id]['title'].iloc[0]
        score = metrics.quality_scores.get(video_id, 0)
        reason = metrics.quality_reasons.get(video_id, "N/A")
        
        print(f"\nVideo: {title}")
        print(f"- ID: {video_id}")
        print(f"- Quality Score: {score}/5")
        print(f"- Reason: {reason}")
        
        if video_id in metrics.failed_videos:
            print(f"- Status: ❌ FAILED")
            print(f"  Reason: {metrics.failure_reasons[video_id]}")
        else:
            print(f"- Status: ✅ PASSED")
    
    # 4. Save Test Results
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'metrics': {
            'total_videos': metrics.total_videos,
            'coverage_rate': metrics.coverage_rate,
            'avg_quality_score': metrics.avg_quality_score,
            'quality_rate': metrics.quality_rate,
            'evaluation_time': metrics.evaluation_time
        },
        'quality_scores': metrics.quality_scores,
        'quality_reasons': metrics.quality_reasons,
        'failed_videos': metrics.failed_videos,
        'failure_reasons': metrics.failure_reasons
    }
    
    results_path = 'data/evaluation_tests/test_results.json'
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n💾 Test results saved to: {results_path}")
    
    # 5. Validation Checks
    print("\n🔍 Validation Checks:")
    print(f"- Coverage Rate > 80%: {'✅' if metrics.coverage_rate > 80 else '❌'}")
    print(f"- Average Quality > 3.0: {'✅' if metrics.avg_quality_score > 3.0 else '❌'}")
    print(f"- Failed Videos < 20%: {'✅' if len(metrics.failed_videos)/metrics.total_videos < 0.2 else '❌'}")
    
    return metrics

if __name__ == "__main__":
    metrics = run_evaluation_tests()