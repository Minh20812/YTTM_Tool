import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import subprocess
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
# Thay thế import get_latest_video2 bằng script RSS reader
from src.youtube.rss_reader import get_latest_videos_from_rss

load_dotenv()
# Tạo đường dẫn đến thư mục storage cùng cấp với thư mục cha của script
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")

def ensure_storage_directory():
    """Tạo thư mục storage nếu chưa tồn tại"""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
        print(f"📁 Created storage directory: {STORAGE_DIR}")
    else:
        print(f"📁 Using storage directory: {STORAGE_DIR}")

def initialize_firebase():
    """Initialize Firebase connection using environment variable"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
    except ValueError:
        # Initialize if not already done
        try:
            # Lấy service account key từ biến môi trường
            service_account_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
            
            if not service_account_key:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not found")
            
            # Parse JSON string thành dict
            service_account_info = json.loads(service_account_key)
            
            # Tạo credentials từ dict
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            
            print("✅ Firebase initialized successfully from environment variable")
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing FIREBASE_SERVICE_ACCOUNT_KEY: {e}")
            raise
        except ValueError as e:
            print(f"❌ Firebase initialization error: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error initializing Firebase: {e}")
            raise
    
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
            existing_urls.add(url)
    
    print(f"📚 Found {len(existing_urls)} existing videos in Firebase")
    return existing_urls

def add_video_to_firebase(video_data):
    """Add new video data to Firebase"""
    db = initialize_firebase()
    
    video_doc = {
        "url": video_data.get('url'),
        "title": video_data.get('title', 'Unknown'),
        "channel": video_data.get('channel', 'Unknown'),
        "channel_url": video_data.get('channel_url', ''),
        "upload_date": video_data.get('upload_date', ''),
        "video_id": video_data.get('video_id', ''),
        "is_short": video_data.get('is_short', False),
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

def download_sub(video_data):
    """Download subtitle for a single video"""
    video_url = video_data.get('url')
    if not video_url:
        print("⚠️ No URL found in video data")
        return False

    info = get_video_info(video_url)
    if not info:
        return False

    video_id = info.get("id")
    title = info.get("title")

    sub_lang, is_user_sub = choose_sub_lang(info)
    suffix = sub_lang + (".cleansub" if is_user_sub else "")

    print(f"\n🎬 {title}")
    print(f"🔗 {video_url}")
    print(f"🌐 Subtitle language: {sub_lang}")
    
    # Tạo đường dẫn file trong thư mục storage
    final_output = os.path.join(STORAGE_DIR, f"{video_id}.{suffix}.srt")
    print(f"💾 Expected output: {final_output}")

    # Tạo temporary output path trong thư mục storage
    temp_output = os.path.join(STORAGE_DIR, f"{video_id}.%(ext)s")
    raw_srt = os.path.join(STORAGE_DIR, f"{video_id}.{sub_lang}.srt")

    if os.path.exists(final_output):
        print(f"⚠️ Skipping download (file exists): {final_output}")
        # Still add to Firebase even if file exists
        add_video_to_firebase(video_data)
        return True

    try:
        print(f"📥 Downloading subtitle...")
        subprocess.run([
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang", sub_lang,
            "--convert-subs", "srt",
            "--skip-download",
            "--output", temp_output,
            video_url
        ], check=True, timeout=120)

        if os.path.exists(raw_srt):
            os.rename(raw_srt, final_output)
            print(f"✅ Saved subtitle: {final_output}")
            
            # Add to Firebase after successful download
            add_video_to_firebase(video_data)
            return True
        else:
            print(f"❌ Subtitle file not found after download: {raw_srt}")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️ Download timeout for {video_url}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed for {video_url}: {e}")
        return False

def process_new_videos(hours=36, skip_shorts=True):
    """Main function to process new videos from YouTube channels using RSS reader"""
    print("🚀 Starting new video processing with RSS reader...")
    
    # Đảm bảo thư mục storage tồn tại
    ensure_storage_directory()
    
    # Step 1: Get latest videos from YouTube channels using RSS reader
    print("📺 Fetching latest videos from YouTube RSS feeds...")
    try:
        new_videos = get_latest_videos_from_rss(
            return_links=True,
            hours=hours,
            skip_shorts=skip_shorts
        )
    except Exception as e:
        print(f"❌ Error fetching videos from RSS: {e}")
        return
    
    if not new_videos:
        print("❌ No new videos found from YouTube RSS feeds")
        return
    
    print(f"📋 Found {len(new_videos)} videos from RSS scan")
    
    # Step 2: Get existing URLs from Firebase
    existing_urls = get_existing_video_urls_from_firebase()
    
    # Step 3: Filter out videos that already exist in Firebase
    truly_new_videos = []
    for video in new_videos:
        if video.get('url') not in existing_urls:
            truly_new_videos.append(video)
            print(f"🆕 New video: {video.get('title', 'Unknown')[:50]}...")
        else:
            print(f"⏭️ Already exists: {video.get('title', 'Unknown')[:50]}...")
    
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
            add_video_to_firebase(video)
    
    # Step 5: Summary
    print("\n" + "="*60)
    print(f"📊 PROCESSING SUMMARY:")
    print(f"   📺 Total videos from RSS: {len(new_videos)}")
    print(f"   🆕 Truly new videos: {len(truly_new_videos)}")
    print(f"   ✅ Successful downloads: {successful_downloads}")
    print(f"   ❌ Failed downloads: {failed_downloads}")
    print(f"   📁 Storage location: {STORAGE_DIR}")
    print(f"   ⏰ Time window: {hours} hours")
    print(f"   🎬 Skip shorts: {skip_shorts}")
    print("="*60)

def download_from_list_fallback(file_path="latest_video_links.txt"):
    """Fallback method to download from text file (original functionality)"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Đảm bảo thư mục storage tồn tại
    ensure_storage_directory()
        
    with open(file_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"\n📋 Processing {len(urls)} video(s) from file...")
    for url in urls:
        # Create video data structure for compatibility
        video_data = {'url': url}
        download_sub(video_data)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file":
            # Use fallback method with file
            file_path = sys.argv[2] if len(sys.argv) > 2 else "latest_video_links.txt"
            download_from_list_fallback(file_path)
        elif sys.argv[1] == "--hours":
            # Set custom hours
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 36
            skip_shorts = True
            if len(sys.argv) > 3 and sys.argv[3] == "--include-shorts":
                skip_shorts = False
            process_new_videos(hours=hours, skip_shorts=skip_shorts)
        else:
            print("Usage:")
            print("  python script.py                              # Default: 36 hours, skip shorts")
            print("  python script.py --hours 24                   # Custom hours, skip shorts")
            print("  python script.py --hours 24 --include-shorts  # Custom hours, include shorts")
            print("  python script.py --file [filename]            # Use file fallback method")
    else:
        # Use new RSS-integrated method with default settings
        process_new_videos(hours=36, skip_shorts=True)