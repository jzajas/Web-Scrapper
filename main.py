from urllib.request import urlopen
from bs4 import BeautifulSoup
import time
import os
from dotenv import load_dotenv


load_dotenv()
PRODUCTS = {}
BASE_SEARCH_URL = os.getenv("BASE_SEARCH_URL")
CARD_NAME = os.getenv("CARD_NAME")
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY"))


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


card_name = CARD_NAME.strip().replace(" ", "+")
available_products = []
current_page = 1

url = get_url(card_name, current_page)
html = urlopen(url).read().decode("utf-8")
max_pages = get_max_page(html)

while current_page <= max_pages:
    print(f"CURRENT PAGE: {current_page}")
    time.sleep(REQUEST_DELAY)

    url = get_url(card_name, current_page)
    html = urlopen(url).read().decode("utf-8")

    products = fetch_products(html)
    products = [p for p in products if "soldout" not in p.get("class", [])]

    for product in products:
        extracted = extract_product_data(product)
        if extracted:
            name, price, url = extracted
            save_product(name, price, url)

    current_page += 1


print(PRODUCTS)
