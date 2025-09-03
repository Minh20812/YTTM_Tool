import subprocess
import json
import os
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from youtube_rss_fetcher import get_latest_videos_from_rss
from dotenv import load_dotenv
import time
import hashlib

load_dotenv()

def initialize_firebase():
    """Initialize Firebase connection"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Initialize if not already done
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
        if not service_account_json:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set")
        # Parse JSON string thành dict
        service_account_info = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def normalize_youtube_url(url):
    """Normalize YouTube URL to standard format"""
    if not url:
        return url
    
    # Extract video ID from various YouTube URL formats
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    return url

def extract_video_id_from_url(url):
    """Extract video ID from YouTube URL"""
    if not url:
        return None
    
    import re
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_recent_video_data_from_firebase(days_back=2):
    """
    Get both URLs and video IDs for robust duplicate detection
    """
    db = initialize_firebase()
    
    # Calculate cutoff timestamp
    cutoff_time = datetime.now() - timedelta(days=days_back)
    
    # Query recent videos
    docs = db.collection("latest_video_links") \
             .where("createdAt", ">=", cutoff_time) \
             .order_by("createdAt", direction=firestore.Query.DESCENDING) \
             .stream()
    
    existing_data = {
        'urls': set(),
        'video_ids': set(),
        'url_title_combos': set()  # Extra protection
    }
    doc_count = 0
    
    for doc in docs:
        doc_count += 1
        data = doc.to_dict()
        
        # Add normalized URL
        url = data.get("url")
        if url:
            normalized_url = normalize_youtube_url(url)
            existing_data['urls'].add(normalized_url)
            
            # Create URL+Title combo for extra protection
            title = data.get("title", "").strip().lower()
            if title:
                combo_key = f"{normalized_url}||{title}"
                existing_data['url_title_combos'].add(combo_key)
        
        # Add video ID for extra protection
        video_id = data.get("video_id")
        if video_id:
            existing_data['video_ids'].add(video_id)
    
    print(f"📚 Found {len(existing_data['urls'])} URLs, {len(existing_data['video_ids'])} video IDs, {len(existing_data['url_title_combos'])} combos in the last {days_back} days")
    return existing_data

def is_video_duplicate_optimized(video_data, existing_data):
    """
    Enhanced duplicate check using multiple methods
    """
    video_url = video_data.get('url')
    video_title = video_data.get('title', '').strip().lower()
    
    # Method 1: Check by normalized URL
    if video_url:
        normalized_url = normalize_youtube_url(video_url)
        if normalized_url in existing_data['urls']:
            return True, "URL match"
        
        # Method 2: Check by URL+Title combo (extra protection against slight variations)
        if video_title:
            combo_key = f"{normalized_url}||{video_title}"
            if combo_key in existing_data['url_title_combos']:
                return True, "URL+Title combo match"
    
    # Method 3: Check by video ID (most reliable)
    video_id = video_data.get('video_id')
    if not video_id:
        # Extract video ID from URL if not provided
        video_id = extract_video_id_from_url(video_url)
        if video_id:
            video_data['video_id'] = video_id  # Cache for later use
    
    if video_id and video_id in existing_data['video_ids']:
        return True, "Video ID match"
    
    return False, "Not duplicate"

def get_video_info_with_retry(video_url, max_retries=2):
    """Get video information using yt-dlp with retry and better error handling"""
    for attempt in range(max_retries):
        try:
            print(f"   🔍 Fetching video info (attempt {attempt + 1}/{max_retries})...")
            
            # Use more specific options for better reliability
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--print-json", 
                "--no-warnings",
                "--no-check-certificates",  # Skip SSL verification if needed
                "--ignore-errors",  # Continue on errors
                "--extract-flat", "False",  # Extract full metadata
                video_url
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30  # Reduced timeout
            )
            
            # Check if we got output
            if result.stdout.strip():
                try:
                    video_info = json.loads(result.stdout.strip())
                    print(f"   ✅ Successfully fetched video info")
                    return video_info
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ JSON decode error: {e}")
                    print(f"   📝 Raw output: {result.stdout[:200]}...")
                    
            if result.stderr:
                print(f"   ⚠️ stderr: {result.stderr[:200]}...")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏱️ Timeout on attempt {attempt + 1}")
        except Exception as e:
            print(f"   ❌ Error on attempt {attempt + 1}: {e}")
        
        # Wait before retry
        if attempt < max_retries - 1:
            time.sleep(2)
    
    print(f"   ❌ Failed to fetch info after {max_retries} attempts")
    return None

def create_video_document(video_data, video_info=None):
    """Create video document with proper data handling"""
    video_url = video_data.get('url', '')
    
    # Extract/ensure video ID
    if video_info:
        video_id = video_info.get('id', '')
    else:
        video_id = video_data.get('video_id', '')
    
    # Fallback: extract video ID from URL if not available
    if not video_id:
        video_id = extract_video_id_from_url(video_url) or ''
    
    # Ensure video_data has video_id for future duplicate checks
    video_data['video_id'] = video_id
    
    # Use yt-dlp data if available, otherwise RSS data
    if video_info:
        title = video_info.get('title', video_data.get('title', 'Unknown'))
        channel = video_info.get('uploader', video_data.get('channel', 'Unknown'))
        upload_date = video_info.get('upload_date', video_data.get('upload_date', ''))
        duration = video_info.get('duration', 0)
        view_count = video_info.get('view_count', 0)
        description = video_info.get('description', '')[:500] if video_info.get('description') else ''
    else:
        title = video_data.get('title', 'Unknown')
        channel = video_data.get('channel', 'Unknown')
        upload_date = video_data.get('upload_date', '')
        duration = 0
        view_count = 0
        description = ''
    
    # Create unique document ID to prevent duplicates at Firestore level
    doc_id = f"{video_id}_{int(time.time())}" if video_id else f"url_{hashlib.md5(video_url.encode()).hexdigest()[:8]}_{int(time.time())}"
    
    # Normalize URL
    normalized_url = normalize_youtube_url(video_url)
    
    video_doc = {
        "url": normalized_url,
        "original_url": video_url,
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "channel_url": video_data.get('channel_url', ''),
        "subtitle_codes": video_data.get('subtitle_codes', 'vi'),
        "upload_date": upload_date,
        "duration": duration,
        "view_count": view_count,
        "description": description,
        "is_short": video_data.get('is_short', False),
        "subtitle_downloaded": False,
        "processed": False,
        "thumbnail": video_data.get('thumbnail', ''),
        "thumbnail_quality": video_data.get('thumbnail_quality', ''),
        "all_thumbnails": video_data.get('all_thumbnails', {}),
        "createdAt": firestore.SERVER_TIMESTAMP,
        "processing_method": "rss_optimized",
        "yt_dlp_success": video_info is not None
    }
    
    return doc_id, video_doc

def add_video_to_firebase(video_data):
    """Add new video data to Firebase with enhanced duplicate prevention"""
    db = initialize_firebase()
    
    video_url = video_data.get('url')
    print(f"   🎬 Processing: {video_data.get('title', 'Unknown')[:50]}...")
    print(f"   🔗 URL: {video_url}")
    
    # Try to get additional video info
    video_info = get_video_info_with_retry(video_url)
    
    # Create document
    doc_id, video_doc = create_video_document(video_data, video_info)
    
    try:
        # Use set with document ID to prevent duplicates
        db.collection("latest_video_links").document(doc_id).set(video_doc)
        
        # Format success message
        title = video_doc['title']
        subtitle_info = f" [Subtitles: {video_doc.get('subtitle_codes', 'vi')}]"
        info_source = " [yt-dlp: ✅]" if video_info else " [yt-dlp: ❌]"
        
        print(f"   ✅ Added to Firebase: {title[:50]}...{subtitle_info}{info_source}")
        return True
        
    except Exception as e:
        print(f"   ❌ Failed to add to Firebase: {e}")
        return False

def save_new_video_links_to_file(videos):
    """Save new video links to file (if this function is used elsewhere)"""
    if not videos:
        return
        
    filename = f"new_video_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(videos, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(videos)} videos to {filename}")
    except Exception as e:
        print(f"❌ Error saving to file: {e}")

def process_new_videos():
    """
    Main function with enhanced duplicate prevention and error handling
    """
    print("🚀 Starting enhanced new video processing...")
    
    # Step 1: Get latest videos from RSS feeds
    print("\n📡 Fetching latest videos from YouTube RSS feeds...")
    try:
        new_videos = get_latest_videos_from_rss(
            return_links=True,
            hours=36,  # Scan last 36 hours
            skip_shorts=True,  # Skip YouTube Shorts
        )
    except Exception as e:
        print(f"❌ Error fetching videos from RSS: {e}")
        return
    
    if not new_videos:
        print("❌ No new videos found from RSS feeds")
        return
    
    print(f"📋 Found {len(new_videos)} videos from RSS scan")
    
    # Step 2: Get existing video data from Firebase (last 2 days only)
    print("\n📚 Loading recent videos from Firebase (last 2 days)...")
    existing_data = get_recent_video_data_from_firebase(days_back=2)
    
    # Step 3: Filter duplicates with enhanced checking
    truly_new_videos = []
    duplicate_count = 0
    
    print(f"\n🔍 Checking for duplicates...")
    for i, video in enumerate(new_videos, 1):
        is_duplicate, match_reason = is_video_duplicate_optimized(video, existing_data)
        
        video_title = video.get('title', 'Unknown')[:50]
        channel = video.get('channel', 'Unknown')
        video_id = video.get('video_id') or extract_video_id_from_url(video.get('url', ''))
        
        print(f"\n[{i}/{len(new_videos)}] {video_title}...")
        print(f"   📺 Channel: {channel}")
        print(f"   🆔 Video ID: {video_id}")
        
        if is_duplicate:
            duplicate_count += 1
            print(f"   ⏭️ DUPLICATE ({match_reason}) - Skipping")
        else:
            truly_new_videos.append(video)
            print(f"   🆕 NEW - Will add to Firebase")
    
    if not truly_new_videos:
        print(f"\n✅ All {len(new_videos)} videos are duplicates - nothing to add")
        return
    
    print(f"\n🎯 Found {len(truly_new_videos)} truly new videos (skipped {duplicate_count} duplicates)")
    
    # Step 4: Add new videos to Firebase
    print(f"\n📤 Adding {len(truly_new_videos)} new videos to Firebase...")
    successful_adds = 0
    failed_adds = 0
    
    for i, video in enumerate(truly_new_videos, 1):
        print(f"\n[{i}/{len(truly_new_videos)}] Adding to Firebase...")
        
        if add_video_to_firebase(video):
            successful_adds += 1
            # Update existing_data to prevent processing duplicates in the same batch
            video_url = normalize_youtube_url(video.get('url', ''))
            video_id = video.get('video_id')
            if video_url:
                existing_data['urls'].add(video_url)
            if video_id:
                existing_data['video_ids'].add(video_id)
        else:
            failed_adds += 1
    
    # Step 5: Final summary
    print("\n" + "="*70)
    print(f"📊 ENHANCED PROCESSING SUMMARY:")
    print(f"   📡 Total videos from RSS: {len(new_videos)}")
    print(f"   🔄 Duplicates found (last 2 days check): {duplicate_count}")
    print(f"   🆕 Truly new videos identified: {len(truly_new_videos)}")
    print(f"   ✅ Successfully added to Firebase: {successful_adds}")
    print(f"   ❌ Failed to add to Firebase: {failed_adds}")
    print(f"   🎯 Actual new videos in database: {successful_adds}")
    print(f"   ⚡ Performance: Only checked last 2 days + enhanced duplicate detection")
    print("="*70)
    
    # Verification step
    if successful_adds != len(truly_new_videos):
        print(f"⚠️  WARNING: Mismatch between identified new videos ({len(truly_new_videos)}) and successfully added ({successful_adds})")

# Debug function
def debug_recent_videos(days_back=2):
    """Debug function to check recent videos"""
    print(f"🔍 DEBUG: Checking videos from last {days_back} days...")
    db = initialize_firebase()
    
    cutoff_time = datetime.now() - timedelta(days=days_back)
    
    docs = db.collection("latest_video_links") \
             .where("createdAt", ">=", cutoff_time) \
             .order_by("createdAt", direction=firestore.Query.DESCENDING) \
             .stream()
    
    videos = []
    for doc in docs:
        data = doc.to_dict()
        videos.append({
            'doc_id': doc.id,
            'title': data.get("title", "No title")[:50],
            'channel': data.get("channel", "Unknown"),
            'video_id': data.get("video_id", "No ID"),
            'url': data.get("url"),
            'created_at': data.get("createdAt")
        })
    
    print(f"\n📊 Found {len(videos)} videos in the last {days_back} days:")
    
    # Group by video_id to find potential duplicates
    video_id_count = {}
    url_count = {}
    
    for i, video in enumerate(videos, 1):
        print(f"{i}. [{video['channel']}] {video['title']}...")
        print(f"   🆔 Video ID: {video['video_id']}")
        print(f"   🔗 URL: {video['url']}")
        print(f"   📅 Created: {video['created_at']}")
        print(f"   📄 Doc ID: {video['doc_id']}")
        print()
        
        # Count duplicates
        vid_id = video['video_id']
        url = video['url']
        
        if vid_id and vid_id != "No ID":
            video_id_count[vid_id] = video_id_count.get(vid_id, 0) + 1
        if url:
            url_count[url] = url_count.get(url, 0) + 1
    
    # Report duplicates
    print("\n🔍 DUPLICATE ANALYSIS:")
    
    duplicate_video_ids = {k: v for k, v in video_id_count.items() if v > 1}
    duplicate_urls = {k: v for k, v in url_count.items() if v > 1}
    
    if duplicate_video_ids:
        print(f"❌ Found {len(duplicate_video_ids)} duplicate video IDs:")
        for vid_id, count in duplicate_video_ids.items():
            print(f"   • {vid_id}: {count} times")
    
    if duplicate_urls:
        print(f"❌ Found {len(duplicate_urls)} duplicate URLs:")
        for url, count in duplicate_urls.items():
            print(f"   • {url}: {count} times")
    
    if not duplicate_video_ids and not duplicate_urls:
        print("✅ No duplicates found!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--debug-recent":
        # Debug recent videos
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        debug_recent_videos(days_back=days)
    else:
        # Run enhanced processing
        process_new_videos()






# import subprocess
# import json
# import os
# from datetime import datetime, timedelta
# import firebase_admin
# from firebase_admin import credentials, firestore
# from youtube_rss_fetcher import get_latest_videos_from_rss
# from dotenv import load_dotenv

# load_dotenv()

# def initialize_firebase():
#     """Initialize Firebase connection"""
#     try:
#         # Check if Firebase is already initialized
#         firebase_admin.get_app()
#     except ValueError:
#         # Initialize if not already done
#         service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
#         if not service_account_json:
#             raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set")
#         # Parse JSON string thành dict
#         service_account_info = json.loads(service_account_json)
#         cred = credentials.Certificate(service_account_info)
#         firebase_admin.initialize_app(cred)
    
#     return firestore.client()

# def get_recent_video_urls_from_firebase(days_back=2):
#     """
#     Get video URLs from Firebase for the last N days only
#     Much more efficient than loading all videos
#     """
#     db = initialize_firebase()
    
