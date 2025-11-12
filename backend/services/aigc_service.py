import asyncio
import datetime
import json
import logging
import re
import uuid

from fastapi import BackgroundTasks

from agent.prompt.aigc import FIRST_FRAME_IMG_PROMPT, V_DANCE_IMAGE_PROMPT, V_SING_IMAGE_PROMPT, V_FIGURE_IMAGE_PROMPT, \
    V_DANCE_VIDEO_PROMPT, V_TURN_PROMPT, V_SPEECH_PROMPT, V_THINK_PROMPT, V_SING_VIDEO_PROMPT, V_DEFAULT_PROMPT
from agent.prompt.tts import SLOGAN_PROMPT
from clients.gen_fal_client import veo3_gen_video_svc_v2
from clients.gen_img import gen_gpt_4o_img_svc, gen_text
from clients.openai_gen_img import gemini_gen_img_svc
from common.error import raise_error
from config import SETTINGS
from entities.dto import GenCoverImgReq, AIGCTask, Cover, TaskStatus, GenVideoReq, Video, DigitalHuman, \
    DigitalVideo, GenCoverResp, AIGCPublishReq, Lyrics, GenerateLyricsResponse, \
    GenerateLyricsResp, GenerateLyricsReq, GenMusicReq, Music, GenerateMusicResponse, GenerateMusicResp, BasicInfoReq, \
    GenXAudioReq, Audio, TwitterTTSTask, TaskType, TaskAndHuman, VideoKeyType, CloneXAudioReq, Fee
from infra.db import aigc_task_get_by_id, aigc_task_save, digital_human_save, digital_human_get_by_digital_human
from services import twitter_tts_service
from services.resource_usage_limit import check_limit_and_record
from services.twitter_service import twitter_fetch_user_svc
from services.twitter_tts_service import voice_clone_svc

style_map = {
    1: "Simpsons cartoon style",
    2: "Pixar 3D cinematic style",
    3: "Futurama cartoon style",
    4: "Pixiv-CG realistic style",
    5: "Japanese 2D anime illustration style",
    6: "pepe style",
    7: "cartoon-style illustration",
    8: "Bored Ape Yacht Club style",
    9: "Pixel art style",
    10: "Abstract geometric style",
    11: "Cyber goth style",
    12: "Doll-like anime style"
}


async def gen_lyrics_svc(req: GenerateLyricsReq, background: BackgroundTasks) -> AIGCTask:
    task = await aigc_task_get_by_id(req.task_id)

    await check_limit_and_record(client=f"task-{task.task_id}", resource="gen-lyrics")

    if task.lyrics:
        task.lyrics.regenerate()
        task.lyrics.input = req
        task.lyrics.output = None
    else:
        task.lyrics = Lyrics(
            sub_task_id=str(uuid.uuid4()),
            input=req,
            output=None,
            created_at=datetime.datetime.now()
        )

    await aigc_task_save(task)

    async def _task_gen_lyrics():
        try:
            result = await twitter_tts_service.generate_lyrics_from_twitter_url(
                twitter_url=task.cover.input.x_link,
                tenant_id=task.tenant_id,
                lang=task.lang,
            )
            response = GenerateLyricsResponse(**result)
        except Exception as e:
            logging.error(f"M failed to generate lyrics {e}", exc_info=True)
            response = None

        cur_task = await aigc_task_get_by_id(task.task_id)
        if response:
            cur_task.lyrics.output = GenerateLyricsResp(
                lyrics=response.lyrics,
                title=response.title,
            )
            cur_task.lyrics.status = TaskStatus.DONE
            cur_task.lyrics.done_at = datetime.datetime.now()

            fee = Fee.total_fee([
                Fee.llm_fee(),
            ])
            cur_task.lyrics.fee.append(fee)

            await aigc_task_save(cur_task)
            return

        cur_task.lyrics.status = TaskStatus.FAILED
        await aigc_task_save(cur_task)

    background.add_task(_task_gen_lyrics)

    return task


