import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import time
import pickle

class Config:
    BASE_URL = "https://www.vatican.va/archive/ENG0015/"
    MAX_DEPTH = 5
    REQUEST_INTERVAL = 0.1  # seconds
    KEY_MAP = {1: 'sections', 2: 'chapters', 3: 'articles', 4: 'paragraphs'}
    LEVELS = {
        'part': 'sections',
        'section': 'chapters',
        'chapter': 'articles',
        'article': 'paragraphs'
    }
    SCRAPED_DATA_FILE = './text_data.pkl'

# Initialize logging
logging.basicConfig(level=logging.INFO)

def extract_items(ul_element, depth):
    items = []
    list_items = ul_element.find_all('li', recursive=False)
    
    if not list_items:
        depth += 1
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
            text_data = get_text_from_catechism()
            with open(Config.SCRAPED_DATA_FILE, 'wb') as f:
                pickle.dump(text_data, f)
            logging.info("Data fetched and saved to pickle file.")
        except Exception as e:
            logging.error(f"An error occurred while fetching data: {e}")
            return

    return text_data


from llama_index.schema import TextNode, NodeRelationship, RelatedNodeInfo


def create_node(name, link, text, level):
    return TextNode(text='' if text is None else text, 
                    metadata={'link': link, 'title': name, 'level': level})

def add_child_relationship(parent_node, child_node):
    if NodeRelationship.CHILD in parent_node.relationships:
        parent_node.relationships[NodeRelationship.CHILD].append(RelatedNodeInfo(node_id=child_node.node_id))
    else:
        parent_node.relationships[NodeRelationship.CHILD] = [RelatedNodeInfo(node_id=child_node.node_id)]

def concatenate_texts(item, level):    
    # Recursive case: go deeper into the structure based on the level
    child_level_key = Config.LEVELS.get(level, '')
    
    child_texts = []
    if child_level_key in item:
        for child_item in item[child_level_key]:
            # Determine the child level based on the current level
            child_level = child_level_key[:-1]  # Remove the plural 's'
            child_texts.append(concatenate_texts(child_item, child_level))
    
    return '\n\n'.join(filter(None, [item.get('text', '')] + child_texts))

def process_nodes(items, parent_node, level, summarization_level):
    nodes = []
    for item in items:
        if level == summarization_level:
            # Use depth-first concatenation to gather text
            concatenated_text = concatenate_texts(item, level)
            item_node = create_node(item['name'], item['link'], concatenated_text, level)
        else:
            item_node = create_node(item['name'], item['link'], item['text'], level)

        nodes.append(item_node)
        add_child_relationship(parent_node, item_node)
        item_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=parent_node.node_id)

        # Decide whether to process next level items
        if level != summarization_level:
            child_level_key = Config.LEVELS.get(level, '')
            child_level = child_level_key[:-1]  # Remove the plural 's'

            if child_level_key in item:
                nodes += process_nodes(item[child_level_key], item_node, child_level, summarization_level)
    return nodes

if __name__ == "__main__":
    text_data = main()
    nodes = []
    # TODO: should we be creating a node if there is no text?

    summarization_level = 'article'  # Can be 'section', 'chapter', 'article' or 'paragraph'

    for part in text_data:
        part_node = create_node(part['name'], part['link'], part['text'], 'part')
        nodes.append(part_node)
        nodes += process_nodes(part.get('sections', []), part_node, 'section', summarization_level)

    for i in range(len(nodes)):
        if i < len(nodes) - 1:
            nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=nodes[i+1].node_id)
        if i > 0:
            nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=nodes[i-1].node_id)

    for n in nodes:
        print(n.get_metadata_str())
        print(len(n.text))
        pass
    # print(nodes[-1].text)
    # print(text_data[-2])

    print(text_data[-1]['sections'][-1]['chapters'][-1])

    # print(part)
    # print(nodes[0].node_id)
    # print(nodes[0].relationships)
    # print(nodes[1].node_id)
    # print(nodes[1].text)