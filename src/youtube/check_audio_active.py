import requests
import os
import time
from urllib.parse import urlparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_link_status(url, timeout=10):
    """
    Kiểm tra trạng thái của một link
    
    Args:
        url (str): URL cần kiểm tra
        timeout (int): Thời gian timeout (giây)
        
    Returns:
        dict: Thông tin về trạng thái link
    """
    url = url.strip()
    if not url:
        return {"url": url, "status": "empty", "status_code": None, "error": "URL trống"}
    
    try:
        # Sử dụng HEAD request để kiểm tra nhanh hơn
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        
        if response.status_code == 200:
            status = "working"
            error = None
        elif response.status_code == 404:
            status = "not_found"
            error = "File không tồn tại (404)"
        elif response.status_code in [403, 401]:
            status = "forbidden"
            error = f"Không có quyền truy cập ({response.status_code})"
        elif response.status_code >= 500:
            status = "server_error"
            error = f"Lỗi server ({response.status_code})"
        else:
            status = "unknown"
            error = f"Mã trạng thái không xác định ({response.status_code})"
            
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
            "error": "Timeout - Phản hồi quá chậm"
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status": "connection_error",
            "status_code": None,
            "error": "Lỗi kết nối - Không thể kết nối đến server"
        }
    except Exception as e:
        return {
            "url": url,
            "status": "error",
            "status_code": None,
            "error": f"Lỗi không xác định: {str(e)}"
        }

def check_links_parallel(urls, max_workers=10, timeout=10):
    """
    Kiểm tra nhiều link song song
    
    Args:
        urls (list): Danh sách URL cần kiểm tra
        max_workers (int): Số thread tối đa
        timeout (int): Thời gian timeout cho mỗi request
        
    Returns:
        list: Danh sách kết quả kiểm tra
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tất cả các task
        future_to_url = {executor.submit(check_link_status, url, timeout): url for url in urls}
        
        # Xử lý kết quả khi hoàn thành
        for i, future in enumerate(as_completed(future_to_url), 1):
            result = future.result()
            results.append(result)
            
            # Hiển thị tiến trình
            status_symbol = "✓" if result["status"] == "working" else "✗"
            print(f"[{i}/{len(urls)}] {status_symbol} {result['url'][:60]}...")
            
            # Delay nhỏ để không spam server
            time.sleep(0.1)
    
    return results

def main():
    """
    Hàm chính
    """
    input_file = 'archive_links.txt'
    working_file = 'working_links.txt'
    broken_file = 'broken_links.txt'
    report_file = 'link_check_report.txt'
    
    # Kiểm tra file input
    if not os.path.exists(input_file):
        print(f"Lỗi: Không tìm thấy file '{input_file}'")
        print("Vui lòng tạo file 'archive_links.txt' và thêm các link cần kiểm tra vào đó.")
        return
    
    try:
        # Đọc danh sách URLs
        with open(input_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f.readlines() if line.strip()]
        
        if not urls:
            print("File input trống!")
            return
            
        print(f"Bắt đầu kiểm tra {len(urls)} link...")
        print("Đang kiểm tra (có thể mất vài phút)...\n")
        
        start_time = time.time()
        
        # Kiểm tra tất cả links
        results = check_links_parallel(urls, max_workers=5, timeout=15)
        
        end_time = time.time()
        
        # Phân loại kết quả
        working_links = []
        broken_links = []
        
        for result in results:
            if result["status"] == "working":
                working_links.append(result["url"])
            else:
                broken_links.append(result)
        
        # Ghi file kết quả
        # File links hoạt động
        with open(working_file, 'w', encoding='utf-8') as f:
            for link in working_links:
                f.write(link + '\n')
        
        # File links không hoạt động
        with open(broken_file, 'w', encoding='utf-8') as f:
            for result in broken_links:
                f.write(f"{result['url']}\n")
        
        # File báo cáo chi tiết
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== BÁO CÁO KIỂM TRA LINK ===\n")
            f.write(f"Thời gian kiểm tra: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Tổng thời gian: {end_time - start_time:.2f} giây\n")
            f.write(f"Tổng số link: {len(urls)}\n")
            f.write(f"Link hoạt động: {len(working_links)}\n")
            f.write(f"Link không hoạt động: {len(broken_links)}\n")
            f.write(f"Tỷ lệ thành công: {len(working_links)/len(urls)*100:.1f}%\n\n")
            
            if broken_links:
                f.write("=== CHI TIẾT LINK KHÔNG HOẠT ĐỘNG ===\n")
                for result in broken_links:
                    f.write(f"URL: {result['url']}\n")
                    f.write(f"Lỗi: {result['error']}\n")
                    f.write(f"Status Code: {result['status_code']}\n")
                    f.write("-" * 50 + "\n")
        
        # Thống kê
        print(f"\n{'='*50}")
        print("KẾT QUẢ KIỂM TRA")
        print(f"{'='*50}")
        print(f"Tổng số link: {len(urls)}")
        print(f"✓ Hoạt động: {len(working_links)} ({len(working_links)/len(urls)*100:.1f}%)")
        print(f"✗ Không hoạt động: {len(broken_links)} ({len(broken_links)/len(urls)*100:.1f}%)")
        print(f"⏱️  Thời gian: {end_time - start_time:.2f} giây")
        print(f"\nFile kết quả:")
        print(f"  - Link hoạt động: '{working_file}'")
        print(f"  - Link không hoạt động: '{broken_file}'")
        print(f"  - Báo cáo chi tiết: '{report_file}'")
        
        # Thống kê theo loại lỗi
        if broken_links:
            error_stats = {}
            for result in broken_links:
                status = result["status"]
                error_stats[status] = error_stats.get(status, 0) + 1
            
            print(f"\nThống kê lỗi:")
            for status, count in error_stats.items():
                status_name = {
                    "not_found": "Không tìm thấy (404)",
                    "forbidden": "Không có quyền truy cập",
                    "timeout": "Timeout",
                    "connection_error": "Lỗi kết nối",
                    "server_error": "Lỗi server",
                    "error": "Lỗi khác"
                }.get(status, status)
                print(f"  - {status_name}: {count}")
        
    except FileNotFoundError:
        print(f"Lỗi: Không thể đọc file '{input_file}'")
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    main()