#     # Calculate cutoff timestamp (N days ago)
#     cutoff_time = datetime.now() - timedelta(days=days_back)
    
#     # Query only videos created in the last N days, ordered by creation time
#     docs = db.collection("latest_video_links") \
#              .where("createdAt", ">=", cutoff_time) \
#              .order_by("createdAt", direction=firestore.Query.DESCENDING) \
#              .stream()
    
#     existing_urls = set()
#     doc_count = 0
    
#     for doc in docs:
#         doc_count += 1
#         data = doc.to_dict()
#         url = data.get("url")
#         if url:
#             # Normalize URL format - remove any extra parameters or variations
#             normalized_url = normalize_youtube_url(url)
#             existing_urls.add(normalized_url)
    
#     print(f"📚 Found {len(existing_urls)} existing videos in the last {days_back} days ({doc_count} documents checked)")
#     return existing_urls

# def get_recent_video_data_from_firebase(days_back=2):
#     """
#     Alternative: Get both URLs and video IDs for more robust duplicate detection
#     """
#     db = initialize_firebase()
    
#     # Calculate cutoff timestamp
#     cutoff_time = datetime.now() - timedelta(days=days_back)
    
#     # Query recent videos
#     docs = db.collection("latest_video_links") \
#              .where("createdAt", ">=", cutoff_time) \
#              .order_by("createdAt", direction=firestore.Query.DESCENDING) \
#              .stream()
    
