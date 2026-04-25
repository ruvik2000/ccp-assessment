import os

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
MERCHANT_ID = os.environ.get("MERCHANT_ID", "getmainelobster")
MERCHANT_NAME = os.environ.get("MERCHANT_NAME", "Get Maine Lobster")
DEFAULT_SHIPPING_REGIONS = [x.strip() for x in os.environ.get("DEFAULT_SHIPPING_REGIONS", "US").split(",") if x.strip()]
