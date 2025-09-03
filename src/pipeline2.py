import os
import subprocess
from datetime import datetime


def get_storage_directory():
    """Lấy đường dẫn thư mục storage"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "storage")


def run_processing_pipeline():
    """Chạy các script theo thứ tự"""
    print("Starting processing pipeline...")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    youtube_dir = os.path.join(base_dir, "src", "youtube")  # cd vào đây
    python_exe = "python"

    # Danh sách script cần chạy theo thứ tự (script, args)
    scripts = [
        ("get_url_video_fromFirebase.py", ["--export-recent", "2"]),
        ("change_yttoa.py", []),
        ("check_audio_active.py", []),
        ("change_atoyt.py", []),
        ("delete_urlFirebase.py", []),
        ("cleanfile_txt.py", []),
    ]

    successful_scripts = 0
    failed_scripts = 0

    for i, (script, args) in enumerate(scripts, 1):
        print(f"\n[{i}/{len(scripts)}] Running {script} {' '.join(args)}")

        try:
            result = subprocess.run(
                [python_exe, script] + args,
                cwd=youtube_dir,   # chạy trong src/youtube
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print(f" {script} completed successfully")
                if result.stdout.strip():
                    print("   Output:\n" + result.stdout.strip())
                successful_scripts += 1
            else:
                print(f"{script} failed (return code {result.returncode})")
                if result.stderr.strip():
                    print("   Error:\n" + result.stderr.strip())
                failed_scripts += 1

        except subprocess.TimeoutExpired:
            print(f"{script} timed out after 5 minutes")
            failed_scripts += 1
        except Exception as e:
            print(f"Error running {script}: {e}")
            failed_scripts += 1

    print("\nProcessing pipeline summary:")
    print(f"    Successful scripts: {successful_scripts}")
    print(f"   Failed scripts: {failed_scripts}")
    print(f"   Storage directory: {get_storage_directory()}")

    return successful_scripts, failed_scripts


def run_pipeline():
    """Main pipeline"""
    print("=" * 60)
    print("STARTING PROCESSING PIPELINE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    successful_scripts, failed_scripts = run_processing_pipeline()

    print("\n" + "=" * 60)
    print("PIPELINE FINISHED")
    print(f"    Successful: {successful_scripts}")
    print(f"   Failed: {failed_scripts}")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()
