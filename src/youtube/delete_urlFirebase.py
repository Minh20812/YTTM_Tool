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

def load_urls_from_file(file_path):
    """
    Đọc các URLs từ file text
    """
    print(f"📖 Reading URLs from file: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return []
    
    urls = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                normalized_url = normalize_youtube_url(line)
                if normalized_url and normalized_url not in urls:
                    urls.append(normalized_url)
        
        print(f"✅ Loaded {len(urls)} unique URLs from file")
        return urls
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return []

def auto_delete_broken_links(batch_size=500):
    """
    Tự động xóa các broken links từ file yt_broken_links.txt
    Không cần xác nhận từ user
    """
    # Tìm file yt_broken_links.txt trong thư mục hiện tại
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "yt_broken_links.txt")
    
    print("🚀 AUTO DELETE BROKEN YOUTUBE LINKS")
    print("=" * 50)
    print(f"📁 Looking for file: {file_path}")
    
    # Kiểm tra file có tồn tại không
    if not os.path.exists(file_path):
        print(f"❌ File not found: yt_broken_links.txt")
        print("   Please make sure the file exists in the same directory as this script")
        return 0
    
    # Load URLs from file
    target_urls = load_urls_from_file(file_path)
    if not target_urls:
        print("❌ No URLs found in file")
        return 0
    
    print(f"🎯 Found {len(target_urls)} broken links to delete")
    
    try:
        db = initialize_firebase()
        
        # Create a set for faster lookup
        target_urls_set = set(target_urls)
        
        documents_to_delete = []
        processed_count = 0
        
        print("🔍 Scanning Firebase documents...")
        
        # Query all documents from the collection
        docs = db.collection("latest_video_links").stream()
        
        for doc in docs:
            processed_count += 1
            data = doc.to_dict()
            doc_url = data.get("url")
            
            if doc_url:
                normalized_doc_url = normalize_youtube_url(doc_url)
                
                # Check if this URL should be deleted
                if normalized_doc_url in target_urls_set:
                    doc_info = {
                        'doc_id': doc.id,
                        'url': normalized_doc_url,
                        'channel': data.get('channel', 'Unknown'),
                        'title': data.get('title', 'Unknown')
                    }
                    documents_to_delete.append(doc_info)
            
            # Progress update
            if processed_count % 1000 == 0:
                print(f"📊 Processed {processed_count} documents, found {len(documents_to_delete)} to delete")
        
        print(f"\n📈 SCAN RESULTS:")
        print(f"   📋 Total documents scanned: {processed_count}")
        print(f"   🎯 Broken links found to delete: {len(documents_to_delete)}")
        
        if not documents_to_delete:
            print("✅ No matching broken links found in database")
            return 0
        
        # Start automatic deletion
        print(f"\n🔥 Starting AUTOMATIC DELETION of {len(documents_to_delete)} broken links...")
        
        # Delete documents in batches
        batch = db.batch()
        batch_count = 0
        deleted_count = 0
        
        for doc_info in documents_to_delete:
            doc_ref = db.collection("latest_video_links").document(doc_info['doc_id'])
            batch.delete(doc_ref)
            batch_count += 1
            deleted_count += 1
            
            print(f"🗑️  Deleting [{deleted_count}/{len(documents_to_delete)}]: {doc_info['channel']} - {doc_info['title'][:50]}...")
            
            # Commit batch when it reaches batch_size
            if batch_count >= batch_size:
                batch.commit()
                print(f"✅ Committed batch of {batch_count} deletions")
                batch = db.batch()
                batch_count = 0
                time.sleep(0.1)  # Small delay to avoid rate limiting
        
        # Commit remaining documents in batch
        if batch_count > 0:
            batch.commit()
            print(f"✅ Committed final batch of {batch_count} deletions")
        
        print(f"\n🎉 SUCCESS! Automatically deleted {deleted_count} broken YouTube links")
        
        # Tạo backup của file đã xử lý
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"yt_broken_links_processed_{timestamp}.txt"
        backup_path = os.path.join(current_dir, backup_file)
        
        try:
            os.rename(file_path, backup_path)
            print(f"📦 Processed file moved to: {backup_file}")
        except Exception as e:
            print(f"⚠️  Warning: Could not move processed file: {e}")
        
        return deleted_count
        
    except Exception as e:
        print(f"❌ Error during deletion process: {e}")
        return 0

def show_broken_links_stats():
    """
    Hiển thị thống kê về file broken links
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "yt_broken_links.txt")
    
    if not os.path.exists(file_path):
        print("❌ yt_broken_links.txt not found in current directory")
        return
    
    urls = load_urls_from_file(file_path)
    if not urls:
        return
    
    print(f"\n📈 BROKEN LINKS STATISTICS:")
    print(f"   📁 File: yt_broken_links.txt")
    print(f"   🔗 Total broken URLs: {len(urls)}")
    print(f"   📊 File size: {os.path.getsize(file_path)} bytes")
    print(f"   📅 Modified: {datetime.fromtimestamp(os.path.getmtime(file_path))}")
    
    # Show first few URLs as preview
    print(f"\n🔍 Preview (first 10 broken links):")
    for i, url in enumerate(urls[:10]):
        print(f"   {i+1}. {url}")
    
    if len(urls) > 10:
        print(f"   ... and {len(urls) - 10} more broken links")

# Main execution
if __name__ == "__main__":
    import sys
    
    # Nếu không có argument, tự động chạy delete
    if len(sys.argv) < 2:
        print("🚀 Running automatic deletion of broken YouTube links...")
        auto_delete_broken_links()
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "--stats":
        show_broken_links_stats()
        
    elif command == "--auto-delete" or command == "--delete":
        auto_delete_broken_links()
        
    elif command == "--help":
        print("🔧 BROKEN YOUTUBE LINKS AUTO DELETER")
        print("=" * 40)
        print("Usage:")
        print("   python auto_delete_broken.py                 # Auto delete broken links")
        print("   python auto_delete_broken.py --auto-delete   # Auto delete broken links")
        print("   python auto_delete_broken.py --stats         # Show file statistics")
        print("   python auto_delete_broken.py --help          # Show this help")
        print("\nNote: Script looks for 'yt_broken_links.txt' in the same directory")
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: --auto-delete, --stats, --help")
        print("Run without arguments for automatic deletion")