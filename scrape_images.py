"""
Food Image Scraper
==================

功能描述：
从 Bing 图片搜索下载指定食物类别的图片，用于测试模型的泛化能力。

使用方法：
python scrape_images.py --query "apple pie" --limit 5 --output "test_images"

参数：
--query: 搜索关键词 (例如 "sushi", "hamburger")
--limit: 下载图片数量 (默认 5)
--output: 保存目录 (默认 "test_images")
"""

import os
import requests
import argparse
from pathlib import Path
import re
import time
from datetime import datetime
import html as html_lib

# 模拟浏览器请求头，防止被反爬虫拦截
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.bing.com/",
}

def clean_filename(query):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "", query).replace(" ", "_")

def download_image(url, save_path):
    """下载单张图片"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        # 检查内容类型是否为图片
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            print(f"Skipping non-image url: {url}")
            return False

        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def scrape_bing_images(query, limit, output_dir):
    """
    从 Bing 搜索并下载图片。
    注意：这是一个简化的实现，通过解析 Bing 搜索结果页面的 HTML 寻找图片链接。
    对于大规模爬取，建议使用官方 API 或更复杂的 Selenium/Playwright 方案。
    """
    print(f"Searching for '{query}'...")
    
    # 创建输出目录
    save_dir = Path(output_dir) / clean_filename(query)
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Bing 图片搜索 URL
    search_url = f"https://www.bing.com/images/search?q={query}&form=HDRSC2&first=1"
    
    try:
        response = requests.get(search_url, headers=HEADERS)
        response.raise_for_status()
        # 解码 HTML 实体 (例如 &quot; -> ")
        html_content = html_lib.unescape(response.text)
        
        # 尝试多种正则模式匹配图片链接
        patterns = [
            r'murl":"(https?://[^"]+)"',
            r'mediaurl":"(https?://[^"]+)"', 
            r'imgurl":"(https?://[^"]+)"',
        ]
        
        image_urls = []
        for pattern in patterns:
            found = re.findall(pattern, html_content)
            if found:
                image_urls.extend(found)
                if len(image_urls) > limit * 2:
                    break
        
        # 去重
        image_urls = list(set(image_urls))
        
        print(f"Found {len(image_urls)} images.")
        
        count = 0
        for i, url in enumerate(image_urls):
            if count >= limit:
                break
                
            # 文件名：keyword_timestamp_index.jpg
            timestamp = int(time.time())
            filename = f"{clean_filename(query)}_{timestamp}_{i}.jpg"
            save_path = save_dir / filename
            
            print(f"Downloading {i+1}/{limit}: {url}")
            if download_image(url, save_path):
                count += 1
                print(f"✅ Saved to {save_path}")
            
            # 礼貌性延时
            time.sleep(0.5)
            
        print(f"\nDone! Downloaded {count} images to {save_dir}")
        
    except Exception as e:
        print(f"Error scraping images: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple Food Image Scraper")
    parser.add_argument("--query", type=str, required=True, help="Food name to search (e.g., 'pizza')")
    parser.add_argument("--limit", type=int, default=5, help="Number of images to download")
    parser.add_argument("--output", type=str, default="test_images", help="Output directory")
    
    args = parser.parse_args()
    
    scrape_bing_images(args.query, args.limit, args.output)
