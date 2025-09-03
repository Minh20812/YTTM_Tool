import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import time

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

def load_urls_from_file(file_path):
    """Read URLs from text file"""
    print(f"[INFO] Reading URLs from file: {file_path}")
    if not os.path.exists(file_path):
        print(f"[ERROR] File not found: {file_path}")
        return []
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                normalized_url = normalize_youtube_url(line)
                if normalized_url and normalized_url not in urls:
                    urls.append(normalized_url)
        print(f"[INFO] Loaded {len(urls)} unique URLs from file")
        return urls
    except Exception as e:
        print(f"[ERROR] Reading file: {e}")
        return []

def auto_delete_broken_links(batch_size=500):
    """Automatically delete broken links listed in yt_broken_links.txt"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "yt_broken_links.txt")
    print("[INFO] AUTO DELETE BROKEN YOUTUBE LINKS")
    print("=" * 50)
    print(f"[INFO] Looking for file: {file_path}")

    if not os.path.exists(file_path):
        print("[ERROR] yt_broken_links.txt not found")
        return 0

    target_urls = load_urls_from_file(file_path)
    if not target_urls:
        print("[INFO] No URLs found in file")
        return 0

    print(f"[INFO] Found {len(target_urls)} broken links to delete")

    try:
        db = initialize_firebase()
        target_urls_set = set(target_urls)
        documents_to_delete = []
        processed_count = 0

        print("[INFO] Scanning Firebase documents...")
        docs = db.collection("latest_video_links").stream()
        for doc in docs:
            processed_count += 1
            data = doc.to_dict()
            doc_url = data.get("url")
            if doc_url:
                normalized_doc_url = normalize_youtube_url(doc_url)
                if normalized_doc_url in target_urls_set:
                    documents_to_delete.append({
                        'doc_id': doc.id,
                        'url': normalized_doc_url,
                        'channel': data.get('channel', 'Unknown'),
                        'title': data.get('title', 'Unknown')
                    })
            if processed_count % 1000 == 0:
                print(f"[INFO] Processed {processed_count} docs, found {len(documents_to_delete)} to delete")

        print("\n=== SCAN RESULTS ===")
        print(f"Total docs scanned: {processed_count}")
        print(f"Broken links matched: {len(documents_to_delete)}")
        if not documents_to_delete:
            print("[INFO] No matching broken links found in database")
            return 0

        print(f"\n[INFO] Starting automatic deletion of {len(documents_to_delete)} links...")

        batch = db.batch()
        batch_count = 0
        deleted_count = 0
        for doc_info in documents_to_delete:
            doc_ref = db.collection("latest_video_links").document(doc_info['doc_id'])
            batch.delete(doc_ref)
            batch_count += 1
            deleted_count += 1

            safe_title = doc_info['title'][:50].encode("ascii", errors="ignore").decode()
            safe_channel = str(doc_info['channel']).encode("ascii", errors="ignore").decode()
            print(f"[DELETE] {deleted_count}/{len(documents_to_delete)}: {safe_channel} - {safe_title}...")
            
            if batch_count >= batch_size:
                batch.commit()
                print(f"[INFO] Committed batch of {batch_count} deletions")
                batch = db.batch()
                batch_count = 0
                time.sleep(0.1)

        if batch_count > 0:
            batch.commit()
            print(f"[INFO] Committed final batch of {batch_count} deletions")

        print(f"\n[SUCCESS] Deleted {deleted_count} broken YouTube links")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"yt_broken_links_processed_{timestamp}.txt"
        backup_path = os.path.join(current_dir, backup_file)
        try:
            os.rename(file_path, backup_path)
            print(f"[INFO] Processed file moved to: {backup_file}")
        except Exception as e:
            print(f"[WARN] Could not move processed file: {e}")

        return deleted_count
    except Exception as e:
        print(f"[ERROR] During deletion process: {e}")
        return 0

def show_broken_links_stats():
    """Show stats of yt_broken_links.txt file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "yt_broken_links.txt")
    if not os.path.exists(file_path):
        print("[ERROR] yt_broken_links.txt not found")
        return
    urls = load_urls_from_file(file_path)
    if not urls:
        return
    print("\n=== BROKEN LINKS STATS ===")
    print(f"File: yt_broken_links.txt")
    print(f"Total broken URLs: {len(urls)}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    print(f"Modified: {datetime.fromtimestamp(os.path.getmtime(file_path))}")
    print("\nPreview (first 10):")
    for i, url in enumerate(urls[:10]):
        print(f"  {i+1}. {url}")
    if len(urls) > 10:
        print(f"  ... and {len(urls) - 10} more")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("[INFO] Running automatic deletion...")
        auto_delete_broken_links()
        sys.exit(0)
    command = sys.argv[1]
    if command == "--stats":
        show_broken_links_stats()
    elif command in ["--auto-delete", "--delete"]:
        auto_delete_broken_links()
    elif command == "--help":
        print("BROKEN YOUTUBE LINKS AUTO DELETER")
        print("=" * 40)
        print("Usage:")
        print("   python auto_delete_broken.py                 # Auto delete broken links")
        print("   python auto_delete_broken.py --auto-delete   # Auto delete broken links")
        print("   python auto_delete_broken.py --stats         # Show file statistics")
        print("   python auto_delete_broken.py --help          # Show this help")
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Available: --auto-delete, --stats, --help")
        print("Run without arguments for automatic deletion")
