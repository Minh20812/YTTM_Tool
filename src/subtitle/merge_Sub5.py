import re
from pathlib import Path

def parse_srt_file(filename):
    """Parse SRT file and return list of subtitle entries"""
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    # Split by double newlines to separate subtitle blocks
    blocks = re.split(r'\n\s*\n', content)
    subtitles = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # Parse subtitle number
            number = int(lines[0])
            
            # Parse timestamp
            timestamp = lines[1]
            
            # Parse text (may be multiple lines)
            text = '\n'.join(lines[2:])
            
            subtitles.append({
                'number': number,
                'timestamp': timestamp,
                'text': text
            })
    
    return subtitles

def parse_timestamp(timestamp):
    """Parse timestamp string to get start and end times"""
    start_str, end_str = timestamp.split(' --> ')
    return start_str.strip(), end_str.strip()

def ends_with_punctuation(text):
    """Check if text ends with punctuation marks"""
    return text.strip().endswith(('.', ',', '?', '!'))

def merge_subtitles(subtitles):
    """Merge subtitles based on punctuation logic"""
    if not subtitles:
        return []
    
    merged = []
    current_group = []
    
    for subtitle in subtitles:
        current_group.append(subtitle)
        
        # Check if current subtitle ends with punctuation
        if ends_with_punctuation(subtitle['text']):
            # Merge the current group
            if current_group:
                # Get start time from first subtitle in group
                start_time, _ = parse_timestamp(current_group[0]['timestamp'])
                
                # Get end time from last subtitle in group
                _, end_time = parse_timestamp(current_group[-1]['timestamp'])
                
                # Combine all text with spaces
                combined_text = ' '.join([sub['text'].strip() for sub in current_group])
                
                merged_subtitle = {
                    'number': len(merged) + 1,
                    'timestamp': f"{start_time} --> {end_time}",
                    'text': combined_text
                }
                
                merged.append(merged_subtitle)
                current_group = []
    
    # Handle remaining subtitles that don't end with punctuation
    if current_group:
        start_time, _ = parse_timestamp(current_group[0]['timestamp'])
        _, end_time = parse_timestamp(current_group[-1]['timestamp'])
        combined_text = ' '.join([sub['text'].strip() for sub in current_group])
        
        merged_subtitle = {
            'number': len(merged) + 1,
            'timestamp': f"{start_time} --> {end_time}",
            'text': combined_text
        }
        merged.append(merged_subtitle)
    
    return merged

def write_srt_file(subtitles, filename):
    """Write subtitles to SRT file"""
    with open(filename, 'w', encoding='utf-8') as f:
        for i, subtitle in enumerate(subtitles):
            f.write(f"{subtitle['number']}\n")
            f.write(f"{subtitle['timestamp']}\n")
            f.write(f"{subtitle['text']}\n")
            
            # Add blank line except for last subtitle
            if i < len(subtitles) - 1:
                f.write("\n")

def process_file(input_file):
    """Process a single SRT file"""
    print(f"Processing: {input_file}")
    
    # Parse input file
    subtitles = parse_srt_file(input_file)
    print(f"Found {len(subtitles)} subtitles")
    
    # Merge subtitles
    merged_subtitles = merge_subtitles(subtitles)
    print(f"Merged to {len(merged_subtitles)} subtitles")
    
    # Generate output filename - replace .merge2.srt with .merge4.srt
    output_file = input_file.replace('.merge2.srt', '.merge4.srt')
    
    # Write output file
    write_srt_file(merged_subtitles, output_file)
    print(f"Output written to: {output_file}")

def main():
    # Xác định thư mục storage cùng cấp với thư mục cha của script
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    storage_dir = parent_dir / "storage"

    # Lấy tất cả file .vi-*.merge2.srt trong storage (có dấu -)
    input_files = [f for f in storage_dir.glob("*.vi-*.merge2.srt") if f.is_file()]
    if not input_files:
        print(f"Không tìm thấy file .vi-*.merge2.srt nào trong thư mục: {storage_dir}")
        print("Looking for files like: .vi-en.merge2.srt, .vi-fr.merge2.srt, etc.")
        return

    print(f"Found {len(input_files)} files to process:")
    for file in input_files:
        print(f"  - {file.name}")

    print("\nProcessing files...")
    for input_file in input_files:
        try:
            process_file(input_file)
            print("✓ Success\n")
        except Exception as e:
            print(f"✗ Error processing {input_file}: {e}\n")
    print("Done!")

if __name__ == "__main__":
    main()

# import re
# import os
# import glob

