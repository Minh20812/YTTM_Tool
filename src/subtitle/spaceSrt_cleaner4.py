import os
import glob
import re

def has_meaningful_text(text_lines):
    """
    Trả về True nếu bất kỳ dòng nào trong text_lines chứa chữ cái (a-z, A-Z, Unicode)
    """
    for line in text_lines:
        line = line.strip()
        if re.search(r'[^\W\d_]', line, re.UNICODE):
            return True
    return False

def process_srt_file(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r'\n{2,}', content)
    cleaned_blocks = []

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            text_lines = lines[2:]
            if has_meaningful_text(text_lines):
                cleaned_blocks.append(block)
        else:
            pass

    cleaned_content = '\n\n'.join(cleaned_blocks)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(cleaned_content)

    print(f"✅ Đã xử lý xong: {input_file} → {output_file}")

def main():
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    storage_dir = os.path.join(parent_dir, 'storage')

    # Lấy tất cả file .vi.clean3.srt trong thư mục storage
    input_files = glob.glob(os.path.join(storage_dir, "*.vi.clean3.srt"))

    if not input_files:
        print(f"❌ Không tìm thấy file .vi.clean3.srt nào trong thư mục: {storage_dir}")
    else:
        for filepath in input_files:
            output_path = filepath.replace(".vi.clean3.srt", ".vi.clean4.srt")
            process_srt_file(filepath, output_path)

        # Xóa các file tạm trong storage
        for pattern in ['*.vi.clean1.srt','*.vi.clean2.srt','*.vi.clean3.srt']:
            for f in glob.glob(os.path.join(storage_dir, pattern)):
                os.remove(f)
                print(f"✓ Đã xóa {f}")

if __name__ == "__main__":
    main()