#     existing_data = {
#         'urls': set(),
#         'video_ids': set()
#     }
#     doc_count = 0
    
#     for doc in docs:
#         doc_count += 1
#         data = doc.to_dict()
        
#         # Add normalized URL
#         url = data.get("url")
#         if url:
#             normalized_url = normalize_youtube_url(url)
#             existing_data['urls'].add(normalized_url)
        
#         # Add video ID for extra protection
#         video_id = data.get("video_id")
#         if video_id:
#             existing_data['video_ids'].add(video_id)
    
#     print(f"📚 Found {len(existing_data['urls'])} URLs and {len(existing_data['video_ids'])} video IDs in the last {days_back} days")
#     return existing_data

# def normalize_youtube_url(url):
#     """Normalize YouTube URL to standard format"""
#     if not url:
#         return url
    
#     # Extract video ID from various YouTube URL formats
#     import re
#     patterns = [
#         r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
#         r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
#     ]
    
#     for pattern in patterns:
#         match = re.search(pattern, url)
#         if match:
#             video_id = match.group(1)
#             return f"https://www.youtube.com/watch?v={video_id}"
    
#     return url

# def extract_video_id_from_url(url):
#     """Extract video ID from YouTube URL"""
#     if not url:
#         return None
    
#     import re
#     patterns = [
#         r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
#         r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
#     ]
    
