# AI System Evaluation Plan: YouTube Summarizer

This document outlines the multi-layered evaluation strategy for the YouTube Summarizer application. Evaluation is performed at three tiers: individual components, the interconnected pipeline/agent, and the end-to-end user experience.

## Tier 1: Component-Level Evaluation

This tier focuses on evaluating the individual building blocks of the system.

### 1. Data Ingestion & Quality
- **Metric**: Transcript Coverage Rate
  - **Implementation**: The existing logging in `youtube.py` that counts successful vs. failed transcript fetches.
  - **Goal**: >90% transcript coverage for processed videos.
- **Metric**: Transcript Quality Check
  - **Implementation**: A post-processing step that uses a small, fast LLM to spot-check transcripts for gibberish or significant formatting errors.
  - **Goal**: Identify and flag low-quality transcripts that might pollute the vector store.

### 2. Chunking Strategy Evaluation
- **Goal**: Compare the effectiveness of `process_documents_recursive` vs. `process_documents_semantic`.
- **Methodology**:
  - Create a small, representative "golden dataset" of 3-5 video transcripts.
  - Run both chunking functions on this dataset.
  - **Human Evaluation**: Manually review the generated chunks. Does the semantic chunker produce more coherent, contextually-complete chunks than the recursive splitter?
  - **Outcome**: Choose the chunking strategy that best preserves meaning for the RAG pipeline.

### 3. LLM & Prompt Evaluation
- **Goal**: Determine the best-performing model and prompt template for our tasks.
- **Methodology (A/B Testing)**:
  - Utilize the model-switching capability in `app.py`.
  - Define a set of "unit test" queries.
  - For each query, generate responses using different models (e.g., `gpt-4o-mini` vs. `claude-3-haiku`) and different prompts (`get_rag_prompt` v1 vs. v2).
  - [cite_start]**Human-in-the-Loop Evaluation [cite: 21]**: Reviewers compare the outputs side-by-side and rate them on clarity, correctness, and helpfulness.

## Tier 2: Pipeline & Agent Trajectory Evaluation

This tier evaluates how well the components work together.

### [cite_start]1. Agent Router Evaluation 
- **Goal**: To measure the accuracy of the `decide_action` routing logic in `workflow.py`.
- **Methodology**:
  - [cite_start]**Create a Diverse Test Dataset [cite: 24]**: Develop a list of 50+ user queries.
    - Include queries that clearly require video context (e.g., "summarize the youtube videos on...").
    - Include queries that are general knowledge (e.g., "what is a large language model?").
    - Include challenging edge cases and ambiguous queries.
  - **Labeling**: Manually label each query with the "correct" action: `SEARCH_VIDEOS` or `DIRECT_ANSWER`.
  - [cite_start]**Automated Evaluation [cite: 20]**: Write a script that runs each query through the `decide_action` function and compares its output to the label.
  - **Metric**: Classification Accuracy (Correct Decisions / Total Queries).
  - [cite_start]**Improvement Cycle [cite: 28]**: Use the failing examples to iteratively improve the routing logic (e.g., move from simple keyword matching to an LLM-based classifier).

### [cite_start]2. RAG Pipeline Evaluation [cite: 13]
- **Goal**: To measure the quality of the "SEARCH_VIDEOS" path from retrieval to generation.
- **Methodology (LLM-as-a-Judge)**: For a set of test queries that trigger the RAG path:
  - [cite_start]**Retrieval Quality **:
    - **Context Precision**: An evaluator LLM checks: "Are the retrieved document chunks relevant for answering the query?" (Score 1-5).
    - **Context Recall**: An evaluator LLM checks: "Was any critical information missing from the context that was needed to fully answer the query?"
  - **Generation Quality**:
    - [cite_start]**Faithfulness / Factual Consistency [cite: 16, 40]**: An evaluator LLM checks the final response against the provided context: "Does the generated answer contradict or hallucinate information not present in the source documents?"
    - **Answer Relevance**: An evaluator LLM checks the final response against the original query: "Does the answer directly and satisfactorily address the user's question?"

## [cite_start]Tier 3: End-to-End & System-Level Evaluation 

This tier evaluates the system from a user's perspective, focusing on overall performance and quality.

### 1. Performance & Cost Metrics
- [cite_start]**Latency **:
  - **Implementation**: Add `time` calls at the start and end of the `run_rag_chain` function.
  - **Metrics**: Log `Time-to-First-Token` and `Total-Query-Time`. Set targets (e.g., P90 < 200ms for first token).
- [cite_start]**Cost **:
  - **Implementation**: Capture token counts from the LLM provider's response object.
  - **Metric**: `Cost per Query`. Monitor this to prevent budget overruns.
- [cite_start]**Robustness **:
  - **Metric**: Error Rate. [cite_start]Monitor the frequency of failed API calls or workflow errors in production[cite: 27].

### [cite_start]2. Qualitative Business Metrics [cite: 23]
- **Goal**: Measure the overall quality and user satisfaction.
- **Methodology**: Combine automated and human-in-the-loop approaches.
  - [cite_start]**Human Feedback [cite: 21]**:
    - **Implementation**: Add thumbs up/down buttons and an optional text feedback box in the Streamlit UI.
    - **Metric**: User Satisfaction Score.
  - [cite_start]**Automated Evaluation [cite: 20] (LLM-as-a-Judge)**:
    - An evaluator LLM rates the final response on a scale of 1-5 for:
      - **Helpfulness**: Did the response achieve the user's likely goal?
      - [cite_start]**Conciseness & Tone [cite: 29]**: Was the response easy to read and appropriately styled?
      - **Correctness**: Was the information provided accurate (for direct answers)?

### [cite_start]3. Continuous Improvement Cycle [cite: 28]
- [cite_start]**Deploy Progressively [cite: 26]**: Use the model switcher to silently run A/B tests in a production environment, comparing a new prompt or model against the current champion.
- [cite_start]**Monitor Production Performance [cite: 27]**: Continuously track all the metrics defined above to detect regressions or opportunities for improvement.