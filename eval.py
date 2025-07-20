#!/usr/bin/env python3
"""
Real YouTube Data Evaluation Script

This script provides comprehensive evaluation of stored YouTube data including:
- Transcript quality analysis
- Content suitability for RAG systems
- Performance metrics
- Detailed reporting and recommendations

python eval.py --list                               # See what data you have
python eval.py --topic "how_to_make_mayonnaise"     # Evaluate a specific topic
python eval.py --all                                # Evaluate all available datasets    
python eval.py --topic "langchain" --export         # Export results to JSON

"""

import pandas as pd
import json
import os
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from src.evaluation import evaluate_transcripts, EvaluationMetrics
from src.youtube import load_video_details


class YouTubeDataEvaluator:
    """Comprehensive evaluator for YouTube data quality and RAG suitability."""
    
    def __init__(self, base_path: str = "data/youtube_data"):
        self.base_path = base_path
        self.evaluation_results = {}
        
    def list_available_datasets(self) -> Dict[str, List[str]]:
        """List all available YouTube datasets."""
        datasets = {}
        
        try:
            raw_data_path = f"{self.base_path}/raw_data"
            if os.path.exists(raw_data_path):
                files = os.listdir(raw_data_path)
                csv_files = [f for f in files if f.endswith('.csv')]
                
                for file in csv_files:
                    # Parse filename: topic_timestamp.csv
                    name_parts = file.replace('.csv', '').split('_')
                    if len(name_parts) >= 2:
                        topic = '_'.join(name_parts[:-2])
                        timestamp = '_'.join(name_parts[-2:])
                        
                        if topic not in datasets:
                            datasets[topic] = []
                        datasets[topic].append(timestamp)
                        
        except Exception as e:
            print(f"Error listing datasets: {e}")
            
        return datasets
    
    def analyze_dataset(self, topic: str, timestamp: str = None, quality_threshold: int = 3) -> Dict:
        """Analyze a specific dataset for quality and RAG suitability."""
        
        print(f"\n🔍 ANALYZING DATASET: {topic}")
        print("=" * 60)
        
        try:
            # Load data
            video_df = load_video_details(
                topic=topic,
                timestamp=timestamp,
                base_path=self.base_path
            )
            
            print(f"✅ Loaded {len(video_df)} videos")
            
            # Run quality evaluation
            print("\n🔄 Running quality evaluation...")
            metrics = evaluate_transcripts(
                df=video_df,
                quality_threshold=quality_threshold,
                model_name="gpt-3.5-turbo"
            )
            
            # Analyze content characteristics
            content_analysis = self._analyze_content_characteristics(video_df)
            
            # Generate detailed report
            report = self._generate_detailed_report(video_df, metrics, content_analysis)
            
            # Store results
            self.evaluation_results[f"{topic}_{timestamp or 'latest'}"] = {
                'metrics': metrics,
                'content_analysis': content_analysis,
                'report': report,
                'video_data': video_df
            }
            
            return report
            
        except Exception as e:
            error_msg = f"Error analyzing dataset {topic}: {str(e)}"
            print(f"❌ {error_msg}")
            return {'error': error_msg}
    
    def _analyze_content_characteristics(self, video_df: pd.DataFrame) -> Dict:
        """Analyze content characteristics for RAG suitability."""
        
        analysis = {
            'transcript_lengths': [],
            'short_content_count': 0,
            'music_heavy_count': 0,
            'channel_distribution': {},
            'view_count_stats': {},
            'content_quality_issues': []
        }
        
        for _, row in video_df.iterrows():
            transcript = row.get('transcript', '')
            
            if pd.notna(transcript):
                # Analyze transcript length
                word_count = len(str(transcript).split())
                analysis['transcript_lengths'].append(word_count)
                
                # Check for short content
                if word_count < 50:
                    analysis['short_content_count'] += 1
                    analysis['content_quality_issues'].append({
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'issue': 'Very short transcript',
                        'word_count': word_count
                    })
                
                # Check for music-heavy content
                music_mentions = transcript.count('[Music]') + transcript.count('foreign')
                if music_mentions > 3:
                    analysis['music_heavy_count'] += 1
                    analysis['content_quality_issues'].append({
                        'video_id': row['video_id'],
                        'title': row['title'],
                        'issue': 'Music-heavy content',
                        'music_mentions': music_mentions
                    })
                
                # Channel distribution
                channel = row.get('author', 'Unknown')
                analysis['channel_distribution'][channel] = analysis['channel_distribution'].get(channel, 0) + 1
        
        # Calculate statistics
        if analysis['transcript_lengths']:
            analysis['avg_transcript_length'] = sum(analysis['transcript_lengths']) / len(analysis['transcript_lengths'])
            analysis['min_transcript_length'] = min(analysis['transcript_lengths'])
            analysis['max_transcript_length'] = max(analysis['transcript_lengths'])
        
        # View count statistics
        view_counts = video_df['view_count'].tolist()
        if view_counts:
            analysis['view_count_stats'] = {
                'avg_views': sum(view_counts) / len(view_counts),
                'min_views': min(view_counts),
                'max_views': max(view_counts)
            }
        
        return analysis
    
    def _generate_detailed_report(self, video_df: pd.DataFrame, metrics: EvaluationMetrics, content_analysis: Dict) -> Dict:
        """Generate comprehensive evaluation report."""
        
        report = {
            'dataset_info': {
                'total_videos': len(video_df),
                'evaluation_timestamp': datetime.now().isoformat(),
                'quality_threshold': 3
            },
            'quality_metrics': {
                'coverage_rate': metrics.coverage_rate,
                'avg_quality_score': metrics.avg_quality_score,
                'quality_pass_rate': metrics.quality_rate,
                'failed_videos_count': len(metrics.failed_videos),
                'evaluation_time': metrics.evaluation_time
            },
            'content_characteristics': {
                'avg_transcript_length': content_analysis.get('avg_transcript_length', 0),
                'short_content_percentage': (content_analysis['short_content_count'] / len(video_df)) * 100,
                'music_heavy_percentage': (content_analysis['music_heavy_count'] / len(video_df)) * 100,
                'channel_diversity': len(content_analysis['channel_distribution'])
            },
            'rag_suitability': self._assess_rag_suitability(metrics, content_analysis),
            'recommendations': self._generate_recommendations(metrics, content_analysis, video_df),
            'detailed_video_analysis': []
        }
        
        # Add per-video analysis
        for _, row in video_df.iterrows():
            video_id = row['video_id']
            video_analysis = {
                'video_id': video_id,
                'title': row['title'],
                'author': row['author'],
                'view_count': row['view_count'],
                'quality_score': metrics.quality_scores.get(video_id, 0),
                'quality_reason': metrics.quality_reasons.get(video_id, 'N/A'),
                'transcript_length': len(str(row.get('transcript', '')).split()),
                'status': 'PASSED' if video_id not in metrics.failed_videos else 'FAILED',
                'rag_suitable': metrics.quality_scores.get(video_id, 0) >= 3
            }
            report['detailed_video_analysis'].append(video_analysis)
        
        return report
    
    def _assess_rag_suitability(self, metrics: EvaluationMetrics, content_analysis: Dict) -> Dict:
        """Assess overall dataset suitability for RAG systems."""
        
        suitability = {
            'overall_score': 0,
            'issues': [],
            'strengths': [],
            'recommendation': ''
        }
        
        # Calculate overall suitability score
        coverage_score = min(metrics.coverage_rate / 100, 1.0) * 25
        quality_score = min(metrics.avg_quality_score / 5, 1.0) * 35
        content_score = min((100 - content_analysis['short_content_count'] / len(content_analysis['transcript_lengths']) * 100) / 100, 1.0) * 25
        diversity_score = min(len(content_analysis['channel_distribution']) / 5, 1.0) * 15
        
        suitability['overall_score'] = coverage_score + quality_score + content_score + diversity_score
        
        # Identify issues
        if metrics.coverage_rate < 90:
            suitability['issues'].append(f"Low transcript coverage: {metrics.coverage_rate:.1f}%")
        
        if metrics.avg_quality_score < 3.5:
            suitability['issues'].append(f"Below-average quality: {metrics.avg_quality_score:.1f}/5")
        
        if content_analysis['short_content_count'] / len(content_analysis['transcript_lengths']) > 0.3:
            suitability['issues'].append("High percentage of short-form content")
        
        if content_analysis['music_heavy_count'] > 0:
            suitability['issues'].append("Music-heavy content detected")
        
        # Identify strengths
        if metrics.coverage_rate >= 95:
            suitability['strengths'].append("Excellent transcript coverage")
        
        if metrics.avg_quality_score >= 4.0:
            suitability['strengths'].append("High-quality content")
        
        if len(content_analysis['channel_distribution']) >= 3:
            suitability['strengths'].append("Good channel diversity")
        
        # Generate recommendation
        if suitability['overall_score'] >= 80:
            suitability['recommendation'] = "✅ EXCELLENT - Ready for production RAG system"
        elif suitability['overall_score'] >= 60:
            suitability['recommendation'] = "⚠️ GOOD - Suitable with minor improvements"
        elif suitability['overall_score'] >= 40:
            suitability['recommendation'] = "⚠️ FAIR - Requires filtering and improvements"
        else:
            suitability['recommendation'] = "❌ POOR - Significant improvements needed"
        
        return suitability
    
    def _generate_recommendations(self, metrics: EvaluationMetrics, content_analysis: Dict, video_df: pd.DataFrame) -> List[str]:
        """Generate actionable recommendations for improvement."""
        
        recommendations = []
        
        # Quality-based recommendations
        if metrics.avg_quality_score < 3.5:
            recommendations.append("🔧 Implement stricter quality filtering (min score 4/5)")
            recommendations.append("📏 Add minimum transcript length requirement (>100 words)")
        
        # Content-based recommendations
        if content_analysis['short_content_count'] > 0:
            recommendations.append("⏱️ Filter out short-form content (YouTube Shorts)")
            recommendations.append("📊 Add duration-based filtering (>60 seconds)")
        
        if content_analysis['music_heavy_count'] > 0:
            recommendations.append("🎵 Filter music-heavy content ([Music] tags)")
        
        # Coverage-based recommendations
        if metrics.coverage_rate < 95:
            recommendations.append("📺 Improve video selection criteria")
            recommendations.append("🔍 Focus on educational/instructional channels")
        
        # RAG-specific recommendations
        failed_percentage = len(metrics.failed_videos) / metrics.total_videos * 100
        if failed_percentage > 20:
            recommendations.append("🛡️ Implement pre-processing quality filters")
            recommendations.append("🎯 Target higher-authority content creators")
        
        # System improvements
        recommendations.append("📈 Implement continuous quality monitoring")
        recommendations.append("🔄 Set up automated quality alerts")
        
        return recommendations
    
    def print_summary_report(self, topic: str, timestamp: str = None):
        """Print a formatted summary report."""
        
        key = f"{topic}_{timestamp or 'latest'}"
        if key not in self.evaluation_results:
            print(f"❌ No evaluation results found for {topic}")
            return
        
        result = self.evaluation_results[key]
        report = result['report']
        metrics = result['metrics']
        
        print("\n" + "=" * 80)
        print(f"📊 YOUTUBE DATA EVALUATION REPORT")
        print("=" * 80)
        
        print(f"\n📂 Dataset: {topic}")
        print(f"🕒 Timestamp: {timestamp or 'latest'}")
        print(f"📅 Evaluated: {report['dataset_info']['evaluation_timestamp']}")
        
        print(f"\n🎯 QUALITY METRICS")
        print("-" * 40)
        print(f"Coverage Rate: {report['quality_metrics']['coverage_rate']:.1f}%")
        print(f"Avg Quality Score: {report['quality_metrics']['avg_quality_score']:.2f}/5")
        print(f"Quality Pass Rate: {report['quality_metrics']['quality_pass_rate']:.1f}%")
        print(f"Failed Videos: {report['quality_metrics']['failed_videos_count']}")
        
        print(f"\n📝 CONTENT ANALYSIS")
        print("-" * 40)
        print(f"Avg Transcript Length: {report['content_characteristics']['avg_transcript_length']:.0f} words")
        print(f"Short Content: {report['content_characteristics']['short_content_percentage']:.1f}%")
        print(f"Music-Heavy Content: {report['content_characteristics']['music_heavy_percentage']:.1f}%")
        print(f"Channel Diversity: {report['content_characteristics']['channel_diversity']} channels")
        
        print(f"\n🚀 RAG SUITABILITY")
        print("-" * 40)
        rag_score = report['rag_suitability']['overall_score']
        print(f"Overall Score: {rag_score:.1f}/100")
        print(f"Recommendation: {report['rag_suitability']['recommendation']}")
        
        if report['rag_suitability']['issues']:
            print(f"\n⚠️ Issues Identified:")
            for issue in report['rag_suitability']['issues']:
                print(f"  • {issue}")
        
        if report['rag_suitability']['strengths']:
            print(f"\n✅ Strengths:")
            for strength in report['rag_suitability']['strengths']:
                print(f"  • {strength}")
        
        print(f"\n💡 RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i:2d}. {rec}")
        
        print(f"\n🔍 FAILED VIDEOS ANALYSIS")
        print("-" * 40)
        for video in report['detailed_video_analysis']:
            if video['status'] == 'FAILED':
                print(f"❌ {video['title']}")
                print(f"   Score: {video['quality_score']}/5 | Length: {video['transcript_length']} words")
                print(f"   Reason: {video['quality_reason']}")
                print()
    
    def export_results(self, topic: str, timestamp: str = None, output_dir: str = "data/evaluation_reports"):
        """Export evaluation results to JSON and CSV files."""
        
        key = f"{topic}_{timestamp or 'latest'}"
        if key not in self.evaluation_results:
            print(f"❌ No evaluation results found for {topic}")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Export JSON report
        json_path = f"{output_dir}/{topic}_evaluation_report.json"
        with open(json_path, 'w') as f:
            # Convert metrics to dict for JSON serialization
            report_data = self.evaluation_results[key]['report'].copy()
            json.dump(report_data, f, indent=2, default=str)
        
        # Export CSV with video details
        csv_path = f"{output_dir}/{topic}_video_analysis.csv"
        video_analysis_df = pd.DataFrame(self.evaluation_results[key]['report']['detailed_video_analysis'])
        video_analysis_df.to_csv(csv_path, index=False)
        
        print(f"\n💾 Results exported:")
        print(f"   JSON Report: {json_path}")
        print(f"   CSV Analysis: {csv_path}")


