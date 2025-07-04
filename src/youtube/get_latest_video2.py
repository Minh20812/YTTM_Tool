import subprocess
import json
from datetime import datetime, timedelta
import sys
import os
import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_cookies():
    """
    Setup cookies from environment variable to avoid bot detection
    """
    cookies_content = os.getenv('COOKIES_CONTENT')
    
    if not cookies_content:
        print("🍪 Cookie environment variable not found. Creating instructions...")
        print("=" * 60)
        print("TO FIX BOT DETECTION ERROR:")
        print("1. Add your cookies to .env file:")
        print("   COOKIES_CONTENT=# Netscape HTTP Cookie File...")
        print("2. Or manually export cookies:")
        print("   - Install browser extension 'Get cookies.txt LOCALLY'")
        print("   - Visit youtube.com in your browser")
        print("   - Use extension to export cookies")
        print("   - Copy content to COOKIES_CONTENT in .env file")
        print("3. Or use yt-dlp's built-in browser cookie extraction:")
        print("   - Add --cookies-from-browser chrome (or firefox, edge, etc.)")
        print("=" * 60)
        return False, None
    
    # Tạo file cookies tạm thời từ biến môi trường
    temp_cookies_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_cookies.txt")
    
    try:
        with open(temp_cookies_file, 'w', encoding='utf-8') as f:
            f.write(cookies_content)
        print(f"✅ Created temporary cookies file: {temp_cookies_file}")
        return True, temp_cookies_file
    except Exception as e:
        print(f"❌ Failed to create cookies file: {e}")
        return False, None

def cleanup_cookies(cookies_file):
    """
    Clean up temporary cookies file
    """
    if cookies_file and os.path.exists(cookies_file):
        try:
            os.remove(cookies_file)
            print(f"🗑️ Cleaned up temporary cookies file")
        except Exception as e:
            print(f"⚠️ Failed to cleanup cookies file: {e}")

def get_recent_videos_with_cookies(channel_url, within_hours=24, max_videos=3, cookies_file=None):
    """
    Enhanced version with multiple strategies to avoid bot detection
    """
    strategies = []
    
    # Strategy 1: Use cookies from environment variable (if available)
    if cookies_file:
        strategies.append({
            'name': 'Environment Cookies',
            'command_extra': ['--cookies', cookies_file, '--sleep-requests', '2']
        })
    
    # Strategy 2: Use cookies from browser
    strategies.extend([
        {
            'name': 'Browser Cookies (Chrome)',
            'command_extra': ['--cookies-from-browser', 'chrome', '--sleep-requests', '2']
        },
        {
            'name': 'Browser Cookies (Firefox)',
            'command_extra': ['--cookies-from-browser', 'firefox', '--sleep-requests', '2']
        },
        # Strategy 3: Use user agent and sleep
        {
            'name': 'User Agent + Sleep',
            'command_extra': [
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--sleep-requests', '3',
                '--sleep-interval', '1'
            ]
        },
        # Strategy 4: Basic with longer timeout
        {
            'name': 'Basic',
            'command_extra': ['--sleep-requests', '1']
        }
    ])
    
    for strategy in strategies:
        print(f"[🔄] Trying strategy: {strategy['name']}")
        
        base_command = [
            'yt-dlp',
            '--dump-json',
            '--playlist-end', str(max_videos),
            '--no-warnings',
            '--ignore-errors',
            '--skip-unavailable-fragments',
            '--no-check-certificates'
        ]
        
        command = base_command + strategy['command_extra'] + [f'{channel_url}/videos']
        
        try:
            # Add random delay to appear more human-like
            time.sleep(random.uniform(1, 3))
            
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                  text=True, timeout=120)
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"[✅] Success with strategy: {strategy['name']}")
                return parse_video_data(result.stdout, within_hours, channel_url)
            else:
                print(f"[❌] Failed with strategy: {strategy['name']}")
                if "Sign in to confirm" in result.stderr:
                    print(f"[🤖] Bot detection triggered")
                    continue
                elif result.stderr:
                    print(f"[🔍] Error: {result.stderr[:100]}...")
                    
        except subprocess.TimeoutExpired:
            print(f"[⏱️] Timeout with strategy: {strategy['name']}")
            continue
        except Exception as e:
            print(f"[❌] Exception with strategy: {strategy['name']}: {e}")
            continue
    
    print(f"[❌] All strategies failed for: {channel_url}")
    return []