#     for pattern in patterns:
#         match = re.search(pattern, url)
#         if match:
#             return match.group(1)
    
#     return None

# def is_video_duplicate_optimized(video_data, existing_data):
#     """
#     Optimized duplicate check using both URL and video ID
#     """
#     # Check by normalized URL
#     video_url = video_data.get('url')
#     if video_url:
#         normalized_url = normalize_youtube_url(video_url)
#         if normalized_url in existing_data['urls']:
#             return True, "URL match"
    
#     # Check by video ID (more reliable)
#     video_id = video_data.get('video_id')
#     if not video_id:
#         # Extract video ID from URL if not provided
#         video_id = extract_video_id_from_url(video_url)
#         if video_id:
#             video_data['video_id'] = video_id  # Cache for later use
    
#     if video_id and video_id in existing_data['video_ids']:
#         return True, "Video ID match"
    
#     return False, "Not duplicate"

# def process_new_videos_optimized():
#     """
#     Optimized version that only checks recent videos for duplicates
#     """
#     print("🚀 Starting optimized new video processing with RSS feeds...")
    
#     # Step 1: Get latest videos from YouTube RSS feeds
#     print("📡 Fetching latest videos from YouTube RSS feeds...")
#     try:
#         new_videos = get_latest_videos_from_rss(
#             return_links=True,
#             hours=36,  # Quét video trong 36 giờ qua
#             skip_shorts=True,  # Bỏ qua Shorts
#         )
#     except Exception as e:
#         print(f"❌ Error fetching videos from RSS: {e}")
#         return
    
