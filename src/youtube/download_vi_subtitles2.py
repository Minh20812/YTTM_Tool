import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import subprocess
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import time
import random
import tempfile
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

def create_cookies_file():
    """Tạo file cookies từ COOKIES_CONTENT trong .env"""
    cookies_content = os.getenv('COOKIES_CONTENT')
    if not cookies_content:
        print("⚠️ No COOKIES_CONTENT found in .env file")
        return None
    
    try:
        # Tạo temporary file cho cookies
        cookies_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        cookies_file.write(cookies_content)
        cookies_file.close()
        
        print(f"🍪 Created cookies file: {cookies_file.name}")
        return cookies_file.name
    except Exception as e:
        print(f"❌ Error creating cookies file: {e}")
        return None

def cleanup_cookies_file(cookies_file_path):
    """Xóa file cookies tạm thời"""
    if cookies_file_path and os.path.exists(cookies_file_path):
        try:
            os.unlink(cookies_file_path)
            print(f"🧹 Cleaned up cookies file: {cookies_file_path}")
        except Exception as e:
            print(f"⚠️ Error cleaning up cookies file: {e}")

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

def get_video_info(video_url, cookies_file=None, max_retries=3):
    """Get video information using yt-dlp with improved error handling and cookies support"""
    for attempt in range(max_retries):
        try:
            # Add delay between retries to avoid rate limiting
            if attempt > 0:
                delay = random.uniform(2, 5) * attempt  # Progressive backoff
                print(f"⏳ Waiting {delay:.1f}s before retry #{attempt + 1}...")
                time.sleep(delay)
            
            # Improved yt-dlp command with better error handling and cookies support
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--dump-single-json",  # Use dump-single-json instead of print-json
                "--no-warnings",
                "--ignore-errors",
                "--no-check-certificate",
                "--socket-timeout", "30",
                "--retries", "3",
            ]
            
            # Add cookies if available
            if cookies_file and os.path.exists(cookies_file):
                cmd.extend(["--cookies", cookies_file])
                print(f"🍪 Using cookies file for authentication")
            
            cmd.append(video_url)
            
            print(f"🔍 Attempt {attempt + 1}: Fetching video info...")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=90  # Increased timeout
            )
            
            # Check if stdout is empty
            if not result.stdout.strip():
                print(f"⚠️ Empty output from yt-dlp (attempt {attempt + 1})")
                if result.stderr:
                    print(f"   Error details: {result.stderr.strip()}")
                continue
            
            # Try to parse JSON
            try:
                video_info = json.loads(result.stdout)
                print(f"✅ Successfully fetched video info (attempt {attempt + 1})")
                return video_info
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse error on attempt {attempt + 1}: {e}")
                print(f"   Raw output: {result.stdout[:200]}...")
                continue
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ Timeout on attempt {attempt + 1} for {video_url}")
            continue
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Command error on attempt {attempt + 1}: {e}")
            if e.stderr:
                print(f"   Error details: {e.stderr}")
            continue
        except Exception as e:
            print(f"⚠️ Unexpected error on attempt {attempt + 1}: {e}")
            continue
    
    print(f"❌ Failed to fetch video info after {max_retries} attempts")
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

