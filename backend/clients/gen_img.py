import logging

import aiohttp
from openai import AsyncOpenAI

from config import SETTINGS
from infra.file import download_and_upload_url, img_url_to_base64


async def gen_gpt_4o_img_svc(img_urls: list[str], prompt: str, scenario: str = "") -> str | None:
    try:
        content = [
            {"type": "text", "text": prompt},
        ]
        for img_url in img_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": await img_url_to_base64(img_url)}
            })

        data = {
            "model": "gpt-4o-image",
            "stream": False,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

        headers = {
            "Authorization": f"Bearer {SETTINGS.PROXY_OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        logging.info(f"Generating...")
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{SETTINGS.PROXY_OPENAI_BASE_URL}/chat/completions", json=data, headers=headers,
                                    timeout=1200) as response:
                logging.info(f"Response: {response.status}")
                if response.status != 200:
                    logging.warning(f'gen_img: http status: {response.status} {scenario}')
                    return None
                result = await response.json()
                if "error" in result:
                    return None
                if "choices" in result and isinstance(result["choices"], list):
                    for choice in result["choices"]:
                        if "message" in choice and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            import re
                            matches = re.findall(r"!\[.*?\]\((https?://[^\s]+)\)", content)
                            for image_url in matches:
                                if image_url:
                                    ret_img = await download_and_upload_url(image_url)
                                    if ret_img:
                                        return ret_img
    except Exception as e:
        logging.error(f"gen_img error: {e} {scenario}", exc_info=True)
    return None


client = AsyncOpenAI(
    api_key=SETTINGS.PROXY_GROK_API_KEY,
    base_url=SETTINGS.PROXY_GROK_BASE_URL
)


async def gen_text(prompt: str) -> str | None:
    resp = await client.chat.completions.create(
        model="grok-3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return resp.choices[0].message.content
