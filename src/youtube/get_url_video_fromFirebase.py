import subprocess
import json
import os
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
from youtube_rss_fetcher import get_latest_videos_from_rss
from dotenv import load_dotenv

load_dotenv()

def initialize_firebase():
    """Initialize Firebase connection"""
    try:
        firebase_admin.get_app()
    except ValueError:
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
        if not service_account_json:
            raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set")
        service_account_info = json.loads(service_account_json)
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    return firestore.client()

def normalize_youtube_url(url):
    """Normalize YouTube URL to standard format"""
    if not url:
        return url
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

def export_all_youtube_urls_to_file(output_file="link_youtube.txt"):
    print("[INFO] Starting export all YouTube URLs...")
    try:
        db = initialize_firebase()
        print("[INFO] Fetching all videos from Firebase...")
        docs = db.collection("latest_video_links").stream()
        urls, doc_count = [], 0
        for doc in docs:
            doc_count += 1
            data = doc.to_dict()
            url = data.get("url")
            if url:
                normalized_url = normalize_youtube_url(url)
                if normalized_url and normalized_url not in urls:
                    urls.append(normalized_url)
                    if len(urls) % 100 == 0:
                        print(f"[INFO] Processed {len(urls)} unique URLs...")
        print(f"[INFO] Found {len(urls)} unique YouTube URLs from {doc_count} documents")
        if urls:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(url + '\n')
            print(f"[OK] Successfully exported {len(urls)} YouTube URLs to '{output_file}'")
            print(f"[INFO] File saved: {os.path.abspath(output_file)}")
        else:
            print("[ERROR] No YouTube URLs found to export")
        return len(urls)
    except Exception as e:
        print(f"[ERROR] Export failed: {e}")
        return 0

def export_recent_youtube_urls_to_file(days_back=7, output_file="link_youtube_recent.txt"):
    print(f"[INFO] Starting export YouTube URLs from last {days_back} days...")
    try:
        db = initialize_firebase()
        cutoff_time = datetime.now() - timedelta(days=days_back)
        print(f"[INFO] Fetching videos from {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} onwards...")
        docs = db.collection("latest_video_links") \
                 .where("createdAt", ">=", cutoff_time) \
                 .order_by("createdAt", direction=firestore.Query.DESCENDING) \
                 .stream()
        urls, doc_count = [], 0
        for doc in docs:
            doc_count += 1
            data = doc.to_dict()
            url = data.get("url")
            if url:
                normalized_url = normalize_youtube_url(url)
                if normalized_url and normalized_url not in urls:
                    urls.append(normalized_url)
        print(f"[INFO] Found {len(urls)} unique YouTube URLs from {doc_count} documents (last {days_back} days)")
        if urls:
            with open(output_file, 'w', encoding='utf-8') as f:
                for url in urls:
                    f.write(url + '\n')
            print(f"[OK] Successfully exported {len(urls)} YouTube URLs to '{output_file}'")
            print(f"[INFO] File saved: {os.path.abspath(output_file)}")
        else:
            print("[ERROR] No YouTube URLs found to export")
        return len(urls)
    except Exception as e:
        print(f"[ERROR] Export recent failed: {e}")
        return 0

def export_urls_by_channel(channel_name=None, output_file=None):
    if not channel_name:
        print("[ERROR] Please specify channel_name parameter")
        return 0
    if not output_file:
        safe_channel_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_channel_name = safe_channel_name.replace(' ', '_')
        output_file = f"link_youtube_{safe_channel_name}.txt"
    print(f"[INFO] Exporting YouTube URLs for channel: {channel_name}")
    try:
        db = initialize_firebase()
        docs = db.collection("latest_video_links").where("channel", "==", channel_name).stream()
        urls, doc_count = [], 0
        for doc in docs:
            doc_count += 1
            data = doc.to_dict()
            url = data.get("url")
            if url:
                normalized_url = normalize_youtube_url(url)
                if normalized_url and normalized_url not in urls:
                    urls.append(normalized_url)
        print(f"[INFO] Found {len(urls)} unique URLs for channel '{channel_name}' from {doc_count} documents")
        if urls:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# YouTube URLs for channel: {channel_name}\n")
                f.write(f"# Total videos: {len(urls)}\n")
                f.write(f"# Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for url in urls:
                    f.write(url + '\n')
            print(f"[OK] Successfully exported {len(urls)} URLs to '{output_file}'")
            print(f"[INFO] File saved: {os.path.abspath(output_file)}")
        else:
            print(f"[ERROR] No videos found for channel '{channel_name}'")
        return len(urls)
    except Exception as e:
        print(f"[ERROR] Export by channel failed: {e}")
        return 0

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "--export-all":
            output_file = sys.argv[2] if len(sys.argv) > 2 else "link_youtube.txt"
            export_all_youtube_urls_to_file(output_file)
        elif command == "--export-recent":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            output_file = sys.argv[3] if len(sys.argv) > 3 else f"link_youtube_recent_{days}days.txt"
            export_recent_youtube_urls_to_file(days_back=days, output_file=output_file)
        elif command == "--export-channel":
            if len(sys.argv) < 3:
                print("[ERROR] Usage: python script.py --export-channel 'Channel Name' [output_file]")
                sys.exit(1)
            channel_name = sys.argv[2]
            output_file = sys.argv[3] if len(sys.argv) > 3 else None
            export_urls_by_channel(channel_name=channel_name, output_file=output_file)
        else:
            print("[ERROR] Unknown command. Available commands:")
            print("   --export-all [output_file]")
            print("   --export-recent [days] [output_file]") 
            print("   --export-channel 'Channel Name' [output_file]")
    else:
        print("[INFO] No arguments given. Use --export-all, --export-recent or --export-channel.")
