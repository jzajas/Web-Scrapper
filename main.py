from urllib.request import urlopen
from bs4 import BeautifulSoup
import time
import os
from dotenv import load_dotenv
import re
import json


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



cards = extract_names("deck.txt")
for card in cards:
    card_name = card.strip().replace(" ", "+")
    available_products = []
    current_page = 1

    url = get_url(card_name, current_page)
    html = urlopen(url).read().decode("utf-8")
    max_pages = get_max_page(html)

    while current_page <= max_pages:
        print(f"CURRENT PAGE: {current_page} for {card}")
        time.sleep(REQUEST_DELAY)

        url = get_url(card_name, current_page)
        html = urlopen(url).read().decode("utf-8")

        products = fetch_products(html)
        products = [p for p in products if "soldout" not in p.get("class", [])]

        for product in products:
            extracted = extract_product_data(product)
            if extracted:
                name, price, url = extracted
                if str(name).startswith(card):
                    print("FOUND STH!")
                    save_product(name, price, url)

        current_page += 1


save_products_to_bookmarks()