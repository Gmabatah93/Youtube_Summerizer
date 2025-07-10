from src.youtube import search_videos, get_video_details
from src.vectorstore import process_documents_recursive, process_documents_semantic, create_chroma_vectorstore
from src.utils import _format_collection_name
from src.workflow import run_rag_chain

# Import all necessary chat model classes
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

import os
from dotenv import load_dotenv
import streamlit as st

# Load environment variables from .env file
load_dotenv()  

# --- CONFIGURATION ---
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "LangChain-YoutubeScraper"
EMBEDDING = OpenAIEmbeddings(model="text-embedding-3-small")

# Define the list of available models from different providers
AVAILABLE_MODELS = {
    "OpenAI": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    "Anthropic": ["claude-3-haiku-20240307", "claude-3-sonnet-20240229"],
    "Google": ["gemini-1.5-flash-latest", "gemini-1.5-pro-latest"]
}
# Create a flattened list for the selectbox options
MODEL_OPTIONS = [model for provider_models in AVAILABLE_MODELS.values() for model in provider_models]


# --- STREAMLIT APP ---
st.set_page_config(page_title="🎬 Youtube Summarizer", layout="wide")
st.title("🎬 Youtube Summarizer")

# Initialize session state variables
if "chat_ready" not in st.session_state:
    st.session_state.chat_ready = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
if "selected_model" not in st.session_state:
    st.session_state.selected_model = MODEL_OPTIONS[0]

# ==============================
# Part 1: Search & RAG Creation
# ==============================
if not st.session_state.chat_ready:
    st.subheader("🔍 Search for YouTube Videos")
    topic = st.text_input("Enter the topic you want to search for:", placeholder="e.g., 'LangChain Agents'")
    max_results = st.slider("Select the number of videos to process:", min_value=1, max_value=20, value=5)
    submit_button = st.button("Create RAG Assistant")

    if submit_button and topic:
        with st.spinner("Searching YouTube, processing transcripts, and building the RAG assistant..."):
            video_ids = search_videos(topic=topic, api_key=os.environ.get('YOUTUBE_API_KEY'), max_results=max_results)
            video_df = get_video_details(video_ids=video_ids, api_key=os.environ.get('YOUTUBE_API_KEY'))

            video_df["Video Title"] = video_df.apply(lambda row: f"[{row['title']}](https://www.youtube.com/watch?v={row['video_id']})", axis=1)
            st.session_state["video_df_display"] = video_df[["Video Title", "author", "publish_time", "view_count"]]

            chunks = process_documents_semantic(video_df=video_df, embedding_model=EMBEDDING)
            formatted_topic = _format_collection_name(topic)
            st.session_state.vectorstore = create_chroma_vectorstore(chunks, EMBEDDING, topic=formatted_topic)

            st.session_state.chat_ready = True
            st.session_state.messages = [{"role": "ai", "content": f"Hi! I'm ready to answer questions about **{topic}**. Choose your AI model from the sidebar and let's begin!"}]
            st.rerun()

# ===================================
# Part 2: Chat Interface
# ===================================
if st.session_state.chat_ready:
    with st.sidebar:
        st.subheader("⚙️ Settings")
        # Ensure selected_model is initialized before use
        if 'selected_model' not in st.session_state:
            st.session_state.selected_model = MODEL_OPTIONS[0]
        
        selected_model = st.selectbox(
            "Choose your AI model:",
            options=MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(st.session_state.selected_model)
        )
        st.session_state.selected_model = selected_model
    
    st.subheader("🤖 Chat with RAGGY (Your YouTube Assistant)")

    with st.expander("📄 Show Processed Video Details"):
        if "video_df_display" in st.session_state:
            st.markdown(st.session_state.video_df_display.to_markdown(index=False), unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if query := st.chat_input("Explicitly mention 'Youtube' if you want me to ref the YouTube videos..."):
        st.session_state.messages.append({"role": "human", "content": query})
        with st.chat_message("human"):
            st.markdown(query)

        if st.session_state.vectorstore:
            with st.spinner(f"Thinking with {st.session_state.selected_model}..."):
                
                # --- LLM Factory Logic ---
                try:
                    model_name = st.session_state.selected_model
                    if model_name in AVAILABLE_MODELS.get("OpenAI", []):
                        llm = ChatOpenAI(model=model_name, temperature=0, streaming=True)
                    elif model_name in AVAILABLE_MODELS.get("Anthropic", []):
                        llm = ChatAnthropic(model=model_name, temperature=0)
                    elif model_name in AVAILABLE_MODELS.get("Google", []):
                        llm = ChatGoogleGenerativeAI(model=model_name, temperature=0, convert_system_message_to_human=True)
                    else:
                        st.error(f"Unknown model provider for: {model_name}")
                        llm = None
                except Exception as e:
                    st.error(f"Failed to initialize the AI model. Ensure you have the correct API keys set in your .env file. Error: {e}")
                    llm = None
                # --- End LLM Factory ---

                if llm:
                    result = run_rag_chain(
                        query=query,
                        vectorstore=st.session_state.vectorstore,
                        chat_history=[{"role": msg["role"], "content": str(msg["content"])} for msg in st.session_state.messages[:-1]],
                        llm=llm
                    )
                    
                    response_content = result.get("response", "Sorry, I couldn't generate a response.")
                    st.session_state.messages.append({"role": "ai", "content": response_content})
                    with st.chat_message("ai"):
                        st.markdown(response_content)
        else:
            st.error("Error: The vectorstore is not available. Please restart the search.")
