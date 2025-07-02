import re
import glob
import os

def count_dots_in_content(content):
    """Đếm số lượng dấu chấm trong nội dung phụ đề"""
    # Tách các subtitle blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    total_dots = 0
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # Lấy phần text (bỏ qua số thứ tự và timestamp)
        text_lines = lines[2:]
        text = ' '.join(text_lines)
        
        # Đếm dấu chấm trong text
        total_dots += text.count('.')
    
    return total_dots

def process_srt_content(content):
    """
    Xử lý nội dung file SRT theo các quy tắc:
    0. Kiểm tra số lượng dấu chấm - nếu >= 10 thì không xử lý
    1. Thêm dấu "," trước từ "nhưng" nếu chưa có
    2. Thêm dấu "." trước từ được viết hoa nếu chưa có  
    3. Xóa phụ đề trùng lặp liền kề
    """
    
    # Kiểm tra số lượng dấu chấm trước khi xử lý
    dot_count = count_dots_in_content(content)
    print(f"Số lượng dấu chấm trong file: {dot_count}")
    
    if dot_count >= 10:
        print("File đã có đủ dấu chấm (>= 10), bỏ qua xử lý các quy tắc 1 và 2")
        # Chỉ thực hiện quy tắc 3 (xóa trùng lặp) vì luôn hữu ích
        return process_only_duplicates(content)
    
    print("File có ít dấu chấm (< 10), thực hiện xử lý đầy đủ")
    
    # Tách các subtitle blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    processed_blocks = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # Lấy số thứ tự, timestamp và text
        subtitle_num = lines[0]
        timestamp = lines[1]
        text_lines = lines[2:]
        text = ' '.join(text_lines)
        
        # Quy tắc 1: Thêm dấu "," trước từ "nhưng" nếu chưa có
        text = re.sub(r'(?<![,\s])\s+nhưng\b', ', nhưng', text)
        
        # Quy tắc 2: Thêm dấu "." trước từ được viết hoa tiếng Việt nếu chưa có
        # Chỉ áp dụng cho từ bắt đầu bằng chữ hoa tiếng Việt, bỏ qua từ tiếng Anh
        vietnamese_upper = 'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ'
        vietnamese_lower = 'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
        
        # Pattern để tìm từ tiếng Việt viết hoa (bao gồm cả chữ A-Z có dấu tiếng Việt)
        vietnamese_word_pattern = f'([{vietnamese_upper}][{vietnamese_lower}]*|[BCDFGHJKLMNPQRSTVWXYZ][{vietnamese_lower}]+)'
        text = re.sub(f'(?<![,\s!?])\s+({vietnamese_word_pattern})', r', \1', text)
        
        processed_blocks.append({
            'num': subtitle_num,
            'timestamp': timestamp,
            'text': text
        })
    
    # Quy tắc 3: Xóa phụ đề trùng lặp liền kề
    filtered_blocks = []
    prev_text = None
    
    for block in processed_blocks:
        if block['text'] != prev_text:
            filtered_blocks.append(block)
            prev_text = block['text']
    
    # Cập nhật lại số thứ tự sau khi xóa trùng lặp
    for i, block in enumerate(filtered_blocks, 1):
        block['num'] = str(i)
    
    # Tạo lại nội dung SRT
    result = []
    for block in filtered_blocks:
        result.append(f"{block['num']}\n{block['timestamp']}\n{block['text']}\n")
    
    return '\n'.join(result)

def process_only_duplicates(content):
    """
    Chỉ xử lý quy tắc 3: Xóa phụ đề trùng lặp liền kề
    Dành cho các file đã có đủ dấu chấm
    """
    
    # Tách các subtitle blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    processed_blocks = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
            
        # Lấy số thứ tự, timestamp và text (không thay đổi text)
        subtitle_num = lines[0]
        timestamp = lines[1]
        text_lines = lines[2:]
        text = ' '.join(text_lines)
        
        processed_blocks.append({
            'num': subtitle_num,
            'timestamp': timestamp,
            'text': text
        })
    
    # Quy tắc 3: Xóa phụ đề trùng lặp liền kề
    filtered_blocks = []
    prev_text = None
    
    for block in processed_blocks:
        if block['text'] != prev_text:
            filtered_blocks.append(block)
            prev_text = block['text']
    
    # Cập nhật lại số thứ tự sau khi xóa trùng lặp
    for i, block in enumerate(filtered_blocks, 1):
        block['num'] = str(i)
    
    # Tạo lại nội dung SRT
    result = []
    for block in filtered_blocks:
        result.append(f"{block['num']}\n{block['timestamp']}\n{block['text']}\n")
    
    return '\n'.join(result)

