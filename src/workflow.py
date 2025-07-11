from typing import TypedDict, Dict, List, Any
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import StateGraph, END
from langsmith import traceable
from src.rag_evaluation import evaluate_rag_response

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
    
    def decide_action(state: YouTubeRAGState) -> YouTubeRAGState:
        """Decide whether to use vectorstore based on explicit YouTube mention."""
        try:
            if "youtube" not in state["query"].lower():
                state["action"] = Action.DIRECT_ANSWER.value
                state["thought"] = "No explicit mention of YouTube. Using direct answer."
                return state

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

    @traceable(run_type="retriever", name="Chroma Retrieval")
    def retrieve(state: YouTubeRAGState) -> YouTubeRAGState:
        """Retrieve documents if needed."""
        try:
            if state["action"] == Action.SEARCH_VIDEOS.value:
                docs = vectorstore.similarity_search(state["query"], k=5)
                state["context"] = docs
                print(f"Retrieved {len(docs)} documents for context")
            return state
        except Exception as e:
            state["error"] = f"Retrieval error: {str(e)}"
            return state

    def generate_response(state: YouTubeRAGState) -> YouTubeRAGState:
        """Generate response based on action and context."""
        try:
            chat_history = []
            for msg in state["chat_history"]:
                if msg["role"] == "human":
                    chat_history.append(HumanMessage(content=msg["content"]))
                else:
                    chat_history.append(AIMessage(content=msg["content"]))

            prompt = get_rag_prompt() if state["action"] == Action.SEARCH_VIDEOS.value else get_direct_prompt()
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


# def create_youtube_rag_chain(vectorstore: Any, model_name: str = "gpt-4o-mini"):
#     """Create a RAG chain for YouTube content retrieval and response generation.
    
#     Args:
#         vectorstore: Initialized vector store (Chroma or Qdrant)
#         model_name: Name of the OpenAI model to use
    
#     Returns:
#         Compiled workflow that can be invoked with a state dictionary
#     """
    
#     # Initialize LLM
#     llm = ChatOpenAI(model=model_name)
    
#     def decide_action(state: YouTubeRAGState) -> YouTubeRAGState:
#         """Decide whether to use vectorstore based on explicit YouTube mention."""
#         try:
#             if "youtube" not in state["query"].lower():
#                 state["action"] = Action.DIRECT_ANSWER.value
#                 state["thought"] = "No explicit mention of YouTube. Using direct answer."
#                 return state

#             decision_prompt = get_decision_prompt()
#             chain = decision_prompt | llm
#             result = chain.invoke({"query": state["query"]})
            
#             state["action"] = (
#                 Action.SEARCH_VIDEOS.value 
#                 if "SEARCH_VIDEOS" in result.content 
#                 else Action.DIRECT_ANSWER.value
#             )
#             state["thought"] = result.content
#             return state
#         except Exception as e:
#             state["error"] = f"Decision error: {str(e)}"
#             return state

#     def retrieve(state: YouTubeRAGState) -> YouTubeRAGState:
#         """Retrieve documents if needed."""
#         try:
#             if state["action"] == Action.SEARCH_VIDEOS.value:
#                 docs = vectorstore.similarity_search(state["query"], k=3)
#                 state["context"] = docs
#                 print(f"Retrieved {len(docs)} documents for context")
#             return state
#         except Exception as e:
#             state["error"] = f"Retrieval error: {str(e)}"
#             return state

#     def generate_response(state: YouTubeRAGState) -> YouTubeRAGState:
#         """Generate response based on action and context."""
#         try:
#             chat_history = []
#             for msg in state["chat_history"]:
#                 if msg["role"] == "human":
#                     chat_history.append(HumanMessage(content=msg["content"]))
#                 else:
#                     chat_history.append(AIMessage(content=msg["content"]))

#             prompt = get_rag_prompt() if state["action"] == Action.SEARCH_VIDEOS.value else get_direct_prompt()
#             chain = prompt | llm
            
#             state["response"] = chain.invoke({
#                 "context": "\n".join(doc.page_content for doc in state["context"]) if state["context"] else "",
#                 "chat_history": chat_history,
#                 "query": state["query"]
#             }).content

#             return state
#         except Exception as e:
#             state["error"] = f"Generation error: {str(e)}"
#             return state


#     # Set up workflow
#     workflow = StateGraph(YouTubeRAGState)
    
#     # Add nodes
#     workflow.add_node("decide", decide_action)
#     workflow.add_node("retrieve", retrieve)
#     workflow.add_node("generate", generate_response)
    
#     # Define the router function for conditional edges
#     def route_action(state: YouTubeRAGState) -> str:
#         """Routes to the next node based on the 'action' key in the state."""
#         return "retrieve" if state["action"] == Action.SEARCH_VIDEOS.value else "generate"

#     # Set entry point
#     workflow.set_entry_point("decide")
    
#     # Define edges
#     workflow.add_conditional_edges(
#         "decide",       # The node that dictates the path
#         route_action,   # The function that returns the next node's name
#         {               # A mapping of the router's output to the actual node
#             "retrieve": "retrieve",
#             "generate": "generate"
#         }
#     )
#     workflow.add_edge("retrieve", "generate") # After retrieval, always generate
#     workflow.add_edge("generate", END)        # After generation, end the process
    
#     # Compile and return
#     return workflow.compile()

# def run_rag_chain(
#     query: str,
#     vectorstore: Any,
#     chat_history: List[Dict[str, str]] = None,
#     model_name: str = "gpt-4-turbo-preview"
# ) -> Dict[str, Any]:
#     """Run the RAG workflow with a query.
    
#     Args:
#         query: User's question
#         vectorstore: Initialized vector store
#         chat_history: Optional chat history
#         model_name: Name of the OpenAI model to use
    
#     Returns:
#         Dictionary containing response, context, and any errors
#     """
    
#     # Initialize state
#     state = YouTubeRAGState(
#         query=query,
#         chat_history=chat_history or [],
#         context=[],
#         response="",
#         error="",
#         action="",
#         thought=""
#     )
    
#     # Create and run workflow
#     app = create_youtube_rag_chain(vectorstore, model_name)
#     result = app.invoke(state)
    
#     return {
#         "response": result["response"],
#         "context": result["context"],
#         "error": result["error"],
#         "action": result["action"],
#         "thought": result["thought"]
#     }