def parse_video_data(stdout_data, within_hours, channel_url):
    """
    Parse video data from yt-dlp output
    """
    videos = []
    now = datetime.utcnow()
    cutoff_time = now - timedelta(hours=within_hours)
    
    lines = [line.strip() for line in stdout_data.strip().split('\n') if line.strip()]
    
    for line in lines:
        try:
            info = json.loads(line)
            
            # Skip premiere/scheduled videos
            if info.get('live_status') in ['is_upcoming', 'was_live']:
                print(f"[⏭️] Skipping premiere/live: {info.get('title', 'Unknown')[:50]}...")
                continue
            
            # Get upload timestamp
            upload_time = None
            
            if info.get('release_timestamp'):
                upload_time = info['release_timestamp']
            elif info.get('timestamp'):
                upload_time = info['timestamp']
            elif info.get('upload_date'):
                try:
                    upload_date_str = info['upload_date']
                    upload_time = datetime.strptime(upload_date_str, '%Y%m%d').timestamp()
                except:
                    continue
            
            if not upload_time:
                print(f"[⚠️] No upload time found for: {info.get('title', 'Unknown')}")
                continue

            uploaded_at = datetime.utcfromtimestamp(upload_time)
            
            print(f"[📅] Video: {info.get('title', 'Unknown')[:50]}... - Upload: {uploaded_at}")

            if uploaded_at >= cutoff_time:
                videos.append({
                    'url': info['webpage_url'],
                    'title': info.get('title', 'Unknown'),
                    'upload_date': uploaded_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'channel': info.get('channel', 'Unknown'),
                    'channel_url': channel_url
                })
                print(f"[✅] New video found: {info.get('title', 'Unknown')[:50]}...")
            else:
                print(f"[❌] Video too old: {info.get('title', 'Unknown')[:50]}...")
                
        except json.JSONDecodeError as e:
            print(f"[🔍] JSON parse error: {e}")
            continue
        except Exception as e:
            print(f"[🔍] Unknown error: {e}")
            continue

    return videos

def get_rss_fallback(channel_url):
    """
    Fallback method using RSS feed (limited but more reliable)
    """
    try:
        # Extract channel ID from URL
        command = [
            'yt-dlp',
            '--dump-json',
            '--playlist-items', '1',
            '--no-warnings',
            channel_url
        ]
        
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=30)
        
        if result.stdout.strip():
            info = json.loads(result.stdout.strip().split('\n')[0])
            channel_id = info.get('channel_id')
            
            if channel_id:
                print(f"[📡] Trying RSS feed for channel ID: {channel_id}")
                # You could implement RSS parsing here as additional fallback
                return []
                
    except Exception as e:
        print(f"[❌] RSS fallback failed: {e}")
        
    return []

def filter_existing_videos(new_videos, history_file='latest_video_links.txt'):
    """Filter out videos that already exist in history file"""
    existing_urls = set()
    
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            existing_urls = {line.strip() for line in f if line.strip()}
        print(f"📚 Read {len(existing_urls)} links from history file")
    
    filtered_videos = []
    for video in new_videos:
        if video['url'] not in existing_urls:
            filtered_videos.append(video)
            print(f"[✨] New video: {video['title'][:50]}...")
        else:
            print(f"[🔄] Skipping duplicate: {video['title'][:50]}...")
    
    return filtered_videos

