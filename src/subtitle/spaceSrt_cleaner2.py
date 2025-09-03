import re
import os
import glob

def parse_time_to_ms(time_str):
    """Chuyển đổi thời gian SRT sang milliseconds"""
    # Format: HH:MM:SS,mmm
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds_parts = parts[2].split(',')
    seconds = int(seconds_parts[0])
    milliseconds = int(seconds_parts[1])
    
    total_ms = hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds
    return total_ms

def ms_to_time_str(ms):
    """Chuyển đổi milliseconds về format SRT"""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    milliseconds = ms % 1000
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def filter_srt(input_file, output_file, min_duration_ms=100):
    """
    Lọc file SRT, loại bỏ những subtitle có thời lượng quá ngắn
    
    Args:
        input_file: Đường dẫn file SRT gốc
        output_file: Đường dẫn file SRT sau khi lọc
        min_duration_ms: Thời lượng tối thiểu (milliseconds), mặc định 100ms
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tách các subtitle blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    
    filtered_blocks = []
    subtitle_counter = 1
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # Lấy dòng thời gian (dòng thứ 2)
        time_line = lines[1]
        
        # Parse thời gian bắt đầu và kết thúc
        time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', time_line)
        if not time_match:
            continue
            
        start_time = time_match.group(1)
        end_time = time_match.group(2)
        
        start_ms = parse_time_to_ms(start_time)
        end_ms = parse_time_to_ms(end_time)
        duration = end_ms - start_ms
        
        # Chỉ giữ lại những subtitle có thời lượng >= min_duration_ms
        if duration >= min_duration_ms:
            # Cập nhật số thứ tự
            lines[0] = str(subtitle_counter)
            filtered_blocks.append('\n'.join(lines))
            subtitle_counter += 1
    
    # Ghi file mới
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(filtered_blocks))
    
    print(f"Đã lọc xong! File gốc có {len(blocks)} subtitle, file mới có {len(filtered_blocks)} subtitle")
    print(f"Đã loại bỏ {len(blocks) - len(filtered_blocks)} subtitle có thời lượng < {min_duration_ms}ms")

def merge_consecutive_subtitles(input_file, output_file, max_gap_ms=50):
    """
    Gộp các subtitle liên tiếp có khoảng cách thời gian nhỏ
    
    Args:
        input_file: Đường dẫn file SRT gốc
        output_file: Đường dẫn file SRT sau khi gộp
        max_gap_ms: Khoảng cách tối đa để gộp (milliseconds)
    """
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = re.split(r'\n\s*\n', content.strip())
    
    merged_blocks = []
    i = 0
    subtitle_counter = 1
    
    while i < len(blocks):
        current_block = blocks[i].strip().split('\n')
        if len(current_block) < 3:
            i += 1
            continue
            
        # Parse thời gian của subtitle hiện tại
        time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', current_block[1])
        if not time_match:
            i += 1
            continue
            
        start_time = time_match.group(1)
        end_time = time_match.group(2)
        text_lines = current_block[2:]
        
        # Kiểm tra subtitle tiếp theo
        j = i + 1
        while j < len(blocks):
            next_block = blocks[j].strip().split('\n')
            if len(next_block) < 3:
                j += 1
                continue
                
            next_time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', next_block[1])
            if not next_time_match:
                break
                
            next_start_time = next_time_match.group(1)
            next_end_time = next_time_match.group(2)
            
            # Tính khoảng cách giữa 2 subtitle
            current_end_ms = parse_time_to_ms(end_time)
            next_start_ms = parse_time_to_ms(next_start_time)
            gap = next_start_ms - current_end_ms
            
            # Nếu khoảng cách nhỏ, gộp lại
            if gap <= max_gap_ms:
                end_time = next_end_time
                text_lines.extend(next_block[2:])
                j += 1
            else:
                break
        
        # Tạo subtitle đã gộp
        merged_subtitle = [
            str(subtitle_counter),
            f"{start_time} --> {end_time}"
        ] + text_lines
        
        merged_blocks.append('\n'.join(merged_subtitle))
        subtitle_counter += 1
        i = j
    
    # Ghi file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(merged_blocks))
    
    print(f"Đã gộp xong! File gốc có {len(blocks)} subtitle, file mới có {len(merged_blocks)} subtitle")

# Cách sử dụng
if __name__ == "__main__":
    # Lấy đường dẫn thư mục cha
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    storage_dir = os.path.join(parent_dir, 'storage')

    # Tìm tất cả file .vi.clean1.srt trong thư mục storage
    input_files = glob.glob(os.path.join(storage_dir, "*.vi.clean1.srt"))

    if not input_files:
        print(f"Không tìm thấy file nào có đuôi .vi.clean1.srt trong thư mục: {storage_dir}")
        print("Vui lòng đặt các file cần xử lý vào thư mục storage")
    else:
        print(f"Tìm thấy {len(input_files)} file(s) để xử lý trong {storage_dir}:")
        for input_file in input_files:
            # Tạo tên file output trong cùng thư mục storage
            output_file = input_file.replace('.vi.clean1.srt', '.vi.clean2.srt')
            print(f"\n--- Đang xử lý: {input_file} ---")
            try:
                filter_srt(input_file, output_file, min_duration_ms=100)
                print(f"✓ Hoàn thành: {output_file}")
            except Exception as e:
                print(f"✗ [ERROR] khi xử lý {input_file}: {str(e)}")
        print(f"\n=== Đã xử lý xong tất cả {len(input_files)} file(s) ===")
    
    # Nếu muốn gộp các subtitle liên tiếp thay vì chỉ lọc, 
    # thay filter_srt() bằng merge_consecutive_subtitles() ở trên