import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_link_status(url, timeout=10):
    """
    Check the status of a single URL
    
    Args:
        url (str): URL to check
        timeout (int): Timeout in seconds
        
    Returns:
        dict: Information about link status
    """
    url = url.strip()
    if not url:
        return {"url": url, "status": "empty", "status_code": None, "error": "Empty URL"}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        
        if response.status_code == 200:
            status = "working"
            error = None
        elif response.status_code == 404:
            status = "not_found"
            error = "File not found (404)"
        elif response.status_code in [403, 401]:
            status = "forbidden"
            error = f"Access denied ({response.status_code})"
        elif response.status_code >= 500:
            status = "server_error"
            error = f"Server error ({response.status_code})"
        else:
            status = "unknown"
            error = f"Unexpected status code ({response.status_code})"
            
        return {
            "url": url,
            "status": status,
            "status_code": response.status_code,
            "error": error
        }
        
    except requests.exceptions.Timeout:
        return {
            "url": url,
            "status": "timeout",
            "status_code": None,
            "error": "Timeout - No response"
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status": "connection_error",
            "status_code": None,
            "error": "Connection error - Cannot reach server"
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "status_code": None,
            "error": f"Unexpected error: {str(e)}"
        }

def check_links_parallel(urls, max_workers=10, timeout=10):
    """
    Check multiple links in parallel
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(check_link_status, url, timeout): url for url in urls}
        for i, future in enumerate(as_completed(future_to_url), 1):
            result = future.result()
            results.append(result)
            status_symbol = "OK" if result["status"] == "working" else "FAIL"
            print(f"[{i}/{len(urls)}] {status_symbol} {result['url'][:60]}...")
            time.sleep(0.1)  # small delay
    return results

def main():
    """
    Main function
    """
    input_file = 'archive_links.txt'
    working_file = 'working_links.txt'
    broken_file = 'broken_links.txt'
    report_file = 'link_check_report.txt'
    
    if not os.path.exists(input_file):
        print(f"[ERROR] File '{input_file}' not found")
        return
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]
        
        if not urls:
            print("[ERROR] Input file is empty")
            return
            
        print(f"[INFO] Checking {len(urls)} links...")
        
        start_time = time.time()
        results = check_links_parallel(urls, max_workers=5, timeout=15)
        end_time = time.time()
        
        working_links = [r["url"] for r in results if r["status"] == "working"]
        broken_links = [r for r in results if r["status"] != "working"]
        
        with open(working_file, 'w', encoding='utf-8') as f:
            for link in working_links:
                f.write(link + '\n')
        
        with open(broken_file, 'w', encoding='utf-8') as f:
            for r in broken_links:
                f.write(f"{r['url']}\n")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== LINK CHECK REPORT ===\n")
            f.write(f"Checked at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total time: {end_time - start_time:.2f} sec\n")
            f.write(f"Total links: {len(urls)}\n")
            f.write(f"Working: {len(working_links)}\n")
            f.write(f"Broken: {len(broken_links)}\n")
            f.write(f"Success rate: {len(working_links)/len(urls)*100:.1f}%\n\n")
            
            if broken_links:
                f.write("=== BROKEN LINKS DETAILS ===\n")
                for r in broken_links:
                    f.write(f"URL: {r['url']}\n")
                    f.write(f"Error: {r['error']}\n")
                    f.write(f"Status Code: {r['status_code']}\n")
                    f.write("-" * 50 + "\n")
        
        print("\n" + "="*50)
        print("LINK CHECK SUMMARY")
        print("="*50)
        print(f"Total links: {len(urls)}")
        print(f"Working: {len(working_links)} ({len(working_links)/len(urls)*100:.1f}%)")
        print(f"Broken: {len(broken_links)} ({len(broken_links)/len(urls)*100:.1f}%)")
        print(f"Time: {end_time - start_time:.2f} sec")
        print("\nOutput files:")
        print(f"  - Working links: '{working_file}'")
        print(f"  - Broken links: '{broken_file}'")
        print(f"  - Detailed report: '{report_file}'")
        
        if broken_links:
            error_stats = {}
            for r in broken_links:
                status = r["status"]
                error_stats[status] = error_stats.get(status, 0) + 1
            
            print("\nError statistics:")
            for status, count in error_stats.items():
                print(f"  - {status}: {count}")
        
    except FileNotFoundError:
        print(f"[ERROR] Cannot read file '{input_file}'")
    except Exception as e:
        print(f"[ERROR] {str(e)}")

if __name__ == "__main__":
    main()
