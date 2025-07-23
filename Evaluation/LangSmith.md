# Observability
- Project --> Trace --> Run
    - Feedback
    - Tags 
    - Metadata
- Track
    - Latency
    - Cost
    - Feedback
    - Cat: Input | Output | Tags | Metadata | Run type

# Evaluation
- **Datasets:** test inputs *(expected outputs)*
- **Target Function:** defines what your evaluating
- **Evaluators:** score your target functions output
- **Evaluators RAG:**
    1. Correctness: Response vs reference answer
        - Goal: Measure "how similar/correct is the RAG chain answer, relative to a ground-truth answer"
        - Mode: Requires a ground truth (reference) answer supplied through a dataset
        - Evaluator: Use LLM-as-judge to assess answer correctness.
    2. Relevance: Response vs input
        - Goal: Measure "how well does the generated response address the initial user input"
        - Mode: Does not require reference answer, because it will compare the answer to the input question
        - Evaluator: Use LLM-as-judge to assess answer relevance, helpfulness, etc
    3. Groundedness: Response vs retrieved docs
        - Goal: Measure "to what extent does the generated response agree with the retrieved context"
        - Mode: Does not require reference answer, because it will compare the answer to the retrieved context
        - Evaluator: Use LLM-as-judge to assess faithfulness, hallucinations, etc.
    4. Retrieval relevance: Retrieved docs vs input
        - Goal: Measure "how relevant are my retrieved results for this query"
        - Mode: Does not require reference answer, because it will compare the question to the retrieved context
        - Evaluator: Use LLM-as-judge to assess relevance