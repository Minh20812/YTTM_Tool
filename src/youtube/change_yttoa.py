import re
import os

def convert_youtube_to_archive(youtube_url):
    """
    Chuyển đổi URL từ YouTube sang archive.org
    
    Args:
        youtube_url (str): URL từ YouTube
        
    Returns:
        str: URL archive.org tương ứng
    """
    # Pattern để match YouTube URL
    patterns = [
        r'https://www\.youtube\.com/watch\?v=([^&\s]+)',
        r'https://youtu\.be/([^?&\s]+)',
        r'youtube\.com/watch\?v=([^&\s]+)',
        r'youtu\.be/([^?&\s]+)'
    ]
    
    video_id = None
    for pattern in patterns:
        match = re.search(pattern, youtube_url.strip())
        if match:
            video_id = match.group(1)
            break
    
    if not video_id:
        return None
    
    # Xử lý các trường hợp đặc biệt
    if video_id.startswith('-'):
        # Trường hợp -R0fPJQr0qo -> a__R0fPJQr0qo
        folder_name = 'a_' + video_id.replace('-', '_')
        file_name = video_id.replace('-', '_') + '.ogg'
    elif video_id.startswith('_'):
        # Trường hợp _wDIe0XEmwI -> a_wDIe0XEmwI
        folder_name = 'a' + video_id
        file_name = video_id + '.ogg'
    else:
        # Trường hợp bình thường 0Wwn5IEqFcg
        folder_name = video_id
        file_name = video_id + '.ogg'
    
    return f"https://archive.org/download/{folder_name}/{file_name}"

def main():
    """
    Hàm chính để đọc file, chuyển đổi link và ghi ra file mới
    """
    input_file = 'link_youtube_recent_2days.txt'
    output_file = 'archive_links.txt'
    
    # Kiểm tra file input có tồn tại không
    if not os.path.exists(input_file):
        print(f"Lỗi: Không tìm thấy file '{input_file}'")
        print("Vui lòng tạo file 'link_youtube_recent_2days.txt' và thêm các link YouTube vào đó.")
        return
    
    converted_links = []
    skipped_links = []
    
    try:
        # Đọc file input
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"Đang xử lý {len(lines)} link...")
        
        # Chuyển đổi từng link
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line:  # Bỏ qua dòng trống
                archive_url = convert_youtube_to_archive(line)
                if archive_url:
                    converted_links.append(archive_url)
                    print(f"[{i}] ✓ Chuyển đổi thành công: {line[:50]}...")
                else:
                    skipped_links.append(line)
                    print(f"[{i}] ✗ Không thể chuyển đổi: {line}")
        
        # Ghi file output
        with open(output_file, 'w', encoding='utf-8') as f:
            for link in converted_links:
                f.write(link + '\n')
        
        # Thống kê kết quả
        print(f"\n=== KẾT QUẢ ===")
        print(f"Tổng số link: {len(lines)}")
        print(f"Chuyển đổi thành công: {len(converted_links)}")
        print(f"Không thể chuyển đổi: {len(skipped_links)}")
        print(f"File kết quả: '{output_file}'")
        
        if skipped_links:
            print(f"\nCác link không thể chuyển đổi:")
            for link in skipped_links:
                print(f"  - {link}")
        
        # Hiển thị một vài ví dụ chuyển đổi
        if converted_links:
            print(f"\nVí dụ chuyển đổi:")
            for i, link in enumerate(converted_links[:3]):
                print(f"  {i+1}. {link}")
    
    except FileNotFoundError:
        print(f"Lỗi: Không thể đọc file '{input_file}'")
    except Exception as e:
        print(f"Lỗi: {str(e)}")

def test_conversion():
    """
    Hàm test để kiểm tra logic chuyển đổi
    """
    test_cases = [
        "https://www.youtube.com/watch?v=0Wwn5IEqFcg",
        "https://www.youtube.com/watch?v=-R0fPJQr0qo", 
        "https://www.youtube.com/watch?v=_wDIe0XEmwI",
        "https://youtu.be/0Wwn5IEqFcg",
        "https://youtu.be/-R0fPJQr0qo",
        "https://youtu.be/_wDIe0XEmwI"
    ]
    
    print("=== TEST CHUYỂN ĐỔI ===")
    for url in test_cases:
        result = convert_youtube_to_archive(url)
        print(f"IN:  {url}")
        print(f"OUT: {result}")
        print()

if __name__ == "__main__":
    # Uncomment dòng dưới để test logic chuyển đổi
    # test_conversion()
    
    main()