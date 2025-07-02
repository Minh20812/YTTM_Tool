#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script chuyển đổi file MP3 sang OGG với tối ưu cho giọng đọc
Yêu cầu: pip install pydub
"""

import os
import glob
from pydub import AudioSegment
from pydub.effects import normalize
import time
from pathlib import Path

def convert_mp3_to_ogg(input_file, output_file, quality=3):
    try:
        print(f"Đang xử lý: {os.path.basename(input_file)}")
        audio = AudioSegment.from_mp3(input_file)
        if audio.channels == 2:
            audio = audio.set_channels(1)
            print("  → Chuyển từ stereo sang mono")
        if audio.frame_rate > 22050:
            audio = audio.set_frame_rate(22050)
            print(f"  → Giảm sample rate xuống 22050Hz")
        audio = normalize(audio)
        print("  → Chuẩn hóa âm lượng")
        audio.export(
            output_file,
            format="ogg",
            codec="libvorbis",
            parameters=["-q:a", str(quality)]
        )
        original_size = os.path.getsize(input_file)
        new_size = os.path.getsize(output_file)
        compression_ratio = ((original_size - new_size) / original_size) * 100
        print(f"  ✓ Hoàn thành: {os.path.basename(output_file)}")
        print(f"  📦 Kích thước: {original_size//1024}KB → {new_size//1024}KB (-{compression_ratio:.1f}%)")
        return True
    except Exception as e:
        print(f"  ❌ Lỗi khi xử lý {input_file}: {str(e)}")
        return False

def main():
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    print("🎵 Script chuyển đổi MP3 sang OGG (Tối ưu cho giọng đọc)")
    print("=" * 60)

    # Tìm tất cả file MP3 trong thư mục storage
    mp3_files = list(storage_dir.glob("*.mp3"))

    if not mp3_files:
        print(f"❌ Không tìm thấy file MP3 nào trong thư mục: {storage_dir}")
        return

    print(f"📁 Tìm thấy {len(mp3_files)} file MP3:")
    for file in mp3_files:
        print(f"   • {file.name}")

    print("\n🚀 Bắt đầu chuyển đổi...")
    print("-" * 40)

    successful = 0
    failed = 0
    start_time = time.time()

    for mp3_file in mp3_files:
        base_name = mp3_file.stem
        ogg_file = storage_dir / f"{base_name}.ogg"
        if convert_mp3_to_ogg(str(mp3_file), str(ogg_file)):
            successful += 1
        else:
            failed += 1
        print()

    elapsed_time = time.time() - start_time
    print("=" * 60)
    print("📊 KẾT QUẢ CHUYỂN ĐỔI:")
    print(f"   ✅ Thành công: {successful} file")
    print(f"   ❌ Thất bại: {failed} file")
    print(f"   ⏱️  Thời gian: {elapsed_time:.1f} giây")
    print(f"   📂 File OGG được lưu trong thư mục: {storage_dir}")

    if successful > 0:
        original_total = sum(os.path.getsize(f) for f in mp3_files if os.path.exists(f))
        ogg_files = list(storage_dir.glob("*.ogg"))
        new_total = sum(os.path.getsize(f) for f in ogg_files)
        total_saved = ((original_total - new_total) / original_total) * 100 if original_total else 0
        print(f"   💾 Tiết kiệm dung lượng: {total_saved:.1f}%")
        print(f"      ({original_total//1024}KB → {new_total//1024}KB)")

    # Xóa các file mp3 sau khi chuyển đổi
    for f in mp3_files:
        try:
            os.remove(f)
            print(f"✓ Đã xóa {f.name}")
        except Exception as e:
            print(f"✗ Không thể xóa {f.name}: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Đã dừng chuyển đổi theo yêu cầu người dùng.")
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {str(e)}")
        print("💡 Hãy kiểm tra lại môi trường Python và thư viện pydub.")