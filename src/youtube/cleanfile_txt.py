import os
import glob

# Xóa các file tạm
for pattern in ['*.txt']:
    for f in glob.glob(pattern):
        os.remove(f)
        print(f"Deleted {f}")