
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi

import pandas as pd

import os
from dotenv import load_dotenv

load_dotenv()

def search_videos(topic, api_key, max_results=20):
    """
    Description:
        Searches for videos on YouTube based on a given topic or keyword.
    
    Args:
        topic (str): The topic or keyword to search for videos on YouTube.
        api_key (str): The API key for accessing the YouTube Data API.
        max_results (int, optional): The maximum number of video results to retrieve. Defaults to 20.

    Returns:
        list: A list of video IDs corresponding to the search results.
    """

    # - Initialize the YouTube API client
    youtube = build(serviceName='youtube', version='v3', developerKey=api_key)

    try:
        search_request = youtube.search().list(
            q=topic,
            part='id,snippet',
            maxResults=max_results,
            type='video'
        )
        search_response = search_request.execute()
        
        video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]
        return video_ids
    except HttpError as e:
        print(f"An HTTP error occurred during video search: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during video search: {e}")
        return []

def get_video_details(video_ids, api_key):
    """
    Description:
        Retrieves detailed information about a list of YouTube videos, 
        including transcriptsmetadata and statistics.

    Args:
        video_ids (list): A list of YouTube video IDs for which details are to be retrieved.
        api_key (str): The API key for accessing the YouTube Data API.

    Returns:
        pd.DataFrame: A pandas DataFrame containing video details such as 
        title, author, description, publish time, view count, and transcripts.
    """

    # Initialize the YouTube API client
    youtube = build(serviceName='youtube', version='v3', developerKey=api_key)
    
    
    video_data_list = []
    ### LOOP: Iterate through batch & fetch details ##########  
    for i in range(0, len(video_ids), 50): 
        batch_ids = video_ids[i:i+50]

        try:
            video_request = youtube.videos().list(
                part='snippet,contentDetails,statistics,status',
                id=",".join(batch_ids)
            )
            video_response = video_request.execute()
            # - extract video details from the response
            for item in video_response.get('items', []):
                video_id = item['id']
                video_author = item.get("snippet", {}).get("channelTitle", "N/A")
                video_title = item.get("snippet", {}).get("title", "N/A")
                video_description = item.get("snippet", {}).get("description", "N/A")
                publish_time = item.get("snippet", {}).get("publishedAt", "N/A")
                video_viewcount = item.get("statistics", {}).get("viewCount", 0)
            
                video_data = {
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "author": video_author,
                    "title": video_title,
                    "description": video_description,
                    "publish_time": publish_time,
                    "view_count": int(video_viewcount)
                }
                video_data_list.append(video_data)

        except HttpError as e:
            print(f"An HTTP error occurred for batch {batch_ids}: {e}")
            # You can add retry logic here, or simply skip this batch
            continue
        except Exception as e:
            print(f"An unexpected error occurred for batch {batch_ids}: {e}")
            continue
    
    ### Seperate LOOP: fetch transcripts ################
    transcripts_map = {}
    # - this ensures that even if a video's metadata fetch failed, we still attempt its transcript,
    # - and it avoids issues if the order or number of successfully fetched videos differs from original video_ids.
    for video_id in video_ids: 
        transcript_text = None
        try:
            print(f"Fetching transcript for video {video_id}...")
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript_text = " ".join([entry['text'] for entry in transcript])
            print(f"Successfully fetched transcript for {video_id}")
            transcripts_map[video_id] = transcript_text
        except Exception as e:
            print(f"Error fetching transcript for Video ID {video_id}: {str(e)}")
            # Try fetching with auto-generated captions
            try:
                print(f"Attempting to fetch auto-generated transcript for {video_id}...")
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'], preserve_formatting=True)
                transcript_text = " ".join([entry['text'] for entry in transcript])
                print(f"Successfully fetched auto-generated transcript for {video_id}")
                transcripts_map[video_id] = transcript_text                
            except Exception as auto_e:
                print(f"Error fetching auto-generated transcript: {str(auto_e)}")
                transcripts_map[video_id] = None
            

    # Create a DataFrame
    video_df = pd.DataFrame(video_data_list)
    
    # Add transcripts to the DataFrame
    # - this correctly aligns transcripts even if some video details failed to fetch.
    print("\nMapping transcripts to DataFrame...")
    video_df['transcript'] = video_df['video_id'].map(transcripts_map)
    
    # Print detailed transcript statistics
    total_videos = len(video_df)
    videos_with_transcripts = video_df['transcript'].notna().sum()
    videos_without_transcripts = video_df['transcript'].isna().sum()
    
    print(f"\nTranscript Statistics:")
    print(f"Total videos: {total_videos}")
    print(f"Videos with transcripts: {videos_with_transcripts}")
    print(f"Videos without transcripts: {videos_without_transcripts}")
    
    if videos_without_transcripts > 0:
        print("\nVideos missing transcripts:")
        missing_transcripts = video_df[video_df['transcript'].isna()]
        for _, row in missing_transcripts.iterrows():
            print(f"Title: {row['title']}")
            print(f"URL: {row['url']}")
            print("---")

    # Fix datetime
    if not video_df.empty:
        video_df['publish_time'] = pd.to_datetime(video_df['publish_time'])
        video_df['publish_time'] = video_df['publish_time'].dt.strftime("%B %d, %Y at %I:%M %p")
        
    return video_df




# # Test the function
# video_ids = search_videos(
#     topic="How to make mayonnaise",
#     api_key=os.environ['YOUTUBE_API_KEY'],
#     max_results=5
# )

# video_details_df = get_video_details(
#     video_ids=video_ids,
#     api_key=os.environ['YOUTUBE_API_KEY']
# )