#     if not new_videos:
#         print("❌ No new videos found from RSS feeds")
#         return
    
#     print(f"📋 Found {len(new_videos)} videos from RSS scan")
    
#     # Step 2: Get existing video data from Firebase (last 2 days only)
#     print("\n📚 Checking recent videos in Firebase (last 2 days)...")
#     existing_data = get_recent_video_data_from_firebase(days_back=2)
    
#     # Step 3: Filter out duplicates using optimized check
#     truly_new_videos = []
#     duplicate_count = 0
    
#     for video in new_videos:
#         is_duplicate, match_reason = is_video_duplicate_optimized(video, existing_data)
        
#         print(f"\n🔍 Checking: {video.get('title', 'Unknown')[:50]}...")
#         print(f"   Channel: {video.get('channel', 'Unknown')}")
#         print(f"   Video ID: {video.get('video_id', extract_video_id_from_url(video.get('url', '')))}")
        
#         if is_duplicate:
#             duplicate_count += 1
#             print(f"⏭️ DUPLICATE ({match_reason}) - Skipping...")
#         else:
#             truly_new_videos.append(video)
#             print(f"🆕 NEW - Will add to Firebase...")
    
#     if not truly_new_videos:
#         print(f"✅ All {len(new_videos)} videos are duplicates ({duplicate_count} found) - nothing to add")
#         # Still save empty file to clear previous content
#         save_new_video_links_to_file([])
#         return
    
