import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import time
import pickle

class Config:
    BASE_URL = "https://www.vatican.va/archive/ENG0015/"
    MAX_DEPTH = 4
    REQUEST_INTERVAL = 0.1  # seconds
    KEY_MAP = {1: 'sections', 2: 'chapters', 3: 'articles', 4: 'paragraphs'}
    SCRAPED_DATA_FILE = './text_data.pkl'

# Initialize logging
logging.basicConfig(level=logging.INFO)

def extract_items(ul_element, depth):
    items = []
    list_items = ul_element.find_all('li', recursive=False)
    
    if not list_items:
        list_items = ul_element.find('ul', recursive=False).find_all('li', recursive=False)

    for li in list_items:
        item = process_list_item(li, depth)
        items.append(item)
    
    return items

def process_list_item(li, depth):
    if depth >= Config.MAX_DEPTH:
        return None
    
    header = li.contents[0]
    title = header.get_text(strip=True)
    link = header.find('a').get('href') if header.find('a') else None
    text = extract_text_from_url(urljoin(Config.BASE_URL, link)) if link else None
    item = {'name': title, 'link': link, 'text': text}

    if next_ul := li.find('ul', recursive=False):
        item[Config.KEY_MAP[depth + 1]] = extract_items(next_ul, depth + 1)

    if depth == 0:
        logging.info(f"Finished extracting data for: {title}")

    return item

def extract_text_from_url(url):
    try:
        time.sleep(Config.REQUEST_INTERVAL)  # Rate limiting
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
    except requests.RequestException as e:
        logging.error(f"Failed to retrieve data from URL: {url} Error: {e}")
        raise

    soup = BeautifulSoup(content, 'html.parser')
    return process_paragraphs(soup)

def process_paragraphs(soup):
    paragraphs = soup.find_all('p')
    list_text = [cleanup_paragraph(p) for p in paragraphs]
    return '\n'.join(list_text)

def cleanup_paragraph(p):
    for sup in p.find_all('sup'):
        sup.decompose()
    return p.get_text(strip=True).replace('\r\n', ' ')

def get_text_from_catechism():
    logging.info("Extracting text from Catechism site")
    toc_url = urljoin(Config.BASE_URL, '_INDEX.HTM')
    try:
        response = requests.get(toc_url)
        response.raise_for_status()
        content = response.content
    except requests.RequestException as e:
        logging.error(f"Failed to retrieve table of contents: {e}")
        raise

    soup = BeautifulSoup(content, 'html.parser')
    top_level_ul = soup.find('ul')
    return extract_items(top_level_ul, 0)

def main():
    if os.path.exists(Config.SCRAPED_DATA_FILE):
        try:
            # Load from pickle file if it exists
            with open(Config.SCRAPED_DATA_FILE, 'rb') as f:
                text_data = pickle.load(f)
            logging.info("Data loaded from pickle file.")
        except Exception as e:
            logging.error(f"Error loading data from pickle file: {e}")
            return
    else:
        try:
            # Fetch data and save to pickle file
            text_data = get_text_from_catechism(Config.BASE_URL)
            with open(Config.SCRAPED_DATA_FILE, 'wb') as f:
                pickle.dump(text_data, f)
            logging.info("Data fetched and saved to pickle file.")
        except Exception as e:
            logging.error(f"An error occurred while fetching data: {e}")
            return

    print(text_data[0])

if __name__ == "__main__":
    main()
