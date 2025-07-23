from langsmith import Client
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to Python path to import src modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.workflow import run_rag_chain
from src.vectorstore import create_chroma_vectorstore, process_documents_semantic
from src.youtube import load_video_details
from src.utils import _format_collection_name
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

load_dotenv()

client = Client()

# CREATE DATASET ================
# Define dataset: these are your YouTube summarization test cases
dataset_name = "PRACTICE: YouTube RAG"

# Check if dataset exists, if not create it
try:
    existing_datasets = list(client.list_datasets(dataset_name=dataset_name))
    if existing_datasets:
        dataset = existing_datasets[0]
        print(f"✅ Using existing dataset: {dataset.id}")
    else:
        dataset = client.create_dataset(dataset_name)
        print(f"📊 Created new dataset: {dataset.id}")
        
        # Create examples based on your actual use case
        client.create_examples(
            dataset_id=dataset.id,
            examples=[
                {
                    "inputs": {"query": "What are the main steps mentioned in the videos?", "topic": "langchain"},
                    "outputs": {
                        "expected_type": "step_by_step_summary",
                        "expected_elements": ["sequential steps", "process description", "specific actions"]
                    }
                },
                {
                    "inputs": {"query": "What specific tools or libraries are demonstrated?", "topic": "langchain"},
                    "outputs": {
                        "expected_type": "tool_identification", 
                        "expected_elements": ["tool names", "library versions", "usage examples"]
                    }
                },
                # Add edge cases
                {
                    "inputs": {"query": "How do I cook pasta?", "topic": "langchain"},
                    "outputs": {
                        "expected_type": "should_indicate_no_relevant_info",
                        "expected_behavior": "decline_unrelated"
                    }
                }
            ]
        )
        print("✅ Added test examples to dataset")
        
except Exception as e:
    print(f"❌ Dataset setup failed: {e}")
    exit(1)

# CREATE EVALUATORS ================
from langsmith import wrappers
import openai

openai_client = wrappers.wrap_openai(openai.OpenAI())

# - Evaluator for YouTube relevance
def youtube_relevance(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Check if response is relevant to YouTube content"""
    response = outputs.get("response", "")
    query = inputs["query"]
    
    # Check for YouTube context indicators
    youtube_indicators = ["video", "videos", "speaker", "creator", "mentioned", "discusses", "tutorial"]
    has_context = any(indicator in response.lower() for indicator in youtube_indicators)
    
    # Special case: unrelated questions should NOT be answered
    if "capital of France" in query:
        cannot_answer = any(phrase in response.lower() for phrase in ["don't have", "not mentioned", "cannot find"])
        return cannot_answer
    
    return has_context

# - Evaluator for response quality using LLM-as-judge
def response_quality(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Use LLM to judge response quality"""
    user_content = f"""
    You are evaluating a YouTube video summarization system.
    
    Query: {inputs['query']}
    Topic: {inputs.get('topic', 'N/A')}
    Response: {outputs.get('response', '')}
    Expected Response Type: {reference_outputs.get('expected_type', 'N/A')}
    
    Evaluate if the response:
    1. Answers the query appropriately
    2. Shows evidence of using video content
    3. Matches the expected response type
    4. Is helpful and informative
    
    Respond with GOOD or POOR:
    """
    
    evaluation = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You are an expert evaluator of AI summarization systems."},
            {"role": "user", "content": user_content},
        ],
    ).choices[0].message.content
    
    return "GOOD" in evaluation.upper()

# - Evaluator for response completeness
def response_completeness(outputs: dict, reference_outputs: dict) -> bool:
    """Check if response is complete and not too short"""
    response = outputs.get("response", "")
    
    # Check for errors
    if outputs.get("success") == False:
        return False
    
    # Basic length check (should be substantial)
    if len(response.split()) < 10:
        return False
    
    # Should not be just an error message
    error_indicators = ["error", "failed", "cannot process", "apologize"]
    if any(indicator in response.lower() for indicator in error_indicators):
        return False
    
    return True

# - TEST: Setup your YouTube RAG function
def youtube_rag_app(query: str, topic: str = "langchain") -> str:
    """Your YouTube RAG application"""
    try:
        # Load video data
        video_df = load_video_details(topic=topic)
        
        # Create vectorstore
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_semantic(video_df=video_df, embedding_model=embedding)
        
        # Create vectorstore (handle the collection_name parameter issue)
        try:
            collection_name = _format_collection_name(topic)
            vectorstore = create_chroma_vectorstore(chunks, embedding, collection_name=collection_name)
        except TypeError:
            vectorstore = create_chroma_vectorstore(chunks, embedding)
        
        # Initialize LLM and run RAG
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        result = run_rag_chain(query=query, vectorstore=vectorstore, chat_history=[], llm=llm)
        
        return result.get("response", result.get("answer", str(result)))
        
    except Exception as e:
        return f"Error processing query: {str(e)}"