async def gen_music_svc(req: GenMusicReq, background: BackgroundTasks) -> AIGCTask:
    task = await aigc_task_get_by_id(req.task_id)

    await check_limit_and_record(client=f"task-{task.task_id}", resource="gen_music")

    if task.music:
        task.music.regenerate()
        task.music.input = req
        task.music.output = None
    else:
        task.music = Music(
            sub_task_id=str(uuid.uuid4()),
            input=req,
            output=None,
            created_at=datetime.datetime.now()
        )

    await aigc_task_save(task)

    async def _task_gen_music():
        lyrics = req.lyrics
        if len(lyrics) > 550:
            lyrics = lyrics[:550]

        result = None
        try:
            result = await twitter_tts_service.generate_music_from_lyrics(
                lyrics=lyrics,
                style=req.style,
                tenant_id=task.tenant_id,
                voice=req.voice,
                model=req.model,
                response_format=req.response_format,
                speed=req.speed,
                reference_audio_url=req.reference_audio_url
            )

            response = GenerateMusicResponse(**result)
        except Exception as e:
            logging.exception(f"failed to generate music {e}")
            response = None

        cur_task = await aigc_task_get_by_id(task.task_id)
        if response and result:
            cur_task.music.output = GenerateMusicResp(**result)
            cur_task.music.status = TaskStatus.DONE
            cur_task.music.done_at = datetime.datetime.now()

            fee = Fee.total_fee([
                Fee.music_fee(),
            ])
            cur_task.music.fee.append(fee)

            await aigc_task_save(cur_task)
            return

        cur_task.music.status = TaskStatus.FAILED
        await aigc_task_save(cur_task)

    background.add_task(_task_gen_music)

    return task


async def gen_twitter_audio_svc(req: GenXAudioReq, background: BackgroundTasks) -> AIGCTask:
    task = await aigc_task_get_by_id(req.task_id)

    if task.audio:
        sub_task = task.audio
        sub_task.regenerate()
        sub_task.input = req
        sub_task.output = []
    else:
        task.audio = Audio(
            sub_task_id=str(uuid.uuid4()),
            input=req,
            output=[],
            created_at=datetime.datetime.now()
        )

    await aigc_task_save(task)

    async def _bg_x_audio_task():
        voice_id = "Abbess"

        result = []
        tasks = []
        voice_clone_url = task.slogan_voice_url
        fee_items = []
        try:

            for twitter_url in req.x_tts_urls:
                tts_task = TwitterTTSTask(
                    task_id=task.audio.sub_task_id or str(uuid.uuid4()),
                    tenant_id=task.tenant_id,
                    twitter_url=twitter_url,
                    voice_id=voice_id,
                    username=task.twitter_username,
                    audio_url_input=task.voice_clone_url,
                    task_type=TaskType.VOICE_CLONE,
                )
                tasks.append(voice_clone_svc(tts_task, task.lang))
                fee_items.append(Fee.clone_fee())

            if not voice_clone_url:
                tts_task = TwitterTTSTask(
                    task_id=task.audio.sub_task_id or str(uuid.uuid4()),
                    tenant_id=task.tenant_id,
                    read_content=task.slogan,
                    voice_id=voice_id,
                    audio_url_input=task.voice_clone_url,
                    task_type=TaskType.VOICE_CLONE,
                )
                slogan = await voice_clone_svc(tts_task, task.lang)
                voice_clone_url = slogan.audio_url

                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, Exception):
                        logging.error(f"voice_clone_svc error: {r}")
                    elif r:
                        result.append(r)
        except Exception as e:
            logging.exception("Error in voice clone tasks")

        cur_task = await aigc_task_get_by_id(task.task_id)
        sub_task = cur_task.audio
        if result and voice_clone_url and len(result) == len(tasks):
            sub_task.output = result
            sub_task.status = TaskStatus.DONE
            sub_task.done_at = datetime.datetime.now()
            cur_task.slogan_voice_url = voice_clone_url

            fee = Fee.total_fee(fee_items)
            sub_task.fee.append(fee)

            await aigc_task_save(cur_task)
            return

        sub_task.status = TaskStatus.FAILED
        await aigc_task_save(cur_task)

    background.add_task(_bg_x_audio_task)

    return task


