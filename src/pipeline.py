import subprocess
import os

def run_pipeline():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_exe = "python"

    subprocess.run([python_exe, os.path.join("src", "youtube", "download_vi_subtitles2.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner2.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner3.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "spaceSrt_cleaner4.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "srt_Cleaner.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "clean_speaker_names3.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub2.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub3.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "merge_Sub5.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "count_words.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "new_merge.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "rename_merge4.py")])
    subprocess.run([python_exe, os.path.join("src", "audio", "convert_merge_to_mp3.py")])
    subprocess.run([python_exe, os.path.join("src", "audio", "convert_mp3_to_ogg.py")])
    subprocess.run([python_exe, os.path.join("src", "audio", "archive_uploader4.py")])
    subprocess.run([python_exe, os.path.join("src", "subtitle", "cleanfile.py")])

# import subprocess
# import os

# # Lấy đường dẫn base directory
# base_dir = "/content/drive/MyDrive"

# subprocess.run(["python", f"{base_dir}/youtube/download_vi_subtitles.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/spaceSrt_cleaner.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/spaceSrt_cleaner2.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/spaceSrt_cleaner3.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/spaceSrt_cleaner4.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/srt_Cleaner.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/clean_speaker_names3.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/merge_Sub.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/merge_Sub2.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/merge_Sub3.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/merge_Sub5.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/count_words.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/new_merge.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/rename_merge4.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/audio/convert_merge_to_mp3.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/audio/convert_mp3_to_ogg.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/audio/archive_uploader4.py"])
# subprocess.run(["python", f"{base_dir}/YoutubeTM/src/subtitle/cleanfile.py"])