# - TEST 1: Basic YouTube RAG
def youtube_target_v1(inputs: dict) -> dict:
    """Target function for YouTube RAG evaluation"""
    query = inputs["query"]
    topic = inputs.get("topic", "langchain")
    
    response = youtube_rag_app(query, topic)
    
    return {
        "response": response,
        "success": "Error" not in response,
        "topic": topic
    }

print("🚀 Running YouTube RAG Evaluation - Version 1 (gpt-4o-mini)")
experiment_results_v1 = client.evaluate(
    youtube_target_v1,  # Your AI system
    data=dataset_name,  # The data to predict and grade over
    evaluators=[youtube_relevance, response_quality, response_completeness],  # The evaluators
    experiment_prefix="youtube-rag-gpt4o-mini",  # Experiment name prefix
)

# - TEST 2: YouTube RAG with different model
def youtube_target_v2(inputs: dict) -> dict:
    """Target function with GPT-4 turbo"""
    query = inputs["query"]
    topic = inputs.get("topic", "langchain")
    
    try:
        video_df = load_video_details(topic=topic)
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_semantic(video_df=video_df, embedding_model=embedding)
        
        try:
            collection_name = _format_collection_name(topic)
            vectorstore = create_chroma_vectorstore(chunks, embedding, collection_name=collection_name)
        except TypeError:
            vectorstore = create_chroma_vectorstore(chunks, embedding)
        
        # Use GPT-4 turbo instead
        llm = ChatOpenAI(model="gpt-4-turbo", temperature=0)
        result = run_rag_chain(query=query, vectorstore=vectorstore, chat_history=[], llm=llm)
        
        response = result.get("response", result.get("answer", str(result)))
        
        return {
            "response": response,
            "success": "Error" not in response,
            "topic": topic,
            "model": "gpt-4-turbo"
        }
        
    except Exception as e:
        return {
            "response": f"Error processing query: {str(e)}",
            "success": False,
            "topic": topic,
            "model": "gpt-4-turbo"
        }

print("🚀 Running YouTube RAG Evaluation - Version 2 (gpt-4-turbo)")
experiment_results_v2 = client.evaluate(
    youtube_target_v2,
    data=dataset_name,
    evaluators=[youtube_relevance, response_quality, response_completeness],
    experiment_prefix="youtube-rag-gpt4-turbo",
)

# - TEST 3: YouTube RAG with enhanced prompt
def youtube_target_v3(inputs: dict) -> dict:
    """Target function with enhanced system prompt"""
    query = inputs["query"]
    topic = inputs.get("topic", "langchain")
    
    # Enhanced system prompt for better performance
    enhanced_prompt = """You are a specialized YouTube video content analyzer. 
    When answering questions, always:
    1. Reference specific video content when possible
    2. Be concise but comprehensive
    3. If the question is unrelated to the video content, clearly state that the information is not available in the videos
    4. Structure your response clearly with key points"""
    
    try:
        video_df = load_video_details(topic=topic)
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_semantic(video_df=video_df, embedding_model=embedding)
        
        try:
            collection_name = _format_collection_name(topic)
            vectorstore = create_chroma_vectorstore(chunks, embedding, collection_name=collection_name)
        except TypeError:
            vectorstore = create_chroma_vectorstore(chunks, embedding)
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Modify the system prompt in your RAG chain if possible
        result = run_rag_chain(query=query, vectorstore=vectorstore, chat_history=[], llm=llm)
        
        response = result.get("response", result.get("answer", str(result)))
        
        return {
            "response": response,
            "success": "Error" not in response,
            "topic": topic,
            "model": "gpt-4o-mini-enhanced"
        }
        
    except Exception as e:
        return {
            "response": f"Error processing query: {str(e)}",
            "success": False,
            "topic": topic,
            "model": "gpt-4o-mini-enhanced"
        }

print("🚀 Running YouTube RAG Evaluation - Version 3 (enhanced prompt)")
experiment_results_v3 = client.evaluate(
    youtube_target_v3,
    data=dataset_name,
    evaluators=[youtube_relevance, response_quality, response_completeness],
    experiment_prefix="youtube-rag-enhanced",
)

# Enhanced evaluators based on test_langsmith_rag.py patterns

