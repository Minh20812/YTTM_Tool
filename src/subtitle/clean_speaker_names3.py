#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import glob
from pathlib import Path

def clean_subtitle_text(text):
    """
    Làm sạch text phụ đề theo các quy tắc:
    1. Loại bỏ text trong ngoặc [], {}, ()
    2. Loại bỏ text trước dấu : (tên người nói)
    """
    # Loại bỏ text trong các loại ngoặc
    text = re.sub(r'\[.*?\]', '', text)  # Loại bỏ [text]
    text = re.sub(r'\{.*?\}', '', text)  # Loại bỏ {text}
    text = re.sub(r'\(.*?\)', '', text)  # Loại bỏ (text)
    text = re.sub(r'\<.*?\>', '', text)  # Loại bỏ (text)
    
    # Loại bỏ tên người nói (text trước dấu :)
    # Chỉ loại bỏ nếu dấu : xuất hiện ở đầu dòng hoặc sau khoảng trắng
    text = re.sub(r'^[^:]*:\s*', '', text)  # Loại bỏ từ đầu dòng đến dấu :
    text = re.sub(r'\n[^:\n]*:\s*', '\n', text)  # Loại bỏ tên người nói trên dòng mới

    # Loại bỏ ký tự ♪
    text = text.replace('♪', '')
    
    # Làm sạch khoảng trắng thừa
    text = re.sub(r'\s+', ' ', text)  # Thay nhiều khoảng trắng bằng 1
    text = text.strip()  # Loại bỏ khoảng trắng đầu cuối
    
    return text

def process_srt_file(input_file, output_file):
    """
    Xử lý file SRT và lưu kết quả
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Thử với encoding khác nếu utf-8 không work
        with open(input_file, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Tách các subtitle entry
    entries = re.split(r'\n\s*\n', content.strip())
    cleaned_entries = []
    
    for entry in entries:
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        
        # Kiểm tra format SRT hợp lệ (ít nhất 3 dòng: số, time, text)
        if len(lines) < 3:
            continue
            
        # Dòng đầu: số thứ tự
        subtitle_number = lines[0]
        
        # Dòng thứ 2: timestamp
        timestamp = lines[1]
        
        # Các dòng còn lại: text cần làm sạch
        subtitle_text = '\n'.join(lines[2:])
        cleaned_text = clean_subtitle_text(subtitle_text)
        
        # Chỉ giữ lại entry nếu còn text sau khi làm sạch
        if cleaned_text.strip():
            cleaned_entry = f"{subtitle_number}\n{timestamp}\n{cleaned_text}"
            cleaned_entries.append(cleaned_entry)
    
    # Ghi file output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(cleaned_entries))
        if cleaned_entries:  # Thêm newline cuối file nếu có content
            f.write('\n\n')
    
    print(f"✓ Đã xử lý: {input_file} → {output_file}")
    print(f"  Số entry gốc: {len(entries)}, Số entry sau khi làm sạch: {len(cleaned_entries)}")

def main():
    """
    Tìm và xử lý tất cả file *.clean5.srt và *.cleansub.srt trong thư mục storage cùng cấp với thư mục cha của script
    """
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    clean5_files = list(storage_dir.glob("*.clean5.srt"))
    cleansub_files = list(storage_dir.glob("*.cleansub.srt"))
    all_files = clean5_files + cleansub_files

    if not all_files:
        print(f"Không tìm thấy file *.clean5.srt hoặc *.cleansub.srt nào trong thư mục: {storage_dir}")
        return

    print(f"Tìm thấy {len(all_files)} file cần xử lý trong {storage_dir}:")
    for file in all_files:
        print(f"  - {file.name}")

    print("\nBắt đầu xử lý...")

    processed_count = 0
    for input_file in all_files:
        try:
            file_path = Path(input_file)
            if input_file.name.endswith('.clean5.srt'):
                output_file = file_path.with_name(file_path.stem.replace('.clean5', '') + '.cleaned.srt')
            elif input_file.name.endswith('.cleansub.srt'):
                output_file = file_path.with_name(file_path.stem.replace('.cleansub', '') + '.cleaned.srt')
            else:
                continue
            process_srt_file(str(input_file), str(output_file))
            processed_count += 1
        except Exception as e:
            print(f"✗ [ERROR] khi xử lý {input_file}: {str(e)}")

    print(f"\n🎉 Hoàn thành! Đã xử lý thành công {processed_count}/{len(all_files)} file.")

if __name__ == "__main__":
    main()