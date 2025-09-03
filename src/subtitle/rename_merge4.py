import os
import glob
from pathlib import Path

def rename_merge4_files(directory):
    """
    Tìm và đổi tên các file .merge4.srt có dấu - ở đầu thành __
    Args:
        directory (str): Thư mục chứa file
    """
    pattern = os.path.join(directory, "*.merge4.srt")
    files = glob.glob(pattern)
    renamed_count = 0

    for file_path in files:
        filename = os.path.basename(file_path)
        directory_path = os.path.dirname(file_path)
        if filename.startswith("-"):
            new_filename = "__" + filename[1:]
            new_file_path = os.path.join(directory_path, new_filename)
            try:
                os.rename(file_path, new_file_path)
                print(f"Đã đổi tên: {filename} -> {new_filename}")
                renamed_count += 1
            except OSError as e:
                print(f"[ERROR] khi đổi tên file {filename}: {e}")
        else:
            print(f"Bỏ qua file (không bắt đầu bằng -): {filename}")

    print(f"\nĐã đổi tên {renamed_count} file(s)")

if __name__ == "__main__":
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    print(f"Đang tìm và đổi tên các file .merge4.srt trong {storage_dir} ...")
    rename_merge4_files(str(storage_dir))