# def clean_srt_content(content):
#     """Chỉ loại bỏ các dòng trống/khoảng trắng, giữ lại tất cả nội dung"""
#     lines = content.split('\n')
#     cleaned_lines = []
    
#     i = 0
#     while i < len(lines):
#         line = lines[i]
        
#         # Kiểm tra xem có phải là dòng timestamp không
#         if '-->' in line:
#             # Thêm dòng timestamp
#             cleaned_lines.append(line)
#             i += 1
            
#             # Loại bỏ các dòng trống/khoảng trắng ngay sau timestamp
#             while i < len(lines) and lines[i].strip() == '':
#                 i += 1
            
#             # Tiếp tục xử lý các dòng còn lại
#             continue
        
#         # Với các dòng khác, giữ nguyên
#         cleaned_lines.append(line)
#         i += 1
    
#     return '\n'.join(cleaned_lines)

import re
import glob
import os

def clean_srt_content(content):
    """
    Thêm ♪ vào tất cả các dòng trống/khoảng trắng,
    trừ dòng trống phân cách giữa các block phụ đề (dòng trống đứng trước số thứ tự block mới).
    Đảm bảo giữa các block chỉ có một dòng trống.
    """
    lines = content.split('\n')
    cleaned_lines = []
    prev_line_is_block_sep = False

    for idx, line in enumerate(lines):
        # Kiểm tra nếu dòng hiện tại là dòng trống/khoảng trắng
        if line.strip() == '':
            # Kiểm tra dòng tiếp theo có phải là số thứ tự block (chỉ chứa số) không
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ''
            if next_line.strip().isdigit():
                # Đây là dòng trống phân cách block, giữ nguyên (không thêm ♪)
                cleaned_lines.append('')
                prev_line_is_block_sep = True
            else:
                # Không phải dòng phân cách block, thay bằng ♪
                cleaned_lines.append('♪')
                prev_line_is_block_sep = False
        else:
            cleaned_lines.append(line)
            prev_line_is_block_sep = False

    return '\n'.join(cleaned_lines)

def process_srt_file(input_file, output_file):
    """Xử lý file SRT để loại bỏ khoảng trống bên dưới timestamp"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean content
        cleaned_content = clean_srt_content(content)
        
        # Ghi file output
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        return True
        
    except Exception as e:
        print(f"Lỗi khi xử lý file {input_file}: {str(e)}")
        return False

def main():
    """Hàm main xử lý tất cả file .vi.srt trong thư mục storage cùng cấp với thư mục cha"""
    # Lấy đường dẫn tuyệt đối của script hiện tại
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Lấy thư mục cha của script
    parent_dir = os.path.dirname(script_dir)
    
    # Đường dẫn đến thư mục storage (cùng cấp với thư mục cha)
    storage_dir = os.path.join(parent_dir, 'storage')
    
    print(f"Thư mục script: {script_dir}")
    print(f"Thư mục cha: {parent_dir}")
    print(f"Thư mục storage: {storage_dir}")
    
    # Kiểm tra xem thư mục storage có tồn tại không
    if not os.path.exists(storage_dir):
        print(f"Không tìm thấy thư mục storage tại: {storage_dir}")
        return
    
    # Tìm tất cả file .vi.srt trong thư mục storage
    search_pattern = os.path.join(storage_dir, "*.vi.srt")
    input_files = glob.glob(search_pattern)
    
    if not input_files:
        print(f"Không tìm thấy file .vi.srt nào trong thư mục: {storage_dir}")
        return
    
    processed_count = 0
    
    print(f"\nTìm thấy {len(input_files)} file .vi.srt:")
    for input_file in input_files:
        print(f"Đang xử lý file: {os.path.basename(input_file)}")
        
        # Lấy tên file không có đường dẫn
        filename = os.path.basename(input_file)
        base_name = filename.replace('.vi.srt', '')
        
        # Tạo tên file output trong cùng thư mục storage
        output_file = os.path.join(storage_dir, f"{base_name}.vi.clean1.srt")
        
        # Xử lý file
        if process_srt_file(input_file, output_file):
            print(f"  ✓ Đã tạo file: {os.path.basename(output_file)}")
            processed_count += 1
        else:
            print(f"  ✗ Lỗi khi xử lý file: {filename}")
    
    print(f"\nHoàn thành! Đã xử lý {processed_count}/{len(input_files)} file.")
    print(f"Các file đã được lưu trong: {storage_dir}")

if __name__ == "__main__":
    main()