# def parse_srt_file(filename):
#     """Parse SRT file and return list of subtitle entries"""
#     with open(filename, 'r', encoding='utf-8') as f:
#         content = f.read().strip()
    
#     # Split by double newlines to separate subtitle blocks
#     blocks = re.split(r'\n\s*\n', content)
#     subtitles = []
    
#     for block in blocks:
#         if not block.strip():
#             continue
            
#         lines = block.strip().split('\n')
#         if len(lines) >= 3:
#             # Parse subtitle number
#             number = int(lines[0])
            
#             # Parse timestamp
#             timestamp = lines[1]
            
#             # Parse text (may be multiple lines)
#             text = '\n'.join(lines[2:])
            
#             subtitles.append({
#                 'number': number,
#                 'timestamp': timestamp,
#                 'text': text
#             })
    
#     return subtitles

# def parse_timestamp(timestamp):
#     """Parse timestamp string to get start and end times"""
#     start_str, end_str = timestamp.split(' --> ')
#     return start_str.strip(), end_str.strip()

# def ends_with_punctuation(text):
#     """Check if text ends with punctuation marks"""
#     return text.strip().endswith(('.', ',', '?', '!'))

# def merge_subtitles(subtitles):
#     """Merge subtitles based on punctuation logic"""
#     if not subtitles:
#         return []
    
#     merged = []
#     current_group = []
    
#     for subtitle in subtitles:
#         current_group.append(subtitle)
        
#         # Check if current subtitle ends with punctuation
#         if ends_with_punctuation(subtitle['text']):
#             # Merge the current group
#             if current_group:
#                 # Get start time from first subtitle in group
#                 start_time, _ = parse_timestamp(current_group[0]['timestamp'])
                
#                 # Get end time from last subtitle in group
#                 _, end_time = parse_timestamp(current_group[-1]['timestamp'])
                
#                 # Combine all text with spaces
#                 combined_text = ' '.join([sub['text'].strip() for sub in current_group])
                
#                 merged_subtitle = {
#                     'number': len(merged) + 1,
#                     'timestamp': f"{start_time} --> {end_time}",
#                     'text': combined_text
#                 }
                
#                 merged.append(merged_subtitle)
#                 current_group = []
    
#     # Handle remaining subtitles that don't end with punctuation
#     if current_group:
#         start_time, _ = parse_timestamp(current_group[0]['timestamp'])
#         _, end_time = parse_timestamp(current_group[-1]['timestamp'])
#         combined_text = ' '.join([sub['text'].strip() for sub in current_group])
        
#         merged_subtitle = {
#             'number': len(merged) + 1,
#             'timestamp': f"{start_time} --> {end_time}",
#             'text': combined_text
#         }
#         merged.append(merged_subtitle)
    
#     return merged

# def write_srt_file(subtitles, filename):
#     """Write subtitles to SRT file"""
#     with open(filename, 'w', encoding='utf-8') as f:
#         for i, subtitle in enumerate(subtitles):
#             f.write(f"{subtitle['number']}\n")
#             f.write(f"{subtitle['timestamp']}\n")
#             f.write(f"{subtitle['text']}\n")
            
#             # Add blank line except for last subtitle
#             if i < len(subtitles) - 1:
#                 f.write("\n")

# def process_file(input_file):
#     """Process a single SRT file"""
#     print(f"Processing: {input_file}")
    
#     # Parse input file
#     subtitles = parse_srt_file(input_file)
#     print(f"Found {len(subtitles)} subtitles")
    
#     # Merge subtitles
#     merged_subtitles = merge_subtitles(subtitles)
#     print(f"Merged to {len(merged_subtitles)} subtitles")
    
#     # Generate output filename
#     output_file = input_file.replace('.merge2.srt', '.merge5.srt')
    
#     # Write output file
#     write_srt_file(merged_subtitles, output_file)
#     print(f"Output written to: {output_file}")

# def main():
#     """Main function to process all .merge2.srt files"""
#     # Find all .merge2.srt files in current directory
#     input_files = glob.glob("*.merge2.srt")
    
#     if not input_files:
#         print("No .merge2.srt files found in current directory")
#         return
    
#     print(f"Found {len(input_files)} files to process:")
#     for file in input_files:
#         print(f"  - {file}")
    
#     print("\nProcessing files...")
#     for input_file in input_files:
#         try:
#             process_file(input_file)
#             print("✓ Success\n")
#         except Exception as e:
#             print(f"✗ Error processing {input_file}: {e}\n")
    
#     print("Done!")

# if __name__ == "__main__":
#     main()