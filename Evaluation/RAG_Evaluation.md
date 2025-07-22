# YouTube Summarizer Evaluation System

A comprehensive system for measuring the quality and effectiveness of our YouTube RAG (Retrieval-Augmented Generation) application. Think of this as your "data quality inspector" that runs behind the scenes.

## 🤔 What Problem Does This Solve?

Imagine you built a YouTube summarizer, but you don't know:
- **"Are the video transcripts actually any good?"** 
- **"How many videos don't even have transcripts?"**
- **"Is my system getting useful content or just music videos and noise?"**

This evaluation system answers those questions automatically.

## 🎯 Why We Chose "Offline" Evaluation

Our evaluation runs **after** data collection, not during user interactions. Here's why:

**The Alternative (Inline Evaluation):**
```
User asks question → Get videos → Evaluate quality → Answer user
                     ↑ This adds 10-30 seconds to every request! ❌
```

**Our Approach (Deferred Evaluation):**
```
User asks question → Get videos → Answer user immediately ✅
[Later, in background] → Evaluate quality → Generate reports
```

**Benefits:**
- ⚡ Zero impact on user experience
- 🔍 More thorough analysis (no time pressure)
- 📊 Better insights through batch processing
- 🧪 Easy to re-run with different criteria

## 🏗️ System Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ app.py      │    │ data/        │    │ eval.py     │
│ (User App)  │───▶│ youtube_data/│───▶│ (Evaluator) │
└─────────────┘    └──────────────┘    └─────────────┘
     │                    │                    │
     ▼                    ▼                    ▼
  Live user           Stored files         Quality reports
  interaction        (CSV + JSON)         & recommendations
```

## 🔬 What Gets Evaluated

### 1. **Transcript Coverage** 
*"How many videos actually have transcripts?"*

**The Problem**: YouTube API might return 20 videos, but only 12 have transcripts
**What We Measure**:
- Total videos found vs. videos with transcripts  
- Coverage percentage (target: >90%)
- Which videos failed and why

**Example Output**:
```
📊 Coverage: 85% (17/20 videos)
❌ Failed: 3 videos (auto-captions disabled)
```

### 2. **Transcript Quality**
*"Are the transcripts good enough for question-answering?"*

**The Problem**: Some transcripts are just "[Music]" or gibberish
**How It Works**: 
- GPT-3.5-turbo reads the **full transcript** (not just a sample)
- Scores each transcript 1-5 on coherence, formatting, and usability
- Provides specific reasons for low scores

**Example Evaluation**:
```
Prompt to LLM:
"Rate this transcript for Q&A usability (1-5):
1=Unusable (gibberish), 5=Excellent (clear, coherent)

Transcript: [full text here]"

Response: 
"SCORE: 4
REASON: Clear content, minor formatting issues"
```

### 3. **Content Analysis**
*"What type of content are we actually getting?"*

**What We Check**:
- Transcript lengths (too short = probably not useful)
- Content variety (are we getting different creators?)
- Educational vs. entertainment value
- Overall RAG system suitability

## 🛠️ How to Use the Evaluation System

### Comprehensive Analysis  
```bash
# See what data you have
python eval.py --list

# Evaluate a specific topic
python eval.py --topic "how_to_make_mayonnaise"

# Evaluate everything
python eval.py --all

# Export results to JSON
python eval.py --topic "langchain" --export
```

### Understanding the Output

**Coverage Report**:
```
📊 EVALUATION RESULTS
Total Videos: 20
Videos with Transcripts: 17 (85%)
❌ Failed Videos: 3
   - Video ABC123: Missing transcript  
   - Video DEF456: Auto-captions disabled
```

**Quality Report**:
```
🎯 Quality Metrics:
Average Quality Score: 3.8/5
High Quality Videos (4-5): 12 (71%)
Low Quality Videos (1-2): 2 (12%)

📝 Quality Issues Found:
   - Video GHI789: Score 2, "Too much background music"
   - Video JKL012: Score 1, "Only contains [Music] tags"
