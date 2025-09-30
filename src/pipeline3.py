from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import time
import os
import re
from urllib.parse import quote

class Views4YouSRTDownloader:
    def __init__(self, headless=False, download_dir="downloads"):
        """
        Views4You.com SRT Downloader - Clean and simple with auto rename
        """
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)
        
        self.headless = headless
        self.driver = None
        self.base_url = "https://views4you.com/tools/youtube-subtitles-downloader"
        self.wait_timeout = 30
    
    def setup_chrome(self):
        """Setup Chrome cho views4you.com"""
        try:
            print("🔧 Setting up Chrome for views4you.com...")
            
            options = Options()
            
            if self.headless:
                options.add_argument("--headless=new")
            
            # Basic options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Window size
            options.add_argument("--window-size=1920,1080")
            
            # User agent
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
            
            # Download preferences
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
            }
            options.add_experimental_option("prefs", prefs)
            
            # Create driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Basic stealth
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.implicitly_wait(10)
            self.driver.set_page_load_timeout(60)
            
            print("✅ Chrome setup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Chrome setup error: {e}")
            return False
    
    def extract_youtube_id(self, youtube_url):
        """Extract YouTube video ID"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, youtube_url)
            if match:
                return match.group(1)
        return None
    
    def get_views4you_url(self, youtube_url):
        """Generate views4you.com URL"""
        encoded_url = quote(youtube_url, safe='')
        return f"{self.base_url}/?url={encoded_url}"
    
    def wait_for_page_load(self, wait_time=10):
        """Wait for page to load completely"""
        print(f"⏳ Waiting {wait_time}s for page to load...")
        time.sleep(wait_time)
        
        # Check if page is ready
        try:
            page_state = self.driver.execute_script("return document.readyState")
            print(f"📄 Page state: {page_state}")
            return page_state == "complete"
        except Exception as e:
            print(f"⚠️ Error checking page state: {e}")
            return False
    
    def find_download_button(self):
        """Find the black Download button"""
        print("🔍 Looking for Download button...")
        
        # Multiple strategies to find the Download button
        search_strategies = [
            # Strategy 1: Find by class and text
            (By.XPATH, "//a[contains(@class, 'btn-black') and contains(., 'Download')]"),
            
            # Strategy 2: Find by class only
            (By.CSS_SELECTOR, "a.btn.btn-black"),
            
            # Strategy 3: Find by data-toggle
            (By.XPATH, "//a[@data-toggle='dropdown' and contains(@class, 'btn-black')]"),
            
            # Strategy 4: Find any button with Download text
            (By.XPATH, "//a[contains(@class, 'btn') and contains(., 'Download')]"),
        ]
        
        for i, (by, selector) in enumerate(search_strategies, 1):
            try:
                print(f"📋 Trying search strategy {i}...")
                buttons = self.driver.find_elements(by, selector)
                
                for button in buttons:
                    if button.is_displayed():
                        button_text = button.text.strip()
                        print(f"  ✅ Found button: '{button_text}'")
                        return button
                        
            except Exception as e:
                print(f"⚠️ Strategy {i} failed: {e}")
                continue
        
        print("❌ Download button not found")
        return None
    
    def click_download_button(self, button):
        """Click the Download button to show dropdown"""
        print("🖱️ Clicking Download button...")
        
        click_methods = [
            ("Standard Click", lambda: button.click()),
            ("ActionChains Click", lambda: ActionChains(self.driver).move_to_element(button).click().perform()),
            ("JavaScript Click", lambda: self.driver.execute_script("arguments[0].click();", button)),
        ]
        
        for method_name, click_method in click_methods:
            try:
                print(f"  Trying {method_name}...")
                
                # Scroll to button
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(1)
                
                # Execute click
                click_method()
                
                print(f"✅ {method_name} successful!")
                time.sleep(2)  # Wait for dropdown to appear
                return True
                
            except Exception as e:
                print(f"⚠️ {method_name} failed: {e}")
                continue
        
        print("❌ All click methods failed")
        return False
    
    def find_srt_link(self):
        """Find the SRT link in dropdown menu"""
        print("🔍 Looking for SRT link in dropdown...")
        
        search_strategies = [
            # Strategy 1: Find by href containing 'ext=srt'
            (By.XPATH, "//a[contains(@href, 'ext=srt') and contains(@class, 'dropdown-item')]"),
            
            # Strategy 2: Find by text 'SRT'
            (By.XPATH, "//a[@class='dropdown-item' and text()='SRT']"),
            
            # Strategy 3: Find in dropdown-menu
            (By.XPATH, "//div[contains(@class, 'dropdown-menu')]//a[contains(@href, 'ext=srt')]"),
            
            # Strategy 4: Any link with SRT text
            (By.XPATH, "//a[contains(text(), 'SRT') and contains(@href, '/download/subtitle/')]"),
        ]
        
        for i, (by, selector) in enumerate(search_strategies, 1):
            try:
                print(f"📋 Trying search strategy {i}...")
                links = self.driver.find_elements(by, selector)
                
                for link in links:
                    if link.is_displayed():
                        link_text = link.text.strip()
                        link_href = link.get_attribute('href')
                        print(f"  ✅ Found SRT link: '{link_text}' -> {link_href}")
                        return link
                        
            except Exception as e:
                print(f"⚠️ Strategy {i} failed: {e}")
                continue
        
        print("❌ SRT link not found")
        return None
    
    def click_srt_link(self, link):
        """Click the SRT link to download"""
        print("🖱️ Clicking SRT link...")
        
        click_methods = [
            ("Standard Click", lambda: link.click()),
            ("ActionChains Click", lambda: ActionChains(self.driver).move_to_element(link).click().perform()),
            ("JavaScript Click", lambda: self.driver.execute_script("arguments[0].click();", link)),
        ]
        
        for method_name, click_method in click_methods:
            try:
                print(f"  Trying {method_name}...")
                
                # Make sure link is visible
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                time.sleep(0.5)
                
                # Execute click
                click_method()
                
                print(f"✅ {method_name} successful!")
                return True
                
            except Exception as e:
                print(f"⚠️ {method_name} failed: {e}")
                continue
        
        print("❌ All click methods failed")
        return False
    
    def wait_for_download(self, timeout=15):
        """Wait for file to be downloaded"""
        print(f"⏳ Waiting for download to complete (max {timeout}s)...")
        
        files_before = set(os.listdir(self.download_dir))
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                files_after = set(os.listdir(self.download_dir))
                new_files = files_after - files_before
                
                # Check for completed downloads (not .crdownload or .tmp)
                completed_files = [f for f in new_files 
                                 if not f.endswith(('.crdownload', '.tmp', '.part')) 
                                 and f.endswith('.srt')]
                
                if completed_files:
                    for file in completed_files:
                        file_path = os.path.join(self.download_dir, file)
                        if os.path.getsize(file_path) > 0:
                            print(f"✅ Download completed: {file}")
                            return completed_files
                
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Error checking downloads: {e}")
                time.sleep(1)
        
        print(f"⚠️ Download timeout after {timeout}s")
        return []
    
    def determine_new_filename(self, original_filename, video_id):
        """
        Determine new filename based on Views4You naming pattern
        
        Rules:
        - [Views4You - English] ... .srt -> video_id.vi-en.cleansub.srt
        - [Views4You - English (auto-generated)] ... .srt -> video_id.vi.srt
        - Other patterns -> video_id.vi-en.cleansub.srt (default)
        """
        print(f"📝 Analyzing filename: {original_filename}")
        
        # Check if it's auto-generated
        if "(auto-generated)" in original_filename or "(auto generated)" in original_filename:
            new_name = f"{video_id}.vi.srt"
            print(f"  → Detected auto-generated subtitle")
        else:
            # Default to manual/clean subtitle
            new_name = f"{video_id}.vi-en.cleansub.srt"
            print(f"  → Detected manual/clean subtitle")
        
        return new_name
    
    def rename_downloaded_files(self, files, video_id):
        """
        Rename downloaded files according to the naming rules
        
        Returns: List of new filenames
        """
        renamed_files = []
        
        for old_filename in files:
            old_path = os.path.join(self.download_dir, old_filename)
            
            if not os.path.exists(old_path):
                print(f"⚠️ File not found: {old_filename}")
                continue
            
            # Determine new filename
            new_filename = self.determine_new_filename(old_filename, video_id)
            new_path = os.path.join(self.download_dir, new_filename)
            
            try:
                # Check if target file already exists
                if os.path.exists(new_path):
                    print(f"⚠️ Target file already exists: {new_filename}")
                    # Add timestamp to make it unique
                    timestamp = int(time.time())
                    base, ext = os.path.splitext(new_filename)
                    new_filename = f"{base}_{timestamp}{ext}"
                    new_path = os.path.join(self.download_dir, new_filename)
                
                # Rename the file
                os.rename(old_path, new_path)
                print(f"✅ Renamed: {old_filename}")
                print(f"      → {new_filename}")
                
                renamed_files.append(new_filename)
                
            except Exception as e:
                print(f"❌ Error renaming {old_filename}: {e}")
                # Keep original filename in results if rename fails
                renamed_files.append(old_filename)
        
        return renamed_files
    
    def download_srt_from_views4you(self, youtube_url, wait_time=10):
        """Main function to download SRT from views4you.com"""
        video_id = self.extract_youtube_id(youtube_url)
        if not video_id:
            print("❌ Invalid YouTube URL")
            return []
        
        if not self.setup_chrome():
            return []
        
        try:
            print(f"🎥 Video ID: {video_id}")
            views4you_url = self.get_views4you_url(youtube_url)
            print(f"🌐 Navigating to: {views4you_url}")
            
            # Navigate to views4you
            self.driver.get(views4you_url)
            
            # Wait for page to load
            self.wait_for_page_load(wait_time)
            
            # Find and click Download button
            download_button = self.find_download_button()
            if not download_button:
                print("❌ Download button not found")
                self.save_debug_screenshot(video_id)
                return []
            
            if not self.click_download_button(download_button):
                print("❌ Failed to click Download button")
                self.save_debug_screenshot(video_id)
                return []
            
            # Find and click SRT link
            srt_link = self.find_srt_link()
            if not srt_link:
                print("❌ SRT link not found")
                self.save_debug_screenshot(video_id)
                return []
            
            if not self.click_srt_link(srt_link):
                print("❌ Failed to click SRT link")
                self.save_debug_screenshot(video_id)
                return []
            
            # Wait for download
            downloaded_files = self.wait_for_download(timeout=15)
            
            if downloaded_files:
                print(f"\n🔄 Renaming downloaded files...")
                renamed_files = self.rename_downloaded_files(downloaded_files, video_id)
                return renamed_files
            
            return []
            
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return []
            
        finally:
            if self.driver:
                try:
                    time.sleep(2)
                    self.driver.quit()
                    print("🔒 Browser closed")
                except:
                    pass
    
    def save_debug_screenshot(self, video_id):
        """Save screenshot for debugging"""
        try:
            screenshot_path = f"views4you_debug_{video_id}.png"
            self.driver.save_screenshot(screenshot_path)
            print(f"📸 Debug screenshot saved: {screenshot_path}")
        except:
            pass

def download_multiple_videos(urls, headless=False, wait_time=10):
    """Download SRT files for multiple YouTube videos"""
    print(f"🚀 Starting batch download for {len(urls)} video(s)...")
    
    results = {
        'success': [],
        'failed': []
    }
    
    for idx, url in enumerate(urls, 1):
        print(f"\n{'='*60}")
        print(f"📹 Processing video {idx}/{len(urls)}")
        print(f"🔗 URL: {url}")
        print(f"{'='*60}")
        
        try:
            # Create new downloader for each video
            downloader = Views4YouSRTDownloader(headless=headless)
            files = downloader.download_srt_from_views4you(url, wait_time=wait_time)
            
            if files:
                print(f"✅ Video {idx} - SUCCESS!")
                results['success'].append({
                    'url': url,
                    'files': files
                })
            else:
                print(f"❌ Video {idx} - FAILED!")
                results['failed'].append(url)
                
        except Exception as e:
            print(f"❌ Video {idx} - ERROR: {e}")
            results['failed'].append(url)
        
        # Small delay between videos
        if idx < len(urls):
            print(f"\n⏳ Waiting 5 seconds before next video...")
            time.sleep(5)
    
    return results

def load_urls_from_file(filename):
    """Load YouTube URLs from a text file"""
    print(f"📂 Loading URLs from: {filename}")
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        urls = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Extract URL if line contains extra text
            if 'youtube.com' in line or 'youtu.be' in line:
                # Try to extract just the URL part
                parts = line.split()
                for part in parts:
                    if 'youtube.com' in part or 'youtu.be' in part:
                        urls.append(part)
                        break
        
        print(f"✅ Loaded {len(urls)} URL(s) from {filename}")
        
        # Show preview
        if urls:
            print(f"\n📋 Preview of URLs:")
            for i, url in enumerate(urls[:5], 1):
                print(f"  {i}. {url}")
            if len(urls) > 5:
                print(f"  ... and {len(urls) - 5} more")
        
        return urls
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return []

def main():
    import sys
    
    print("🚀 Views4You.com SRT Downloader - Batch Mode with Auto Rename")
    print("📥 Download SRT subtitles from multiple YouTube videos\n")
    
    # Get YouTube URLs
    urls = []
    
    # Method 1: Auto-detect urls.txt file
    if os.path.exists('urls.txt'):
        print("✅ Found 'urls.txt' file! Loading automatically...")
        urls = load_urls_from_file('urls.txt')
    
    # Method 2: From command line arguments
    if not urls and len(sys.argv) > 1:
        # Check if first argument is a filename
        if sys.argv[1].endswith('.txt') and os.path.exists(sys.argv[1]):
            urls = load_urls_from_file(sys.argv[1])
        else:
            urls = sys.argv[1:]
            print(f"📋 Found {len(urls)} URL(s) from command line")
    
    # Method 3: Use default test URL if nothing provided
    if not urls:
        print("⚠️ No URLs provided. Please create 'urls.txt' or pass URLs as arguments.")
        print("Example: python pipeline3.py https://youtube.com/watch?v=...")
        return
    
    # Validate URLs
    valid_urls = []
    downloader_temp = Views4YouSRTDownloader()
    for url in urls:
        video_id = downloader_temp.extract_youtube_id(url)
        if video_id:
            valid_urls.append(url)
        else:
            print(f"⚠️ Invalid URL skipped: {url}")
    
    if not valid_urls:
        print("❌ No valid YouTube URLs found!")
        return
    
    print(f"\n✅ {len(valid_urls)} valid URL(s) ready to process")
    
    # Auto settings - no questions asked
    headless = True  # Run in headless mode by default
    wait_time = 10   # Default wait time
    
    print(f"⚙️ Settings: headless={headless}, wait_time={wait_time}s")
    
    # Start downloading
    print(f"\n{'='*60}")
    print("🚀 STARTING BATCH DOWNLOAD")
    print(f"{'='*60}\n")
    
    results = download_multiple_videos(valid_urls, headless=headless, wait_time=wait_time)
    
    # Show final summary
    print(f"\n{'='*60}")
    print("📊 DOWNLOAD SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {len(results['success'])}/{len(valid_urls)}")
    print(f"❌ Failed: {len(results['failed'])}/{len(valid_urls)}")
    
    if results['success']:
        print(f"\n🎉 Successfully downloaded files:")
        total_files = 0
        for item in results['success']:
            print(f"\n  🔗 {item['url']}")
            for f in item['files']:
                print(f"    📄 {f}")
                total_files += 1
        print(f"\n  📊 Total: {total_files} file(s)")
        
        # Get download directory from first successful download
        if results['success']:
            downloader = Views4YouSRTDownloader()
            print(f"  📁 Location: {downloader.download_dir}")
    
    if results['failed']:
        print(f"\n❌ Failed URLs:")
        for url in results['failed']:
            print(f"  🔗 {url}")
        print(f"\n💡 Troubleshooting tips:")
        print("   1. Run with headless=False to see what's happening")
        print("   2. Check if videos have subtitles available")
        print("   3. Increase wait time (some pages load slower)")
        print("   4. Check debug screenshots")
        print("   5. Try running failed URLs individually")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()