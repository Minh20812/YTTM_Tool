import re
import os
from datetime import datetime
from pathlib import Path

def count_words_and_punct(lines):
    count = 0
    for i, line in enumerate(lines):
        words = re.findall(r'\w+', line)
        count += len(words)
        # Đếm dấu câu , . ? ! (2 từ mỗi dấu, trừ khi ở cuối block)
        # if i == len(lines) - 1:
        #     puncts = re.findall(r'[,.?!]', line)
        #     if puncts and line.rstrip()[-1] in ',.?!':
        #         count += (len(puncts) - 1) * 2
        #     else:
        #         count += len(puncts) * 2
        # else:
        #     count += len(re.findall(r'[,.?!]', line)) * 2
    return count

def get_time_range(block):
    for line in block:
        m = re.match(r'^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
        if m:
            start = datetime.strptime(m.group(1), "%H:%M:%S,%f")
            end = datetime.strptime(m.group(2), "%H:%M:%S,%f")
            return (start, end)
    return (None, None)

def process_srt_file(input_file):
    # Tạo tên file output
    base_name = os.path.splitext(input_file)[0]  # Bỏ extension
    if base_name.endswith('.merge3'):
        base_name = base_name[:-7]  # Bỏ '.merge3'
    output_file = base_name + '.count.txt'
    
    print(f"Đang xử lý: {input_file} -> {output_file}")
    
    # Đọc file input
    with open(input_file, encoding='utf-8') as f:
        lines = f.readlines()

    # Chia thành các blocks
    blocks = []
    block = []
    for line in lines:
        if line.strip() == '':
            if block:
                blocks.append(block)
                block = []
        else:
            block.append(line.strip())
    if block:
        blocks.append(block)

    # Xử lý từng block
    total_words = 0
    total_est_seconds = 0
    total_real_seconds = 0

    with open(output_file, 'w', encoding='utf-8') as out:
        negative_rate_blocks = []
        for idx, block in enumerate(blocks, 1):
            # Lấy dòng thời gian
            start_time, end_time = get_time_range(block)
            # Bỏ qua dòng số thứ tự và thời gian
            content_lines = [l for l in block if not re.match(r'^\d+$', l) and not re.match(r'^\d{2}:\d{2}:\d{2}', l)]
            word_count = count_words_and_punct(content_lines)
            total_words += word_count
            # Tính thời gian nói cho block này (ước lượng)
            block_seconds = word_count * 8 / 37 if word_count > 0 else 0
            total_est_seconds += block_seconds
            # Tính thời gian thực tế từ phụ đề
            if start_time and end_time:
                real_seconds = (end_time - start_time).total_seconds()
                total_real_seconds += real_seconds
            else:
                real_seconds = 0
            # Tính rate theo công thức yêu cầu
            if block_seconds > 0 and real_seconds > 0:
                k = real_seconds / block_seconds
                rate = (1 - 1 / k) * 100
            else:
                rate = 0
            if rate < 0:
                negative_rate_blocks.append(idx)

            out.write(
                f'Block {idx}: {word_count} từ, '
                f'Ước lượng: {block_seconds:.2f} giây, '
                f'Thực tế: {real_seconds:.2f} giây, '
                f'Chênh lệch: {block_seconds-real_seconds:.2f} giây, '
                f'Rate: {rate:.2f}%\n'
            )

        # Tổng kết
        out.write(f'\nTổng số từ: {total_words}\n')
        out.write(f'Tổng thời gian nói (ước lượng): {total_est_seconds:.2f} giây\n')
        out.write(f'Tổng thời gian nói (thực tế từ phụ đề): {total_real_seconds:.2f} giây\n')
        out.write(f'Tổng chênh lệch: {total_est_seconds-total_real_seconds:.2f} giây\n')
        out.write(f'Các phụ đề có rate < 0%: {negative_rate_blocks}\n')

    print(f"Đã ghi kết quả vào {output_file}")
    return output_file

def main():
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    merge3_files = list(storage_dir.glob("*.merge3.srt"))

    if not merge3_files:
        print(f"Không tìm thấy file .merge3.srt nào trong thư mục: {storage_dir}")
    else:
        print(f"Tìm thấy {len(merge3_files)} file .merge3.srt:")
        for file in merge3_files:
            print(f"  - {file.name}")
        
        print("\nBắt đầu xử lý...")
        processed_files = []
        
        for input_file in merge3_files:
            try:
                output_file = process_srt_file(str(input_file))
                processed_files.append(output_file)
            except Exception as e:
                print(f"Lỗi khi xử lý {input_file}: {e}")
        
        print(f"\nHoàn thành! Đã xử lý {len(processed_files)} file:")
        for file in processed_files:
            print(f"  - {file}")

if __name__ == "__main__":
    main()