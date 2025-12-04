import openai

from config import SETTINGS

openai_client = openai.AsyncClient(api_key=SETTINGS.OPENAI_API_KEY)

proxy_client = openai.AsyncClient(
    api_key=SETTINGS.PROXY_OPENAI_API_KEY,
    base_url=SETTINGS.PROXY_OPENAI_BASE_URL,
)
