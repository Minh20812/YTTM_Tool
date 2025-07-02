import srt
import re
from pathlib import Path

def move_short_sentences(subtitles):
    new_subs = list(subtitles)

    for i, sub in enumerate(subtitles):
        text = sub.content.strip()

        # ==== XỬ LÝ CÂU NGẮN Ở ĐẦU PHỤ ĐỀ ====
        match = re.match(r'^((?:[\wÀ-ỹ\'’\-]+\s?){1,2})([.,?!])', text)
        if match and i > 0:
            matched_text = match.group(0)
            # Kiểm tra nếu sau dấu câu vẫn còn chữ (không phải cuối đoạn)
            if len(text) > len(matched_text):
                new_subs[i].content = text[len(matched_text):].lstrip()
                new_subs[i - 1].content = new_subs[i - 1].content.rstrip() + ' ' + matched_text

        # ==== XỬ LÝ CÂU NGẮN Ở CUỐI PHỤ ĐỀ ====
        match_end = re.search(r'((?:[\wÀ-ỹ\'’\-]+\s?){1,2})([.,?!])\s*$', text)
        if match_end and i < len(subtitles) - 1:
            matched_text = match_end.group(0)
            # Chỉ xử lý nếu dấu câu KHÔNG phải là ký tự cuối cùng của toàn bộ nội dung
            if not text.endswith(matched_text.strip()):
                words = match_end.group(1).strip()
                new_subs[i].content = text[:text.rfind(matched_text)].rstrip()
                new_subs[i + 1].content = words + ' ' + new_subs[i + 1].content.lstrip()

    return new_subs

if __name__ == "__main__":
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    # Lặp qua tất cả file .cleaned.srt trong thư mục storage
    input_files = storage_dir.glob('*.cleaned.srt')

    found = False
    for input_path in input_files:
        found = True
        print(f"📄 Đang xử lý: {input_path.name}")

        with open(input_path, 'r', encoding='utf-8') as f:
            srt_data = f.read()

        subs = list(srt.parse(srt_data))
        cleaned_subs = move_short_sentences(subs)
        output_srt = srt.compose(cleaned_subs)

        # Tạo file output .vi.merge.srt trong storage
        output_path = input_path.with_name(input_path.name.replace('.cleaned.srt', '.merge.srt'))
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_srt)

        print(f"✅ Đã lưu: {output_path.name}")

    if not found:
        print(f"❌ Không tìm thấy file .cleaned.srt nào trong thư mục: {storage_dir}")
    else:
        print("🎉 Hoàn tất xử lý tất cả file .cleaned.srt.")