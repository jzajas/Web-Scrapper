from dotenv import load_dotenv
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
import time
import os
import re


load_dotenv()
PRODUCTS = {}
BASE_SEARCH_URL = os.getenv("BASE_SEARCH_URL")
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY"))
BASIC_LANDS = {"Plains", "Swamp", "Mountain", "Forest", "Island"}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url, retries=5, delay=5):
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8")

        except HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                print(f"[Retry {attempt}/{retries}] HTTP {e.code} → sleeping {delay}s")
                time.sleep(delay)
            else:
                raise

        except URLError as e:
            print(f"[Network error] {e} → sleeping {delay}s")
            time.sleep(delay)

    raise RuntimeError(f"Failed to fetch {url} after {retries} retries")


def get_max_page(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")

    pagination = soup.find("ul", class_="pagination")
    if not pagination:
        return 1

    pages = [
        int(a.get_text(strip=True))
        for a in pagination.find_all("a")
        if a.get_text(strip=True).isdigit()
    ]

    return max(pages) if pages else 1


def get_url(name: str, page: int) :
    return (
        f"{BASE_SEARCH_URL}"
        f"?query={name}"
        f"&page={page}"
        f"&order=desc"
        f"&sort=relevance"
        f"&n=128"
    )


def fetch_products(html: str):
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("article", class_="product-column")


def extract_product_data(product):
    link = product.find("a", class_="link")
    if not link:
        return None

    card_name = link.get("data-name")
    card_price = link.get("data-price")
    card_url = link.get("href")

    if not (card_name and card_price and card_url):
        return None

    return card_name.strip(), float(card_price), card_url.strip()


def save_product(name: str, price, url: str) -> None:
    if name not in PRODUCTS:
        PRODUCTS[name] = {}

    PRODUCTS[name][url] = price


def extract_names(filename: str) -> list[str]:
    names = []

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            line = re.sub(r"^\d+\s+", "", line)
            line = line.split(" / ")[0]
            line = re.sub(r"\s*\(.*$", "", line)
            line = re.sub(r"\s*\*.*\*$", "", line)

            names.append(line)

    return names


def save_products_to_bookmarks(filename="bookmarks.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n")
        f.write("<META HTTP-EQUIV='Content-Type' CONTENT='text/html; charset=UTF-8'>\n")
        f.write("<TITLE>Products</TITLE>\n<H1>Products</H1>\n<DL><p>\n")

        for name, entries in PRODUCTS.items():
            f.write(f"<DT><H3>{name}</H3>\n<DL><p>\n")
            for url, price in entries.items():
                f.write(f"<DT><A HREF='{url}'>{price}</A>\n")
            f.write("</DL><p>\n")

        f.write("</DL><p>")


def scrape_card(original_name: str) -> None:
    search_card_name = re.sub(" ", "+", original_name)
    search_card_name = search_card_name.strip()

    if search_card_name in BASIC_LANDS:
        return

    print(f"\n=== SCRAPING: {search_card_name} ===")

    try:
        first_url = get_url(search_card_name, 1)
        first_html = fetch_html(first_url)
        max_pages = get_max_page(first_html)
    except RuntimeError:
        print(f"[SKIP] Failed initial request for {search_card_name}")
        return

    for page in range(1, max_pages + 1):
        print(f"Page {page}/{max_pages}")
        time.sleep(REQUEST_DELAY)

        try:
            html = first_html if page == 1 else fetch_html(get_url(search_card_name, page))
        except RuntimeError:
            print(f"[SKIP PAGE] {search_card_name} page {page}")
            continue

        products = fetch_products(html)

        for product in products:
            if "soldout" in product.get("class", []):
                continue

            extracted = extract_product_data(product)
            if not extracted:
                continue

            name, price, url = extracted

            if name.startswith(original_name):
                print("saved product")
                save_product(name, price, url)


def scrape_deck(deck_file: str) -> None:
    cards = extract_names(deck_file)

    for card in cards:
        scrape_card(card)

    save_products_to_bookmarks()


if __name__ == "__main__":
    scrape_deck("deck.txt")
