import os
import logging
import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import threading
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text widget."""
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        formatter = logging.Formatter('%(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.configure(state='disabled')
            self.text_widget.yview(tk.END)
        self.text_widget.after(0, append)

def get_cartridge_links(url):
    logger.info(f"Fetching cartridge links from: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to retrieve cartridge links from {url}: {e}")
        return []
    soup = BeautifulSoup(response.content, 'html.parser')
    cartridge_links = []
    for cart_div in soup.select('div.cart'):
        link = cart_div.find('a', href=True)
        if link and link['href'].startswith('/play?cart='):
            full_url = f'https://tic80.com{link["href"]}'
            cartridge_links.append(full_url)
            logger.debug(f"Found cartridge link: {full_url}")
    logger.info(f"Total cartridges found: {len(cartridge_links)}")
    return cartridge_links

def download_tic_file(url, folder_path):
    logger.debug(f"Accessing cartridge page for download: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to access cartridge page {url}: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Download the .tic file
    tic_link = soup.select_one('a[href$=".tic"]')
    if tic_link:
        tic_url = f'https://tic80.com{tic_link.get("href")}'
        tic_filename = tic_url.split('/')[-1]
        logger.debug(f"Downloading .tic file from: {tic_url}")
        try:
            tic_response = requests.get(tic_url)
            tic_response.raise_for_status()
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, tic_filename)
            with open(file_path, 'wb') as file:
                file.write(tic_response.content)
            logger.info(f"Downloaded and saved file: {file_path}")
        except requests.RequestException as e:
            logger.error(f"Failed to download .tic file from {tic_url}: {e}")
            return
    else:
        logger.warning(f"No .tic download link found on page: {url}")
        return

    # Download metadata (GIF image, description, and author)
    image_meta = soup.select_one('meta[property="og:image"]')
    description_meta = soup.select_one('meta[name="description"]')
    author_meta = soup.select_one('meta[name="author"]')

    if image_meta and 'content' in image_meta.attrs:
        image_url = image_meta['content']
        image_filename = os.path.splitext(tic_filename)[0] + os.path.splitext(image_url)[1]
        images_folder = os.path.join(folder_path, 'images')
        os.makedirs(images_folder, exist_ok=True)
        image_path = os.path.join(images_folder, image_filename)
        try:
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            with open(image_path, 'wb') as img_file:
                img_file.write(image_response.content)
            logger.info(f"Downloaded and saved image: {image_path}")
        except requests.RequestException as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
    else:
        logger.warning("No image metadata found")

    description = description_meta['content'] if description_meta and 'content' in description_meta.attrs else "No description available"
    author = author_meta['content'].replace('by ', '') if author_meta and 'content' in author_meta.attrs else "Unknown author"

    # Update gamelist.xml
    gamelist_path = os.path.join(folder_path, 'gamelist.xml')
    game_name = os.path.splitext(tic_filename)[0].replace('_', ' ')

    # Load or create XML structure
    if os.path.exists(gamelist_path):
        tree = ET.parse(gamelist_path)
        root = tree.getroot()
    else:
        root = ET.Element('gameList')
        tree = ET.ElementTree(root)

    # Add game entry
    game_element = ET.SubElement(root, 'game')
    ET.SubElement(game_element, 'path').text = f'./{tic_filename}'
    ET.SubElement(game_element, 'name').text = game_name
    ET.SubElement(game_element, 'desc').text = description
    ET.SubElement(game_element, 'developer').text = author
    ET.SubElement(game_element, 'image').text = f'./images/{image_filename}'

    # Format XML with indentation (Python 3.9+)
    try:
        ET.indent(tree, space="  ", level=0)
    except AttributeError:
        # Manual pretty-printing if `ET.indent` is not available
        from xml.dom import minidom
        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        pretty_xml = "\n".join(line for line in pretty_xml.splitlines() if line.strip())

        # Write to file
        with open(gamelist_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
    else:
        # Write formatted XML directly
        tree.write(gamelist_path, encoding="utf-8", xml_declaration=True)
    logger.info(f"Updated or created gamelist.xml with entry for: {tic_filename}")

def download_tic_file2(url, folder_path):
    logger.debug(f"Accessing cartridge page for download: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to access cartridge page {url}: {e}")
        return
    soup = BeautifulSoup(response.content, 'html.parser')
    tic_link = soup.select_one('a[href$=".tic"]')
    if tic_link:
        tic_url = f'https://tic80.com{tic_link.get("href")}'
        tic_filename = tic_url.split('/')[-1]
        logger.debug(f"Downloading .tic file from: {tic_url}")
        try:
            tic_response = requests.get(tic_url)
            tic_response.raise_for_status()
            os.makedirs(folder_path, exist_ok=True)
            file_path = os.path.join(folder_path, tic_filename)
            with open(file_path, 'wb') as file:
                file.write(tic_response.content)
            logger.info(f"Downloaded and saved file: {file_path}")
        except requests.RequestException as e:
            logger.error(f"Failed to download .tic file from {tic_url}: {e}")
    else:
        logger.warning(f"No .tic download link found on page: {url}")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("TIC-80 Cart Downloader")

        # URL Frame
        url_frame = ttk.Frame(root)
        url_frame.pack(padx=10, pady=5, fill='x')

        ttk.Label(url_frame, text="TIC-80 Games URL:").pack(side='left')
        self.url_var = tk.StringVar(value='https://tic80.com/play?cat=0&sort=2&page=0')
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        url_entry.pack(side='left', expand=True, fill='x')

        # Download Folder Frame
        folder_frame = ttk.Frame(root)
        folder_frame.pack(padx=10, pady=5, fill='x')

        ttk.Label(folder_frame, text="Download Folder:").pack(side='left')
        self.folder_var = tk.StringVar(value='tic_files')
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=50)
        folder_entry.pack(side='left', expand=True, fill='x')
        browse_button = ttk.Button(folder_frame, text="Browse", command=self.browse_folder)
        browse_button.pack(side='left')

        # Start Button
        start_button = ttk.Button(root, text="Start Download", command=self.start_download)
        start_button.pack(pady=5)

        # Log Text Widget
        self.log_text = tk.Text(root, state='disabled', height=15)
        self.log_text.pack(padx=10, pady=5, fill='both', expand=True)

        # Set up logging to the text widget
        text_handler = TextHandler(self.log_text)
        logger.addHandler(text_handler)

        # For threading
        self.thread = None

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_var.set(folder_selected)

    def start_download(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.run_download)
            self.thread.start()
        else:
            logger.warning("Download already in progress")

    def run_download(self):
        url = self.url_var.get()
        folder = self.folder_var.get()
        logger.info("Starting process to fetch and download TIC-80 cartridges")

        cartridge_links = get_cartridge_links(url)
        for link in cartridge_links:
            download_tic_file(link, folder)

        logger.info("Finished fetching and downloading TIC-80 cartridges")

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == '__main__':
    main()
