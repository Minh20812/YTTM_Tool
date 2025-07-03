import os
import glob

# Xác định thư mục storage cùng cấp với thư mục cha của script
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
storage_dir = os.path.join(parent_dir, 'storage')

# Xóa file links trong storage
for filename in ['latest_video_links.txt', 'enhanced_batch_downloader.py', 'failed_downloads.txt']:
    file_path = os.path.join(storage_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"✓ Đã xóa {file_path}")

# Xóa các file tạm trong storage
patterns = [
    '*.srt', '*.vi.srt', '*.mp3', '*.ogg', '*.count.txt', '*.json',
    '*.cleaned.srt', '*_merged.srt', '*.log', '*.cleansub.srt'
]
for pattern in patterns:
    for f in glob.glob(os.path.join(storage_dir, pattern)):
        os.remove(f)
        print(f"✓ Đã xóa {f}")

# import os
# import glob

# # Xóa file links
# if os.path.exists('latest_video_links.txt'):
#     os.remove('latest_video_links.txt')
#     print("✓ Đã xóa latest_video_links.txt")

# if os.path.exists('enhanced_batch_downloader.py'):
#     os.remove('enhanced_batch_downloader.py')
#     print("✓ Đã xóa enhanced_batch_downloader.py")

# if os.path.exists('failed_downloads.txt'):
#     os.remove('failed_downloads.txt')
#     print("✓ Đã xóa failed_downloads.txt")

# # Xóa các file tạm
# for pattern in ['*.srt', '*.vi.srt', '*.mp3', '*.ogg', '*.count.txt', '*.json', '*.cleaned.srt', '*_merged.srt', '*.log', '*.cleansub.srt']:
#     for f in glob.glob(pattern):
#         os.remove(f)
#         print(f"✓ Đã xóa {f}")