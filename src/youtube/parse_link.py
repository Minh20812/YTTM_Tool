import firebase_admin
from firebase_admin import credentials, firestore
from src.youtube.get_latest_video2 import main as get_latest_links
from datetime import datetime

cred = credentials.Certificate("./serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

def get_existing_links():
    """Get all existing video URLs from Firestore"""
    docs = db.collection("latest_video_links").stream()
    return set(doc.to_dict().get("url") for doc in docs if doc.to_dict().get("url"))

def add_new_videos(new_videos):
    """Add new video data to Firestore"""
    existing_links = get_existing_links()
    added = 0
    
    for video in new_videos:
        url = video.get('url')
        if not url:
            print(f"⚠️ Skipping video without URL: {video}")
            continue
            
        if url not in existing_links:
            # Add complete video information to Firestore
            video_data = {
                "url": url,
                "title": video.get('title', 'Unknown'),
                "channel": video.get('channel', 'Unknown'),
                "channel_url": video.get('channel_url', ''),
                "upload_date": video.get('upload_date', ''),
                "createdAt": firestore.SERVER_TIMESTAMP
            }
            
            db.collection("latest_video_links").add(video_data)
            print(f"➕ Đã thêm mới: {video.get('title', 'Unknown')[:60]}...")
            print(f"   🔗 {url}")
            added += 1
        else:
            print(f"⏭️ Bỏ qua (đã tồn tại): {video.get('title', 'Unknown')[:60]}...")
    
    print(f"\n📊 Tổng cộng: {len(new_videos)} video.")
    print(f"✅ Đã thêm {added} video mới vào Firestore.")
    print(f"⏭️ {len(new_videos) - added} video đã tồn tại và bị bỏ qua.")

def cleanup_old_entries(days_old=30):
    """Optional: Clean up entries older than specified days"""
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    # Query old documents
    old_docs = db.collection("latest_video_links").where(
        "createdAt", "<", cutoff_date
    ).stream()
    
    deleted_count = 0
    for doc in old_docs:
        doc.reference.delete()
        deleted_count += 1
    
    if deleted_count > 0:
        print(f"🗑️ Cleaned up {deleted_count} entries older than {days_old} days")

if __name__ == "__main__":
    print("🚀 Starting YouTube video collection...")
    
    # Get new videos from YouTube
    new_videos = get_latest_links(return_links=True)
    
    if new_videos:
        print(f"\n📥 Processing {len(new_videos)} videos...")
        add_new_videos(new_videos)
        
        # Optional: Clean up old entries (uncomment if needed)
        # cleanup_old_entries(days_old=30)
        
    else:
        print("❌ No new videos found to process.")
    
    print("\n✅ Script completed!")