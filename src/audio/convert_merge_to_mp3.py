# import glob
# import subprocess
# import os
# import shutil  # <- Thêm để di chuyển file

# def convert_to_mp3(srt_file, original_base_name):
#     mp3_file = f"{original_base_name}.mp3"
#     output_folder = "Files mp3"  # <- Tên thư mục đích

#     print(f"[🎧] Đang tạo MP3 từ {srt_file} ...")

#     try:
#         subprocess.run(
#             [
#                 "python", "-m", "edge_srt_to_speech",
#                 srt_file, mp3_file,
#                 "--voice", "vi-VN-NamMinhNeural"
#             ],
#             check=True
#         )
#         print(f"[✅] Đã tạo MP3: {mp3_file}")

#         # 🔄 Tạo thư mục nếu chưa có
#         os.makedirs(output_folder, exist_ok=True)

#         # 📦 Di chuyển file vào thư mục
#         destination_path = os.path.join(output_folder, mp3_file)
#         shutil.move(mp3_file, destination_path)
#         print(f"[📁] Đã chuyển vào thư mục '{output_folder}': {destination_path}")

#     except subprocess.CalledProcessError as e:
#         print(f"[❌] Lỗi khi tạo {mp3_file}")
#         print(f"     ↳ Trạng thái: {e.returncode}")
#     except Exception as e:
#         print(f"[🔥] Lỗi không xác định khi xử lý {srt_file}: {e}")

# def main():
#     srt_files = glob.glob("*.merge4.srt")
#     print(f"[📂] Tìm thấy {len(srt_files)} file *.merge4.srt")

#     for srt_file in srt_files:
#         if not srt_file.endswith(".merge4.srt"):
#             continue
        
#         full_base_name = srt_file.replace('.merge4.srt', '')  
#         video_id = full_base_name.split('.')[0]  # Lấy ID video YouTube
        
#         print(f"\n[🎬] Đang xử lý: {srt_file} → {video_id}.mp3")
#         convert_to_mp3(srt_file, video_id)

#     print("\n[🏁] Đã hoàn tất chuyển đổi tất cả file.")

# if __name__ == "__main__":
#     main()



import glob
import subprocess
import os
from pathlib import Path

def convert_to_mp3(srt_file, output_dir):
    base_name = srt_file.stem.replace('.merge4', '')
    mp3_file = output_dir / f"{base_name}.mp3"

    print(f"[🎧] Đang tạo MP3 từ {srt_file} ...")

    try:
        subprocess.run(
            [
                "python", "-m", "edge_srt_to_speech",
                str(srt_file), str(mp3_file),
                "--voice", "vi-VN-NamMinhNeural"
            ],
            check=True
        )
        print(f"[✅] Đã tạo MP3: {mp3_file}")
    except subprocess.CalledProcessError as e:
        print(f"[❌] Lỗi khi tạo {mp3_file}")
        print(f"     ↳ Trạng thái: {e.returncode}")
    except Exception as e:
        print(f"[🔥] Lỗi không xác định khi xử lý {srt_file}: {e}")

def main():
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    srt_files = list(storage_dir.glob("*.merge4.srt"))
    print(f"[📂] Tìm thấy {len(srt_files)} file *.merge4.srt trong {storage_dir}")

    for srt_file in srt_files:
        print(f"\n[🎬] Đang xử lý: {srt_file.name}")
        convert_to_mp3(srt_file, storage_dir)

    print("\n[🏁] Đã hoàn tất chuyển đổi tất cả file.")

if __name__ == "__main__":
    main()