#     print(f"\n🎯 Found {len(truly_new_videos)} truly new videos (skipped {duplicate_count} duplicates)")
    
#     # Step 4: Save new video links to file BEFORE adding to Firebase
#     print(f"\n💾 Saving {len(truly_new_videos)} new video links to file...")
#     save_new_video_links_to_file(truly_new_videos)
    
#     # Step 5: Add new videos to Firebase
#     successful_adds = 0
#     failed_adds = 0
    
#     for i, video in enumerate(truly_new_videos, 1):
#         print(f"\n[{i}/{len(truly_new_videos)}] Adding to Firebase...")
        
#         if add_video_to_firebase(video):
#             successful_adds += 1
#         else:
#             failed_adds += 1
    
#     # Step 6: Summary
#     print("\n" + "="*60)
#     print(f"📊 OPTIMIZED PROCESSING SUMMARY:")
#     print(f"   📡 Total videos from RSS: {len(new_videos)}")
#     print(f"   🔄 Duplicates found (last 2 days): {duplicate_count}")
#     print(f"   🆕 Truly new videos: {len(truly_new_videos)}")
#     print(f"   💾 New videos saved to file: {len(truly_new_videos)}")
#     print(f"   ✅ Successfully added to Firebase: {successful_adds}")
#     print(f"   ❌ Failed to add to Firebase: {failed_adds}")
#     print("="*60)

# def add_video_to_firebase(video_data):
#     """Add new video data to Firebase with enhanced video ID extraction"""
#     db = initialize_firebase()
    
#     # Get additional video info if needed
#     video_url = video_data.get('url')
#     video_info = get_video_info(video_url)
    
#     # Use video info from yt-dlp if available, otherwise use RSS data
#     if video_info:
#         video_id = video_info.get('id', video_data.get('video_id', ''))
#         title = video_info.get('title', video_data.get('title', 'Unknown'))
#         channel = video_info.get('uploader', video_data.get('channel', 'Unknown'))
#         upload_date = video_info.get('upload_date', video_data.get('upload_date', ''))
#         duration = video_info.get('duration', 0)
#         view_count = video_info.get('view_count', 0)
#         description = video_info.get('description', '')
#     else:
#         # Fallback to RSS data if yt-dlp fails
#         video_id = video_data.get('video_id', '')
#         # If video_id is still empty, extract from URL
#         if not video_id:
#             video_id = extract_video_id_from_url(video_url) or ''
        
#         title = video_data.get('title', 'Unknown')
#         channel = video_data.get('channel', 'Unknown')
#         upload_date = video_data.get('upload_date', '')
#         duration = 0
#         view_count = 0
#         description = ''
    
#     # Normalize URL before storing
#     normalized_url = normalize_youtube_url(video_url)
    