from typing_extensions import Annotated, TypedDict

# Grade output schemas (like in test_langsmith_rag.py)
class YouTubeRelevanceGrade(TypedDict):
    explanation: Annotated[str, "Explain your reasoning for the score"]
    relevant: Annotated[bool, "True if response shows YouTube video context"]

class ResponseQualityGrade(TypedDict):
    explanation: Annotated[str, "Explain your reasoning"]
    quality: Annotated[bool, "True if response is high quality"]

# Enhanced evaluators with structured output
relevance_llm = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(YouTubeRelevanceGrade, method="json_schema", strict=True)

def youtube_relevance_enhanced(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Enhanced YouTube relevance evaluator with reasoning"""
    relevance_instructions = """You are evaluating a YouTube video summarization system.
    
    Grade criteria:
    (1) Response should indicate it's drawing from YouTube video content
    (2) For unrelated questions, system should indicate no relevant info available
    (3) Response should contain video-specific indicators (speakers, mentions, etc.)
    
    A relevance value of True means the response appropriately handles YouTube content.
    A relevance value of False means the response doesn't show YouTube context."""
    
    content = f"""
    QUERY: {inputs['query']}
    TOPIC: {inputs.get('topic', 'N/A')}
    RESPONSE: {outputs.get('response', '')}
    EXPECTED TYPE: {reference_outputs.get('expected_type', 'N/A')}
    """
    
    grade = relevance_llm.invoke([
        {"role": "system", "content": relevance_instructions},
        {"role": "user", "content": content}
    ])
    return grade["relevant"]

# Add this evaluator inspired by test_langsmith_rag.py
def youtube_groundedness(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Check if response is grounded in actual video content"""
    response = outputs.get("response", "")
    topic = inputs.get("topic", "")
    
    # Check if response contains specific claims that could be verified
    # vs generic statements
    specific_indicators = [
        "in the video", "speaker mentions", "according to", 
        "the tutorial shows", "demonstrates", "explains that"
    ]
    
    has_specific_claims = any(indicator in response.lower() for indicator in specific_indicators)
    
    # Penalize vague responses
    vague_indicators = ["generally", "typically", "usually", "often"]
    is_too_vague = sum(1 for indicator in vague_indicators if indicator in response.lower()) > 2
    
    return has_specific_claims and not is_too_vague

# - NEW EVALUATOR: Retrieval quality for YouTube content
def retrieval_quality_enhanced(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """Check quality of retrieved YouTube content"""
    # This would need access to the retrieved documents
    # You might need to modify your target function to return retrieved docs
    
    retrieved_docs = outputs.get("retrieved_docs", [])
    query = inputs["query"]
    
    if not retrieved_docs:
        return False
    
    # Check if retrieved content seems relevant to query
    query_terms = set(query.lower().split())
    relevant_docs = 0
    
    for doc in retrieved_docs:
        doc_text = str(doc).lower()
        if len(query_terms.intersection(set(doc_text.split()))) > 0:
            relevant_docs += 1
    
    return (relevant_docs / len(retrieved_docs)) > 0.5

print("✅ All evaluations completed!")
print("🔗 Check your results in LangSmith dashboard")

# - ENHANCED TARGET FUNCTION: Returning more evaluation info
def youtube_target_enhanced(inputs: dict) -> dict:
    """Enhanced target function returning more evaluation info"""
    query = inputs["query"]
    topic = inputs.get("topic", "langchain")
    
    try:
        video_df = load_video_details(topic=topic)
        embedding = OpenAIEmbeddings(model="text-embedding-3-small")
        chunks = process_documents_semantic(video_df=video_df, embedding_model=embedding)
        
        try:
            collection_name = _format_collection_name(topic)
            vectorstore = create_chroma_vectorstore(chunks, embedding, collection_name=collection_name)
        except TypeError:
            vectorstore = create_chroma_vectorstore(chunks, embedding)
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        result = run_rag_chain(query=query, vectorstore=vectorstore, chat_history=[], llm=llm)
        
        # Get retrieved documents for evaluation
        retrieved_docs = result.get("source_documents", result.get("context", []))
        response = result.get("response", result.get("answer", str(result)))
        
        return {
            "response": response,
            "documents": retrieved_docs,  # Like RAG example
            "success": "Error" not in response,
            "topic": topic,
            "num_retrieved": len(retrieved_docs)
        }
        
    except Exception as e:
        return {
            "response": f"Error processing query: {str(e)}",
            "documents": [],
            "success": False,
            "topic": topic,
            "error": str(e)
        }