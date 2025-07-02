import re
import os
import glob
from pathlib import Path

def parse_srt(content):
    """Parse nội dung SRT thành danh sách các subtitle"""
    subtitles = []
    blocks = content.strip().split('\n\n')
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                # Lấy số thứ tự
                number = int(lines[0])
                
                # Lấy timestamp
                timestamp = lines[1]
                
                # Lấy nội dung (có thể nhiều dòng)
                text = '\n'.join(lines[2:])
                
                subtitles.append({
                    'number': number,
                    'timestamp': timestamp,
                    'text': text
                })
            except ValueError:
                continue
    
    return subtitles

def count_words(text):
    """Đếm số từ trong text"""
    # Loại bỏ các ký tự đặc biệt và đếm từ
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def parse_timestamp(timestamp):
    """Parse timestamp thành start và end time"""
    start_str, end_str = timestamp.split(' --> ')
    return start_str.strip(), end_str.strip()

def ends_with_punctuation(text):
    """Kiểm tra xem text có kết thúc bằng dấu câu không"""
    return text.strip().endswith(('.', ',', '?', '!'))

def merge_subtitles(subtitles):
    """Gộp các subtitle theo logic yêu cầu"""
    if not subtitles:
        return []
    
    merged = []
    current_group = []
    current_word_count = 0
    
    for subtitle in subtitles:
        text = subtitle['text']
        word_count = count_words(text)
        
        # Nếu subtitle hiện tại đã >= 20 từ, giữ nguyên
        if word_count >= 20:
            # Xử lý group hiện tại trước (nếu có)
            if current_group:
                merged.append(create_merged_subtitle(current_group))
                current_group = []
                current_word_count = 0
            
            # Thêm subtitle hiện tại vào merged
            merged.append(subtitle)
            continue
        
        # Kiểm tra xem có thể thêm vào group hiện tại không
        if current_word_count + word_count <= 20:
            current_group.append(subtitle)
            current_word_count += word_count
            
            # Nếu kết thúc bằng dấu câu, ưu tiên kết thúc group tại đây
            if ends_with_punctuation(text):
                merged.append(create_merged_subtitle(current_group))
                current_group = []
                current_word_count = 0
        else:
            # Không thể thêm vào group hiện tại
            if current_group:
                merged.append(create_merged_subtitle(current_group))
            
            # Bắt đầu group mới
            current_group = [subtitle]
            current_word_count = word_count
    
    # Xử lý group cuối cùng
    if current_group:
        merged.append(create_merged_subtitle(current_group))
    
    return merged

def create_merged_subtitle(group):
    """Tạo subtitle mới từ một group các subtitle"""
    if len(group) == 1:
        return group[0]
    
    # Lấy timestamp bắt đầu từ subtitle đầu tiên
    start_time, _ = parse_timestamp(group[0]['timestamp'])
    
    # Lấy timestamp kết thúc từ subtitle cuối cùng
    _, end_time = parse_timestamp(group[-1]['timestamp'])
    
    # Gộp text
    merged_text = ' '.join(sub['text'].replace('\n', ' ') for sub in group)
    
    return {
        'number': group[0]['number'],  # Sẽ được đánh số lại sau
        'timestamp': f"{start_time} --> {end_time}",
        'text': merged_text
    }

