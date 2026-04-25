from fastapi import FastAPI
from typing import List
from app.scraper import extract_catalog, Product

app = FastAPI(
    title="FastAPI Project",
    description="A basic FastAPI project template",
    version="0.1.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI project!"}

@app.get("/api/scrape/catalog", response_model=List[Product])
def get_catalog():
    """Scrapes the catalog and returns a list of Products."""
    return extract_catalog()
