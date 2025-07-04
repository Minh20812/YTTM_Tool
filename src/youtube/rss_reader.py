import feedparser
import datetime
import requests
from urllib.parse import parse_qs, urlparse
import re

class YouTubeRSSReader:
    def __init__(self):
        self.channels = []
        self.new_videos = []
        self.skip_shorts = True
        self.cutoff_hours = 36
    
    def set_skip_shorts(self, skip=True):
        """Thiết lập có bỏ qua Shorts hay không"""
        self.skip_shorts = skip
    
    def set_cutoff_hours(self, hours=36):
        """Thiết lập thời gian quét video (mặc định 36 giờ)"""
        self.cutoff_hours = hours
    
    def add_channel(self, channel_id=None, channel_url=None, channel_name=None):
        """Thêm kênh YouTube để theo dõi"""
        if channel_url and not channel_id:
            # Trích xuất channel ID từ URL
            if '/channel/' in channel_url:
                channel_id = channel_url.split('/channel/')[1].split('/')[0]
            elif '/c/' in channel_url or '/@' in channel_url:
                print(f"⚠️ Cần channel ID cho {channel_url}. Vui lòng sử dụng URL dạng /channel/")
                return False
        
        if channel_id:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            channel_main_url = f"https://www.youtube.com/channel/{channel_id}"
            
            self.channels.append({
                'id': channel_id,
                'name': channel_name or channel_id,
                'rss_url': rss_url,
                'channel_url': channel_main_url
            })
            print(f"✅ Đã thêm kênh: {channel_name or channel_id}")
            return True
        
        print(f"❌ Không thể thêm kênh: thiếu channel_id")
        return False
    
    def add_channels_from_list(self, channels_list):
        """Thêm nhiều kênh từ danh sách"""
        for channel_info in channels_list:
            if isinstance(channel_info, tuple) and len(channel_info) == 2:
                channel_id, channel_name = channel_info
                self.add_channel(channel_id=channel_id, channel_name=channel_name)
            elif isinstance(channel_info, dict):
                self.add_channel(**channel_info)
    
    def is_youtube_short(self, entry):
        """Kiểm tra xem video có phải YouTube Shorts không"""
        # Kiểm tra URL
        if '/shorts/' in entry.link:
            return True
        
        # Kiểm tra title
        title = entry.title.lower()
        if title.startswith('#') or '#shorts' in title or '#short' in title:
            return True
        
        # Kiểm tra description
        description = entry.get('summary', '').lower()
        if '#shorts' in description or '#short' in description:
            return True
        
        return False
    
    def normalize_youtube_url(self, url):
        """Chuẩn hóa URL YouTube"""
        if not url:
            return url
        
        # Trích xuất video ID
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
    
    def fetch_recent_videos(self, hours=None):
        """Lấy video mới trong khoảng thời gian chỉ định"""
        if hours is None:
            hours = self.cutoff_hours
            
        cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
        self.new_videos = []
        
        print(f"🔍 Quét video mới trong {hours} giờ qua (sau {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
        for channel in self.channels:
            print(f"\n📺 Đang kiểm tra kênh: {channel['name']}")
            
            try:
                # Lấy RSS feed
                feed = feedparser.parse(channel['rss_url'])
                
                if feed.bozo:
                    print(f"⚠️ Lỗi khi đọc RSS feed cho {channel['name']}: {feed.bozo_exception}")
                    continue
                
                channel_videos = 0
                
                # Kiểm tra từng video
                for entry in feed.entries:
                    # Chuyển đổi thời gian published
                    published_time = datetime.datetime(*entry.published_parsed[:6])
                    
                    # Chỉ lấy video mới trong khoảng thời gian chỉ định
                    if published_time > cutoff_time:
                        # Kiểm tra xem có phải YouTube Shorts không
                        is_short = self.is_youtube_short(entry)
                        
                        if not (self.skip_shorts and is_short):
                            # Chuẩn hóa URL
                            normalized_url = self.normalize_youtube_url(entry.link)
                            
                            # Trích xuất video ID
                            video_id = ''
                            if 'v=' in entry.link:
                                video_id = entry.link.split('v=')[1].split('&')[0]
                            
                            video_info = {
                                'title': entry.title,
                                'url': normalized_url,
                                'original_url': entry.link,
                                'channel': channel['name'],
                                'channel_url': channel['channel_url'],
                                'upload_date': published_time.strftime('%Y-%m-%d'),
                                'published_datetime': published_time,
                                'description': entry.get('summary', ''),
                                'video_id': video_id,
                                'is_short': is_short
                            }
                            
                            self.new_videos.append(video_info)
                            channel_videos += 1
                            
                            video_type = "Shorts" if is_short else "Video"
                            print(f"   ✅ {video_type}: {entry.title}")
                        else:
                            print(f"   ⏭️ Bỏ qua Shorts: {entry.title}")
                
                print(f"   📊 Tìm thấy {channel_videos} video mới từ {channel['name']}")
                
            except Exception as e:
                print(f"❌ Lỗi khi xử lý kênh {channel['name']}: {str(e)}")
        
        # Sắp xếp video theo thời gian mới nhất
        self.new_videos.sort(key=lambda x: x['published_datetime'], reverse=True)
        
        print(f"\n🎯 Tổng cộng tìm thấy {len(self.new_videos)} video mới")
        return self.new_videos
    
    def get_video_list_for_processing(self):
        """Trả về danh sách video theo format mà script 1 cần"""
        return self.new_videos
    
    def print_summary(self):
        """In tóm tắt kết quả"""
        if not self.new_videos:
            print("\n❌ Không có video mới nào.")
            return
        
        print(f"\n📋 TỔNG KẾT:")
        print(f"   📺 Tổng số video: {len(self.new_videos)}")
        
        # Thống kê theo kênh
        channel_stats = {}
        for video in self.new_videos:
            channel = video['channel']
            if channel not in channel_stats:
                channel_stats[channel] = 0
            channel_stats[channel] += 1
        
        print(f"   📊 Phân bố theo kênh:")
        for channel, count in sorted(channel_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"      • {channel}: {count} video")
        
        # Thống kê theo loại
        shorts_count = sum(1 for v in self.new_videos if v.get('is_short', False))
        regular_count = len(self.new_videos) - shorts_count
        
        print(f"   📹 Loại video:")
        print(f"      • Video thường: {regular_count}")
        print(f"      • Shorts: {shorts_count}")

# Hàm chính để tích hợp vào script 1
def get_latest_videos_from_rss(return_links=True, hours=36, skip_shorts=True):
    """
    Hàm chính để lấy danh sách video mới từ RSS feeds
    Thay thế cho get_latest_video2.main()
    """
    
    # Danh sách các kênh YouTube
    channels_to_monitor = [
        ("UCLXo7UDZvByw2ixzpQCufnA", "Vox"),
        ("UCvJJ_dzjViJCoLf5uKUTwoA", "CNBC"),
        ("UCHnyfMqiRRG1u-2MsSQLbXA", "Veritasium"),
        ("UCpVm7bg6pXKo1Pr6k5kxG9A", "NatGeo"),
        ("UCK7tptUDHh-RYDsdxO1-5QQ", "WSJ"),
        ("UCZYTClx2T1of7BRZ86-8fow", "SciShow"),
        ("UCcyq283he07B7_KUX07mmtA", "Business Insider"),
        ("UCwmZiChSryoWQCZMIQezgTg", "BBC Earth"),
        ("UCODHrzPMGbNv67e84WDZhQQ", "Fern"),
        ("UCsBjURrPoezykLs9EqgamOA", "Fireship"),
        ("UCtRFmSyL4fSLQkn-wMqlmdA", "History of the Universe"),
        ("UCKWaEZ-_VweaEx1j62do_vQ", "IBM Technology"),
        ("UCDPk9MG2RexnOMGTD-YnSnA", "Nat Geo Animals"),
        ("UCmGSJVG3mCRXVOP4yZrU1Dw", "Johnny Harris"),
        ("UC6ktP3PLU5sAJxN9Rb0TALg", "Mike Shake"),
        ("UCtYKe7-XbaDjpUwcU5x0bLg", "Neo"),
        ("UCoxcjq-8xIDTYp3uz647V5A", "Numberphile"),
        ("UC7_gcs09iThXybpVgjHZ_7g", "PBS Space Time"),
        ("UCQSpnDG3YsFNf5-qHocF-WQ", "ThioJoe"),
        ("UCsooa4yRKGN_zEE8iknghZA", "TED-Ed"),
        ("UCAuUUnT6oDeKwE6v1NGQxug", "TED"),
        ("UCEIwxahdLz7bap-VDs9h35A", "Steve Mould"),
        ("UC1yNl2E66ZzKApQdRuTQ4tw", "Sabine Hossenfelder"),
        ("UCTpmmkp1E4nmZqWPS-dl5bg", "Quanta Science"),
        ("UCgNg3vwj3xt7QOrcIDaHdFg", "PolyMatter"),
        ("UCMOqf8ab-42UUQIdVoKwjlQ", "Practical Engineering"),
        ("UC513PdAP2-jWkJunTh5kXRw", "CrunchLabs"),
        ("UCW39zufHfsuGgpLviKh297Q", "DW Documentary"),
        ("UCHaHD477h-FeBbVh9Sh7syA", "BBC Learning English"),
        ("UCvK4bOhULCpmLabd2pDMtnA", "Yes Theory"),
        ("UC9RM-iSvTu1uPJb8X5yp3EQ", "Wendover Productions"),
        ("UC4JX40jDee_tINbkjycV4Sg", "Tech With Tim"),
        ("UC6biysICWOJ-C3P4Tyeggzg", "Low Level"),
    ]
    
    # Tạo RSS reader
    reader = YouTubeRSSReader()
    reader.set_skip_shorts(skip_shorts)
    reader.set_cutoff_hours(hours)
    
    # Thêm các kênh
    reader.add_channels_from_list(channels_to_monitor)
    
    # Lấy video mới
    videos = reader.fetch_recent_videos(hours)
    
    # In tóm tắt
    reader.print_summary()
    
    if return_links:
        return videos
    else:
        return len(videos)

# Hàm để test độc lập
def main():
    """Hàm test chính"""
    print("🚀 Bắt đầu quét video mới từ RSS feeds...")
    
    videos = get_latest_videos_from_rss(
        return_links=True,
        hours=36,
        skip_shorts=True
    )
    
    if videos:
        print(f"\n📝 Danh sách {len(videos)} video mới:")
        print("=" * 80)
        
        for i, video in enumerate(videos, 1):
            print(f"{i}. [{video['channel']}] {video['title']}")
            print(f"   🔗 {video['url']}")
            print(f"   📅 {video['upload_date']}")
            print("-" * 80)
    else:
        print("\n❌ Không tìm thấy video mới nào.")

if __name__ == "__main__":
    main()


# import feedparser
# import datetime
# import requests
# from urllib.parse import parse_qs, urlparse
# import re

# class YouTubeRSSReader:
#     def __init__(self):
#         self.channels = []
#         self.new_videos = []
#         self.skip_shorts = True
#         self.cutoff_hours = 36
    
#     def set_skip_shorts(self, skip=True):
#         """Thiết lập có bỏ qua Shorts hay không"""
#         self.skip_shorts = skip
    
#     def set_cutoff_hours(self, hours=36):
#         """Thiết lập thời gian quét video (mặc định 36 giờ)"""
#         self.cutoff_hours = hours
    
#     def add_channel(self, channel_id=None, channel_url=None, channel_name=None):
#         """Thêm kênh YouTube để theo dõi"""
#         if channel_url and not channel_id:
#             # Trích xuất channel ID từ URL
#             if '/channel/' in channel_url:
#                 channel_id = channel_url.split('/channel/')[1].split('/')[0]
#             elif '/c/' in channel_url or '/@' in channel_url:
#                 print(f"⚠️ Cần channel ID cho {channel_url}. Vui lòng sử dụng URL dạng /channel/")
#                 return False
        
#         if channel_id:
#             rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
#             channel_main_url = f"https://www.youtube.com/channel/{channel_id}"
            
#             self.channels.append({
#                 'id': channel_id,
#                 'name': channel_name or channel_id,
#                 'rss_url': rss_url,
#                 'channel_url': channel_main_url
#             })
#             print(f"✅ Đã thêm kênh: {channel_name or channel_id}")
#             return True
        
#         print(f"❌ Không thể thêm kênh: thiếu channel_id")
#         return False
    
#     def add_channels_from_list(self, channels_list):
#         """Thêm nhiều kênh từ danh sách"""
#         for channel_info in channels_list:
#             if isinstance(channel_info, tuple) and len(channel_info) == 2:
#                 channel_id, channel_name = channel_info
#                 self.add_channel(channel_id=channel_id, channel_name=channel_name)
#             elif isinstance(channel_info, dict):
#                 self.add_channel(**channel_info)
    
#     def is_youtube_short(self, entry):
#         """Kiểm tra xem video có phải YouTube Shorts không"""
#         # Kiểm tra URL
#         if '/shorts/' in entry.link:
#             return True
        
#         # Kiểm tra title
#         title = entry.title.lower()
#         if title.startswith('#') or '#shorts' in title or '#short' in title:
#             return True
        
#         # Kiểm tra description
#         description = entry.get('summary', '').lower()
#         if '#shorts' in description or '#short' in description:
#             return True
        
#         return False
    
#     def normalize_youtube_url(self, url):
#         """Chuẩn hóa URL YouTube"""
#         if not url:
#             return url
        
#         # Trích xuất video ID
#         patterns = [
#             r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
#             r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})',
#         ]
        
#         for pattern in patterns:
#             match = re.search(pattern, url)
#             if match:
#                 video_id = match.group(1)
#                 return f"https://www.youtube.com/watch?v={video_id}"
        
#         return url
    
#     def fetch_recent_videos(self, hours=None):
#         """Lấy video mới trong khoảng thời gian chỉ định"""
#         if hours is None:
#             hours = self.cutoff_hours
            
#         cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=hours)
#         self.new_videos = []
        
#         print(f"🔍 Quét video mới trong {hours} giờ qua (sau {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
        
#         for channel in self.channels:
#             print(f"\n📺 Đang kiểm tra kênh: {channel['name']}")
            
#             try:
#                 # Lấy RSS feed
#                 feed = feedparser.parse(channel['rss_url'])
                
#                 if feed.bozo:
#                     print(f"⚠️ Lỗi khi đọc RSS feed cho {channel['name']}: {feed.bozo_exception}")
#                     continue
                
#                 channel_videos = 0
                
#                 # Kiểm tra từng video
#                 for entry in feed.entries:
#                     # Chuyển đổi thời gian published
#                     published_time = datetime.datetime(*entry.published_parsed[:6])
                    
#                     # Chỉ lấy video mới trong khoảng thời gian chỉ định
#                     if published_time > cutoff_time:
#                         # Kiểm tra xem có phải YouTube Shorts không
#                         is_short = self.is_youtube_short(entry)
                        
#                         if not (self.skip_shorts and is_short):
#                             # Chuẩn hóa URL
#                             normalized_url = self.normalize_youtube_url(entry.link)
                            
#                             video_info = {
#                                 'title': entry.title,
#                                 'url': normalized_url,
#                                 'original_url': entry.link,
#                                 'channel': channel['name'],
#                                 'channel_url': channel['channel_url'],
#                                 'upload_date': published_time.strftime('%Y-%m-%d'),
#                                 'published_datetime': published_time,
#                                 'description': entry.get('summary', ''),
#                                 'video_id': entry.link.split('v=')[1].split('&')[0] if 'v=' in entry.link else '',
#                                 'is_short': is_short
#                             }
                            
#                             self.new_videos.append(video_info)
#                             channel_videos += 1
                            
#                             video_type = "Shorts" if is_short else "Video"
#                             print(f"   ✅ {video_type}: {entry.title}")
#                         else:
#                             print(f"   ⏭️ Bỏ qua Shorts: {entry.title}")
                
#                 print(f"   📊 Tìm thấy {channel_videos} video mới từ {channel['name']}")
                
#             except Exception as e:
#                 print(f"❌ Lỗi khi xử lý kênh {channel['name']}: {str(e)}")
        
#         # Sắp xếp video theo thời gian mới nhất
#         self.new_videos.sort(key=lambda x: x['published_datetime'], reverse=True)
        
#         print(f"\n🎯 Tổng cộng tìm thấy {len(self.new_videos)} video mới")
#         return self.new_videos
    
#     def get_video_list_for_processing(self):
#         """Trả về danh sách video theo format mà script 1 cần"""
#         return self.new_videos
    
#     def print_summary(self):
#         """In tóm tắt kết quả"""
#         if not self.new_videos:
#             print("\n❌ Không có video mới nào.")
#             return
        
#         print(f"\n📋 TỔNG KẾT:")
#         print(f"   📺 Tổng số video: {len(self.new_videos)}")
        
#         # Thống kê theo kênh
#         channel_stats = {}
#         for video in self.new_videos:
#             channel = video['channel']
#             if channel not in channel_stats:
#                 channel_stats[channel] = 0
#             channel_stats[channel] += 1
        
#         print(f"   📊 Phân bố theo kênh:")
#         for channel, count in sorted(channel_stats.items(), key=lambda x: x[1], reverse=True):
#             print(f"      • {channel}: {count} video")
        
#         # Thống kê theo loại
#         shorts_count = sum(1 for v in self.new_videos if v.get('is_short', False))
#         regular_count = len(self.new_videos) - shorts_count
        
#         print(f"   📹 Loại video:")
#         print(f"      • Video thường: {regular_count}")
#         print(f"      • Shorts: {shorts_count}")

# # Hàm chính để tích hợp vào script 1
# def get_latest_videos_from_rss(return_links=True, hours=36, skip_shorts=True):
#     """
#     Hàm chính để lấy danh sách video mới từ RSS feeds
#     Thay thế cho get_latest_video2.main()
#     """
    
#     # Danh sách các kênh YouTube
#     channels_to_monitor = [
#         ("UCLXo7UDZvByw2ixzpQCufnA", "Vox"),
#         ("UCvJJ_dzjViJCoLf5uKUTwoA", "CNBC"),
#         ("UCHnyfMqiRRG1u-2MsSQLbXA", "Veritasium"),
#         ("UCpVm7bg6pXKo1Pr6k5kxG9A", "NatGeo"),
#         ("UCK7tptUDHh-RYDsdxO1-5QQ", "WSJ"),
#         ("UCZYTClx2T1of7BRZ86-8fow", "SciShow"),
#         ("UCcyq283he07B7_KUX07mmtA", "Business Insider"),
#         ("UCwmZiChSryoWQCZMIQezgTg", "BBC Earth"),
#         ("UCODHrzPMGbNv67e84WDZhQQ", "Fern"),
#         ("UCsBjURrPoezykLs9EqgamOA", "Fireship"),
#         ("UCtRFmSyL4fSLQkn-wMqlmdA", "History of the Universe"),
#         ("UCKWaEZ-_VweaEx1j62do_vQ", "IBM Technology"),
#         ("UCDPk9MG2RexnOMGTD-YnSnA", "Nat Geo Animals"),
#         ("UCmGSJVG3mCRXVOP4yZrU1Dw", "Johnny Harris"),
#         ("UC6ktP3PLU5sAJxN9Rb0TALg", "Mike Shake"),
#         ("UCtYKe7-XbaDjpUwcU5x0bLg", "Neo"),
#         ("UCoxcjq-8xIDTYp3uz647V5A", "Numberphile"),
#         ("UC7_gcs09iThXybpVgjHZ_7g", "PBS Space Time"),
#         ("UCQSpnDG3YsFNf5-qHocF-WQ", "ThioJoe"),
#         ("UCsooa4yRKGN_zEE8iknghZA", "TED-Ed"),
#         ("UCAuUUnT6oDeKwE6v1NGQxug", "TED"),
#         ("UCEIwxahdLz7bap-VDs9h35A", "Steve Mould"),
#         ("UC1yNl2E66ZzKApQdRuTQ4tw", "Sabine Hossenfelder"),
#         ("UCTpmmkp1E4nmZqWPS-dl5bg", "Quanta Science"),
#         ("UCgNg3vwj3xt7QOrcIDaHdFg", "PolyMatter"),
#         ("UCMOqf8ab-42UUQIdVoKwjlQ", "Practical Engineering"),
#         ("UC513PdAP2-jWkJunTh5kXRw", "CrunchLabs"),
#         ("UCW39zufHfsuGgpLviKh297Q", "DW Documentary"),
#         ("UCHaHD477h-FeBbVh9Sh7syA", "BBC Learning English"),
#         ("UCvK4bOhULCpmLabd2pDMtnA", "Yes Theory"),
#         ("UC9RM-iSvTu1uPJb8X5yp3EQ", "Wendover Productions"),
#     ]
    
#     # Tạo RSS reader
#     reader = YouTubeRSSReader()
#     reader.set_skip_shorts(skip_shorts)
#     reader.set_cutoff_hours(hours)
    
#     # Thêm các kênh
#     reader.add_channels_from_list(channels_to_monitor)
    
#     # Lấy video mới
#     videos = reader.fetch_recent_videos(hours)
    
#     # In tóm tắt
#     reader.print_summary()
    
#     if return_links:
#         return videos
#     else:
#         return len(videos)

# # Hàm để test độc lập
# def main():
#     """Hàm test chính"""
#     print("🚀 Bắt đầu quét video mới từ RSS feeds...")
    
#     videos = get_latest_videos_from_rss(
#         return_links=True,
#         hours=36,
#         skip_shorts=True
#     )
    
#     if videos:
#         print(f"\n📝 Danh sách {len(videos)} video mới:")
#         print("=" * 80)
        
#         for i, video in enumerate(videos, 1):
#             print(f"{i}. [{video['channel']}] {video['title']}")
#             print(f"   🔗 {video['url']}")
#             print(f"   📅 {video['upload_date']}")
#             print("-" * 80)
#     else:
#         print("\n❌ Không tìm thấy video mới nào.")

# if __name__ == "__main__":
#     main()