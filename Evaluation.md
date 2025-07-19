# AI System Evaluation Plan: YouTube Summarizer

This document outlines the multi-layered evaluation strategy for the YouTube Summarizer application. Evaluation is performed at three tiers: individual components, the interconnected pipeline/agent, and the end-to-end user experience.

## Tier 1: Component-Level Evaluation

This tier focuses on evaluating the individual building blocks of the system.

### 1. Data Ingestion & Quality
- **Metric**: Transcript Coverage Ratio
  - **Explanation**: to quantify how many videos have usable transcripts, which directly impacts the effectiveness of downstream summarization and retrieval. High coverage ensures the system can process and summarize most videos, minimizing gaps in user experience.
- **Metric**: Transcript Quality Check
  - **Implementation**: A post-processing step that uses a small, fast LLM to spot-check transcripts for gibberish or significant formatting errors.
  - **Goal**: Identify and flag low-quality transcripts that might pollute the vector store.

### 2. LLM & Prompt Evaluation
- **Goal**: Determine the best-performing model and prompt template for our tasks.
- **Methodology (A/B Testing)**:
  - Utilize the model-switching capability in `app.py`.
  - Define a set of "unit test" queries.
  - For each query, generate responses using different models (e.g., `gpt-4o-mini` vs. `claude-3-haiku`) and different prompts (`get_rag_prompt` v1 vs. v2).
  - [cite_start]**Human-in-the-Loop Evaluation [cite: 21]**: Reviewers compare the outputs side-by-side and rate them on clarity, correctness, and helpfulness.

## Tier 2: Pipeline & Agent Trajectory Evaluation

This tier evaluates how well the components work together.

### 1. Agent Router Evaluation 
- **Goal**: To measure the accuracy of the `decide_action` routing logic in `workflow.py`.
- **Methodology**:
  - **Create a Diverse Test Dataset**: Develop a list of 50+ user queries.
    - Include queries that clearly require video context (e.g., "summarize the youtube videos on...").
    - Include queries that are general knowledge (e.g., "what is a large language model?").
    - Include challenging edge cases and ambiguous queries.
  - **Metric**: Classification Accuracy (Correct Decisions / Total Queries).
  - **Improvement Cycle**: Use the failing examples to iteratively improve the routing logic (e.g., move from simple keyword matching to an LLM-based classifier).

### 2. RAG Pipeline Evaluation
- **Goal**: To measure the quality of the "SEARCH_VIDEOS" path from retrieval to generation.
- **Methodology (LLM-as-a-Judge)**: For a set of test queries that trigger the RAG path:
  - **Retrieval Quality**:
    - **Context Precision**: An evaluator LLM checks: "Are the retrieved document chunks relevant for answering the query?" (Score 1-5).
    - **Context Recall**: An evaluator LLM checks: "Was any critical information missing from the context that was needed to fully answer the query?"
  - **Generation Quality**:
    - **Faithfulness / Factual Consistency**: An evaluator LLM checks the final response against the provided context: "Does the generated answer contradict or hallucinate information not present in the source documents?"
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




Deciding Where to Place the Evaluator in Your RAG Architecture
When integrating an evaluator into your Retrieval-Augmented Generation (RAG) workflow with LangChain, your placement decision depends on requirements for latency, traceability, scalability, and operational complexity. Here is a breakdown of both options and guidance on choosing the right approach.

1. Inline Evaluation (Evaluator Runs Before Response to Frontend)
Pros
Immediate Feedback: Ensures every response is evaluated before the user receives it.

Synchronous Quality Control: Results can be used for real-time metrics, rejection, or adjustment of outputs (e.g., reranking, quality gating).

Transactional Cohesion: Clear linkage between the inference and its evaluation; improves debugging and monitoring.

Cons
Increased Latency: Evaluator processing time is added directly to user-facing response time.

Resource Contention: Synchronous evaluators can create bottlenecks if resource-intensive.

Scalability Limits: May not be ideal if evaluation logic grows more complex (e.g., using external models or services for evaluation).

2. Deferred Evaluation (Save, Then Evaluate On File System)
Pros
Asynchronous Processing: No additional latency for the end-user; evaluations can run independently and in bulk.

Easier Scaling: Batch or scheduled evaluation aligns well with distributed processing and microservices.

Data Persistence: Storing results enables re-evaluation, audits, and experimentation without re-generating original outputs.

Operational Flexibility: Can prioritize, throttle, or schedule evaluations based on resources and workloads.

Cons
Weaker Immediate Feedback Loop: Cannot perform real-time quality gating, re-ranking, or user-facing adjustments.

Additional Complexity: Requires mechanisms for storing, retrieving, and tracing evaluation records.

Eventual Consistency: Evaluation results may lag behind output generation, which impacts monitoring or adaptive behavior.

Decision Table
Criterion	Inline Evaluation	Deferred Evaluation
User Response Latency	Higher	Minimal
Real-Time Quality Control	Possible	Not possible
Resource Utilization	Immediate, possibly higher per request	Batched, easier to optimize
Traceability & Auditing	Good (if data persisted)	Best (if storing both output & results)
Scalability	May bottleneck under heavy usage	Easier to scale horizontally
Implementation Complexity	Simpler to couple evaluator & response	Needs coordination with storage/evaluation
Recommendations
Choose Inline Evaluation If:

You must enforce real-time quality control, re-ranking, or gating before the user sees results.

User experience demands high trust in every answer.

You have manageable inference and evaluation workloads.

Choose Deferred Evaluation If:

Scaling throughput and reducing frontend latency are top priorities.

Evaluation logic is CPU/GPU-intensive or uses third-party services.

You need to run evaluations repeatedly, perform A/B tests, or retain outputs for regulatory/audit reasons.

System can tolerate eventual consistency between response and its evaluation.

Hybrid Approach
Many mature architectures start with inline evaluation and evolve toward hybrid models:

Fast/cheap evaluator inline for gating or quick scoring.

Full evaluator deferred for detailed scoring, analytics, or human-in-the-loop processes.

Summary: Choose inline evaluation for immediate, interactive quality control, and deferred/batch evaluation otherwise. For most applications with significant scale or experimentation needs, deferred evaluation (Option 2) is typically more robust and operationally flexible unless there’s a strict requirement for per-response real-time quality management.




