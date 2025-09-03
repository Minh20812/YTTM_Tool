import re
import os

def convert_youtube_to_archive(youtube_url):
    """
    Convert YouTube URL to archive.org URL
    
    Args:
        youtube_url (str): URL from YouTube
        
    Returns:
        str: Corresponding archive.org URL
    """
    # Patterns to match YouTube URLs
    patterns = [
        r'https://www\.youtube\.com/watch\?v=([^&\s]+)',
        r'https://youtu\.be/([^?&\s]+)',
        r'youtube\.com/watch\?v=([^&\s]+)',
        r'youtu\.be/([^?&\s]+)'
    ]
    
    video_id = None
    for pattern in patterns:
        match = re.search(pattern, youtube_url.strip())
        if match:
            video_id = match.group(1)
            break
    
    if not video_id:
        return None
    
    # Handle special cases
    if video_id.startswith('-'):
        # Example: -R0fPJQr0qo -> a__R0fPJQr0qo
        folder_name = 'a_' + video_id.replace('-', '_')
        file_name = video_id.replace('-', '_') + '.ogg'
    elif video_id.startswith('_'):
        # Example: _wDIe0XEmwI -> a_wDIe0XEmwI
        folder_name = 'a' + video_id
        file_name = video_id + '.ogg'
    else:
        # Normal case
        folder_name = video_id
        file_name = video_id + '.ogg'
    
    return f"https://archive.org/download/{folder_name}/{file_name}"

def main():
    """
    Main function to read file, convert links, and write results
    """
    input_file = 'link_youtube_recent_2days.txt'
    output_file = 'archive_links.txt'
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"[ERROR] File '{input_file}' not found")
        print("Please create 'link_youtube_recent_2days.txt' and add YouTube links into it.")
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
                archive_url = convert_youtube_to_archive(line)
                if archive_url:
                    converted_links.append(archive_url)
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
        
        # Show some examples
        if converted_links:
            print("\nExamples of converted links:")
            for i, link in enumerate(converted_links[:3]):
                print(f"  {i+1}. {link}")
    
    except FileNotFoundError:
        print(f"[ERROR] Cannot read file '{input_file}'")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

def test_conversion():
    """
    Test function to check conversion logic
    """
    test_cases = [
        "https://www.youtube.com/watch?v=0Wwn5IEqFcg",
        "https://www.youtube.com/watch?v=-R0fPJQr0qo", 
        "https://www.youtube.com/watch?v=_wDIe0XEmwI",
        "https://youtu.be/0Wwn5IEqFcg",
        "https://youtu.be/-R0fPJQr0qo",
        "https://youtu.be/_wDIe0XEmwI"
    ]
    
    print("=== TEST CONVERSION ===")
    for url in test_cases:
        result = convert_youtube_to_archive(url)
        print(f"IN:  {url}")
        print(f"OUT: {result}")
        print()

if __name__ == "__main__":
    # Uncomment to test logic
    # test_conversion()
    
    main()