def process_srt_file(input_file, output_file):
    """Xử lý một file SRT"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        processed_content = process_srt_content(content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"Đã xử lý: {input_file} -> {output_file}")
        
    except Exception as e:
        print(f"Lỗi khi xử lý file {input_file}: {str(e)}")

def main():
    """Hàm chính - xử lý tất cả file *.clean4.srt trong thư mục storage cùng cấp với thư mục cha"""
    # Xác định thư mục storage
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    storage_dir = os.path.join(parent_dir, 'storage')

    # Tìm tất cả file *.clean4.srt trong thư mục storage
    input_files = glob.glob(os.path.join(storage_dir, "*.clean4.srt"))
    
    if not input_files:
        print(f"Không tìm thấy file nào có pattern *.clean4.srt trong thư mục: {storage_dir}")
        return
    
    print(f"Tìm thấy {len(input_files)} file để xử lý:")
    
    for input_file in input_files:
        print(f"\n--- Xử lý file: {input_file} ---")
        
        # Tạo tên file output trong cùng thư mục storage
        base_name = os.path.splitext(os.path.basename(input_file))[0].replace('.clean4', '')
        output_file = os.path.join(storage_dir, f"{base_name}.clean5.srt")
        
        process_srt_file(input_file, output_file)
    
    print("\nHoàn thành xử lý tất cả file!")

if __name__ == "__main__":
    main()
    
# import re
# import glob
# import os

# def process_srt_content(content):
#     """
#     Xử lý nội dung file SRT theo các quy tắc:
#     1. Thêm dấu "," trước từ "nhưng" nếu chưa có
#     2. Thêm dấu "." trước từ được viết hoa nếu chưa có  
#     3. Xóa phụ đề trùng lặp liền kề
#     """
    
#     # Tách các subtitle blocks
#     blocks = re.split(r'\n\s*\n', content.strip())
#     processed_blocks = []
    
#     for block in blocks:
#         if not block.strip():
#             continue
            
#         lines = block.strip().split('\n')
#         if len(lines) < 3:
#             continue
            
#         # Lấy số thứ tự, timestamp và text
#         subtitle_num = lines[0]
#         timestamp = lines[1]
#         text_lines = lines[2:]
#         text = ' '.join(text_lines)
        
#         # Quy tắc 1: Thêm dấu "," trước từ "nhưng" nếu chưa có
#         text = re.sub(r'(?<![,\s])\s+nhưng\b', ', nhưng', text)
        
#         # Quy tắc 2: Thêm dấu "." trước từ được viết hoa tiếng Việt nếu chưa có
#         # Chỉ áp dụng cho từ bắt đầu bằng chữ hoa tiếng Việt, bỏ qua từ tiếng Anh
#         vietnamese_upper = 'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ'
#         vietnamese_lower = 'àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
        
#         # Pattern để tìm từ tiếng Việt viết hoa (bao gồm cả chữ A-Z có dấu tiếng Việt)
#         vietnamese_word_pattern = f'([{vietnamese_upper}][{vietnamese_lower}]*|[BCDFGHJKLMNPQRSTVWXYZ][{vietnamese_lower}]+)'
#         text = re.sub(f'(?<![,\s!?])\s+({vietnamese_word_pattern})', r', \1', text)
        
#         processed_blocks.append({
#             'num': subtitle_num,
#             'timestamp': timestamp,
#             'text': text
#         })
    
#     # Quy tắc 3: Xóa phụ đề trùng lặp liền kề
#     filtered_blocks = []
#     prev_text = None
    
#     for block in processed_blocks:
#         if block['text'] != prev_text:
#             filtered_blocks.append(block)
#             prev_text = block['text']
    
#     # Cập nhật lại số thứ tự sau khi xóa trùng lặp
#     for i, block in enumerate(filtered_blocks, 1):
#         block['num'] = str(i)
    
#     # Tạo lại nội dung SRT
#     result = []
#     for block in filtered_blocks:
#         result.append(f"{block['num']}\n{block['timestamp']}\n{block['text']}\n")
    
#     return '\n'.join(result)

# def process_srt_file(input_file, output_file):
#     """Xử lý một file SRT"""
#     try:
#         with open(input_file, 'r', encoding='utf-8') as f:
#             content = f.read()
        
#         processed_content = process_srt_content(content)
        
#         with open(output_file, 'w', encoding='utf-8') as f:
#             f.write(processed_content)
        
#         print(f"Đã xử lý: {input_file} -> {output_file}")
        
#     except Exception as e:
#         print(f"Lỗi khi xử lý file {input_file}: {str(e)}")

# def main():
#     """Hàm chính - xử lý tất cả file *.clean4.srt"""
    
#     # Tìm tất cả file có pattern *.clean4.srt
#     input_files = glob.glob("*.clean4.srt")
    
#     if not input_files:
#         print("Không tìm thấy file nào có pattern *.clean4.srt")
#         return
    
#     print(f"Tìm thấy {len(input_files)} file để xử lý:")
    
#     for input_file in input_files:
#         # Tạo tên file output
#         base_name = input_file.replace('.clean4.srt', '')
#         output_file = f"{base_name}.clean5.srt"
        
#         process_srt_file(input_file, output_file)
    
#     print("Hoàn thành xử lý tất cả file!")

# if __name__ == "__main__":
#     main()