from dataclasses import dataclass
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

@dataclass
class RAGMetrics:
    """Stores RAG evaluation metrics."""
    context_precision: float
    context_recall: float
    factual_consistency: float
    answer_relevance: float
    evaluation_details: Dict[str, Any]

def evaluate_rag_response(
    query: str,
    retrieved_chunks: List[Document],
    generated_response: str,
    evaluator_model: str = "gpt-4-turbo-preview"
) -> RAGMetrics:
    """Evaluates RAG pipeline quality using LLM as judge."""
    
    evaluator = ChatOpenAI(model=evaluator_model, temperature=0)
    
    def parse_score(response: str) -> tuple[int, str]:
        """Safely parse score and reason from LLM response."""
        try:
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            score_line = next(line for line in lines if line.startswith('SCORE:'))
            reason_line = next(line for line in lines if line.startswith('REASON:'))
            
            score = int(score_line.split(':')[1].strip())
            reason = reason_line.split(':')[1].strip()
            
            return score, reason
        except Exception as e:
            print(f"Error parsing response: {e}")
            print(f"Raw response: {response}")
            return 1, "Error parsing LLM response"
    
    # 1. Evaluate Context Precision
    precision_prompt = f"""Rate the relevance of these retrieved chunks for answering the query:
    Query: {query}
    
    Retrieved Chunks:
    {[chunk.page_content for chunk in retrieved_chunks]}
    
    Score from 1-5 where:
    1 = Completely irrelevant
    5 = Highly relevant and focused
    
    Respond with only a number and brief explanation, format:
    SCORE: [number]
    REASON: [brief explanation]
    """
    
    # 2. Evaluate Context Recall
    recall_prompt = f"""Check if any critical information is missing from these chunks:
    Query: {query}
    Context: {[chunk.page_content for chunk in retrieved_chunks]}
    
    Is there important information missing needed to fully answer the query?
    Score 1-5 where:
    1 = Critical information missing
    5 = All necessary information present
    
    SCORE: [number]
    REASON: [brief explanation]
    """
    
    # 3. Evaluate Factual Consistency
    consistency_prompt = f"""Check if this response is consistent with the provided context:
    Query: {query}
    Context: {[chunk.page_content for chunk in retrieved_chunks]}
    Response: {generated_response}
    
    Score 1-5 where:
    1 = Major hallucinations/contradictions
    5 = Perfectly consistent with context
    
    SCORE: [number]
    REASON: [brief explanation]
    """
    
    # 4. Evaluate Answer Relevance
    relevance_prompt = f"""Rate how well this response answers the original query:
    Query: {query}
    Response: {generated_response}
    
    Score 1-5 where:
    1 = Does not address the question
    5 = Perfectly answers the question
    
    SCORE: [number]
    REASON: [brief explanation]
    """
    
    # Get scores
    precision_response = evaluator.invoke(precision_prompt)
    recall_response = evaluator.invoke(recall_prompt)
    consistency_response = evaluator.invoke(consistency_prompt)
    relevance_response = evaluator.invoke(relevance_prompt)
    
    # Parse scores with error handling
    try:
        precision_score, precision_reason = parse_score(precision_response.content)
        recall_score, recall_reason = parse_score(recall_response.content)
        consistency_score, consistency_reason = parse_score(consistency_response.content)
        relevance_score, relevance_reason = parse_score(relevance_response.content)
    except Exception as e:
        print(f"Error during evaluation: {e}")
        return RAGMetrics(
            context_precision=0.0,
            context_recall=0.0,
            factual_consistency=0.0,
            answer_relevance=0.0,
            evaluation_details={
                "error": str(e),
                "precision_reason": "Evaluation failed",
                "recall_reason": "Evaluation failed",
                "consistency_reason": "Evaluation failed",
                "relevance_reason": "Evaluation failed"
            }
        )
    
    return RAGMetrics(
        context_precision=precision_score / 5.0,
        context_recall=recall_score / 5.0,
        factual_consistency=consistency_score / 5.0,
        answer_relevance=relevance_score / 5.0,
        evaluation_details={
            "precision_reason": precision_reason,
            "recall_reason": recall_reason,
            "consistency_reason": consistency_reason,
            "relevance_reason": relevance_reason
        }
    )