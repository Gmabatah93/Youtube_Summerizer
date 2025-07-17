from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
import time  # Add time import
import os
from dotenv import load_dotenv
from src.evaluation import evaluate_transcripts

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
    
    # DECIDED NOT TO INCLUDE EVALUATION IN THIS FUNCTION IN THE FRONTEND
    # # Run transcript evaluation
    # print("\nEvaluating transcript quality...")
    # metrics = evaluate_transcripts(video_df)
    
    # # Add quality scores to DataFrame
    # video_df['quality_score'] = video_df['video_id'].map(metrics.quality_scores)
    # video_df['quality_reason'] = video_df['video_id'].map(metrics.quality_reasons)
    
    # # Print comprehensive statistics
    # print(f"\nTranscript Statistics:")
    # print(f"Total videos: {metrics.total_videos}")
    # print(f"Videos with transcripts: {metrics.videos_with_transcripts}")
    # print(f"Coverage rate: {metrics.coverage_rate:.2f}%")
    # print(f"Average quality score: {metrics.avg_quality_score:.1f}/5")
    # print(f"High quality transcripts: {metrics.high_quality_count}")
    # print(f"Quality pass rate: {metrics.quality_rate:.1f}%")
    
    # if metrics.failed_videos:
    #     print("\nFailed or Low Quality Videos:")
    #     for video_id in metrics.failed_videos:
    #         video = video_df[video_df['video_id'] == video_id].iloc[0]
    #         print(f"Title: {video['title']}")
    #         print(f"URL: {video['url']}")
    #         print(f"Quality Score: {metrics.quality_scores[video_id]}/5")
    #         print(f"Reason: {metrics.quality_reasons[video_id]}")
    #         print("---")

    # # Fix datetime (keep your existing datetime handling)
    # if not video_df.empty:
    #     video_df['publish_time'] = pd.to_datetime(video_df['publish_time'])
    #     video_df['publish_time'] = video_df['publish_time'].dt.strftime("%B %d, %Y at %I:%M %p")
    
    # # Store evaluation metrics in DataFrame attributes
    # video_df.attrs['transcript_coverage_rate'] = metrics.coverage_rate
    # video_df.attrs['transcript_quality_rate'] = metrics.quality_rate
    # video_df.attrs['evaluation_timestamp'] = metrics.timestamp
        
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