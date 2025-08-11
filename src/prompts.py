from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_decision_prompt() -> ChatPromptTemplate:
    """Get the prompt for deciding whether to search videos."""
    return ChatPromptTemplate.from_messages([
        ("system", """You are an AI that decides how to answer questions.
        
        RULES:
        - Choose SEARCH_VIDEOS only if the word "youtube" appears in the question
        - Choose DIRECT_ANSWER for all other questions
        
        Respond with either "SEARCH_VIDEOS" or "DIRECT_ANSWER" followed by your reasoning.
        """),
        ("human", "{query}")
    ])


def get_rag_prompt() -> ChatPromptTemplate:
    """Get the prompt for RAG-based responses."""
    return ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant that provides concise answers based on the given context.
        Use the provided context to answer the query directly. If citing a YouTube video is necessary, include only the most relevant video title and URL as a source.
        
        Context: {context}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{query}")
    ])


def get_direct_prompt() -> ChatPromptTemplate:
    """Get the prompt for direct (non-RAG) responses."""
    return ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant that answers questions.
        Since the question didn't mention YouTube specifically, I'll provide a general answer.
        If you want information from YouTube videos, please include 'YouTube' in your question.
        """),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{query}")
    ])