def main():
    """Main function for command-line usage."""
    
    parser = argparse.ArgumentParser(description="Evaluate YouTube data quality for RAG systems")
    parser.add_argument("--topic", type=str, help="Topic to evaluate (e.g., 'how_to_make_mayonnaise')")
    parser.add_argument("--timestamp", type=str, help="Specific timestamp to evaluate")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--all", action="store_true", help="Evaluate all available datasets")
    parser.add_argument("--export", action="store_true", help="Export results to files")
    parser.add_argument("--threshold", type=int, default=3, help="Quality threshold (1-5)")
    
    args = parser.parse_args()
    
    evaluator = YouTubeDataEvaluator()
    
    if args.list:
        print("\n📂 Available Datasets:")
        datasets = evaluator.list_available_datasets()
        for topic, timestamps in datasets.items():
            print(f"\n📁 {topic}:")
            for ts in timestamps:
                print(f"   🕒 {ts}")
        return
    
    if args.all:
        datasets = evaluator.list_available_datasets()
        for topic in datasets.keys():
            evaluator.analyze_dataset(topic, quality_threshold=args.threshold)
            evaluator.print_summary_report(topic)
            if args.export:
                evaluator.export_results(topic)
        return
    
    if args.topic:
        evaluator.analyze_dataset(args.topic, args.timestamp, quality_threshold=args.threshold)
        evaluator.print_summary_report(args.topic, args.timestamp)
        if args.export:
            evaluator.export_results(args.topic, args.timestamp)
    else:
        # Default behavior - evaluate mayonnaise dataset
        print("🔄 No arguments provided, running default evaluation...")
        evaluator.analyze_dataset("how_to_make_mayonnaise", "20231001_120000", quality_threshold=args.threshold)
        evaluator.print_summary_report("how_to_make_mayonnaise", "20231001_120000")


if __name__ == "__main__":
    main()