```

## 📁 File Structure

```
src/evaluation.py          # Core evaluation logic
eval.py                    # Command-line evaluation tool
test_eval.py              # Quick testing script
data/evaluation_tests/    # Evaluation results storage
data/youtube_data/        # Source data to evaluate
```

## 🎯 Key Metrics Explained

| Metric | What It Means | Good Target |
|--------|---------------|-------------|
| **Coverage Rate** | % of videos with usable transcripts | >90% |
| **Quality Rate** | % of transcripts scoring 4-5/5 | >70% |
| **Average Quality** | Mean quality score across all transcripts | >3.5/5 |
| **Failed Videos** | Count of videos with no/bad transcripts | <10% |

## 🚀 Using Results to Improve Your System

### If Coverage is Low (<80%):
- Switch to channels that enable auto-captions
- Filter by video language during search
- Try different search terms

### If Quality is Low (<3.0 average):
- Filter out videos shorter than 5 minutes
- Avoid music-heavy channels
- Target educational/tutorial content

### If Both are Good:
- Your data collection is working well!
- Focus on improving the RAG retrieval/generation components

## 🔄 Future Enhancements: Production Pipeline
![Picture](image/RagEvaluation.png)
source: https://huggingface.co/learn/cookbook/en/rag_evaluation

### Retriever Improvements
- **Query Reformulation:** Not implemented (user queries are used as-is)
- **Metadata Usage in Search:** Metadata is stored but not yet utilized in retrieval  
   _Planned upgrade: Incorporate metadata to improve search relevance_

### Reader Enhancements

1. **Post-Processing**
      - **Document Filtering:** Remove irrelevant or low-quality chunks
      - **Deduplication:** Merge similar or overlapping content
      - **Content Cleaning:** Eliminate noise and formatting artifacts

2. **Aggregation**
      - **Content Summarization:** Compress multiple chunks into key points
      - **Context Fusion:** Merge related information from different sources
      - **Hierarchical Organization:** Structure information by relevance or topic

3. **Prompt Compression**
      - **Token Optimization:** Reduce context length while preserving meaning
      - **Relevance Ranking:** Order content by importance
      - **Smart Truncation:** Retain the most relevant parts if context exceeds limits

4. **Reranking**
      - **Semantic Reranking:** Reorder results based on actual relevance to the query
      - **Cross-Encoder Models:** Apply specialized models for improved ranking
      - **Metadata Boosting:** Adjust ranking using source quality and authority


## 💡 Pro Tips

1. **Run evaluations after collecting new data** to catch quality issues early
2. **Export results to JSON** for tracking trends over time  
3. **Use the reports** to refine your YouTube search strategies
4. **Set up regular evaluation runs** (weekly/monthly) to monitor data quality

This evaluation system helps you build confidence that your RAG system is working with high-quality, relevant content rather than garbage data.

---

## 🔧 Technical Implementation Details

### Core Components

**`src/evaluation.py`**
- `EvaluationMetrics` dataclass: Stores all evaluation results
- `evaluate_transcripts()`: Main evaluation function using GPT-3.5-turbo
- Quality scoring on 1-5 scale with detailed reasoning
- Coverage analysis and failure tracking

**`eval.py`**
- `YouTubeDataEvaluator` class: Batch processing and reporting
- Command-line interface for easy evaluation runs
- JSON export functionality for trend analysis
- Comprehensive reporting with actionable insights

**`test_eval.py`**
- Quick validation script for testing the evaluation system
- Useful for development and debugging

### Evaluation Process Flow

1. **Data Loading**: Load stored YouTube data (CSV files with video metadata and transcripts)
2. **Coverage Analysis**: Count videos with/without transcripts, identify failure reasons
3. **Quality Assessment**: 
   - Filter out transcripts shorter than 100 characters
   - Send full transcript to GPT-3.5-turbo for scoring
   - Parse score and reasoning from LLM response
4. **Metrics Calculation**: Aggregate results into comprehensive metrics
5. **Report Generation**: Format results with actionable recommendations

### Quality Scoring Criteria

The LLM evaluates transcripts on:
- **Text coherence and readability**
- **Proper formatting and structure**  
- **Content completeness**
- **Overall usability for Q&A systems**

**Score Meanings**:
- 5 = Excellent (clean, coherent, well-formatted)
- 4 = Good (minor issues but highly usable)
- 3 = Fair (some issues but still usable)
- 2 = Poor (major formatting/coherence problems)
- 1 = Unusable (gibberish, music-only, or nonsensical)

### Data Storage Structure

```
data/youtube_data/
├── raw_data/           # Original video metadata
├── transcripts/        # Extracted transcripts  
├── metadata/          # Additional video details
└── evaluation_tests/  # Evaluation results
```

This structure enables:
- Easy batch processing across multiple topics
- Historical tracking of evaluation results
- Separation of concerns between data collection and evaluation

The evaluation system is designed to be **extensible** - you can easily add new metrics, change quality criteria, or integrate additional LLMs for evaluation.