#     video_doc = {
#         "url": normalized_url,
#         "original_url": video_url,  # Keep original for reference
#         "video_id": video_id,  # Store video ID for better duplicate detection
#         "title": title,
#         "channel": channel,
#         "channel_url": video_data.get('channel_url', ''),
#         "subtitle_codes": video_data.get('subtitle_codes', 'vi'),
#         "upload_date": upload_date,
#         "duration": duration,
#         "view_count": view_count,
#         "description": description[:500] if description else '',
#         "is_short": video_data.get('is_short', False),
#         "subtitle_downloaded": False,
#         "processed": False,
#         # Thumbnail data
#         "thumbnail": video_data.get('thumbnail', ''),
#         "thumbnail_quality": video_data.get('thumbnail_quality', ''),
#         "all_thumbnails": video_data.get('all_thumbnails', {}),
#         "createdAt": firestore.SERVER_TIMESTAMP
#     }
    
#     try:
#         db.collection("latest_video_links").add(video_doc)
#         subtitle_info = f" [Subtitles: {video_data.get('subtitle_codes', 'vi')}]"
#         thumbnail_info = f" [Thumbnail: {video_data.get('thumbnail_quality', 'N/A')}]" if video_data.get('thumbnail') else ""
#         print(f"✅ Added to Firebase: {title[:50]}...{subtitle_info}{thumbnail_info}")
#         return True
#     except Exception as e:
#         print(f"❌ Failed to add to Firebase: {e}")
#         return False

# def get_video_info(video_url):
#     """Get video information using yt-dlp"""
#     try:
#         result = subprocess.run(
#             ["yt-dlp", "--skip-download", "--print-json", "--no-warnings", video_url],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             timeout=60
#         )
#         return json.loads(result.stdout)
#     except subprocess.TimeoutExpired:
#         print(f"⏱️ Timeout fetching info for {video_url}")
#         return None
#     except Exception as e:
#         print(f"⚠️ Error fetching info for {video_url}: {e}")
#         return None



# def normalize_youtube_url(url):
#     """Normalize YouTube URL to standard format"""
#     if not url:
#         return url
    
#     # Extract video ID from various YouTube URL formats
#     import re
#     patterns = [
#         r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
#         r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
#     ]
    
#     for pattern in patterns:
#         match = re.search(pattern, url)
#         if match:
#             video_id = match.group(1)
#             return f"https://www.youtube.com/watch?v={video_id}"
    
#     return url

# def extract_video_id_from_url(url):
#     """Extract video ID from YouTube URL"""
#     if not url:
#         return None
    
#     import re
#     patterns = [
#         r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
#         r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
#     ]
    
#     for pattern in patterns:
#         match = re.search(pattern, url)
#         if match:
#             return match.group(1)
    
#     return None

# def is_video_duplicate_optimized(video_data, existing_data):
#     """
#     Optimized duplicate check using both URL and video ID
#     """
#     # Check by normalized URL
#     video_url = video_data.get('url')
#     if video_url:
#         normalized_url = normalize_youtube_url(video_url)
#         if normalized_url in existing_data['urls']:
#             return True, "URL match"
    
#     # Check by video ID (more reliable)
#     video_id = video_data.get('video_id')
#     if not video_id:
#         # Extract video ID from URL if not provided
#         video_id = extract_video_id_from_url(video_url)
#         if video_id:
#             video_data['video_id'] = video_id  # Cache for later use
    
#     if video_id and video_id in existing_data['video_ids']:
#         return True, "Video ID match"
    
#     return False, "Not duplicate"

# # Main optimized function
# def process_new_videos():
#     """
#     Main function to process new videos with optimized duplicate checking
#     """
#     print("🚀 Starting optimized new video processing...")
    
#     # Step 1: Get latest videos from YouTube RSS feeds
#     print("📡 Fetching latest videos from YouTube RSS feeds...")
#     try:
#         new_videos = get_latest_videos_from_rss(
#             return_links=True,
#             hours=36,  # Quét video trong 36 giờ qua
#             skip_shorts=True,  # Bỏ qua Shorts
#         )
#     except Exception as e:
#         print(f"❌ Error fetching videos from RSS: {e}")
#         return
    
#     if not new_videos:
#         print("❌ No new videos found from RSS feeds")
#         return
    
