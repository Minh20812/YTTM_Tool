import subprocess
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore
from youtube_rss_fetcher import get_latest_videos_from_rss
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import SRTFormatter
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled
import re

def initialize_firebase():
    """Initialize Firebase connection"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Initialize if not already done
        cred = credentials.Certificate("./serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def get_existing_video_urls_from_firebase():
    """Get all existing video URLs from Firebase collection"""
    db = initialize_firebase()
    docs = db.collection("latest_video_links").stream()
    existing_urls = set()
    
    for doc in docs:
        data = doc.to_dict()
        url = data.get("url")
        if url:
            # Normalize URL format - remove any extra parameters or variations
            normalized_url = normalize_youtube_url(url)
            existing_urls.add(normalized_url)
    
    print(f"📚 Found {len(existing_urls)} existing videos in Firebase")
    return existing_urls

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

def add_video_to_firebase(video_data):
    """Add new video data to Firebase"""
    db = initialize_firebase()
    
    # Normalize URL before storing
    normalized_url = normalize_youtube_url(video_data.get('url'))
    
    video_doc = {
        "url": normalized_url,
        "original_url": video_data.get('url'),  # Keep original for reference
        "title": video_data.get('title', 'Unknown'),
        "channel": video_data.get('channel', 'Unknown'),
        "channel_url": video_data.get('channel_url', ''),
        "upload_date": video_data.get('upload_date', ''),
        "video_id": video_data.get('video_id', ''),
        "is_short": video_data.get('is_short', False),
        "subtitle_downloaded": True,
        "createdAt": firestore.SERVER_TIMESTAMP
    }
    
    db.collection("latest_video_links").add(video_doc)
    print(f"✅ Added to Firebase: {video_data.get('title', 'Unknown')[:50]}...")

def get_video_info(video_url):
    """Get video information using yt-dlp"""
    try:
        result = subprocess.run(
            ["yt-dlp", "--skip-download", "--print-json", "--no-warnings", video_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"⏱️ Timeout fetching info for {video_url}")
        return None
    except Exception as e:
        print(f"⚠️ Error fetching info for {video_url}: {e}")
        return None

def detect_user_english_sub(user_subs):
    """Detect if English user-generated subtitles are available"""
    for lang in user_subs:
        if lang.startswith("en"):
            return lang  # e.g., 'en', 'en-GB', 'en-US'
    return None

def choose_sub_lang(info):
    """Choose subtitle language preference"""
    user_subs = info.get("subtitles", {})
    user_en = detect_user_english_sub(user_subs)

    if user_en:
        return (f"vi-{user_en}", True)  # True = is_user_sub
    else:
        return ("vi", False)

def extract_video_id(url_or_id):
    """Extract YouTube video ID from various URL formats"""
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url_or_id)
    return match.group(1) if match else url_or_id

def download_sub(video_data):
    """Download subtitle using youtube-transcript-api and save as .srt"""
    video_url = video_data.get('url')
    if not video_url:
        print("⚠️ No URL found in video data")
        return False

    video_id = extract_video_id(video_url)
    output_file = ""
    suffix = ""
    title = video_data.get('title', 'Unknown')

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Ưu tiên phụ đề do uploader upload
        english_codes = ['en', 'en-US', 'en-GB', 'en-CA', 'en-AU', 'en-IN']
        try:
            transcript = transcript_list.find_manually_created_transcript(english_codes)
            suffix = "vi.cleansub"
            print("✅ Dùng phụ đề do uploader upload")
        except:
            transcript = transcript_list.find_generated_transcript(english_codes)
            suffix = "vi"
            print("ℹ️ Dùng phụ đề auto-generated")

        # Kiểm tra dịch được không
        if not transcript.is_translatable:
            print("❌ Phụ đề không hỗ trợ dịch sang tiếng Việt")
            return False

        available_langs = [lang.language_code for lang in transcript.translation_languages]
        if "vi" not in available_langs:
            print("❌ Không hỗ trợ dịch sang tiếng Việt")
            return False

        translated = transcript.translate("vi")
        data = translated.fetch()

        srt = SRTFormatter().format_transcript(data)
        output_file = f"{video_id}.{suffix}.srt"

        if os.path.exists(output_file):
            print(f"⚠️ File đã tồn tại: {output_file}, bỏ qua")
            add_video_to_firebase(video_data)
            return True

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt)

        print(f"✅ Đã lưu phụ đề: {output_file}")
        add_video_to_firebase(video_data)
        return True

    except NoTranscriptFound:
        print("❌ Không tìm thấy phụ đề")
        return False
    except TranscriptsDisabled:
        print("❌ Video đã tắt phụ đề")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False

def process_new_videos():
    """Main function to process new videos from YouTube channels using RSS feeds"""
    print("🚀 Starting new video processing with RSS feeds...")
    
    # Step 1: Get latest videos from YouTube RSS feeds
    print("📡 Fetching latest videos from YouTube RSS feeds...")
    try:
        new_videos = get_latest_videos_from_rss(
            return_links=True,
            hours=36,  # Quét video trong 36 giờ qua
            skip_shorts=True  # Bỏ qua Shorts
        )
    except Exception as e:
        print(f"❌ Error fetching videos from RSS: {e}")
        return
    
    if not new_videos:
        print("❌ No new videos found from RSS feeds")
        return
    
    print(f"📋 Found {len(new_videos)} videos from RSS scan")
    
    # Debug: Print some of the new videos found
    print("🔍 Sample of new videos found:")
    for i, video in enumerate(new_videos[:3]):  # Show first 3
        print(f"   {i+1}. [{video.get('channel', 'Unknown')}] {video.get('title', 'No title')}")
        print(f"      URL: {video.get('url', 'No URL')}")
        print(f"      Upload Date: {video.get('upload_date', 'Unknown')}")
    
    # Step 2: Get existing URLs from Firebase
    print("\n📚 Checking existing videos in Firebase...")
    existing_urls = get_existing_video_urls_from_firebase()
    
    # Step 3: Filter out videos that already exist in Firebase
    truly_new_videos = []
    for video in new_videos:
        original_url = video.get('url')
        normalized_url = normalize_youtube_url(original_url)
        
        print(f"\n🔍 Checking video: {video.get('title', 'Unknown')[:50]}...")
        print(f"   Channel: {video.get('channel', 'Unknown')}")
        print(f"   Original URL: {original_url}")
        print(f"   Normalized URL: {normalized_url}")
        print(f"   Exists in Firebase: {normalized_url in existing_urls}")
        
        if normalized_url not in existing_urls:
            truly_new_videos.append(video)
            print(f"🆕 NEW - Will process: {video.get('title', 'Unknown')[:50]}...")
        else:
            print(f"⏭️ EXISTS - Skipping: {video.get('title', 'Unknown')[:50]}...")
    
    if not truly_new_videos:
        print("✅ All videos already exist in Firebase - nothing to download")
        return
    
    print(f"\n🎯 Processing {len(truly_new_videos)} truly new videos...")
    
    # Step 4: Download subtitles for new videos
    successful_downloads = 0
    failed_downloads = 0
    
    for i, video in enumerate(truly_new_videos, 1):
        print(f"\n[{i}/{len(truly_new_videos)}] Processing video...")
        
        if download_sub(video):
            successful_downloads += 1
        else:
            failed_downloads += 1
            # Still add to Firebase to avoid reprocessing failed videos
            # add_video_to_firebase(video)
    
    # Step 5: Summary
    print("\n" + "="*60)
    print(f"📊 PROCESSING SUMMARY:")
    print(f"   📡 Total videos from RSS: {len(new_videos)}")
    print(f"   🆕 Truly new videos: {len(truly_new_videos)}")
    print(f"   ✅ Successful downloads: {successful_downloads}")
    print(f"   ❌ Failed downloads: {failed_downloads}")
    print("="*60)

def download_from_list_fallback(file_path="latest_video_links.txt"):
    """Fallback method to download from text file (original functionality)"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
        
    with open(file_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"\n📋 Processing {len(urls)} video(s) from file...")
    for url in urls:
        # Create video data structure for compatibility
        video_data = {'url': url}
        download_sub(video_data)

