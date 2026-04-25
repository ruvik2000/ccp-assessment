import sys
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List, Optional

def _handle_from_product_url(url: str) -> Optional[str]:
    if "/products/" not in url:
        return None
    return url.rstrip("/").split("/products/", 1)[-1].split("?")[0] or None


class Product(BaseModel):
    title: str
    url: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    handle: Optional[str] = None

def extract_catalog() -> List[Product]:
    url = "https://getmainelobster.com/collections/all"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    
    products = []
    
    # Targeting regular Shopify Dawn theme `.card-wrapper` as well as generic `.product-item`
    cards = soup.select(".card-wrapper")
    if not cards:
        cards = soup.select(".product-item")
    if not cards:
        cards = soup.select(".grid-view-item")
        
    for card in cards:
        try:
            # Title & URL
            heading = card.select_one(".card__heading a")
            if not heading:
                heading = card.find("a", href=True)
                
            if not heading or "products" not in heading.get("href", ""):
                continue
                
            product_url = heading["href"]
            if product_url.startswith("/"):
                product_url = f"https://getmainelobster.com{product_url}"
                
            title = heading.get_text(strip=True)
            if not title: # try falling back to img alt
                img = card.find("img")
                if img and img.get("alt"):
                    title = img["alt"]
            if not title:
                continue
                
            # Image
            img = card.find("img")
            img_url = None
            if img:
                img_url = img.get("src") or img.get("data-src")
                if img_url and img_url.startswith("//"):
                    img_url = f"https:{img_url}"
                    
            # Price
            price_tag = card.select_one(".price-item")
            if not price_tag:
                 price_tag = card.select_one(".price")
            price = price_tag.get_text(strip=True) if price_tag else None
            
            products.append(Product(
                title=title,
                url=product_url,
                price=price,
                image_url=img_url,
                handle=_handle_from_product_url(product_url),
            ))
        except Exception as e:
            continue
            
    return products

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    prods = extract_catalog()
    print(f"Found {len(prods)} products.")
    for p in prods[:3]:
        print(p.model_dump())
