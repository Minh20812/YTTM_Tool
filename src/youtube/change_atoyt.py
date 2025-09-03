import re
import os

def convert_archive_to_youtube(archive_url):
    """
    Convert archive.org URL to YouTube URL
    
    Args:
        archive_url (str): URL from archive.org
        
    Returns:
        str: Corresponding YouTube URL
    """
    # Pattern to match archive.org URL
    pattern = r'https://archive\.org/download/([^/]+)/[^/]+\.ogg'
    match = re.match(pattern, archive_url.strip())
    
    if not match:
        return None
    
    folder_name = match.group(1)
    
    # Handle special cases
    if folder_name.startswith('a_'):
        # Case like a__R0fPJQr0qo -> -R0fPJQr0qo
        if folder_name.startswith('a__'):
            video_id = '-' + folder_name[3:]
        # Case like a_wDIe0XEmwI -> _wDIe0XEmwI
        elif folder_name.startswith('a_'):
            video_id = '_' + folder_name[2:]
    else:
        # Normal case like 0Wwn5IEqFcg
        video_id = folder_name
    
    return f"https://www.youtube.com/watch?v={video_id}"

def main():
    """
    Main function to read file, convert links, and write results
    """
    input_file = 'broken_links.txt'
    output_file = 'yt_broken_links.txt'
    
    # Check input file exists
    if not os.path.exists(input_file):
        print(f"[ERROR] File '{input_file}' not found")
        print("Please create 'broken_links.txt' and add archive.org links into it.")
        return
    
    converted_links = []
    skipped_links = []
    
    try:
        # Read input file
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"[INFO] Processing {len(lines)} links...")
        
        # Convert each link
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line:  # skip empty lines
                youtube_url = convert_archive_to_youtube(line)
                if youtube_url:
                    converted_links.append(youtube_url)
                    print(f"[{i}] OK Converted: {line[:50]}...")
                else:
                    skipped_links.append(line)
                    print(f"[{i}] FAIL Cannot convert: {line}")
        
        # Write output file
        with open(output_file, 'w', encoding='utf-8') as f:
            for link in converted_links:
                f.write(link + '\n')
        
        # Summary
        print("\n=== SUMMARY ===")
        print(f"Total links: {len(lines)}")
        print(f"Converted successfully: {len(converted_links)}")
        print(f"Failed to convert: {len(skipped_links)}")
        print(f"Output file: '{output_file}'")
        
        if skipped_links:
            print("\nLinks that could not be converted:")
            for link in skipped_links:
                print(f"  - {link}")
    
    except FileNotFoundError:
        print(f"[ERROR] Cannot read file '{input_file}'")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    main()
