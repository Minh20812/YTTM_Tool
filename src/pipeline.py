import subprocess
import os
import sys
import json
import tempfile
from datetime import datetime

def run_download_script():
    """Chạy script download và trả về thông tin về các video đã tải thành công"""
    print("🚀 Starting subtitle download process...")
    
    # Lưu danh sách file hiện có trước khi chạy script
    storage_dir = get_storage_directory()
    existing_files = set()
    if os.path.exists(storage_dir):
        existing_files = set(os.listdir(storage_dir))
    
    # Chạy script download
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exe = "python"
    download_script = os.path.join("src", "youtube", "download_vi_subtitles2.py")
    
    try:
        # Chạy script download với capture output để theo dõi
        result = subprocess.run(
            [python_exe, download_script], 
            capture_output=True, 
            text=True,
            cwd=base_dir
        )
        
        print(f"Download script return code: {result.returncode}")
        if result.stdout:
            print("Download script output:")
            print(result.stdout)
        if result.stderr:
            print("Download script errors:")
            print(result.stderr)
        
        # Kiểm tra file mới được tạo
        new_files = set()
        if os.path.exists(storage_dir):
            current_files = set(os.listdir(storage_dir))
            new_files = current_files - existing_files
        
        # Lọc chỉ lấy file .srt mới
        new_subtitle_files = [f for f in new_files if f.endswith('.srt')]
        
        print(f"📊 New subtitle files detected: {len(new_subtitle_files)}")
        for file in new_subtitle_files:
            print(f"   📄 {file}")
        
        return len(new_subtitle_files) > 0, new_subtitle_files
        
    except Exception as e:
        print(f"❌ Error running download script: {e}")
        return False, []

def get_storage_directory():
    """Lấy đường dẫn thư mục storage"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "storage")

def run_processing_pipeline():
    """Chạy các script xử lý subtitle"""
    print("🔄 Starting subtitle processing pipeline...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exe = "python"
    
    # Danh sách các script cần chạy theo thứ tự
    scripts = [
        ("src", "subtitle", "spaceSrt_cleaner.py"),
        ("src", "subtitle", "spaceSrt_cleaner2.py"),
        ("src", "subtitle", "spaceSrt_cleaner3.py"),
        ("src", "subtitle", "spaceSrt_cleaner4.py"),
        ("src", "subtitle", "srt_Cleaner.py"),
        ("src", "subtitle", "clean_speaker_names3.py"),
        ("src", "subtitle", "merge_Sub.py"),
        ("src", "subtitle", "merge_Sub2.py"),
        ("src", "subtitle", "merge_Sub3.py"),
        ("src", "subtitle", "merge_Sub5.py"),
        ("src", "subtitle", "count_words.py"),
        ("src", "subtitle", "new_merge.py"),
        ("src", "subtitle", "rename_merge4.py"),
        ("src", "audio", "convert_merge_to_mp3.py"),
        ("src", "audio", "convert_mp3_to_ogg.py"),
        ("src", "audio", "archive_uploader4.py"),
        ("src", "subtitle", "cleanfile.py")
    ]
    
    successful_scripts = 0
    failed_scripts = 0
    
    for i, script_path in enumerate(scripts, 1):
        script_file = os.path.join(*script_path)
        script_name = script_path[-1]
        
        print(f"\n[{i}/{len(scripts)}] Running {script_name}...")
        
        try:
            result = subprocess.run(
                [python_exe, script_file],
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per script
            )
            
            if result.returncode == 0:
                print(f"✅ {script_name} completed successfully")
                successful_scripts += 1
            else:
                print(f"⚠️ {script_name} completed with warnings (return code: {result.returncode})")
                if result.stderr:
                    print(f"   Error output: {result.stderr[:200]}...")
                failed_scripts += 1
                
        except subprocess.TimeoutExpired:
            print(f"⏱️ {script_name} timed out after 5 minutes")
            failed_scripts += 1
        except Exception as e:
            print(f"❌ Error running {script_name}: {e}")
            failed_scripts += 1
    
    print(f"\n📊 Processing pipeline summary:")
    print(f"   ✅ Successful scripts: {successful_scripts}")
    print(f"   ❌ Failed scripts: {failed_scripts}")
    print(f"   📁 Storage directory: {get_storage_directory()}")
    
    return successful_scripts, failed_scripts

def run_pipeline():
    """Main pipeline function với logic conditional"""
    print("="*60)
    print("🚀 STARTING YOUTUBE SUBTITLE PROCESSING PIPELINE")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Bước 1: Chạy script download
    has_new_videos, new_files = run_download_script()
    
    if not has_new_videos:
        print("\n" + "="*60)
        print("⏹️ PIPELINE STOPPED - NO NEW VIDEOS DETECTED")
        print("   No new subtitle files were downloaded.")
        print("   The processing pipeline will not run.")
        print("="*60)
        return
    
    print(f"\n✅ NEW VIDEOS DETECTED - {len(new_files)} new subtitle files")
    print("🔄 Proceeding with processing pipeline...")
    
    # Bước 2: Chạy pipeline xử lý
    successful_scripts, failed_scripts = run_processing_pipeline()
    
    # Bước 3: Tổng kết
    print("\n" + "="*60)
    print("🏁 PIPELINE COMPLETED")
    print(f"   📺 New subtitle files processed: {len(new_files)}")
    print(f"   ✅ Successful processing scripts: {successful_scripts}")
    print(f"   ❌ Failed processing scripts: {failed_scripts}")
    print(f"   ⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Hiển thị danh sách file mới
    if new_files:
        print("\n📄 New subtitle files:")
        for file in new_files:
            print(f"   • {file}")

def run_pipeline_force():
    """Chạy toàn bộ pipeline bất kể có video mới hay không"""
    print("="*60)
    print("🚀 FORCING COMPLETE PIPELINE RUN")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Chạy download script
    print("📥 Step 1: Running download script...")
    has_new_videos, new_files = run_download_script()
    
    # Chạy processing pipeline bất kể kết quả
    print("\n🔄 Step 2: Running processing pipeline (forced)...")
    successful_scripts, failed_scripts = run_processing_pipeline()
    
    # Tổng kết
    print("\n" + "="*60)
    print("🏁 FORCED PIPELINE COMPLETED")
    print(f"   📺 New subtitle files: {len(new_files) if new_files else 0}")
    print(f"   ✅ Successful processing scripts: {successful_scripts}")
    print(f"   ❌ Failed processing scripts: {failed_scripts}")
    print(f"   ⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        run_pipeline_force()
    else:
        run_pipeline()


# import subprocess
# import os

# def run_pipeline():
#     base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     python_exe = "python"

#     subprocess.run([python_exe, os.path.join("src", "youtube", "download_vi_subtitles2.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner2.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner3.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner4.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "srt_Cleaner.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "clean_speaker_names3.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub2.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub3.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub5.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "count_words.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "new_merge.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "rename_merge4.py")])
#     subprocess.run([python_exe, os.path.join("src", "audio", "convert_merge_to_mp3.py")])
#     subprocess.run([python_exe, os.path.join("src", "audio", "convert_mp3_to_ogg.py")])
#     subprocess.run([python_exe, os.path.join("src", "audio", "archive_uploader4.py")])
#     subprocess.run([python_exe, os.path.join("src", "subtitle", "cleanfile.py")])