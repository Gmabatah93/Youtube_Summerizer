from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_decision_prompt() -> ChatPromptTemplate:
    """Get the prompt for deciding whether to search videos."""
    return ChatPromptTemplate.from_messages([
        ("system", """You are an AI that decides how to answer questions.

            RULES:
            - Choose SEARCH_VIDEOS only if the word "youtube" appears in the question
            - Choose DIRECT_ANSWER for all other questions

        Respond with exactly one token: SEARCH_VIDEOS or DIRECT_ANSWER. Do not include any reasoning.
        """),
        ("human", "{query}")
    ])


def get_rag_prompt() -> ChatPromptTemplate:
    """Get the prompt for RAG-based responses."""
    return ChatPromptTemplate.from_messages([
        ("system", """You are a helpful AI assistant that provides concise answers strictly based on the given context (YouTube video transcripts).
            - Only use the provided context to answer the query.
            - Do not recommend or cite any videos that are not in the context.
            - If the context is empty or insufficient, say so and ask the user to refine the query.
            - Prefer bullet points that synthesize lessons from the transcripts; avoid generic advice not present in the context.
            - If citing, include at most one most relevant video title and URL.
         
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