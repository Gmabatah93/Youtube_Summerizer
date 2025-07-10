
from src.youtube import search_videos, get_video_details
from src.vectorstore import process_documents_recursive, process_documents_semantic

from langchain_openai import OpenAIEmbeddings

import os
import pandas as pd
from dotenv import load_dotenv
load_dotenv()



embedding = OpenAIEmbeddings(model="text-embedding-3-small")

# API
topic = "What is an AI Agent"
df = pd.read_csv("data/aiAgent.csv")

video_ids = search_videos(
    topic=topic,
    api_key=os.environ['YOUTUBE_API_KEY'],
    max_results=5
)

video_df = get_video_details(
    video_ids=video_ids,
    api_key=os.environ['YOUTUBE_API_KEY']
)
video_df.to_csv("data/aiAgent.csv", index=False)


# VECTORSTORE
# - recursive
chunk_recursive = process_documents_recursive(df)
chunk_semantic = process_documents_semantic(df, embedding)
