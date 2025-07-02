#!/usr/bin/env python3
"""
Archive.org OGG Auto Uploader with YouTube Integration
Tự động upload tất cả file OGG lên Archive.org với metadata từ YouTube
"""

import os
import sys
import glob
import random
import requests
import json
from pathlib import Path
from internetarchive import upload, configure, get_item, get_session
from internetarchive.exceptions import ItemLocateError
import time
import logging
from datetime import datetime, timedelta
import re

# Thiết lập logging với encoding UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('upload_log.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class YouTubeArchiveUploader:
    def __init__(self):
        """Khởi tạo uploader với credentials và YouTube API"""
        self.setup_credentials()
        self.session = get_session()
        self.upload_delay_base = 30
        self.max_retries = 5
        
        # YouTube API Key - BẠN CẦN THAY ĐỔI KEY NÀY
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube_cache = {}  # Cache để tránh gọi API nhiều lần
        
    def setup_credentials(self):
        """Thiết lập credentials cho Archive.org"""
        # BẠN NÊN THAY ĐỔI THÔNG TIN ĐĂNG NHẬP NÀY
        IA_ACCESS_KEY = os.getenv("IA_ACCESS_KEY", "")
        IA_SECRET_KEY = os.getenv("IA_SECRET_KEY", "")
        
        if IA_ACCESS_KEY and IA_SECRET_KEY:
            configure(IA_ACCESS_KEY, IA_SECRET_KEY)
            logger.info("🔑 Đã thiết lập credentials cho Archive.org")
        else:
            logger.error("❌ Chưa khai báo credentials")
            sys.exit(1)

    def is_youtube_video_id(self, filename):
        """Kiểm tra có phải YouTube video ID không"""
        stem = Path(filename).stem
        if stem.startswith('__') and len(stem) == 13:
            video_id = '-' + stem[2:]
        else:
            video_id = stem
        return bool(re.match(r'^[a-zA-Z0-9_-]{11}$', video_id))

    def get_youtube_video_info(self, video_id):
        """Lấy thông tin video từ YouTube API"""
        if video_id in self.youtube_cache:
            logger.info(f"📋 Sử dụng cache cho video: {video_id}")
            return self.youtube_cache[video_id]
        
        if not self.youtube_api_key or self.youtube_api_key == "myapikey":
            logger.warning("⚠️ Chưa cấu hình YouTube API key, sử dụng metadata mặc định")
            return None
        
        try:
            logger.info(f"🔍 Đang lấy thông tin từ YouTube API cho: {video_id}")
            
            # API endpoint để lấy thông tin video
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                'part': 'snippet,statistics,contentDetails,status',
                'id': video_id,
                'key': self.youtube_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' not in data or len(data['items']) == 0:
                logger.warning(f"⚠️ Không tìm thấy video với ID: {video_id}")
                return None
            
            video_info = data['items'][0]
            
            # Cache kết quả
            self.youtube_cache[video_id] = video_info
            logger.info(f"✅ Đã lấy thông tin YouTube cho: {video_info['snippet']['title']}")
            
            return video_info
            
        except requests.RequestException as e:
            logger.error(f"❌ Lỗi khi gọi YouTube API: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi lấy thông tin YouTube: {str(e)}")
            return None

    def format_duration(self, duration_iso):
        """Chuyển đổi duration ISO 8601 sang định dạng dễ đọc"""
        try:
            # Parse ISO 8601 duration (PT4M13S -> 4:13)
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
            if not match:
                return "Unknown"
            
            hours, minutes, seconds = match.groups()
            hours = int(hours) if hours else 0
            minutes = int(minutes) if minutes else 0
            seconds = int(seconds) if seconds else 0
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        except:
            return "Unknown"

    def format_number(self, num_str):
        """Format số lượng view, like với dấu phẩy"""
        try:
            return f"{int(num_str):,}"
        except:
            return num_str

    def create_youtube_metadata(self, ogg_file, youtube_info):
        """Tạo metadata từ thông tin YouTube cho file OGG"""
        filename = Path(ogg_file).stem
        file_size = os.path.getsize(ogg_file)
        
        if not youtube_info:
            # Fallback metadata nếu không có thông tin YouTube
            return self.create_fallback_metadata(ogg_file)
        
        snippet = youtube_info.get('snippet', {})
        statistics = youtube_info.get('statistics', {})
        content_details = youtube_info.get('contentDetails', {})
        
        # Thông tin cơ bản
        title = snippet.get('title', filename)
        description = snippet.get('description', '')
        channel_title = snippet.get('channelTitle', 'Unknown Channel')
        published_at = snippet.get('publishedAt', '')
        
        # Thông tin thống kê
        view_count = self.format_number(statistics.get('viewCount', '0'))
        like_count = self.format_number(statistics.get('likeCount', '0'))
        comment_count = self.format_number(statistics.get('commentCount', '0'))
        
        # Duration
        duration = self.format_duration(content_details.get('duration', ''))
        
        # Tags
        tags = snippet.get('tags', [])
        if not tags:
            tags = ['youtube', 'audio', 'video']
        
        # Tạo description chi tiết
        detailed_description = []
        detailed_description.append(f"Original Title: {title}")
        detailed_description.append(f"Channel: {channel_title}")
        detailed_description.append(f"Duration: {duration}")
        detailed_description.append(f"Views: {view_count}")
        detailed_description.append(f"Likes: {like_count}")
        if comment_count != '0':
            detailed_description.append(f"Comments: {comment_count}")
        detailed_description.append(f"Published: {published_at}")
        detailed_description.append(f"YouTube URL: https://www.youtube.com/watch?v={filename}")
        detailed_description.append("")
        detailed_description.append("Original Description:")
        if description:
            # Giới hạn description gốc để tránh quá dài
            truncated_desc = description[:1000] + "..." if len(description) > 1000 else description
            detailed_description.append(truncated_desc)
        else:
            detailed_description.append("No description available.")
        detailed_description.append("")
        detailed_description.append("This OGG audio file was extracted and optimized from YouTube video for educational and archival purposes.")
        detailed_description.append(f"Audio format: OGG Vorbis (optimized for voice/speech)")
        detailed_description.append(f"Audio file size: {file_size:,} bytes")
        detailed_description.append(f"Archived on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Tạo subject tags từ YouTube tags và thông tin khác
        subjects = ['youtube-audio', 'ogg-vorbis', 'video-audio', 'audio-archive', 'optimized-audio']
        subjects.extend(tags[:10])  # Giới hạn 10 tags đầu tiên
        subjects.append(channel_title.lower().replace(' ', '-'))
        
        # Loại bỏ ký tự đặc biệt khỏi subjects
        clean_subjects = []
        for subject in subjects:
            clean_subject = re.sub(r'[^a-zA-Z0-9-_\s]', '', str(subject))
            if clean_subject and len(clean_subject) > 1:
                clean_subjects.append(clean_subject[:50])  # Giới hạn độ dài
        
        metadata = {
            'title': f"{title} (OGG Audio)",
            'description': '\n'.join(detailed_description),
            'subject': clean_subjects[:20],  # Giới hạn 20 subjects
            'mediatype': 'audio',
            'collection': 'opensource_audio',
            'language': 'eng',  # Có thể detect language từ video
            'creator': channel_title,
            'date': published_at[:10] if published_at else datetime.now().strftime('%Y-%m-%d'),
            'licenseurl': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'source': f"https://www.youtube.com/watch?v={filename}",
            'identifier-access': 'public',
            'identifier-ark': f"ark:/13960/t{filename}",
            'addeddate': datetime.now().isoformat(),
            'publicdate': datetime.now().isoformat(),
            'uploader': 'YouTube OGG Audio Archive Tool',
            'scanner': 'YouTube OGG Audio Archiver v3.0',
            'scanningcenter': 'youtube-ogg-audio-preservation',
            'sponsorship': 'Educational Archive Project',
            'contributor': 'YouTube OGG Audio Preservation Initiative',
            'coverage': channel_title,
            'duration': duration,
            'youtube-id': filename,
            'youtube-title': title,
            'youtube-channel': channel_title,
            'youtube-views': view_count,
            'youtube-likes': like_count,
            'youtube-published': published_at,
            'audio-source': 'youtube-video-extraction-ogg',
            'audio-format': 'OGG Vorbis',
            'audio-optimization': 'speech-optimized',
            'preservation-note': 'Archived for educational and research purposes in OGG format'
        }
        
        return metadata

    def create_fallback_metadata(self, ogg_file):
        """Tạo metadata mặc định khi không có thông tin YouTube cho file OGG"""
        filename = Path(ogg_file).stem
        file_size = os.path.getsize(ogg_file)
        
        metadata = {
            'title': f"OGG Audio: {filename}",
            'description': f"OGG audio file from YouTube video ID: {filename}\n\nYouTube URL: https://www.youtube.com/watch?v={filename}\n\nThis OGG audio file was extracted and optimized for educational and archival purposes.\nAudio format: OGG Vorbis (speech-optimized)\nFile size: {file_size:,} bytes\nArchived on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'subject': ['youtube-audio', 'ogg-vorbis', 'video-audio', 'audio-archive', 'education', 'optimized-audio'],
            'mediatype': 'audio',
            'collection': 'opensource_audio',
            'language': 'eng',
            'creator': 'Unknown YouTube Channel',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'licenseurl': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
            'source': f"https://www.youtube.com/watch?v={filename}",
            'youtube-id': filename,
            'audio-source': 'youtube-video-extraction-ogg',
            'audio-format': 'OGG Vorbis',
            'audio-optimization': 'speech-optimized'
        }
        
        return metadata

    def get_random_delay(self, base_delay):
        """Tạo delay ngẫu nhiên để tránh pattern detection"""
        return base_delay + random.randint(10, 30)

    def get_ogg_files(self, folder_path):
        """Lấy danh sách tất cả file OGG trong folder"""
        folder_path = Path(folder_path)
        if not folder_path.exists():
            logger.error(f"❌ Folder không tồn tại: {folder_path}")
            return []
        
        ogg_files = []
        for pattern in ['*.ogg', '*.OGG']:
            ogg_files.extend(glob.glob(str(folder_path / pattern)))
        
        logger.info(f"📝 Tìm thấy {len(ogg_files)} file OGG trong {folder_path}")
        return sorted(ogg_files)

    def sanitize_identifier(self, filename):
        """Tạo identifier từ tên file OGG (YouTube video ID) - GIỐNG NHƯ CODE MP3"""
        identifier = Path(filename).stem
        
        # YouTube video ID thường đã clean, chỉ cần kiểm tra cơ bản
        identifier = ''.join(c for c in identifier if c.isalnum() or c in '-_')
        
        if not identifier or len(identifier.strip()) == 0:
            identifier = "untitled"
        
        # Đảm bảo ký tự đầu là chữ/số
        if not identifier[0].isalnum():
            identifier = 'a' + identifier
        
        # Đảm bảo độ dài 5-100 ký tự
        if len(identifier) < 5:
            identifier = identifier + 'audio'[:5-len(identifier)]
        if len(identifier) > 100:
            identifier = identifier[:100]
        
        # ĐÃ BỎ phần thêm suffix '-ogg' để giống như code MP3
        return identifier

    def wait_with_progress(self, seconds, message="Đang chờ"):
        """Hiển thị progress bar khi chờ"""
        logger.info(f"⏳ {message} {seconds} giây...")
        for i in range(seconds):
            remaining = seconds - i
            print(f"\r⏳ Còn lại: {remaining:3d} giây", end='', flush=True)
            time.sleep(1)
        print("\r" + " " * 20 + "\r", end='')

    def handle_spam_error(self, attempt, max_attempts):
        """Xử lý lỗi spam với exponential backoff"""
        if attempt >= max_attempts:
            logger.error("❌ Đã thử tối đa số lần cho phép. Account có thể bị hạn chế.")
            return False
        
        delays = [300, 900, 1800, 3600, 7200]  # 5min, 15min, 30min, 1hour, 2hours
        delay = delays[min(attempt, len(delays)-1)]
        
        logger.warning(f"🚫 Phát hiện spam detection. Đợi {delay//60} phút trước khi thử lại...")
        logger.info("💡 Gợi ý: Hãy kiểm tra email và liên hệ info@archive.org nếu cần")
        
        self.wait_with_progress(delay, f"Chờ để tránh spam detection ({delay//60} phút)")
        return True

    def upload_file(self, ogg_file):
        """Upload một file OGG lên Archive.org với metadata từ YouTube"""
        filename = Path(ogg_file).name
        stem = Path(ogg_file).stem

        # Nếu tên file bắt đầu bằng 2 dấu gạch dưới (đã được đổi tên từ -video_id.ogg)
        if stem.startswith('__') and len(stem) == 13:  # 2 dấu __ + 11 ký tự ID
            video_id = '-' + stem[2:]
        else:
            video_id = stem
        
        logger.info(f"⬆️ Bắt đầu upload: {filename}")
        
        # Kiểm tra xem có phải YouTube video ID không
        if self.is_youtube_video_id(filename):
            logger.info(f"🎬 Phát hiện YouTube video ID: {video_id}")
            youtube_info = self.get_youtube_video_info(video_id)
        else:
            logger.info(f"📁 File thông thường (không phải YouTube ID): {filename}")
            youtube_info = None
        
        # Tạo identifier và metadata
        identifier = self.sanitize_identifier(ogg_file)
        metadata = self.create_youtube_metadata(ogg_file, youtube_info)
        
        logger.info(f"🔑 Sử dụng identifier: {identifier}")
        if youtube_info and 'snippet' in youtube_info:
            logger.info(f"📺 Video: {youtube_info['snippet']['title']}")
            logger.info(f"📺 Channel: {youtube_info['snippet']['channelTitle']}")
        
        # Kiểm tra xem item đã tồn tại chưa
        try:
            item = get_item(identifier)
            if item.exists:
                logger.warning(f"⚠️ Item {identifier} đã tồn tại")
                
                counter = 1
                original_identifier = identifier
                while item.exists and counter <= 10:
                    counter += 1
                    identifier = f"{original_identifier}-{counter}"
                    item = get_item(identifier)
                
                if counter > 10:
                    logger.error(f"❌ Quá nhiều item trùng tên: {filename}")
                    return False
                    
                logger.info(f"🔄 Sử dụng identifier mới: {identifier}")
                
        except Exception as e:
            logger.debug(f"Không thể kiểm tra item existence: {e}")
        
        # Upload với retry logic
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔄 Lần thử {attempt + 1}/{self.max_retries}")
                
                result = upload(
                    identifier,
                    files=[ogg_file],
                    metadata=metadata,
                    verbose=True,
                    verify=True,
                    checksum=True,
                    retries=2,
                    retries_sleep=10
                )
                
                if result and len(result) > 0 and hasattr(result[0], 'status_code'):
                    if result[0].status_code == 200:
                        logger.info(f"✅ Upload thành công: {filename}")
                        logger.info(f"🔗 URL: https://archive.org/details/{identifier}")
                        
                        try:
                            os.remove(ogg_file)
                            logger.info(f"🗑️ Đã xóa file: {filename}")
                        except Exception as e:
                            logger.warning(f"⚠️ Không thể xóa file {filename}: {e}")
                        
                        return True
                    else:
                        logger.warning(f"⚠️ Upload status: {result[0].status_code}")
                
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"❌ Lỗi upload lần {attempt + 1}: {str(e)}")
                
                if "spam" in error_msg or "reduce your request rate" in error_msg:
                    logger.error("🚫 Phát hiện spam detection!")
                    if not self.handle_spam_error(attempt, self.max_retries):
                        return False
                    continue
                    
                elif "rate" in error_msg or "too many" in error_msg:
                    delay = (attempt + 1) * 60
                    logger.warning(f"⏱️ Rate limit, đợi {delay} giây...")
                    self.wait_with_progress(delay, "Chờ rate limit")
                    continue
                    
                elif "connection" in error_msg or "timeout" in error_msg:
                    delay = 30 + (attempt * 10)
                    logger.warning(f"🌐 Lỗi kết nối, đợi {delay} giây...")
                    self.wait_with_progress(delay, "Chờ kết nối")
                    continue
                    
                else:
                    delay = 20 + (attempt * 10)
                    logger.warning(f"🔄 Lỗi không xác định, đợi {delay} giây...")
                    self.wait_with_progress(delay, "Chờ thử lại")
        
        logger.error(f"❌ Upload thất bại sau {self.max_retries} lần thử: {filename}")
        return False

    def upload_folder(self, folder_path):
      """Upload tất cả file OGG trong folder với metadata từ YouTube"""
      ogg_files = self.get_ogg_files(folder_path)
      
      if not ogg_files:
          logger.warning("⚠️ Không tìm thấy file OGG nào để upload")
          return
      
      # Phân loại files
      youtube_files = []
      regular_files = []
      
      for ogg_file in ogg_files:
          if self.is_youtube_video_id(Path(ogg_file).name):
              youtube_files.append(ogg_file)
          else:
              regular_files.append(ogg_file)
      
      logger.info("=" * 60)
      logger.info(f"🚀 Bắt đầu upload {len(ogg_files)} file OGG...")
      logger.info(f"🎬 YouTube videos: {len(youtube_files)} file")
      logger.info(f"📁 Regular files: {len(regular_files)} file")
      logger.info("=" * 60)
      
      success_count = 0
      skipped_count = 0
      failed_count = 0
      
      for i, ogg_file in enumerate(ogg_files, 1):
          logger.info(f"\n[{i}/{len(ogg_files)}] 📝 Đang xử lý: {Path(ogg_file).name}")
          
          # Kiểm tra item có tồn tại trước khi upload không
          identifier = self.sanitize_identifier(ogg_file)
          try:
              item = get_item(identifier)
              if item.exists:
                  logger.warning(f"⚠️ Item {identifier} đã tồn tại - BỎ QUA")
                  logger.info(f"🔗 Item đã có tại: https://archive.org/details/{identifier}")
                  skipped_count += 1
                  continue
          except Exception as e:
              logger.debug(f"Không thể kiểm tra item existence: {e}")
          
          if self.upload_file(ogg_file):
              success_count += 1
          else:
              failed_count += 1
          
          if i < len(ogg_files):
              delay = self.get_random_delay(self.upload_delay_base)
              logger.info(f"⏳ Nghỉ {delay} giây...")
              self.wait_with_progress(delay, "Chờ upload file tiếp theo")
      
      logger.info("\n" + "=" * 60)
      logger.info("📊 KẾT QUẢ CUỐI CÙNG:")
      logger.info(f"✅ Upload thành công: {success_count} file")
      logger.info(f"⏭️ Bỏ qua (đã tồn tại): {skipped_count} file")
      logger.info(f"❌ Thất bại: {failed_count} file")
      logger.info(f"📁 Tổng cộng: {len(ogg_files)} file")
      logger.info("=" * 60)

def main():
    """Hàm main để chạy tool với YouTube integration cho file OGG"""
    logger.info("=" * 60)
    logger.info("🚀 YouTube Archive.org OGG Uploader")
    logger.info("🎬 Tự động lấy metadata từ YouTube API cho file OGG")
    logger.info("=" * 60)
    
    try:
        uploader = YouTubeArchiveUploader()
        
        current_dir = Path(__file__).resolve().parent
        parent_dir = current_dir.parent
        storage_dir = parent_dir / "storage"
        logger.info(f"📂 Sử dụng folder: {storage_dir}")

        uploader.upload_folder(str(storage_dir))
        
    except KeyboardInterrupt:
        logger.info("\n⛔ Đã dừng upload theo yêu cầu người dùng")
    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()