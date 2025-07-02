import srt
import os
from pathlib import Path

def clean_srt_blocks(subtitles):
    cleaned = []
    prev_lines = []  # Lưu tất cả dòng của phụ đề trước

    for sub in subtitles:
        current_lines = sub.content.strip().split('\n')
        # Lọc ra những dòng chưa xuất hiện ở phụ đề trước
        filtered_lines = []
        for line in current_lines:
            line_stripped = line.strip()
            if line_stripped not in [prev_line.strip() for prev_line in prev_lines]:
                filtered_lines.append(line)
        # Cập nhật nội dung phụ đề
        if filtered_lines:
            sub.content = '\n'.join(filtered_lines)
        else:
            sub.content = ""
        prev_lines = current_lines
        cleaned.append(sub)
    return cleaned

if __name__ == "__main__":
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    # Lấy tất cả file .vi.clean2.srt trong thư mục storage
    input_files = list(storage_dir.glob('*.vi.clean2.srt'))

    if not input_files:
        print(f"❌ Không tìm thấy file .vi.clean2.srt nào trong thư mục: {storage_dir}")
    else:
        print(f"📂 Tìm thấy {len(input_files)} file trong {storage_dir}:")
        for input_path in input_files:
            print(f"📄 Đang xử lý: {input_path.name}")

            # Đọc nội dung file
            with open(input_path, 'r', encoding='utf-8') as f:
                srt_data = f.read()

            # Phân tích và xử lý
            subtitles = list(srt.parse(srt_data))
            cleaned_subs = clean_srt_blocks(subtitles)
            output_srt = srt.compose(cleaned_subs)

            # Ghi ra file mới trong storage
            output_path = input_path.with_name(input_path.name.replace('.vi.clean2.srt', '.vi.clean3.srt'))
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_srt)

            print(f"✅ Đã lưu: {output_path.name}")

        print("🎉 Xử lý xong tất cả các file.")

# import srt
# import os
# import glob
# from pathlib import Path


# def clean_srt_blocks(subtitles):
#     cleaned = []
#     prev_line = ""

#     for sub in subtitles:
#         lines = sub.content.strip().split('\n')

#         if len(lines) == 2:
#             line1, line2 = lines
#             if line1.strip() == prev_line.strip():
#                 sub.content = line2
#                 prev_line = line2
#             else:
#                 prev_line = line2
#         elif len(lines) == 1:
#             prev_line = lines[0]
#         else:
#             prev_line = lines[-1] if lines else ""

#         cleaned.append(sub)
    
#     return cleaned

# # 📂 Lấy tất cả file .vi.clean2.srt trong thư mục hiện tại
# input_files = Path('.').glob('*.vi.clean2.srt')

# for input_path in input_files:
#     print(f"📄 Đang xử lý: {input_path.name}")

#     # Đọc nội dung file
#     with open(input_path, 'r', encoding='utf-8') as f:
#         srt_data = f.read()

#     # Phân tích và xử lý
#     subtitles = list(srt.parse(srt_data))
#     cleaned_subs = clean_srt_blocks(subtitles)
#     output_srt = srt.compose(cleaned_subs)

#     # Ghi ra file mới
#     output_path = input_path.with_name(input_path.name.replace('.vi.clean2.srt', '.vi.clean3.srt'))
#     with open(output_path, 'w', encoding='utf-8') as f:
#         f.write(output_srt)

#     print(f"✅ Đã lưu: {output_path.name}")

# print("🎉 Xử lý xong tất cả các file.")
