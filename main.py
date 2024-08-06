import yaml
import feedparser
import requests
from requests.adapters import HTTPAdapter
from time import struct_time
import time
from dateutil import parser
import re
import logging
import logging.config
import sys
import json
import schedule
import transmission_rpc

# Load the configuration file
logging.config.fileConfig('logging.conf')

# Create a logger
log = logging.getLogger('sampleLogger')


class DownloadItem:
    def __init__(self, title: str, time: float, url: str):
        self.title = title
        self.time = time
        self.url = url
        pass
    pass


# Function to parse the RSS feed and extract magnet links
def parse_rss_feed(url: str, proxy: str, time_since: float, title_match: list[str]) -> list[DownloadItem]:
    # Create a session with proxy support
    session = requests.Session()
    if proxy:
        session.proxies = {
            'http': proxy,
            'https': proxy
        }
    
    # Retry strategy for the session
    # retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    # session.mount('http://', HTTPAdapter(max_retries=retries))
    # session.mount('https://', HTTPAdapter(max_retries=retries))

    # Build title matching regex
    title_pattern: list[re.Pattern] = []
    for pattern in title_match:
        title_pattern.append(re.compile(pattern))
    
    try:
        response = session.get(url)
        response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        feed = feedparser.parse(response.content)
    except requests.RequestException as e:
        log.error(f"Error fetching RSS feed from {url}: {e}")
        return []
    
    items = feed.get('items', [])
    magnets = []
    for item in items:
        if item.has_key("published_parsed"):
            published_time = time.mktime(item.published_parsed)
            if published_time <= time_since:
                continue

        is_match = True
        for reg in title_pattern:
            if reg.search(item.title) == None:
                is_match =False
                break
        
        if not is_match:
            log.debug("Ignore %s title not match", item.title)
            continue

        for link in item.get("links", []):
            if link.get("type", "") == "application/x-bittorrent":
                if link.has_key("href"):
                    magnets.append(DownloadItem(item.title, time.mktime(item.published_parsed), link.href))
    return magnets

# Load the YAML configuration
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)
        

# Function to add a torrent
def download_torrent(url: str, download_dir: str, proxy: str, config: dict[dict]):
    transmission = transmission_rpc.Client(
        host=config.get("transmission_rpc_host"),
        port=config.get("transmission_rpc_port"),
    )

    # download torrent file through a proxy if have
    if url.startswith("http"):
        session = requests.Session()
        if proxy:
            session.proxies = {
                'http': proxy,
                'https': proxy
            }
        log.debug(f"Download torrent file from '{url}'")
        response = session.get(url)
        response.raise_for_status()
        torrent_file = response.content
        
        log.debug(f"Upload torrent file to transmission")
        transmission.add_torrent(torrent_file, download_dir=download_dir)
    elif url.startswith("magnet"):
        transmission.add_torrent(url, download_dir=download_dir)

def fetch_feeds():

    log.info("Start fetching download feeds")
    
    config_file = "config.yaml"  # Path to your YAML config file
    config = load_config(config_file)
    
    global_proxy = config.get('global_proxy')  # Get global proxy setting
    for download in config.get('task', []):
        name = download.get('name')
        rss_url = download.get('rss')
        save_to = download.get('save_to')
        # Use the proxy specified for the individual download, or fallback to global proxy
        proxy = download.get('proxy', global_proxy)
        since = download.get('since', 0)
        title_match = download.get('title_match', [])

        if (not 'since' in download):
            log.warn("Missing time since, will fetch all links")

        if isinstance(since, str):
            dt = parser.parse(since)
            since = dt.timestamp()
            download['since'] = since

        
        log.info(f"Fetching: {name}, save to {save_to}")
        
        # Parse the RSS feed and get magnet links
        if rss_url:
            magnet_links = parse_rss_feed(rss_url, proxy, since, title_match)
            for magnet in magnet_links:
                log.info(f"Download {magnet.title}")
                download_torrent(magnet.url, save_to, proxy, config)

            if len(magnet_links) > 0:
                last_link = max(magnet_links, key=lambda item: item.time)
                log.info(f"Update last update time as {last_link.time}")
                download['since'] = last_link.time
            else:
                log.info("No new feeds")

    with open(config_file, "w", encoding='utf-8') as file:
        yaml.safe_dump(config, file, allow_unicode=True)

if __name__ == "__main__":
    config_file = "config.yaml"  # Path to your YAML config file
    config = load_config(config_file)
    
    fetch_feeds()

    