def test_rss_integration():
    """Test function to verify RSS integration works"""
    print("🧪 Testing RSS integration...")
    
    try:
        videos = get_latest_videos_from_rss(
            return_links=True,
            hours=168,  # 7 ngày để test
            skip_shorts=True
        )
        
        print(f"✅ RSS integration test successful!")
        print(f"📊 Found {len(videos)} videos in the last 7 days")
        
        if videos:
            print("\n📝 Sample videos:")
            for i, video in enumerate(videos[:5]):
                print(f"   {i+1}. [{video.get('channel', 'Unknown')}] {video.get('title', 'No title')[:50]}...")
                print(f"      📅 {video.get('upload_date', 'Unknown')}")
                print(f"      🔗 {video.get('url', 'No URL')}")
        
        return True
        
    except Exception as e:
        print(f"❌ RSS integration test failed: {e}")
        return False

def debug_firebase_urls():
    """Debug function to check all URLs in Firebase"""
    print("🔍 DEBUG: Checking all URLs in Firebase...")
    db = initialize_firebase()
    docs = db.collection("latest_video_links").stream()
    
    for i, doc in enumerate(docs, 1):
        data = doc.to_dict()
        url = data.get("url")
        title = data.get("title", "No title")
        channel = data.get("channel", "Unknown")
        print(f"{i}. [{channel}] {title[:50]}...")
        print(f"   URL: {url}")
        print(f"   Normalized: {normalize_youtube_url(url)}")
        print()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        # Use fallback method with file
        file_path = sys.argv[2] if len(sys.argv) > 2 else "latest_video_links.txt"
        download_from_list_fallback(file_path)
    elif len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Debug Firebase URLs
        debug_firebase_urls()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test RSS integration
        test_rss_integration()
    else:
        # Use new RSS-integrated method
        process_new_videos()
