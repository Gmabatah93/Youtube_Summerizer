from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
import time  # Add time import
import os
from dotenv import load_dotenv
import json

load_dotenv()
PODCAST_CATEGORY_ID = 22  # YouTube category ID for podcasts

def search_videos(topic, api_key, max_results=20):
    """
    Description:
        Searches for videos on YouTube based on a given topic or keyword.
    
    Args:
        topic (str): The topic or keyword to search for videos on YouTube.
        channel_id (str, optional): The channel ID to filter results.
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
            type='video',
            videoCategoryId=PODCAST_CATEGORY_ID,
            videoDuration='long',
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

def get_video_details(video_ids, api_key, delay: float = 1.0):
    """
    Get video details and transcripts with rate limiting.
    
    Args:
        video_ids: List of YouTube video IDs
        api_key: YouTube API key
        delay: Time to wait between requests in seconds
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
    
    ### Separate LOOP: fetch transcripts ################
    print("=" * 20 + " FETCH TRANSCRIPT " + "=" * 20)
    transcripts_map = {}
    for video_id in video_ids: 
        transcript_text = None
        try:
            print(f"Fetching transcript for video {video_id}...")
            
            # Add delay before request
            time.sleep(delay)
            
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript_text = " ".join([entry['text'] for entry in transcript])
            print(f"Successfully fetched transcript for {video_id}")
            print("---" * 20)
            transcripts_map[video_id] = transcript_text
            
        except Exception as e:
            print(f"Error fetching transcript for Video ID {video_id}: {str(e)}")
            try:
                print(f"Attempting to fetch auto-generated transcript...")
                time.sleep(delay)  # Add delay before retry
                transcript = YouTubeTranscriptApi.get_transcript(
                    video_id, 
                    languages=['en'], 
                    preserve_formatting=True
                )
                transcript_text = " ".join([entry['text'] for entry in transcript])
                print(f"Successfully fetched auto-generated transcript")
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
    print(f"Mapped transcripts to {len(video_df)} videos")

    return video_df


def store_video_details(
    video_df: pd.DataFrame,
    topic: str,
    base_path: str = "data/youtube_data",
    timestamp: str = None
) -> dict:
    """Store video details and transcripts for future analysis."""
    import os
    from datetime import datetime
    
    print(f"\nSTORING FOR TOPIC: {topic}" + "=" * 20)
    # Create timestamp and format topic for filenames
    timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    formatted_topic = topic.lower().replace(' ', '_')
    
    # Create directory structure
    subdirs = ['raw_data', 'transcripts', 'metadata']
    for subdir in subdirs:
        os.makedirs(f"{base_path}/{subdir}", exist_ok=True)
    
    # Prepare paths
    raw_path = f"{base_path}/raw_data/{formatted_topic}_{timestamp}.csv"
    transcript_path = f"{base_path}/transcripts/{formatted_topic}_{timestamp}.csv"
    metadata_path = f"{base_path}/metadata/{formatted_topic}_{timestamp}.json"
    
    # Store full raw data
    video_df.to_csv(raw_path, index=False)
    
    # Store transcripts separately
    transcript_df = video_df[['video_id', 'title', 'transcript']].copy()
    transcript_df.to_csv(transcript_path, index=False)
    
    # Store metadata (convert numpy types to Python native types)
    metadata = {
        'topic': topic,
        'timestamp': timestamp,
        'total_videos': int(len(video_df)),
        'videos_with_transcripts': int(video_df['transcript'].notna().sum()),
        'coverage_rate': float(video_df['transcript'].notna().sum() / len(video_df) * 100),
        'source_urls': [str(url) for url in video_df['url'].tolist()],
        'video_ids': [str(vid) for vid in video_df['video_id'].tolist()]
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nStored video details:")
    print(f"- Raw data: {raw_path}")
    print(f"- Transcripts: {transcript_path}")
    print(f"- Metadata: {metadata_path}")
    
    return {
        'raw_path': raw_path,
        'transcript_path': transcript_path,
        'metadata_path': metadata_path
    }

def load_video_details(topic: str = None, timestamp: str = None, base_path: str = "data/youtube_data") -> pd.DataFrame:
    """
    Load stored video details and transcripts.
    
    Args:
        topic: Optional topic to load specific data
        timestamp: Optional timestamp to load specific version
        base_path: Base directory for data storage
    
    Returns:
        pd.DataFrame: Loaded video details
    """
    import glob
    
    # Find latest data if topic/timestamp not specified
    if not (topic and timestamp):
        pattern = f"{base_path}/raw_data/*.csv"
        files = glob.glob(pattern)
        if not files:
            raise FileNotFoundError("No stored video data found")
        raw_path = max(files)  # Get most recent
    else:
        formatted_topic = topic.lower().replace(' ', '_')
        raw_path = f"{base_path}/raw_data/{formatted_topic}_{timestamp}.csv"
    
    # Load data
    video_df = pd.read_csv(raw_path)
    print(f"Loaded video details from: {raw_path}")
    print(f"Found {len(video_df)} videos")
    
    return video_df



        
# Test the function
# video_ids = search_videos(
#     topic="Financial Freedom @TheDiaryOfACEO",  # Example topic
#     api_key=os.environ['YOUTUBE_API_KEY'],
#     max_results=3
# )

# video_details_df = get_video_details(
#     video_ids=video_ids,
#     api_key=os.environ['YOUTUBE_API_KEY']
# )

# path = store_video_details(
#     video_df=video_details_df,
#     topic="How to make mayonnaise",
#     base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data",
#     timestamp="20231001_120000"  # Example timestamp, can be replaced with current time
# )

# # Test Evaluation
# loaded_video_df = load_video_details(
#     topic="How to make mayonnaise",
#     timestamp="20231001_120000",
#     base_path="/Users/isiomamabatah/Desktop/Python/Projects/Youtube_Summerizer/data/youtube_data"
# )

# from evaluation import evaluate_transcripts

# metrics = evaluate_transcripts(
#     df=loaded_video_df,
#     quality_threshold=0.5,  # Example threshold
#     sample_size=3 # Example minimum view count
# )