def download_sub(video_data, cookies_file=None, max_retries=2):
    """Download subtitle for a single video with improved error handling and cookies support"""
    video_url = video_data.get('url')
    if not video_url:
        print("⚠️ No URL found in video data")
        return False

    info = get_video_info(video_url, cookies_file)
    if not info:
        print("❌ Could not fetch video information")
        return False

    video_id = info.get("id")
    title = info.get("title", "Unknown Title")
    
    # Debug: Print video info keys to understand what's available
    print(f"🔍 Video ID: {video_id}")
    print(f"🔍 Available keys in info: {list(info.keys())}")
    
    # Check if subtitles are available
    available_subs = info.get("subtitles", {})
    auto_subs = info.get("automatic_captions", {})
    
    print(f"🔍 Available subtitles: {list(available_subs.keys()) if available_subs else 'None'}")
    print(f"🔍 Auto captions: {list(auto_subs.keys()) if auto_subs else 'None'}")
    
    if not available_subs and not auto_subs:
        print("⚠️ No subtitles available for this video")
        return False

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
        return True

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = random.uniform(2, 4) * attempt
                print(f"⏳ Waiting {delay:.1f}s before subtitle download retry #{attempt + 1}...")
                time.sleep(delay)
            
            print(f"📥 Downloading subtitle (attempt {attempt + 1})...")
            
            cmd = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", sub_lang,
                "--convert-subs", "srt",
                "--skip-download",
                "--output", temp_output,
                "--socket-timeout", "30",
                "--retries", "3",
                "--ignore-errors",
            ]
            
            # Add cookies if available
            if cookies_file and os.path.exists(cookies_file):
                cmd.extend(["--cookies", cookies_file])
            
            cmd.append(video_url)
            
            result = subprocess.run(cmd, 
                                  check=True, 
                                  timeout=180,  # Increased timeout
                                  capture_output=True, 
                                  text=True)

            if os.path.exists(raw_srt):
                os.rename(raw_srt, final_output)
                print(f"✅ Saved subtitle: {final_output}")
                
                # Add to Firebase after successful download
                add_video_to_firebase(video_data)
                return True
            else:
                print(f"⚠️ Subtitle file not found after download: {raw_srt}")
                # Check if any subtitle files were created
                possible_files = [f for f in os.listdir(STORAGE_DIR) if f.startswith(video_id) and f.endswith('.srt')]
                if possible_files:
                    print(f"   Found alternative subtitle files: {possible_files}")
                    # Use the first available subtitle file
                    alt_file = os.path.join(STORAGE_DIR, possible_files[0])
                    os.rename(alt_file, final_output)
                    print(f"✅ Saved alternative subtitle: {final_output}")
                    add_video_to_firebase(video_data)
                    return True
                continue

        except subprocess.TimeoutExpired:
            print(f"⏱️ Subtitle download timeout (attempt {attempt + 1})")
            continue
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Subtitle download failed (attempt {attempt + 1}): {e}")
            if e.stderr:
                print(f"   Error details: {e.stderr}")
            continue
        except Exception as e:
            print(f"⚠️ Unexpected error during subtitle download (attempt {attempt + 1}): {e}")
            continue

    print(f"❌ Failed to download subtitle after {max_retries} attempts")
    return False

def process_new_videos(hours=36, skip_shorts=True):
    """Main function to process new videos from YouTube channels using RSS reader"""
    print("🚀 Starting new video processing with RSS reader...")
    
    # Đảm bảo thư mục storage tồn tại
    ensure_storage_directory()
    
    # Tạo cookies file từ environment variable
    cookies_file = create_cookies_file()
    
    try:
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
            
            if download_sub(video, cookies_file):
                successful_downloads += 1
            else:
                failed_downloads += 1
            
            # Add delay between video processing to avoid rate limiting
            if i < len(truly_new_videos):
                delay = random.uniform(1, 3)
                print(f"⏳ Waiting {delay:.1f}s before processing next video...")
                time.sleep(delay)
        
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
        print(f"   🍪 Cookies used: {'Yes' if cookies_file else 'No'}")
        print("="*60)
        
    finally:
        # Cleanup cookies file
        if cookies_file:
            cleanup_cookies_file(cookies_file)

