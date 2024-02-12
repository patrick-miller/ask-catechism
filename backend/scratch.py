import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import time
import pickle
from llama_index import VectorStoreIndex
from llama_index.schema import TextNode, NodeRelationship, RelatedNodeInfo

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
    SCRAPED_DATA_FILE = './data/text_data.pkl'
    NODES_FILE = './data/nodes.pkl'
    STORAGE_DIR = './storage'
    # Can be 'section', 'chapter', 'article' or 'paragraph'
    SUMMARIZATION_LEVEL = 'paragraph'

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def extract_items(ul_element, depth):
    items = []
    other_ul = ul_element.find('ul', recursive=False)
    list_items = ul_element.find_all('li', recursive=False)
    
    if other_ul:
        logger.info(f'Another list found within the UL: {depth}')
        item = {'name': '', 'link': '', 'text': '', Config.KEY_MAP[depth + 1]: extract_items(other_ul, depth + 1)}
        items.append(item)

    for li in list_items:
        item = process_list_item(li, depth)
        items.append(item)
    
    return items

def process_list_item(li, depth):
    if depth >= Config.MAX_DEPTH:
        return None
        
    header = li.contents[0]
    title = header.get_text(strip=True)

    logger.info(f"Started extracting data for: {title}")

    link = header.find('a').get('href') if header.find('a') else None
    text = extract_text_from_url(urljoin(Config.BASE_URL, link)) if link else None
    item = {'name': title, 'link': link, 'text': text}

    if next_ul := li.find('ul', recursive=False):
        item[Config.KEY_MAP[depth + 1]] = extract_items(next_ul, depth + 1)

    logger.info(f"Finished extracting data for: {title}")

    return item

def extract_text_from_url(url):
    try:
        time.sleep(Config.REQUEST_INTERVAL)  # Rate limiting
        response = requests.get(url)
        response.raise_for_status()
        content = response.content
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve data from URL: {url} Error: {e}")
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
    logger.info("Extracting text from Catechism site")
    toc_url = urljoin(Config.BASE_URL, '_INDEX.HTM')
    try:
        response = requests.get(toc_url)
        response.raise_for_status()
        content = response.content
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve table of contents: {e}")
        raise

    soup = BeautifulSoup(content, 'html.parser')
    top_level_ul = soup.find('ul')
    return extract_items(top_level_ul, 0)

def load_data_from_file_or_collect(file, function):
    if os.path.exists(file):
        try:
            # Load from pickle file if it exists
            with open(file, 'rb') as f:
                data = pickle.load(f)
            logger.info("Data loaded from pickle file.")
        except Exception as e:
            logger.error(f"Error loading data from pickle file: {e}")
            return
    else:
        try:
            # Fetch data and save to pickle file
            data = function()
            with open(Config.SCRAPED_DATA_FILE, 'wb') as f:
                pickle.dump(data, f)
            logger.info("Data fetched and saved to pickle file.")
        except Exception as e:
            logger.error(f"An error occurred while fetching data: {e}")
            return
    return data

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

def create_node_stucture(text_data, summarization_level):
    nodes = []
    for part in text_data:
        part_node = create_node(part['name'], part['link'], part['text'], 'part')
        nodes.append(part_node)
        nodes += process_nodes(part.get('sections', []), part_node, 'section', summarization_level)

    for i in range(len(nodes)):
        if i < len(nodes) - 1:
            nodes[i].relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=nodes[i+1].node_id)
        if i > 0:
            nodes[i].relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=nodes[i-1].node_id)

    return nodes

if __name__ == "__main__":
    logger.info("Creating new index")
    
    text_data = load_data_from_file_or_collect(Config.SCRAPED_DATA_FILE, get_text_from_catechism)

    nodes = create_node_stucture(text_data, Config.SUMMARIZATION_LEVEL)

    # index = VectorStoreIndex(nodes)
    # index.storage_context.persist(Config.STORAGE_DIR)
    
    # logger.info(f"Finished creating new index. Stored in {Config.STORAGE_DIR}")
    
    



    ### TODO: save down the nodes for retrieval




    ##### RECOMMENDATION: Go with the paragraph level chunking and an 8k context window. Need massaging of the max token chunk.

    ### Debugging strategies around chunking
    # character_lengths = []
    # for n in nodes:
    #     print(n.get_metadata_str())
    #     print(len(n.text))
    #     character_lengths += [len(n.text)]
    #     pass
    # print('Summary Statistics')
    # print(f'Total characters: {sum(character_lengths)}')
    # print(f'Number of nodes: {len(nodes)}')
    # print(f'Average characters per node: {sum(character_lengths) / len(nodes)}')
    # print(f'Max characters per node: {max(character_lengths)}')
    
    # For the most granular (paragraphs), the max characters is 33k and the average is 3k.
    # That gives us ~8k tokens for the max (need to verify)
    # For the next level up (articles), the max characters is 110k and the average is 11k
    # That gives us ~28k tokens for the max (need to verify)
    # For the next level up (chapters), the max characters is 182k and the average is 31k
    # That gives us ~46k tokens for the max (need to verify)


    ### Print all of the numbers in the text
    ### Turn this into a test
    # import re
    # all_numbers = []
    # for n in nodes:
    #     t = n.text
    #     integer_numbers = re.findall(r'\b\d+\b', t)

    #     # Convert the extracted strings to integers
    #     integer_numbers = [int(number) for number in integer_numbers]
    #     all_numbers += integer_numbers
    
    # missing_numbers = [number for number in range(1, 2866) if number not in all_numbers]
    # print(missing_numbers)
    # This should be empty


    # ### This checks the structure of the table of contents
    # for part in text_data:
    #     print(part['name'])
    #     for section in part['sections']:
    #         print(section['name'])
    #         for chapter in section['chapters']:
    #             print(chapter['name'])
    #             for article in chapter.get('articles', []):
    #                 print(article['name'])
    #                 for paragraph in article.get('paragraphs', []):
    #                     print(paragraph['name'])
