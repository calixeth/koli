import json
import logging
import re

import aiohttp

from config import SETTINGS
from entities.dto import GenVideoResp
from infra.file import img_url_to_base64

task_id_pattern = re.compile(r"Task ID: `([^`]+)`")
watch_pattern = re.compile(r"\[▶️ Watch Online\]\(([^)]+)\)")
download_pattern = re.compile(r"\[⏬ Download Video\]\(([^)]+)\)")


async def veo3_gen_video_svc(img_url: str, prompt: str) -> GenVideoResp | None:
    try:
        url = f"{SETTINGS.PROXY_OPENAI_BASE_URL}/chat/completions"
        base64_data = await img_url_to_base64(img_url)
        payload = {
            "temperature": 0.001,
            "messages": [
                {
                    "content": [
                        {"type": "text", "text": f"{prompt}"},
                        {"type": "image_url", "image_url": {
                            "url": base64_data}}
                    ],
                    "role": "user"
                }
            ],
            "model": "veo3",
            "stream": True
        }

        headers = {
            'Accept': 'application/json',
            'Authorization': f"Bearer {SETTINGS.PROXY_OPENAI_API_KEY}",
            'Content-Type': 'application/json'
        }

        logging.info(f"veo3_gen_video_svc begin")

        data = {}
        success = False
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    async for chunk in resp.content:
                        if chunk:
                            text = chunk.decode("utf-8", errors="ignore").strip()
                            logging.info(f"veo3_gen_video_chunk {text}")

                            for line in text.splitlines():
                                line = line.strip()
                                if not line.startswith("data: "):
                                    continue
                                if line == "data: [DONE]":
                                    continue

                            json_str = line[len("data: "):].strip()
                            try:
                                obj = json.loads(json_str)
                            except json.JSONDecodeError:
                                logging.warning(f"Not valid JSON: {json_str}")
                                continue

                            content = obj["choices"][0]["delta"].get("content", "")

                            m = task_id_pattern.search(content)
                            if m:
                                data["task_id"] = m.group(1)

                            wm = watch_pattern.search(content)
                            dm = download_pattern.search(content)
                            if wm:
                                data["watch_url"] = wm.group(1)
                            if dm:
                                data["download_url"] = dm.group(1)
                                success = True
                else:
                    logging.error(f"Request failed with status {resp.status}")
        if success:
            logging.info(f"veo3_gen_video_svc success {data}")
            return GenVideoResp(
                out_id=data["task_id"],
                view_url=data["watch_url"],
                download_url=data["download_url"],
            )
    except Exception as e:
        logging.error(f"veo3_gen_video_svc error: {e}", exc_info=True)
    return None