def download_from_list_fallback(file_path="latest_video_links.txt"):
    """Fallback method to download from text file (original functionality)"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    # Đảm bảo thư mục storage tồn tại
    ensure_storage_directory()
    
    # Tạo cookies file
    cookies_file = create_cookies_file()
    
    try:
        with open(file_path, "r") as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"\n📋 Processing {len(urls)} video(s) from file...")
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing URL: {url}")
            # Create video data structure for compatibility
            video_data = {'url': url}
            download_sub(video_data, cookies_file)
            
            # Add delay between downloads
            if i < len(urls):
                delay = random.uniform(1, 3)
                print(f"⏳ Waiting {delay:.1f}s before next download...")
                time.sleep(delay)
    finally:
        # Cleanup cookies file
        if cookies_file:
            cleanup_cookies_file(cookies_file)

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


# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
# import subprocess
# import json
# from dotenv import load_dotenv
# import firebase_admin
# from firebase_admin import credentials, firestore
# # Thay thế import get_latest_video2 bằng script RSS reader
# from src.youtube.rss_reader import get_latest_videos_from_rss

# load_dotenv()
# # Tạo đường dẫn đến thư mục storage cùng cấp với thư mục cha của script
# STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage")

# def ensure_storage_directory():
#     """Tạo thư mục storage nếu chưa tồn tại"""
#     if not os.path.exists(STORAGE_DIR):
#         os.makedirs(STORAGE_DIR)
#         print(f"📁 Created storage directory: {STORAGE_DIR}")
#     else:
#         print(f"📁 Using storage directory: {STORAGE_DIR}")

# def initialize_firebase():
#     """Initialize Firebase connection using environment variable"""
#     try:
#         # Check if Firebase is already initialized
#         firebase_admin.get_app()
#     except ValueError:
#         # Initialize if not already done
#         try:
#             # Lấy service account key từ biến môi trường
#             service_account_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
            
#             if not service_account_key:
#                 raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not found")
            
#             # Parse JSON string thành dict
#             service_account_info = json.loads(service_account_key)
            
#             # Tạo credentials từ dict
#             cred = credentials.Certificate(service_account_info)
#             firebase_admin.initialize_app(cred)
            
#             print("✅ Firebase initialized successfully from environment variable")
            
#         except json.JSONDecodeError as e:
#             print(f"❌ Error parsing FIREBASE_SERVICE_ACCOUNT_KEY: {e}")
#             raise
#         except ValueError as e:
#             print(f"❌ Firebase initialization error: {e}")
#             raise
#         except Exception as e:
#             print(f"❌ Unexpected error initializing Firebase: {e}")
#             raise
    
#     return firestore.client()

# def get_existing_video_urls_from_firebase():
#     """Get all existing video URLs from Firebase collection"""
#     db = initialize_firebase()
#     docs = db.collection("latest_video_links").stream()
#     existing_urls = set()
    
#     for doc in docs:
#         data = doc.to_dict()
#         url = data.get("url")
#         if url:
#             existing_urls.add(url)
    
#     print(f"📚 Found {len(existing_urls)} existing videos in Firebase")
#     return existing_urls

# def add_video_to_firebase(video_data):
#     """Add new video data to Firebase"""
#     db = initialize_firebase()
    
#     video_doc = {
#         "url": video_data.get('url'),
#         "title": video_data.get('title', 'Unknown'),
#         "channel": video_data.get('channel', 'Unknown'),
#         "channel_url": video_data.get('channel_url', ''),
#         "upload_date": video_data.get('upload_date', ''),
#         "video_id": video_data.get('video_id', ''),
#         "is_short": video_data.get('is_short', False),
#         "createdAt": firestore.SERVER_TIMESTAMP
#     }
    
#     db.collection("latest_video_links").add(video_doc)
#     print(f"✅ Added to Firebase: {video_data.get('title', 'Unknown')[:50]}...")

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

# def detect_user_english_sub(user_subs):
#     """Detect if English user-generated subtitles are available"""
#     for lang in user_subs:
#         if lang.startswith("en"):
#             return lang  # e.g., 'en', 'en-GB', 'en-US'
#     return None

# def choose_sub_lang(info):
#     """Choose subtitle language preference"""
#     user_subs = info.get("subtitles", {})
#     user_en = detect_user_english_sub(user_subs)

#     if user_en:
#         return (f"vi-{user_en}", True)  # True = is_user_sub
#     else:
#         return ("vi", False)

# def download_sub(video_data):
#     """Download subtitle for a single video"""
#     video_url = video_data.get('url')
#     if not video_url:
#         print("⚠️ No URL found in video data")
#         return False

#     info = get_video_info(video_url)
#     if not info:
#         return False

#     video_id = info.get("id")
#     title = info.get("title")

#     sub_lang, is_user_sub = choose_sub_lang(info)
#     suffix = sub_lang + (".cleansub" if is_user_sub else "")

#     print(f"\n🎬 {title}")
#     print(f"🔗 {video_url}")
#     print(f"🌐 Subtitle language: {sub_lang}")
    
#     # Tạo đường dẫn file trong thư mục storage
#     final_output = os.path.join(STORAGE_DIR, f"{video_id}.{suffix}.srt")
#     print(f"💾 Expected output: {final_output}")

#     # Tạo temporary output path trong thư mục storage
#     temp_output = os.path.join(STORAGE_DIR, f"{video_id}.%(ext)s")
#     raw_srt = os.path.join(STORAGE_DIR, f"{video_id}.{sub_lang}.srt")

#     if os.path.exists(final_output):
#         print(f"⚠️ Skipping download (file exists): {final_output}")
#         # Still add to Firebase even if file exists
#         add_video_to_firebase(video_data)
#         return True

#     try:
#         print(f"📥 Downloading subtitle...")
#         subprocess.run([
#             "yt-dlp",
#             "--write-auto-sub",
#             "--sub-lang", sub_lang,
#             "--convert-subs", "srt",
#             "--skip-download",
#             "--output", temp_output,
#             video_url
#         ], check=True, timeout=120)

#         if os.path.exists(raw_srt):
#             os.rename(raw_srt, final_output)
#             print(f"✅ Saved subtitle: {final_output}")
            
#             # Add to Firebase after successful download
#             add_video_to_firebase(video_data)
#             return True
#         else:
#             print(f"❌ Subtitle file not found after download: {raw_srt}")
#             return False

#     except subprocess.TimeoutExpired:
#         print(f"⏱️ Download timeout for {video_url}")
#         return False
#     except subprocess.CalledProcessError as e:
#         print(f"❌ Download failed for {video_url}: {e}")
#         return False

# def process_new_videos(hours=36, skip_shorts=True):
#     """Main function to process new videos from YouTube channels using RSS reader"""
#     print("🚀 Starting new video processing with RSS reader...")
    
#     # Đảm bảo thư mục storage tồn tại
#     ensure_storage_directory()
    
#     # Step 1: Get latest videos from YouTube channels using RSS reader
#     print("📺 Fetching latest videos from YouTube RSS feeds...")
#     try:
#         new_videos = get_latest_videos_from_rss(
#             return_links=True,
#             hours=hours,
#             skip_shorts=skip_shorts
#         )
#     except Exception as e:
#         print(f"❌ Error fetching videos from RSS: {e}")
#         return
    
#     if not new_videos:
#         print("❌ No new videos found from YouTube RSS feeds")
#         return
    
#     print(f"📋 Found {len(new_videos)} videos from RSS scan")
    
#     # Step 2: Get existing URLs from Firebase
#     existing_urls = get_existing_video_urls_from_firebase()
    
#     # Step 3: Filter out videos that already exist in Firebase
#     truly_new_videos = []
#     for video in new_videos:
#         if video.get('url') not in existing_urls:
#             truly_new_videos.append(video)
#             print(f"🆕 New video: {video.get('title', 'Unknown')[:50]}...")
#         else:
#             print(f"⏭️ Already exists: {video.get('title', 'Unknown')[:50]}...")
    
#     if not truly_new_videos:
#         print("✅ All videos already exist in Firebase - nothing to download")
#         return
    
#     print(f"\n🎯 Processing {len(truly_new_videos)} truly new videos...")
    
#     # Step 4: Download subtitles for new videos
#     successful_downloads = 0
#     failed_downloads = 0
    
#     for i, video in enumerate(truly_new_videos, 1):
#         print(f"\n[{i}/{len(truly_new_videos)}] Processing video...")
        
#         if download_sub(video):
#             successful_downloads += 1
#         else:
#             failed_downloads += 1
#             # Still add to Firebase to avoid reprocessing failed videos
#             add_video_to_firebase(video)
    
#     # Step 5: Summary
#     print("\n" + "="*60)
#     print(f"📊 PROCESSING SUMMARY:")
#     print(f"   📺 Total videos from RSS: {len(new_videos)}")
#     print(f"   🆕 Truly new videos: {len(truly_new_videos)}")
#     print(f"   ✅ Successful downloads: {successful_downloads}")
#     print(f"   ❌ Failed downloads: {failed_downloads}")
#     print(f"   📁 Storage location: {STORAGE_DIR}")
#     print(f"   ⏰ Time window: {hours} hours")
#     print(f"   🎬 Skip shorts: {skip_shorts}")
#     print("="*60)

# def download_from_list_fallback(file_path="latest_video_links.txt"):
#     """Fallback method to download from text file (original functionality)"""
#     if not os.path.exists(file_path):
#         print(f"❌ File not found: {file_path}")
#         return
    
#     # Đảm bảo thư mục storage tồn tại
#     ensure_storage_directory()
        
#     with open(file_path, "r") as f:
#         urls = [line.strip() for line in f if line.strip()]

#     print(f"\n📋 Processing {len(urls)} video(s) from file...")
#     for url in urls:
#         # Create video data structure for compatibility
#         video_data = {'url': url}
#         download_sub(video_data)

# if __name__ == "__main__":
#     import sys
    
#     if len(sys.argv) > 1:
#         if sys.argv[1] == "--file":
#             # Use fallback method with file
#             file_path = sys.argv[2] if len(sys.argv) > 2 else "latest_video_links.txt"
#             download_from_list_fallback(file_path)
#         elif sys.argv[1] == "--hours":
#             # Set custom hours
#             hours = int(sys.argv[2]) if len(sys.argv) > 2 else 36
#             skip_shorts = True
#             if len(sys.argv) > 3 and sys.argv[3] == "--include-shorts":
#                 skip_shorts = False
#             process_new_videos(hours=hours, skip_shorts=skip_shorts)
#         else:
#             print("Usage:")
#             print("  python script.py                              # Default: 36 hours, skip shorts")
#             print("  python script.py --hours 24                   # Custom hours, skip shorts")
#             print("  python script.py --hours 24 --include-shorts  # Custom hours, include shorts")
#             print("  python script.py --file [filename]            # Use file fallback method")
#     else:
#         # Use new RSS-integrated method with default settings
#         process_new_videos(hours=36, skip_shorts=True)