#     print(f"📋 Found {len(new_videos)} videos from RSS scan")
    
#     # Step 2: Get existing video data from Firebase (last 2 days only) 
#     print("\n📚 Checking recent videos in Firebase (last 2 days)...")
#     existing_data = get_recent_video_data_from_firebase(days_back=2)
    
#     # Step 3: Filter out duplicates using optimized check
#     truly_new_videos = []
#     duplicate_count = 0
    
#     for video in new_videos:
#         is_duplicate, match_reason = is_video_duplicate_optimized(video, existing_data)
        
#         video_title = video.get('title', 'Unknown')[:50]
#         channel = video.get('channel', 'Unknown')
#         video_id = video.get('video_id') or extract_video_id_from_url(video.get('url', ''))
        
#         print(f"\n🔍 Checking: {video_title}...")
#         print(f"   📺 Channel: {channel}")
#         print(f"   🆔 Video ID: {video_id}")
        
#         if is_duplicate:
#             duplicate_count += 1
#             print(f"⏭️ DUPLICATE ({match_reason}) - Skipping...")
#         else:
#             truly_new_videos.append(video)
#             print(f"🆕 NEW - Will add to Firebase...")
    
#     if not truly_new_videos:
#         print(f"✅ All {len(new_videos)} videos are duplicates ({duplicate_count} found) - nothing to add")
#         return
    
#     print(f"\n🎯 Found {len(truly_new_videos)} truly new videos (skipped {duplicate_count} duplicates)")
    
#     # Step 4: Add new videos to Firebase
#     successful_adds = 0
#     failed_adds = 0
    
#     for i, video in enumerate(truly_new_videos, 1):
#         print(f"\n[{i}/{len(truly_new_videos)}] Adding to Firebase...")
        
#         if add_video_to_firebase(video):
#             successful_adds += 1
#         else:
#             failed_adds += 1
    
#     # Step 6: Summary
#     print("\n" + "="*70)
#     print(f"📊 OPTIMIZED PROCESSING SUMMARY:")
#     print(f"   📡 Total videos from RSS: {len(new_videos)}")
#     print(f"   🔄 Duplicates found (last 2 days check): {duplicate_count}")
#     print(f"   🆕 Truly new videos: {len(truly_new_videos)}")
#     print(f"   💾 New videos saved to file: {len(truly_new_videos)}")
#     print(f"   ✅ Successfully added to Firebase: {successful_adds}")
#     print(f"   ❌ Failed to add to Firebase: {failed_adds}")
#     print(f"   ⚡ Performance: Only checked last 2 days instead of all videos")
#     print("="*70)

# # Debug functions for the optimized version
# def debug_recent_videos(days_back=2):
#     """Debug function to check recent videos only"""
#     print(f"🔍 DEBUG: Checking videos from last {days_back} days...")
#     db = initialize_firebase()
    
#     cutoff_time = datetime.now() - timedelta(days=days_back)
    
#     docs = db.collection("latest_video_links") \
#              .where("createdAt", ">=", cutoff_time) \
#              .order_by("createdAt", direction=firestore.Query.DESCENDING) \
#              .stream()
    
#     count = 0
#     for doc in docs:
#         count += 1
#         data = doc.to_dict()
#         url = data.get("url")
#         title = data.get("title", "No title")
#         channel = data.get("channel", "Unknown")
#         video_id = data.get("video_id", "No ID")
#         created_at = data.get("createdAt")
        
#         print(f"{count}. [{channel}] {title[:50]}...")
#         print(f"   🆔 Video ID: {video_id}")
#         print(f"   🔗 URL: {url}")
#         print(f"   📅 Created: {created_at}")
#         print()
    
#     print(f"📊 Total recent videos (last {days_back} days): {count}")

# if __name__ == "__main__":
#     import sys
    
#     if len(sys.argv) > 1 and sys.argv[1] == "--debug-recent":
#         # Debug recent videos only
#         days = int(sys.argv[2]) if len(sys.argv) > 2 else 2
#         debug_recent_videos(days_back=days)
#     else:
#         # Use optimized method
#         process_new_videos()