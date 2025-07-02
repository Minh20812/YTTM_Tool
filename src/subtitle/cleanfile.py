import os
import glob

# Xóa file links
if os.path.exists('latest_video_links.txt'):
    os.remove('latest_video_links.txt')
    print("✓ Đã xóa latest_video_links.txt")

if os.path.exists('enhanced_batch_downloader.py'):
    os.remove('enhanced_batch_downloader.py')
    print("✓ Đã xóa enhanced_batch_downloader.py")

if os.path.exists('failed_downloads.txt'):
    os.remove('failed_downloads.txt')
    print("✓ Đã xóa failed_downloads.txt")

# Xóa các file tạm
for pattern in ['*.srt', '*.vi.srt', '*.mp3', '*.ogg', '*.count.txt', '*.json', '*.cleaned.srt', '*_merged.srt', '*.log', '*.cleansub.srt']:
    for f in glob.glob(pattern):
        os.remove(f)
        print(f"✓ Đã xóa {f}")