async def clone_twitter_audio_svc(req: CloneXAudioReq, background: BackgroundTasks):
    async def _bg_x_clone_twitter_audio_task():
        if not req.username or not req.text:
            return
        digital_human: DigitalHuman = await digital_human_get_by_digital_human(req.username)
        if not digital_human:
            return

        voice_id = "Abbess"
        voice_clone_url = digital_human.slogan_voice_url
        try:
            tts_task = TwitterTTSTask(
                task_id=str(uuid.uuid4()),
                tenant_id=digital_human.from_tenant_id,
                read_content=req.text,
                voice_id=voice_id,
                audio_url_input=voice_clone_url,
                task_type=TaskType.VOICE_CLONE,
            )
            result = await voice_clone_svc(tts_task, "")
            if result and voice_clone_url:
                digital_human.audios.append(result)
                await digital_human_save(digital_human)

                cur_task = await aigc_task_get_by_id(digital_human.from_task_id)
                if cur_task:
                    cur_task.audio.output.append(result)
                    await aigc_task_save(cur_task)
        except Exception as e:
            logging.exception("Error in clone_twitter_audio_svc tasks")

    background.add_task(_bg_x_clone_twitter_audio_task)


async def save_basic_info(req: BasicInfoReq, background: BackgroundTasks) -> AIGCTask:
    task = await aigc_task_get_by_id(req.task_id)

    task.gender = req.gender
    task.lang = req.lang
    task.voice_clone_url = req.voice_clone_url
    task.slogan = req.slogan
    task.updated_at = datetime.datetime.now()
    await aigc_task_save(task)

    return task


async def gen_cover_img_svc(req: GenCoverImgReq, background: BackgroundTasks) -> AIGCTask:
    style = style_map.get(req.style_id, "")
    if not style:
        raise_error(f"unknown style_id: {req.style_id}")

    username = req.x_link.replace("https://x.com/", "")

    twitter_bo = await twitter_fetch_user_svc(username)
    if not twitter_bo:
        raise_error("twitter user not found")

    # if not req.img_url:
    #     logging.info(f"use {twitter_bo.avatar_url}")
    #     img_base64 = twitter_bo.avatar_base64
    # else:
    #     logging.info(f"use {req.img_url}")
    #     img_base64 = await img_url_to_base64(req.img_url)

    task = await aigc_task_get_by_id(req.task_id)
    task.twitter_link = req.x_link
    task.twitter_username = username
    task.twitter_avatar_url = twitter_bo.avatar_url

    await check_limit_and_record(client=f"task-{task.task_id}", resource="gen-img")

    if task.cover:
        task.cover.regenerate()
        task.cover.input = req
        task.cover.output = None
    else:
        task.cover = Cover(
            sub_task_id=str(uuid.uuid4()),
            input=req,
            output=None,
            created_at=datetime.datetime.now()
        )

    await aigc_task_save(task)

    async def _task_gen_cover_img_svc():
        logging.info(f"M begin _task_gen_cover_img_svc")

        if not task.slogan:
            slogan_retry = 10
            text = ""
            while slogan_retry > 0:
                try:
                    logging.info(f"gen slogan {username}")
                    text = await gen_text(SLOGAN_PROMPT.format(account=username))
                    pattern = re.compile(r'\{.*?\}', re.DOTALL)
                    match = pattern.search(text)
                    if match:
                        json_str = match.group(0)
                        data = json.loads(json_str)
                        if "slogan" in data and "description" in data:
                            curc_task = await aigc_task_get_by_id(task.task_id)
                            curc_task.slogan = data["slogan"]
                            curc_task.slogan_description = data["description"]
                            await aigc_task_save(curc_task)
                        break
                except Exception as e:
                    slogan_retry -= 1
                    logging.error(f"M slogan gen text {text} error: {e} ", exc_info=True)

        base_img = req.img_url
        if not base_img:
            base_img = twitter_bo.avatar_url_400x400
        first_frame_imgs_task = gen_gpt_4o_img_svc(img_urls=[base_img],
                                                   prompt=FIRST_FRAME_IMG_PROMPT.format(style=style),
                                                   scenario="first_frame")
        dance_imgs_task = gen_gpt_4o_img_svc(img_urls=[SETTINGS.GEN_T_URL_DANCE, base_img],
                                             prompt=V_DANCE_IMAGE_PROMPT,
                                             scenario="dance")
        sing_imgs_task = gen_gpt_4o_img_svc(img_urls=[SETTINGS.GEN_T_URL_SING, base_img],
                                            prompt=V_SING_IMAGE_PROMPT,
                                            scenario="sing")
        # figure_imgs_task = gemini_gen_img_svc(img_url=base_img,
        #                                       prompt=V_FIGURE_IMAGE_PROMPT,
        #                                       scenario="figure")

        first_frame_imgs, dance_imgs, sing_imgs = await asyncio.gather(
            first_frame_imgs_task,
            dance_imgs_task,
            sing_imgs_task,
        )

        cur_task = await aigc_task_get_by_id(task.task_id)

        first_frame_url = first_frame_imgs
        # if first_frame_imgs and first_frame_imgs.data:
        #     first_frame_url = await s3_upload_openai_img(first_frame_imgs.data[0])
        # if not first_frame_url:
        #     logging.info(f"M first_frame_url upload error")

        dance_url = dance_imgs
        # if dance_imgs and dance_imgs.data:
        #     dance_url = await s3_upload_openai_img(dance_imgs.data[0])
        # if not dance_url:
        #     logging.info(f"M dance_url upload error")

        sing_url = sing_imgs
        # if sing_imgs and sing_imgs.data:
        #     sing_url = await s3_upload_openai_img(sing_imgs.data[0])
        # if not sing_url:
        #     logging.info(f"M sing_url upload error")

        # figure_url = ""
        # if figure_imgs and figure_imgs.data:
        #     # figure_url = await s3_upload_openai_img(figure_imgs.data[0])
        #     figure_url = figure_imgs.data[0].url
        # if not figure_url:
        #     logging.info(f"M figure_url upload error")

        if first_frame_url and dance_url and sing_url:
            cur_task.cover.output = GenCoverResp(
                first_frame_img_url=first_frame_url,
                cover_img_url=first_frame_url,
                dance_first_frame_img_url=dance_url,
                sing_first_frame_img_url=sing_url,
                figure_first_frame_img_url="xxx",
            )

            fee = Fee.total_fee([
                Fee.img_fee(),
                Fee.img_fee(),
                Fee.img_fee(),
                Fee.img_fee(),
                Fee.llm_fee(),
            ])

            cur_task.cover.status = TaskStatus.DONE
            cur_task.cover.done_at = datetime.datetime.now()
            cur_task.cover.fee.append(fee)
            logging.info(f"M cur_cover_img_svc: {cur_task.cover.output.model_dump_json()}")
            await aigc_task_save(cur_task)
            return

        cur_task.cover.status = TaskStatus.FAILED
        await aigc_task_save(cur_task)

    background.add_task(_task_gen_cover_img_svc)

    return task