def update_yt_dlp():
    """
    Update yt-dlp to latest version
    """
    print("🔄 Checking yt-dlp version...")
    try:
        result = subprocess.run(['yt-dlp', '--version'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        current_version = result.stdout.strip()
        print(f"📦 Current yt-dlp version: {current_version}")
        
        print("🔄 Updating yt-dlp...")
        update_result = subprocess.run(['pip', 'install', '--upgrade', 'yt-dlp'], 
                                     capture_output=True, text=True)
        
        if update_result.returncode == 0:
            print("✅ yt-dlp updated successfully")
        else:
            print(f"⚠️ Update warning: {update_result.stderr}")
            
    except Exception as e:
        print(f"❌ Failed to update yt-dlp: {e}")

def main(return_links=False):
    update_yt_dlp()
    
    # Setup cookies từ environment variable
    cookies_ready, cookies_file = setup_cookies()
    
    channels = [
        # 'https://www.youtube.com/@Vox',
          'https://www.youtube.com/@CNBC',
        # 'https://www.youtube.com/@veritasium', 
        # 'https://www.youtube.com/@NatGeo',
        # 'https://www.youtube.com/@wsj',
        # 'https://www.youtube.com/@SciShow',
        # 'https://www.youtube.com/@BusinessInsider',
        # 'https://www.youtube.com/@NatGeoAnimals',
        # 'https://www.youtube.com/@bbcearth',
        # 'https://www.youtube.com/@fern-tv',
        # 'https://www.youtube.com/@Fireship',
        # 'https://www.youtube.com/@HistoryoftheUniverse',
        # 'https://www.youtube.com/@IBMTechnology',
        # 'https://www.youtube.com/@johnnyharris',
        # 'https://www.youtube.com/@MikeShake',
        # 'https://www.youtube.com/@neoexplains',
        # 'https://www.youtube.com/@numberphile',
        # 'https://www.youtube.com/@pbsspacetime',
        # 'https://www.youtube.com/@PolyMatter',
        # 'https://www.youtube.com/@QuantaScienceChannel',
        # 'https://www.youtube.com/@SabineHossenfelder',
        # 'https://www.youtube.com/@SteveMould',
        # 'https://www.youtube.com/@TED',
        # 'https://www.youtube.com/@TEDEd',
        # 'https://www.youtube.com/@ThioJoe',
        # 'https://www.youtube.com/@Wendoverproductions',
        # 'https://www.youtube.com/@YesTheory',
        # 'https://www.youtube.com/@bbclearningenglish',
        # 'https://www.youtube.com/@DWDocumentary',
        # 'https://www.youtube.com/@CrunchLabs',
        # 'https://www.youtube.com/@PracticalEngineeringChannel'
    ]

    print(f"🚀 Starting scan of {len(channels)} YouTube channels...")
    print(f"⏰ Looking for videos uploaded in the last 24 hours")
    if cookies_ready:
        print(f"🍪 Using cookies from environment variable")
    else:
        print(f"⚠️ No cookies available - may face bot detection")
    print("-" * 60)

    all_recent_videos = []
    failed_channels = []

    try:
        for i, channel_url in enumerate(channels, 1):
            print(f"\n[{i}/{len(channels)}] 🔍 Checking: {channel_url}")
            recent_videos = get_recent_videos_with_cookies(
                channel_url, 
                within_hours=24, 
                max_videos=3,
                cookies_file=cookies_file
            )
            if recent_videos:
                print(f"[✅] Found {len(recent_videos)} new videos from this channel")
                all_recent_videos.extend(recent_videos)
            else:
                print(f"[❌] No new videos found from this channel")
                failed_channels.append(channel_url)
            if i < len(channels):
                delay = random.uniform(2, 5)
                print(f"[⏳] Waiting {delay:.1f}s before next channel...")
                time.sleep(delay)

    finally:
        # Always cleanup cookies file
        cleanup_cookies(cookies_file)

    print("\n" + "="*60)
    print(f"📊 SUMMARY: Found {len(all_recent_videos)} new videos")

    if failed_channels:
        print(f"⚠️ Failed channels ({len(failed_channels)}):")
        for channel in failed_channels[:5]:
            print(f"   - {channel}")
        if len(failed_channels) > 5:
            print(f"   ... and {len(failed_channels) - 5} more")

    if all_recent_videos:
        print(f"\n📋 New videos (raw, chưa filter Firestore):")
        for video in all_recent_videos[:5]:
            print(f"  • {video['title'][:60]}...")
            print(f"    🔗 {video['url']}")
            print(f"    📺 {video['channel']}")
        print(f"\n🎯 RESULT: Found {len(all_recent_videos)} new videos!")
        if return_links:
            return all_recent_videos
    else:
        print("❌ No new videos found!")
        print("\n🔍 Possible reasons:")
        print("   - Channels haven't posted new videos in 24h")
        print("   - YouTube bot detection is blocking requests")
        print("   - Need to setup cookies in .env file")
        print("   - Network connectivity issues")
        print("\n💡 Try:")
        print("   1. Add COOKIES_CONTENT to .env file")
        print("   2. Run script with longer intervals between requests")
        print("   3. Check if yt-dlp needs updating")
        if return_links:
            return []

if __name__ == "__main__":
    main()


# import subprocess
# import json
# from datetime import datetime, timedelta
# import sys
# import os
# import time
# import random

# def setup_cookies():
#     """
#     Setup cookies from browser to avoid bot detection
#     """
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     parent_dir = os.path.dirname(os.path.dirname(current_dir))
#     cookies_file = os.path.join(parent_dir, 'cookies.txt')
    
#     if not os.path.exists(cookies_file):
#         print("🍪 Cookie file not found. Creating instructions...")
#         print("=" * 60)
#         print("TO FIX BOT DETECTION ERROR:")
#         print("1. Install browser_cookie3: pip install browser_cookie3")
#         print("2. Or manually export cookies:")
#         print("   - Install browser extension 'Get cookies.txt LOCALLY'")
#         print("   - Visit youtube.com in your browser")
#         print("   - Use extension to export cookies to 'cookies.txt'")
#         print("3. Or use yt-dlp's built-in browser cookie extraction:")
#         print("   - Add --cookies-from-browser chrome (or firefox, edge, etc.)")
#         print("=" * 60)
#         return False
    
#     return True

# def get_recent_videos_with_cookies(channel_url, within_hours=24, max_videos=3):
#     """
#     Enhanced version with multiple strategies to avoid bot detection
#     """
#     strategies = [
#         # Strategy 1: Use cookies from browser
#         {
#             'name': 'Browser Cookies',
#             'command_extra': ['--cookies-from-browser', 'chrome', '--sleep-requests', '2']
#         },
#         # Strategy 2: Use manual cookies file
#         {
#             'name': 'Manual Cookies',
#             'command_extra': ['--cookies', 'cookies.txt', '--sleep-requests', '2']
#         },
#         # Strategy 3: Use user agent and sleep
#         {
#             'name': 'User Agent + Sleep',
#             'command_extra': [
#                 '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
#                 '--sleep-requests', '3',
#                 '--sleep-interval', '1'
#             ]
#         },
#         # Strategy 4: Basic with longer timeout
#         {
#             'name': 'Basic',
#             'command_extra': ['--sleep-requests', '1']
#         }
#     ]
    
#     for strategy in strategies:
#         print(f"[🔄] Trying strategy: {strategy['name']}")
        
#         base_command = [
#             'yt-dlp',
#             '--dump-json',
#             '--playlist-end', str(max_videos),
#             '--no-warnings',
#             '--ignore-errors',
#             '--skip-unavailable-fragments',
#             '--no-check-certificates'
#         ]
        
#         command = base_command + strategy['command_extra'] + [f'{channel_url}/videos']
        
#         try:
#             # Add random delay to appear more human-like
#             time.sleep(random.uniform(1, 3))
            
#             result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
#                                   text=True, timeout=120)
            
#             if result.returncode == 0 and result.stdout.strip():
#                 print(f"[✅] Success with strategy: {strategy['name']}")
#                 return parse_video_data(result.stdout, within_hours, channel_url)
#             else:
#                 print(f"[❌] Failed with strategy: {strategy['name']}")
#                 if "Sign in to confirm" in result.stderr:
#                     print(f"[🤖] Bot detection triggered")
#                     continue
#                 elif result.stderr:
#                     print(f"[🔍] Error: {result.stderr[:100]}...")
                    
#         except subprocess.TimeoutExpired:
#             print(f"[⏱️] Timeout with strategy: {strategy['name']}")
#             continue
#         except Exception as e:
#             print(f"[❌] Exception with strategy: {strategy['name']}: {e}")
#             continue
    
#     print(f"[❌] All strategies failed for: {channel_url}")
#     return []

# def parse_video_data(stdout_data, within_hours, channel_url):
#     """
#     Parse video data from yt-dlp output
#     """
#     videos = []
#     now = datetime.utcnow()
#     cutoff_time = now - timedelta(hours=within_hours)
    
#     lines = [line.strip() for line in stdout_data.strip().split('\n') if line.strip()]
    
#     for line in lines:
#         try:
#             info = json.loads(line)
            
#             # Skip premiere/scheduled videos
#             if info.get('live_status') in ['is_upcoming', 'was_live']:
#                 print(f"[⏭️] Skipping premiere/live: {info.get('title', 'Unknown')[:50]}...")
#                 continue
            
#             # Get upload timestamp
#             upload_time = None
            
#             if info.get('release_timestamp'):
#                 upload_time = info['release_timestamp']
#             elif info.get('timestamp'):
#                 upload_time = info['timestamp']
#             elif info.get('upload_date'):
#                 try:
#                     upload_date_str = info['upload_date']
#                     upload_time = datetime.strptime(upload_date_str, '%Y%m%d').timestamp()
#                 except:
#                     continue
            
#             if not upload_time:
#                 print(f"[⚠️] No upload time found for: {info.get('title', 'Unknown')}")
#                 continue

#             uploaded_at = datetime.utcfromtimestamp(upload_time)
            
#             print(f"[📅] Video: {info.get('title', 'Unknown')[:50]}... - Upload: {uploaded_at}")

#             if uploaded_at >= cutoff_time:
#                 videos.append({
#                     'url': info['webpage_url'],
#                     'title': info.get('title', 'Unknown'),
#                     'upload_date': uploaded_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
#                     'channel': info.get('channel', 'Unknown'),
#                     'channel_url': channel_url
#                 })
#                 print(f"[✅] New video found: {info.get('title', 'Unknown')[:50]}...")
#             else:
#                 print(f"[❌] Video too old: {info.get('title', 'Unknown')[:50]}...")
                
#         except json.JSONDecodeError as e:
#             print(f"[🔍] JSON parse error: {e}")
#             continue
#         except Exception as e:
#             print(f"[🔍] Unknown error: {e}")
#             continue

#     return videos

# def get_rss_fallback(channel_url):
#     """
#     Fallback method using RSS feed (limited but more reliable)
#     """
#     try:
#         # Extract channel ID from URL
#         command = [
#             'yt-dlp',
#             '--dump-json',
#             '--playlist-items', '1',
#             '--no-warnings',
#             channel_url
#         ]
        
#         result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
#                               text=True, timeout=30)
        
#         if result.stdout.strip():
#             info = json.loads(result.stdout.strip().split('\n')[0])
#             channel_id = info.get('channel_id')
            
#             if channel_id:
#                 print(f"[📡] Trying RSS feed for channel ID: {channel_id}")
#                 # You could implement RSS parsing here as additional fallback
#                 return []
                
#     except Exception as e:
#         print(f"[❌] RSS fallback failed: {e}")
        
#     return []

# def filter_existing_videos(new_videos, history_file='latest_video_links.txt'):
#     """Filter out videos that already exist in history file"""
#     existing_urls = set()
    
#     if os.path.exists(history_file):
#         with open(history_file, 'r', encoding='utf-8') as f:
#             existing_urls = {line.strip() for line in f if line.strip()}
#         print(f"📚 Read {len(existing_urls)} links from history file")
    
#     filtered_videos = []
#     for video in new_videos:
#         if video['url'] not in existing_urls:
#             filtered_videos.append(video)
#             print(f"[✨] New video: {video['title'][:50]}...")
#         else:
#             print(f"[🔄] Skipping duplicate: {video['title'][:50]}...")
    
#     return filtered_videos

# def update_yt_dlp():
#     """
#     Update yt-dlp to latest version
#     """
#     print("🔄 Checking yt-dlp version...")
#     try:
#         result = subprocess.run(['yt-dlp', '--version'], 
#                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#         current_version = result.stdout.strip()
#         print(f"📦 Current yt-dlp version: {current_version}")
        
#         print("🔄 Updating yt-dlp...")
#         update_result = subprocess.run(['pip', 'install', '--upgrade', 'yt-dlp'], 
#                                      capture_output=True, text=True)
        
#         if update_result.returncode == 0:
#             print("✅ yt-dlp updated successfully")
#         else:
#             print(f"⚠️ Update warning: {update_result.stderr}")
            
#     except Exception as e:
#         print(f"❌ Failed to update yt-dlp: {e}")

# def main(return_links=False):
#     update_yt_dlp()
#     setup_cookies()

#     channels = [
#         'https://www.youtube.com/@Vox',
#         'https://www.youtube.com/@veritasium', 
#         'https://www.youtube.com/@NatGeo',
#         'https://www.youtube.com/@wsj',
#         'https://www.youtube.com/@SciShow',
#         'https://www.youtube.com/@BusinessInsider',
#         'https://www.youtube.com/@NatGeoAnimals',
#         'https://www.youtube.com/@bbcearth',
#         'https://www.youtube.com/@fern-tv',
#         'https://www.youtube.com/@Fireship',
#         'https://www.youtube.com/@HistoryoftheUniverse',
#         'https://www.youtube.com/@IBMTechnology',
#         'https://www.youtube.com/@johnnyharris',
#         'https://www.youtube.com/@MikeShake',
#         'https://www.youtube.com/@neoexplains',
#         'https://www.youtube.com/@numberphile',
#         'https://www.youtube.com/@pbsspacetime',
#         'https://www.youtube.com/@PolyMatter',
#         'https://www.youtube.com/@QuantaScienceChannel',
#         'https://www.youtube.com/@SabineHossenfelder',
#         'https://www.youtube.com/@SteveMould',
#         'https://www.youtube.com/@TED',
#         'https://www.youtube.com/@TEDEd',
#         'https://www.youtube.com/@ThioJoe',
#         'https://www.youtube.com/@Wendoverproductions',
#         'https://www.youtube.com/@YesTheory',
#         'https://www.youtube.com/@bbclearningenglish',
#         'https://www.youtube.com/@DWDocumentary',
#         'https://www.youtube.com/@CrunchLabs',
#         'https://www.youtube.com/@PracticalEngineeringChannel'
#     ]

#     print(f"🚀 Starting scan of {len(channels)} YouTube channels...")
#     print(f"⏰ Looking for videos uploaded in the last 24 hours")
#     print("-" * 60)

#     all_recent_videos = []
#     failed_channels = []

#     for i, channel_url in enumerate(channels, 1):
#         print(f"\n[{i}/{len(channels)}] 🔍 Checking: {channel_url}")
#         recent_videos = get_recent_videos_with_cookies(channel_url, within_hours=24, max_videos=3)
#         if recent_videos:
#             print(f"[✅] Found {len(recent_videos)} new videos from this channel")
#             all_recent_videos.extend(recent_videos)
#         else:
#             print(f"[❌] No new videos found from this channel")
#             failed_channels.append(channel_url)
#         if i < len(channels):
#             delay = random.uniform(2, 5)
#             print(f"[⏳] Waiting {delay:.1f}s before next channel...")
#             time.sleep(delay)

#     print("\n" + "="*60)
#     print(f"📊 SUMMARY: Found {len(all_recent_videos)} new videos")

#     if failed_channels:
#         print(f"⚠️ Failed channels ({len(failed_channels)}):")
#         for channel in failed_channels[:5]:
#             print(f"   - {channel}")
#         if len(failed_channels) > 5:
#             print(f"   ... and {len(failed_channels) - 5} more")

#     if all_recent_videos:
#         print(f"\n📋 New videos (raw, chưa filter Firestore):")
#         for video in all_recent_videos[:5]:
#             print(f"  • {video['title'][:60]}...")
#             print(f"    🔗 {video['url']}")
#             print(f"    📺 {video['channel']}")
#         print(f"\n🎯 RESULT: Found {len(all_recent_videos)} new videos!")
#         if return_links:
#             return all_recent_videos
#     else:
#         print("❌ No new videos found!")
#         print("\n🔍 Possible reasons:")
#         print("   - Channels haven't posted new videos in 24h")
#         print("   - YouTube bot detection is blocking requests")
#         print("   - Need to setup cookies for authentication")
#         print("   - Network connectivity issues")
#         print("\n💡 Try:")
#         print("   1. Setup browser cookies (see instructions above)")
#         print("   2. Run script with longer intervals between requests")
#         print("   3. Check if yt-dlp needs updating")
#         if return_links:
#             return []

# if __name__ == "__main__":
#     main()