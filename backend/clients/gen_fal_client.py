import logging

import fal_client

from config import SETTINGS
from entities.dto import GenVideoResp
from infra.file import download_and_upload_url


async def veo3_gen_video_svc_v2(img_url: str, prompt: str) -> GenVideoResp | None:
    try:
        handler = await fal_client.submit_async(
            SETTINGS.IMAGE_TO_VIDEO_V2,
            arguments={
                "prompt": prompt,
                "image_url": img_url,
                "negative_prompt": "blur, distort, and low quality",
                "cfg_scale": 0.5
            },
        )

        result = await handler.get()
        logging.debug(f"result: {result}")
        if result and isinstance(result, dict):
            if "video" in result and result["video"] and isinstance(result["video"], dict):
                if "url" in result["video"] and result["video"]["url"]:
                    _view_url = result["video"]["url"]
                    a_view_url = await download_and_upload_url(_view_url)
                    return GenVideoResp(
                        out_id="",
                        view_url=a_view_url,
                        download_url=""
                    )
    except Exception as e:
        logging.error(f"M veo3_gen_video_svc_v2 error: {e}", exc_info=True)
    return None


async def veo3_gen_video_svc_v3(img_url: str, prompt: str) -> GenVideoResp | None:
    try:
        handler = await fal_client.submit_async(
            SETTINGS.IMAGE_TO_VIDEO_V3,
            arguments={
                "prompt": prompt,
                "image_url": img_url,
            },
        )

        result = await handler.get()
        logging.debug(f"result: {result}")
        if result and isinstance(result, dict):
            if "video" in result and result["video"] and isinstance(result["video"], dict):
                if "url" in result["video"] and result["video"]["url"]:
                    _view_url = result["video"]["url"]
                    a_view_url = await download_and_upload_url(_view_url)
                    return GenVideoResp(
                        out_id="",
                        view_url=a_view_url,
                        download_url=""
                    )
    except Exception as e:
        logging.error(f"M veo3_gen_video_svc_v2 error: {e}", exc_info=True)
    return None


async def gen_img_svc_v3(img_urls: list[str], prompt: str) -> str | None:
    try:
        handler = await fal_client.submit_async(
            SETTINGS.IMAGE_TO_IMAGE_V3,
            arguments={
                "prompt": prompt,
                "image_urls": img_urls,
            },
        )

        result = await handler.get()
        if result and isinstance(result, dict):
            if "images" in result and result["images"] and isinstance(result["images"], list):
                img = result["images"][0]
                if "url" in img and img["url"]:
                    return img["url"]
    except Exception as e:
        logging.error(f"M veo3_gen_video_svc_v2 error: {e}", exc_info=True)
    return None