async def gen_video_svc(req: GenVideoReq, background: BackgroundTasks) -> AIGCTask:
    org_task = await aigc_task_get_by_id(req.task_id)
    if not org_task.cover or not org_task.cover.output:
        raise_error("cover img not found")

    await check_limit_and_record(client=f"task-{org_task.task_id}", resource=f"gen-video-{req.key}")
    regenerate: bool = False
    for v in org_task.videos:
        if v.input.key == req.key:
            v.regenerate()
            v.input = req
            v.output = None
            regenerate = True
            break
    if not regenerate:
        org_task.videos.append(
            Video(
                sub_task_id=str(uuid.uuid4()),
                input=req,
                output=None,
                status=TaskStatus.IN_PROGRESS,
                created_at=datetime.datetime.now()
            )
        )

    await aigc_task_save(org_task)

    async def _task_video_svc(task: AIGCTask, req: GenVideoReq):
        logging.info(f"M _task_video_svc req: {req.model_dump_json()}")

        if VideoKeyType.DANCE == req.key:
            prompt = V_DANCE_VIDEO_PROMPT
        # elif VideoKeyType.GOGO == req.key:
        #     prompt = V_GOGO_PROMPT
        elif VideoKeyType.TURN == req.key:
            prompt = V_TURN_PROMPT
        # elif VideoKeyType.ANGRY == req.key:
        #     prompt = V_ANGRY_PROMPT
        # elif VideoKeyType.SAYING == req.key:
        #     prompt = V_SAYING_PROMPT
        elif VideoKeyType.SPEECH == req.key:
            prompt = V_SPEECH_PROMPT
        elif VideoKeyType.THINK == req.key:
            prompt = V_THINK_PROMPT
        elif VideoKeyType.SING == req.key:
            prompt = V_SING_VIDEO_PROMPT
        elif VideoKeyType.FIGURE == req.key:
            prompt = V_FIGURE_IMAGE_PROMPT
        else:
            prompt = V_DEFAULT_PROMPT

        if VideoKeyType.DANCE == req.key:
            first_frame_img_url = task.cover.output.dance_first_frame_img_url
        elif VideoKeyType.SING == req.key:
            first_frame_img_url = task.cover.output.sing_first_frame_img_url
        elif VideoKeyType.FIGURE == req.key:
            first_frame_img_url = task.cover.output.figure_first_frame_img_url
        else:
            first_frame_img_url = task.cover.output.first_frame_img_url

        if VideoKeyType.DANCE == req.key:
            data = await veo3_gen_video_svc_v2(first_frame_img_url, prompt)
        elif VideoKeyType.SING == req.key:
            data = await veo3_gen_video_svc_v2(first_frame_img_url, prompt)
        elif VideoKeyType.FIGURE == req.key:
            data = await veo3_gen_video_svc_v2(first_frame_img_url, prompt)
        else:
            data = await veo3_gen_video_svc_v2(first_frame_img_url, prompt)

        cur_task = await aigc_task_get_by_id(task.task_id)
        if data:
            for v in cur_task.videos:
                if v.input.key == req.key:
                    v.output = data
                    v.status = TaskStatus.DONE
                    v.done_at = datetime.datetime.now()
                    fee = Fee.total_fee([
                        Fee.video_fee(),
                    ])
                    v.fee.append(fee)
                    break

            await aigc_task_save(cur_task)
        else:
            for v in cur_task.videos:
                if v.input.key == req.key:
                    v.status = TaskStatus.FAILED
                    v.done_at = datetime.datetime.now()
                    break
            await aigc_task_save(cur_task)

    background.add_task(_task_video_svc, org_task, req)
    return org_task


