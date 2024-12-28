import requests
from bs4 import BeautifulSoup
import csv
import json
import os
from urllib.parse import urlparse
from pathlib import Path

def download_image(url, folder_path, product_handle, image_type):
    """Download image and return local path"""
    if not url:
        return None
        
    # Create folder if it doesn't exist
    Path(folder_path).mkdir(parents=True, exist_ok=True)
    
    try:
        # Get file extension from URL
        ext = os.path.splitext(urlparse(url).path)[1]
        if not ext:
            ext = '.jpg'
            
        # Create filename
        filename = f"{product_handle}_{image_type}{ext}"
        filepath = os.path.join(folder_path, filename)
        
        # Download image if it doesn't exist
        if not os.path.exists(filepath):
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return filepath
        
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

def scrape_lama_retail():
    url = "https://lamaretail.com/collections/man-jackets-coats"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes
    except requests.RequestException as e:
        print(f"Failed to fetch the page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    print(f"\nScraping men's jackets and coats from: {url}")
    
    # Verify we're on the right collection page
    collection_title = soup.select_one('h1.collection-hero__title')
    if collection_title:
        print(f"Collection found: {collection_title.text.strip()}")
    
    # Simplify the product container selection
    products = soup.select('div.grid__item.grid-product')
    print(f"\nFound {len(products)} products in the men's jackets collection")

    # Create images folder
    images_folder = os.path.join(os.path.dirname(__file__), 'images')

    products_data = []
    for index, product in enumerate(products, 1):
        try:
            # Get product metadata
            product_handle = product.get('data-product-handle', '')
            product_id = product.get('data-product-id', '')
            
            # Get product content div
            content = product.select_one('.grid-product__content')
            if not content:
                continue
                
            # Get product info - updated selectors
            name = content.select_one('.grid-product__title, .grid-product__title--body')
            name = name.text.strip() if name else "Name not found"
            
            # Updated price selectors
            regular_price = content.select_one('.grid-product__price--original .money, .price-item--regular')
            sale_price = content.select_one('.grid-product__price:not(.grid-product__price--original) .money')
            
            # Get product images - updated selectors
            primary_img = product.select_one('.image-wrap img, .grid__image img')
            secondary_img = product.select_one('.grid-product__secondary-image img')
            
            # Download images
            primary_image_url = f"https:{primary_img['src']}" if primary_img and 'src' in primary_img.attrs else None
            secondary_image_url = f"https:{secondary_img['src']}" if secondary_img and 'src' in secondary_img.attrs else None
            
            primary_image_path = download_image(primary_image_url, images_folder, product_handle, 'primary')
            secondary_image_path = download_image(secondary_image_url, images_folder, product_handle, 'secondary')
            
            products_data.append({
                'name': name,
                'product_id': product_id,
                'handle': product_handle,
                'regular_price': regular_price.text.strip() if regular_price else None,
                'sale_price': sale_price.text.strip() if sale_price else None,
                'is_on_sale': bool(sale_price),
                'primary_image_url': primary_image_url,
                'secondary_image_url': secondary_image_url,
                'primary_image_path': primary_image_path,
                'secondary_image_path': secondary_image_path,
                'link': f"https://lamaretail.com/products/{product_handle}" if product_handle else None
            })
            print(f"[{index}/{len(products)}] Processing: {name}")
            print(f"  - Downloaded images to: {images_folder}")
            
        except Exception as e:
            print(f"Error processing product #{index}: {str(e)}")
            continue

    print(f"\nSuccessfully scraped {len(products_data)} products")
    return products_data

def save_to_csv(data):
    if not data:
        print("No data to save!")
        return
        
    fields = ['name', 'product_id', 'handle', 'regular_price', 'sale_price', 'is_on_sale', 
              'primary_image_url', 'secondary_image_url', 'primary_image_path', 'secondary_image_path', 'link']
    
    csv_path = os.path.join(os.path.dirname(__file__), 'lama_products.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
        print(f"Data saved to: {csv_path}")

def main():
    print("Starting scraping process...")
    products_data = scrape_lama_retail()
    save_to_csv(products_data)
    print(f"Scraping complete! Found {len(products_data)} products.")

if __name__ == "__main__":
    main()
