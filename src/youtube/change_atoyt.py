import re
import os

def convert_archive_to_youtube(archive_url):
    """
    Chuyển đổi URL từ archive.org sang YouTube
    
    Args:
        archive_url (str): URL từ archive.org
        
    Returns:
        str: URL YouTube tương ứng
    """
    # Pattern để match URL archive.org
    pattern = r'https://archive\.org/download/([^/]+)/[^/]+\.ogg'
    match = re.match(pattern, archive_url.strip())
    
    if not match:
        return None
    
    folder_name = match.group(1)
    
    # Xử lý các trường hợp đặc biệt
    if folder_name.startswith('a_'):
        # Trường hợp như a__R0fPJQr0qo -> -R0fPJQr0qo
        if folder_name.startswith('a__'):
            video_id = '-' + folder_name[3:]  # Bỏ 'a__' và thêm '-'
        # Trường hợp như a_wDIe0XEmwI -> _wDIe0XEmwI
        elif folder_name.startswith('a_'):
            video_id = '_' + folder_name[2:]  # Bỏ 'a_' và thêm '_'
    else:
        # Trường hợp bình thường như 0Wwn5IEqFcg
        video_id = folder_name
    
    return f"https://www.youtube.com/watch?v={video_id}"

def main():
    """
    Hàm chính để đọc file, chuyển đổi link và ghi ra file mới
    """
    input_file = 'broken_links.txt'
    output_file = 'yt_broken_links.txt'
    
    # Kiểm tra file input có tồn tại không
    if not os.path.exists(input_file):
        print(f"Lỗi: Không tìm thấy file '{input_file}'")
        print("Vui lòng tạo file 'broken_links.txt' và thêm các link archive.org vào đó.")
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
                youtube_url = convert_archive_to_youtube(line)
                if youtube_url:
                    converted_links.append(youtube_url)
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
    
    except FileNotFoundError:
        print(f"Lỗi: Không thể đọc file '{input_file}'")
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()