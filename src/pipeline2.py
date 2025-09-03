import os
import subprocess
from datetime import datetime

def get_storage_directory():
    """Lấy đường dẫn thư mục storage"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "storage")

def run_processing_pipeline():
    """Chạy các script theo thứ tự cố định"""
    print("🔄 Starting processing pipeline...")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exe = "python"

    # Danh sách script cần chạy (có thể kèm args)
    scripts = [
        ("src", "youtube", "get_url_video_fromFirebase.py", ["--export-recent", "2"]),
        ("src", "youtube", "change_yttoa.py", []),
        ("src", "youtube", "check_audio_active.py", []),
        ("src", "youtube", "change_atoyt.py", []),
        ("src", "youtube", "delete_urlFirebase.py", []),
        ("src", "youtube", "cleanfile_txt.py", []),
    ]

    successful_scripts = 0
    failed_scripts = 0

    for i, (folder1, folder2, script, args) in enumerate(scripts, 1):
        script_file = os.path.join(base_dir, folder1, folder2, script)
        script_name = script

        print(f"\n[{i}/{len(scripts)}] Running {script_name} {' '.join(args)}...")

        try:
            result = subprocess.run(
                [python_exe, script_file] + args,
                cwd=base_dir,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print(f"✅ {script_name} completed successfully")
                if result.stdout:
                    print(f"   Output: {result.stdout[:200]}...")
                successful_scripts += 1
            else:
                print(f"⚠️ {script_name} failed (return code: {result.returncode})")
                if result.stderr:
                    print(f"   Error: {result.stderr[:200]}...")
                failed_scripts += 1

        except subprocess.TimeoutExpired:
            print(f"⏱️ {script_name} timed out after 5 minutes")
            failed_scripts += 1
        except Exception as e:
            print(f"❌ Error running {script_name}: {e}")
            failed_scripts += 1

    print("\n📊 Processing pipeline summary:")
    print(f"   ✅ Successful scripts: {successful_scripts}")
    print(f"   ❌ Failed scripts: {failed_scripts}")
    print(f"   📁 Storage directory: {get_storage_directory()}")

    return successful_scripts, failed_scripts


def run_pipeline():
    """Main pipeline"""
    print("="*60)
    print("🚀 STARTING PROCESSING PIPELINE")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    successful_scripts, failed_scripts = run_processing_pipeline()

    print("\n" + "="*60)
    print("🏁 PIPELINE FINISHED")
    print(f"   ✅ Successful: {successful_scripts}")
    print(f"   ❌ Failed: {failed_scripts}")
    print("="*60)
