import re
import glob
import os
from pathlib import Path

def split_srt_blocks(content):
    blocks = re.split(r'\n{2,}', content.strip())
    result = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) >= 3:
            idx = lines[0]
            timecode = lines[1]
            text = ' '.join(lines[2:]).strip()
            result.append([idx, timecode, text])
    return result

def process_blocks(blocks):
    new_blocks = []
    for i in range(len(blocks)):
        idx, timecode, text = blocks[i]
        # Tìm dấu chấm kết thúc câu từ cuối lên
        match = list(re.finditer(r'([.,?!])', text))
        if match:
            last_punct = match[-1]
            end_idx = last_punct.end()
            trailing_text = text[end_idx:].strip()
            trailing_words = trailing_text.split()
            if 0 < len(trailing_words) <= 2 and i + 1 < len(blocks):
                # Xoá các từ sau dấu câu khỏi block hiện tại
                text = text[:end_idx].strip()
                # Thêm các từ đó vào đầu block kế tiếp (không thêm dấu câu)
                next_idx, next_timecode, next_text = blocks[i + 1]
                new_text = ' '.join(trailing_words) + ' ' + next_text
                blocks[i + 1] = [next_idx, next_timecode, new_text.strip()]
        new_blocks.append([idx, timecode, text])
    return new_blocks

def rebuild_srt(blocks):
    lines = []
    for idx, timecode, text in blocks:
        lines.append(idx)
        lines.append(timecode)
        lines.extend(text.strip().split('\n'))
        lines.append("")
    return '\n'.join(lines)

def process_srt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = split_srt_blocks(content)
    processed = process_blocks(blocks)
    result = rebuild_srt(processed)

    output_file = file_path.with_name(file_path.name.replace('.merge.srt', '.merge2.srt'))
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"✅ Đã xử lý: {file_path} → {output_file}")

if __name__ == '__main__':
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    input_files = list(storage_dir.glob("*.merge.srt"))
    if not input_files:
        print(f"❌ Không tìm thấy file .merge.srt nào trong thư mục: {storage_dir}")
    else:
        for file_path in input_files:
            process_srt_file(file_path)