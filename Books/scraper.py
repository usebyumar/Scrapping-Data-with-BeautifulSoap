import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict
import logging
import os
from urllib.parse import urlparse
from pathlib import Path

# Add these lines after the existing imports
import shutil
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BookScraper:
    def __init__(self):
        self.base_url = 'https://books.toscrape.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Add images directory creation
        self.base_images_dir = Path('images')
        self.base_images_dir.mkdir(exist_ok=True)

    def get_category_image_dir(self, category_name: str) -> Path:
        """Create and return category-specific image directory"""
        # Clean category name for filesystem
        safe_category_name = "".join(c if c.isalnum() or c in (' ','-','_') else '_' for c in category_name)
        category_dir = self.base_images_dir / safe_category_name
        category_dir.mkdir(exist_ok=True)
        return category_dir

    def get_categories(self) -> List[Dict]:
        try:
            logging.info(f"Fetching categories from {self.base_url}")
            response = self.session.get(self.base_url)
            response.raise_for_status()  # Raise exception for bad status codes
            soup = BeautifulSoup(response.content, 'html.parser')
            categories = []
            
            # Updated selector to match the specific category navigation
            for link in soup.select('.nav-list ul li a'):
                name = link.text.strip()
                url = link.get('href')
                if url and name != 'Books':  # Skip the main "Books" category
                    full_url = f"{self.base_url}/{url}" if not url.startswith('http') else url
                    categories.append({
                        'name': name,
                        'url': full_url
                    })
                    logging.info(f"Found category: {name}")
            
            return categories
        except Exception as e:
            logging.error(f"Error fetching categories: {e}")
            return []

    def download_image(self, image_url: str, category_name: str) -> str:
        try:
            # Get category-specific directory
            category_dir = self.get_category_image_dir(category_name)
            
            # Create unique filename from URL
            filename = hashlib.md5(image_url.encode()).hexdigest() + '.jpg'
            filepath = category_dir / filename
            
            # Don't download if already exists
            if filepath.exists():
                return str(filepath)

            # Download image
            response = self.session.get(image_url, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)
            
            logging.info(f"Downloaded image: {category_name}/{filename}")
            return str(filepath)
        except Exception as e:
            logging.error(f"Error downloading image {image_url}: {e}")
            return ''

    def get_books_from_category(self, category_url: str, category_name: str) -> List[Dict]:
        try:
            logging.info(f"Fetching books from {category_url}")
            response = self.session.get(category_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            books = []

            for book in soup.select('article.product_pod'):
                try:
                    image_url = self.base_url + '/' + book.select_one('img').get('src', '').lstrip('/')
                    local_image_path = self.download_image(image_url, category_name)
                    
                    book_data = {
                        'title': book.select_one('h3 a').get('title', ''),
                        'price': book.select_one('.price_color').text.strip(),
                        'rating': book.select_one('.star-rating').get('class')[1],
                        'availability': book.select_one('.instock').text.strip(),
                        'image_path': local_image_path,
                        'category': category_name
                    }
                    books.append(book_data)
                    logging.info(f"Processed book: {book_data['title']}")
                except Exception as e:
                    logging.error(f"Error processing book: {e}")
                    continue

            # Check for next page
            next_page = soup.select_one('li.next a')
            if next_page:
                next_url = category_url.rsplit('/', 1)[0] + '/' + next_page.get('href')
                books.extend(self.get_books_from_category(next_url, category_name))

            return books
        except Exception as e:
            logging.error(f"Error fetching books from {category_url}: {e}")
            return []

    def save_to_csv(self, data: List[Dict], filename: str):
        if not data:
            logging.warning("No data to save!")
            return
            
        # Convert image paths to relative paths
        for book in data:
            book['image_path'] = os.path.relpath(book['image_path'])
            
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        logging.info(f"Saved {len(data)} records to {filename}")

def main():
    scraper = BookScraper()
    
    # Get all categories
    categories = scraper.get_categories()
    logging.info(f"Found {len(categories)} categories")

    if not categories:
        logging.error("No categories found! Exiting...")
        return

    # Get books from each category
    all_books = []
    for category in categories:
        logging.info(f"Processing category: {category['name']}")
        books = scraper.get_books_from_category(category['url'], category['name'])
        all_books.extend(books)
        logging.info(f"Found {len(books)} books in {category['name']}")

    # Save results
    scraper.save_to_csv(all_books, 'books.csv')
    logging.info(f"Scraping completed. Total books scraped: {len(all_books)}")

if __name__ == "__main__":
    main()
