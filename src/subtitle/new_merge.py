import re
import sys
import os
import glob
from pathlib import Path

def parse_negative_blocks(count_file):
    with open(count_file, encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'Các phụ đề có rate < 0%: \[([^\]]*)\]', content)
    if not match:
        return []
    nums = match.group(1)
    return [int(x.strip()) for x in nums.split(',') if x.strip().isdigit()]

def parse_block_rates(count_file):
    rates = {}
    with open(count_file, encoding='utf-8') as f:
        for line in f:
            m = re.match(r'Block (\d+):.*Rate: ([\d\.\-]+)%', line)
            if m:
                rates[int(m.group(1))] = float(m.group(2))
    return rates

def parse_srt_blocks(srt_file):
    with open(srt_file, encoding='utf-8') as f:
        content = f.read()
    blocks = [block.split('\n') for block in re.split(r'\n\s*\n', content.strip())]
    return blocks

def get_timestamp(block):
    for line in block:
        m = re.match(r'^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', line)
        if m:
            return m.group(1), m.group(2)
    return None, None

def set_timestamp(block, start, end):
    new_block = []
    found = False
    for line in block:
        if not found and re.match(r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', line):
            new_block.append(f"{start} --> {end}")
            found = True
        else:
            new_block.append(line)
    return new_block

def merge_blocks(blocks, negative_blocks, block_rates):
    merged = [block[:] for block in blocks]
    merged_indices = set()
    for idx in negative_blocks:
        i = idx - 1
        if i in merged_indices:
            continue
        left = i - 1 if i - 1 >= 0 else None
        right = i + 1 if i + 1 < len(merged) else None
        left_rate = block_rates.get(left + 1, float('-inf')) if left is not None else float('-inf')
        right_rate = block_rates.get(right + 1, float('-inf')) if right is not None else float('-inf')
        if left_rate >= right_rate and left is not None and left not in merged_indices:
            start, _ = get_timestamp(merged[left])
            _, end = get_timestamp(merged[i])
            left_content = [l for l in merged[left] if not re.match(r'^\d+$', l) and not re.match(r'^\d{2}:\d{2}:\d{2}', l)]
            this_content = [l for l in merged[i] if not re.match(r'^\d+$', l) and not re.match(r'^\d{2}:\d{2}:\d{2}', l)]
            new_block = [
                merged[left][0],
                f"{start} --> {end}"
            ] + left_content + this_content
            merged[left] = new_block
            merged_indices.add(i)
        elif right is not None and right not in merged_indices:
            start, _ = get_timestamp(merged[i])
            _, end = get_timestamp(merged[right])
            this_content = [l for l in merged[i] if not re.match(r'^\d+$', l) and not re.match(r'^\d{2}:\d{2}:\d{2}', l)]
            right_content = [l for l in merged[right] if not re.match(r'^\d+$', l) and not re.match(r'^\d{2}:\d{2}:\d{2}', l)]
            new_block = [
                merged[right][0],
                f"{start} --> {end}"
            ] + this_content + right_content
            merged[right] = new_block
            merged_indices.add(i)
    result = [block for idx, block in enumerate(merged) if idx not in merged_indices]
    return result

def write_srt_blocks(blocks, out_file):
    with open(out_file, 'w', encoding='utf-8') as f:
        for i, block in enumerate(blocks, 1):
            block[0] = str(i)
            f.write('\n'.join(block) + '\n\n')

def process_file_set(base_name, storage_dir):
    count_file = storage_dir / f"{base_name}.count.txt"
    input_srt = storage_dir / f"{base_name}.merge3.srt"
    output_srt = storage_dir / f"{base_name}.merge4.srt"

    if not count_file.exists():
        print(f"Không tìm thấy file: {count_file}")
        return False
    if not input_srt.exists():
        print(f"Không tìm thấy file: {input_srt}")
        return False

    try:
        print(f"Đang xử lý: {base_name}")
        negative_blocks = parse_negative_blocks(count_file)
        block_rates = parse_block_rates(count_file)
        blocks = parse_srt_blocks(input_srt)
        merged_blocks = merge_blocks(blocks, negative_blocks, block_rates)
        write_srt_blocks(merged_blocks, output_srt)
        print(f"  ✓ Hoàn thành: {output_srt}")
        return True
    except Exception as e:
        print(f"  ✗ Lỗi khi xử lý {base_name}: {e}")
        return False

def find_base_names(storage_dir):
    count_files = list(storage_dir.glob("*.count.txt"))
    base_names = []
    for count_file in count_files:
        base_name = count_file.name.replace(".count.txt", "")
        base_names.append(base_name)
    return base_names

if __name__ == "__main__":
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    print("Tìm kiếm các file cần xử lý...")

    base_names = find_base_names(storage_dir)

    if not base_names:
        print(f"Không tìm thấy file .count.txt nào trong thư mục: {storage_dir}")
        sys.exit(1)

    print(f"Tìm thấy {len(base_names)} bộ file:")
    for base_name in base_names:
        print(f"  - {base_name}")

    print("\nBắt đầu xử lý...")
    success_count = 0

    for base_name in base_names:
        if process_file_set(base_name, storage_dir):
            success_count += 1

    print(f"\nHoàn thành! Đã xử lý thành công {success_count}/{len(base_names)} bộ file.")