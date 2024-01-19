import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def extract_items(ul_element, depth, base_url):
    items = []
    list_items = ul_element.find_all('li', recursive=False)
    if len(list_items) == 0:
        list_items = ul_element.find('ul', recursive=False).find_all('li', recursive=False)

    for li in list_items:
        header = li.contents[0]
        title = header.get_text(strip=True)
        link = header.find('a').get('href') if header.find('a') else None
        text = extract_text_from_url(urljoin(base_url, link)) if link else None
        item = {'name': title, 'link': link, 'text': text}

        # Recursively extract nested items
        next_ul = li.find('ul', recursive=False)
        if next_ul and depth < 4:  # Assuming a maximum depth of 4
            key_map = {1: 'sections', 2: 'chapters', 3: 'articles', 4: 'paragraphs'}
            key = key_map[depth + 1]
            item[key] = extract_items(next_ul, depth + 1, base_url)

        items.append(item)
    return items

def get_text_from_catechism(base_url):
    toc_url = urljoin(base_url, '_INDEX.HTM')
    try:
        response = requests.get(toc_url)
        response.raise_for_status()
        content = response.content
    except requests.RequestException as e:
        raise e

    soup = BeautifulSoup(content, 'html.parser')
    top_level_ul = soup.find('ul')
    items = extract_items(top_level_ul, 0, base_url)

    return items

def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
    except requests.RequestException as e:
        raise e

    soup = BeautifulSoup(content, 'html.parser')

    paragraphs = soup.find_all('p')
    list_text = []
    for p in paragraphs:
        for sup in p.find_all('sup'):
            sup.decompose()

        list_text.append(p.get_text(strip=True))

    # TODO: there are alot of \r\n in here that should be replaced by ' '
    # TODO: The leading line number is also removable (or extractable)
    output_text = '\n'.join(list_text)
    return output_text


# URL of the Vatican archive page
BASE_URL = "https://www.vatican.va/archive/ENG0015/"

text_data = get_text_from_catechism(BASE_URL)
print(text_data[0])