async def aigc_task_publish_by_id(req: AIGCPublishReq, user_dict: dict, background: BackgroundTasks) -> DigitalHuman:
    wallet_address = user_dict.get("wallet_address", "")
    task: AIGCTask = await aigc_task_get_by_id(req.task_id)
    if not task:
        raise_error("task not found")

    task.check_all_ready()

    org = await digital_human_get_by_digital_human(task.twitter_username)
    update = False
    if org:
        if org.from_task_id != task.task_id:
            raise_error("username is repeated")
        else:
            update = True

    if update:
        id = org.id
        created_at = org.created_at

        sum = 0.0
        for fee in task.cover.fee:
            sum += fee.amount
        for fee in task.lyrics.fee:
            sum += fee.amount
        for fee in task.music.fee:
            sum += fee.amount
        for fee in task.audio.fee:
            sum += fee.amount
        for video in task.videos:
            for fee in video.fee:
                sum += fee.amount
        fee = org.fee
        for fee in fee:
            sum -= fee.amount
        fee.append(Fee.total_fee([
            Fee(
                name="item",
                amount=sum,
                items=[],
            ),
        ]))
    else:
        id = str(uuid.uuid4())
        created_at = datetime.datetime.now()
        fee = []

    videos: list[DigitalVideo] = []
    for v in task.videos:
        if v.status == TaskStatus.DONE and v.output.view_url:
            videos.append(DigitalVideo(
                key=v.input.key,
                view_url=v.output.view_url,
            ))

    basic = TaskAndHuman(**task.model_dump())

    audios = task.audio.output
    if task.audio.history:
        for h in task.audio.history:
            audios.extend(Audio(**h).output)

    bo = DigitalHuman(
        id=id,
        from_task_id=task.task_id,
        from_tenant_id=task.tenant_id,
        digital_name=task.twitter_username,
        publisher_wallet_address=wallet_address,
        cover_img=task.cover.output.cover_img_url,
        sing_image=task.cover.output.sing_first_frame_img_url,
        figure_image=task.cover.output.figure_first_frame_img_url,
        first_frame_image=task.cover.output.first_frame_img_url,
        dance_image=task.cover.output.dance_first_frame_img_url,
        videos=videos,
        updated_at=datetime.datetime.now(),
        created_at=created_at,
        songs={
            "lyrics": task.lyrics.output.lyrics,
            "lyrics_title": task.lyrics.output.title,
            "music_audio_url": task.music.output.audio_url,
            "music_style": task.music.output.style,
            "music_model": task.music.output.model,
            "music_voice": task.music.output.voice,
            "music_response_format": task.music.output.response_format,
            "music_speed": task.music.output.speed,
        },
        fee=fee,
        audios=audios,
        **basic.model_dump()
    )

    await digital_human_save(bo)

    # background.add_task(_voice_ttl_task, req, user_dict, username, id)
    return bo
