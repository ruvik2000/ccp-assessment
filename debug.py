import requests
from bs4 import BeautifulSoup

url = "https://getmainelobster.com/collections/all"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.text, "html.parser")

cards = soup.select(".card-wrapper")
if cards:
    print(cards[0].prettify())
else:
    cards = soup.select(".card")
    if cards:
        print(cards[0].prettify())
