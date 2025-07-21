from typing import TypedDict, Dict, List, Any
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, END
from langsmith import traceable
from src.rag_evaluation import evaluate_rag_response
from src.rag_post_processing import (
    post_process_documents,
    rerank_documents,
    aggregate_and_compress
)

import uuid
from src.prompts import get_decision_prompt, get_rag_prompt, get_direct_prompt

class Action(Enum):
    SEARCH_VIDEOS = "search_videos"
    DIRECT_ANSWER = "direct_answer"

class YouTubeRAGState(TypedDict):
    """Enhanced state for YouTube ReAct workflow."""
    query: str
    chat_history: List[Dict[str, str]]
    context: List[Document]
    response: str
    error: str
    action: str
    thought: str
    thread_id: str  

# The function now accepts an instantiated llm object instead of a model_name string
def create_youtube_rag_chain(vectorstore: Any, llm: BaseChatModel):
    """Create a RAG chain using a provided LLM instance."""
    print("=" * 30)
    print("=" * 20 + "LANGGRAPH" + "=" * 20)
    print("=" * 30)

    def decide_action(state: YouTubeRAGState) -> YouTubeRAGState:
        """Decide whether to use vectorstore based on explicit YouTube mention."""
        print("=" * 10 + "DECIDE NODE" + "=" * 10)
        print(f"Deciding action for query: {state['query']}")
        try:
            if "youtube" not in state["query"].lower():
                state["action"] = Action.DIRECT_ANSWER.value
                state["thought"] = "No explicit mention of YouTube. Using direct answer."
                return state

            print(f"YouTube mention found")
            decision_prompt = get_decision_prompt()
            # The llm object is already initialized and ready to use
            chain = decision_prompt | llm
            result = chain.invoke({"query": state["query"]})
            
            state["action"] = (
                Action.SEARCH_VIDEOS.value 
                if "SEARCH_VIDEOS" in result.content 
                else Action.DIRECT_ANSWER.value
            )
            state["thought"] = result.content
            return state
        except Exception as e:
            state["error"] = f"Decision error: {str(e)}"
            return state

    @traceable(run_type="retriever", name="Enhanced Chroma Retrieval")
    def retrieve(state: YouTubeRAGState) -> YouTubeRAGState:
        """Enhanced document retrieval with post-processing and reranking."""
        print("=" * 10 + "ENHANCED RETRIEVE NODE" + "=" * 10)
        try:
            if state["action"] == Action.SEARCH_VIDEOS.value:
                # Step 1: Initial retrieval (get more candidates)
                print("Step 1: Getting initial candidates...")
                raw_docs = vectorstore.similarity_search_with_score(state["query"], k=15)
                print(f"Found {len(raw_docs)} initial candidates")
                
                # Step 2: Post-process and filter
                print("Step 2: Post-processing and filtering...")
                processed_docs = post_process_documents(raw_docs, state["query"])
                print(f"After filtering: {len(processed_docs)} quality documents")
                
                # Step 3: Rerank by relevance and metadata
                print("Step 3: Reranking by metadata and relevance...")
                reranked_docs = rerank_documents(processed_docs, state["query"])
                print(f"Reranked {len(reranked_docs)} documents")
                
                # Step 4: Aggregate and compress context
                print("Step 4: Aggregating and compressing context...")
                final_context = aggregate_and_compress(reranked_docs[:5], state["query"])
                
                state["context"] = final_context
                print(f"Final context: {len(final_context)} aggregated documents")
                
                # Log final context for debugging
                for i, doc in enumerate(final_context):
                    title = doc.metadata.get('title', 'Unknown')[:50]
                    author = doc.metadata.get('author', 'Unknown')
                    aggregated = doc.metadata.get('aggregated', False)
                    print(f"  Doc {i+1}: {title}... by {author} {'(aggregated)' if aggregated else ''}")
            return state
        except Exception as e:
            print(f"Enhanced retrieval failed: {str(e)}")
            print("Falling back to basic retrieval...")
            # Fallback to basic retrieval
            try:
                docs = vectorstore.similarity_search(state["query"], k=5)
                state["context"] = docs
                print(f"Fallback: Retrieved {len(docs)} documents")
            except Exception as fallback_error:
                state["error"] = f"Both enhanced and fallback retrieval failed: {str(fallback_error)}"
            return state

    def generate_response(state: YouTubeRAGState) -> YouTubeRAGState:
        """Generate response based on action and context."""
        print("=" * 10 + "GENERATE NODE" + "=" * 10)
        try:
            chat_history = []
            for msg in state["chat_history"]:
                if msg["role"] == "human":
                    chat_history.append(HumanMessage(content=msg["content"]))
                else:
                    chat_history.append(AIMessage(content=msg["content"]))

            # Determine which prompt to use based on action
            if state["action"] == Action.SEARCH_VIDEOS.value:
                print(f"\n'YouTube' mention found adding context")
                prompt = get_rag_prompt()
            else:
                print(f"\nNo YouTube mention found, answering with just: {llm.model_name}")
                prompt = get_direct_prompt()

            chain = prompt | llm
                
            state["response"] = chain.invoke({
                "context": "\n".join(doc.page_content for doc in state["context"]) if state["context"] else "",
                "chat_history": chat_history,
                "query": state["query"]
            }).content

            # Evaluate RAG quality if in testing mode
            if state.get("evaluate_rag", False):
                metrics = evaluate_rag_response(
                    query=state["query"],
                    retrieved_chunks=state["context"],
                    generated_response=state["response"]
                )
                state["rag_metrics"] = metrics
            
            return state
        except Exception as e:
            state["error"] = f"Generation error: {str(e)}"
            return state

    workflow = StateGraph(YouTubeRAGState)
    
    workflow.add_node("decide", decide_action)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("generate", generate_response)
    
    def route_action(state: YouTubeRAGState) -> str:
        return "retrieve" if state["action"] == Action.SEARCH_VIDEOS.value else "generate"

    workflow.set_entry_point("decide")
    workflow.add_conditional_edges("decide", route_action, {"retrieve": "retrieve", "generate": "generate"})
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    return workflow.compile()

# This function now accepts the llm object to pass it down
def run_rag_chain(
    query: str,
    vectorstore: Any,
    llm: BaseChatModel,
    chat_history: List[Dict[str, str]] = None,
    thread_id: str = None
) -> Dict[str, Any]:
    """Run the RAG workflow with a query and an LLM instance."""
    
    # Generate thread_id if not provided
    if not thread_id:
        thread_id = str(uuid.uuid4())

    state = YouTubeRAGState(
        query=query,
        chat_history=chat_history or [],
        context=[],
        response="",
        error="",
        action="",
        thought=""
    )
    
    # Pass the llm object directly to the chain creator
    app = create_youtube_rag_chain(vectorstore, llm)
    result = app.invoke(state)
    
    return {
        "response": result["response"],
        "context": result["context"],
        "error": result["error"],
        "action": result["action"],
        "thought": result["thought"]
    }