def write_srt(subtitles, output_file):
    """Ghi danh sách subtitle ra file SRT"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, subtitle in enumerate(subtitles, 1):
            f.write(f"{i}\n")
            f.write(f"{subtitle['timestamp']}\n")
            f.write(f"{subtitle['text']}\n\n")

def process_file(input_file):
    """Xử lý một file SRT"""
    # Đọc file input
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Thử với encoding khác nếu utf-8 không work
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    
    # Parse subtitle
    subtitles = parse_srt(content)
    
    if not subtitles:
        print(f"Không thể parse file {input_file}")
        return False
    
    print(f"File {input_file}: {len(subtitles)} subtitle gốc")
    
    # Gộp subtitle
    merged_subtitles = merge_subtitles(subtitles)
    
    print(f"Sau khi gộp: {len(merged_subtitles)} subtitle")
    
    # Tạo tên file output
    output_file = input_file.replace('.merge2.srt', '.merge3.srt')
    
    try:
        # Ghi file output
        write_srt(merged_subtitles, output_file)
        print(f"Đã tạo file: {output_file}")
        
        # Xóa file gốc sau khi tạo thành công file mới
        os.remove(input_file)
        print(f"Đã xóa file gốc: {input_file}")
        
        print("-" * 50)
        return True
        
    except Exception as e:
        print(f"Lỗi khi ghi file {output_file}: {e}")
        return False

def main():
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"
    input_files = list(storage_dir.glob("*.merge2.srt"))
    if not input_files:
        print(f"Không tìm thấy file .merge2.srt nào trong thư mục: {storage_dir}")
        return
    print(f"Tìm thấy {len(input_files)} file(s) để xử lý:")
    for file in input_files:
        print(f"- {file.name}")
    print("-" * 50)
    success_count = 0
    for input_file in input_files:
        if process_file(input_file):
            success_count += 1
    print(f"Hoàn thành xử lý {success_count}/{len(input_files)} file(s)!")

if __name__ == "__main__":
    main()

# import re
# import os
# import glob

# def parse_srt(content):
#     """Parse nội dung SRT thành danh sách các subtitle"""
#     subtitles = []
#     blocks = content.strip().split('\n\n')
    
#     for block in blocks:
#         lines = block.strip().split('\n')
#         if len(lines) >= 3:
#             try:
#                 # Lấy số thứ tự
#                 number = int(lines[0])
                
#                 # Lấy timestamp
#                 timestamp = lines[1]
                
#                 # Lấy nội dung (có thể nhiều dòng)
#                 text = '\n'.join(lines[2:])
                
#                 subtitles.append({
#                     'number': number,
#                     'timestamp': timestamp,
#                     'text': text
#                 })
#             except ValueError:
#                 continue
    
#     return subtitles

# def count_words(text):
#     """Đếm số từ trong text"""
#     # Loại bỏ các ký tự đặc biệt và đếm từ
#     words = re.findall(r'\b\w+\b', text)
#     return len(words)

# def parse_timestamp(timestamp):
#     """Parse timestamp thành start và end time"""
#     start_str, end_str = timestamp.split(' --> ')
#     return start_str.strip(), end_str.strip()

# def ends_with_punctuation(text):
#     """Kiểm tra xem text có kết thúc bằng dấu câu không"""
#     return text.strip().endswith(('.', ',', '?', '!'))

# def merge_subtitles(subtitles):
#     """Gộp các subtitle theo logic yêu cầu"""
#     if not subtitles:
#         return []
    
#     merged = []
#     current_group = []
#     current_word_count = 0
    
#     for subtitle in subtitles:
#         text = subtitle['text']
#         word_count = count_words(text)
        
#         # Nếu subtitle hiện tại đã >= 20 từ, giữ nguyên
#         if word_count >= 20:
#             # Xử lý group hiện tại trước (nếu có)
#             if current_group:
#                 merged.append(create_merged_subtitle(current_group))
#                 current_group = []
#                 current_word_count = 0
            
#             # Thêm subtitle hiện tại vào merged
#             merged.append(subtitle)
#             continue
        
#         # Kiểm tra xem có thể thêm vào group hiện tại không
#         if current_word_count + word_count <= 20:
#             current_group.append(subtitle)
#             current_word_count += word_count
            
#             # Nếu kết thúc bằng dấu câu, ưu tiên kết thúc group tại đây
#             if ends_with_punctuation(text):
#                 merged.append(create_merged_subtitle(current_group))
#                 current_group = []
#                 current_word_count = 0
#         else:
#             # Không thể thêm vào group hiện tại
#             if current_group:
#                 merged.append(create_merged_subtitle(current_group))
            
#             # Bắt đầu group mới
#             current_group = [subtitle]
#             current_word_count = word_count
    
#     # Xử lý group cuối cùng
#     if current_group:
#         merged.append(create_merged_subtitle(current_group))
    
#     return merged

# def create_merged_subtitle(group):
#     """Tạo subtitle mới từ một group các subtitle"""
#     if len(group) == 1:
#         return group[0]
    
#     # Lấy timestamp bắt đầu từ subtitle đầu tiên
#     start_time, _ = parse_timestamp(group[0]['timestamp'])
    
#     # Lấy timestamp kết thúc từ subtitle cuối cùng
#     _, end_time = parse_timestamp(group[-1]['timestamp'])
    
#     # Gộp text
#     merged_text = ' '.join(sub['text'].replace('\n', ' ') for sub in group)
    
#     return {
#         'number': group[0]['number'],  # Sẽ được đánh số lại sau
#         'timestamp': f"{start_time} --> {end_time}",
#         'text': merged_text
#     }

# def write_srt(subtitles, output_file):
#     """Ghi danh sách subtitle ra file SRT"""
#     with open(output_file, 'w', encoding='utf-8') as f:
#         for i, subtitle in enumerate(subtitles, 1):
#             f.write(f"{i}\n")
#             f.write(f"{subtitle['timestamp']}\n")
#             f.write(f"{subtitle['text']}\n\n")

# def process_file(input_file):
#     """Xử lý một file SRT"""
#     # Đọc file input
#     try:
#         with open(input_file, 'r', encoding='utf-8') as f:
#             content = f.read()
#     except UnicodeDecodeError:
#         # Thử với encoding khác nếu utf-8 không work
#         with open(input_file, 'r', encoding='utf-8-sig') as f:
#             content = f.read()
    
#     # Parse subtitle
#     subtitles = parse_srt(content)
    
#     if not subtitles:
#         print(f"Không thể parse file {input_file}")
#         return
    
#     print(f"File {input_file}: {len(subtitles)} subtitle gốc")
    
#     # Gộp subtitle
#     merged_subtitles = merge_subtitles(subtitles)
    
#     print(f"Sau khi gộp: {len(merged_subtitles)} subtitle")
    
#     # Tạo tên file output
#     output_file = input_file.replace('.merge2.srt', '.merge3.srt')
    
#     # Ghi file output
#     write_srt(merged_subtitles, output_file)
    
#     print(f"Đã tạo file: {output_file}")
#     print("-" * 50)

# def main():
#     """Hàm main - xử lý tất cả file .merge2.srt trong thư mục hiện tại"""
#     # Tìm tất cả file .merge2.srt
#     input_files = glob.glob("*.vi.merge2.srt")
    
#     if not input_files:
#         print("Không tìm thấy file .merge2.srt nào trong thư mục hiện tại")
#         return
    
#     print(f"Tìm thấy {len(input_files)} file(s) để xử lý:")
#     for file in input_files:
#         print(f"- {file}")
#     print("-" * 50)
    
#     # Xử lý từng file
#     for input_file in input_files:
#         process_file(input_file)
    
#     print("Hoàn thành xử lý tất cả file!")

# if __name__ == "__main__":
#     main()