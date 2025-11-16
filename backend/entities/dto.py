import datetime
import uuid
from enum import StrEnum
from typing import Any, Optional, List

from pydantic import BaseModel, Field

from common.error import raise_error
from entities.bo import Language, TwitterTTSResp


class Fee(BaseModel):
    name: str
    amount: float = 0.0
    currency: str = "USD"
    items: list["Fee"] = Field(description="items", default_factory=list)

    @staticmethod
    def img_fee() -> "Fee":
        return Fee(
            name="img",
            amount=0.4,
            items=[],
        )

    @staticmethod
    def llm_fee() -> "Fee":
        return Fee(
            name="llm",
            amount=0.002,
            items=[],
        )

    @staticmethod
    def music_fee() -> "Fee":
        return Fee(
            name="music",
            amount=1,
            items=[],
        )

    @staticmethod
    def video_fee() -> "Fee":
        return Fee(
            name="video",
            amount=3,
            items=[],
        )

    @staticmethod
    def clone_fee() -> "Fee":
        return Fee(
            name="clone",
            amount=0.5,
            items=[],
        )

    @staticmethod
    def total_fee(items: list["Fee"]) -> "Fee":
        return Fee(
            name="total",
            amount=sum(item.total() for item in items),
            items=items,
        )

    def total(self) -> float:
        return self.amount + sum(item.total() for item in self.items)


class TaskStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class TaskType(StrEnum):
    """Task type for Twitter TTS tasks"""
    TTS = "tts"  # Text-to-Speech (default)
    VOICE_CLONE = "voice_clone"  # Voice cloning
    MUSIC_GEN = "music_gen"  # Music generation


class MusicStyle(StrEnum):
    """Music style for music generation tasks"""
    POP = "pop"  # Pop music
    ROCK = "rock"  # Rock music
    JAZZ = "jazz"  # Jazz music
    CLASSICAL = "classical"  # Classical music
    ELECTRONIC = "electronic"  # Electronic music
    FOLK = "folk"  # Folk music
    BLUES = "blues"  # Blues music
    COUNTRY = "country"  # Country music
    HIP_HOP = "hip_hop"  # Hip hop music
    AMBIENT = "ambient"  # Ambient music
    CUSTOM = "custom"  # Custom style


class Gender(StrEnum):
    MALE = "0"
    FEMALE = "1"


class AIGCTaskID(BaseModel):
    """
    task_id
    """
    task_id: str = Field(description="task_id", default="")


class SubTask(BaseModel):
    sub_task_id: str = Field(description="sub_task_id")
    status: TaskStatus = Field(description="status", default=TaskStatus.IN_PROGRESS)
    created_at: datetime.datetime = Field(description="created_at")
    done_at: datetime.datetime | None = Field(description="done_at", default=None)
    history: list[dict[str, Any]] = Field(description="history", default_factory=list)
    fee: list[Fee] = Field(description="fee", default_factory=list)

    def regenerate(self) -> None:
        if self.status == TaskStatus.DONE:
            current_dict = self.model_dump()
            current_dict.pop("history", None)
            self.history.insert(0, current_dict)

        self.status = TaskStatus.IN_PROGRESS
        self.created_at = datetime.datetime.now()
        self.done_at = None
        self.sub_task_id = str(uuid.uuid4())


class GenCoverImgReq(AIGCTaskID):
    x_link: str = Field(description="x link")
    img_url: str = Field(default="", description="manually specify cover img")
    style_id: int = Field(description="style id", default=1)


class BasicInfoReq(AIGCTaskID):
    gender: Gender = Field(description="gender", default=Gender.MALE)
    slogan: str = Field(description="slogan", default="")
    voice_clone_url: str = Field(description="voice_clone_url", default="")
    lang: Language = Field(description="language", default=Language.ENGLISH)


class TaskAndHuman(BaseModel):
    twitter_link: str = Field(description="twitter_link", default="")
    twitter_username: str = Field(description="twitter_username", default="")
    twitter_avatar_url: str = Field(description="twitter_avatar_url", default="")
    gender: Gender = Field(description="gender", default=Gender.MALE)
    slogan: str = Field(description="slogan", default="")
    slogan_description: str = Field(description="slogan description", default="")
    slogan_voice_url: str = Field(description="slogan_voice_url", default="")
    voice_clone_url: str = Field(description="voice_clone_url", default="")
    lang: Language = Field(description="language", default=Language.ENGLISH)


class AIGCPublishReq(BaseModel):
    """
    """
    task_id: str = Field(description="task_id")


class PageReq(BaseModel):
    """
    """
    page: int = Field(default=1, ge=1)
    pagesize: int = Field(default=10, ge=1, le=1000)


class DigitalHumanPageReq(BaseModel):
    """
    """
    tag: str = Field(description="tag", default="")


class GenXAudioReq(AIGCTaskID):
    """
    """
    x_tts_urls: list[str] = Field(description="x tts url", default_factory=list)


class CloneXAudioReq(BaseModel):
    """
    """
    username: str = Field(description="username", default="")
    text: str = Field(description="text", default="")


class ID(BaseModel):
    """
    id
    """
    id: str = Field(description="id", default=None)


class InvitationCode(BaseModel):
    """
    invitation_code
    """
    invitation_code: str = Field(description="invitation_code", default=None)


class Username(BaseModel):
    """
    username
    """
    digital_name: str = Field(description="digital_name", default=None)


class Username1(BaseModel):
    """
    username
    """
    username: str = Field(description="username", default=None)


class ChatReq(BaseModel):
    """
    chat
    """
    query: str = Field(description="query")
    conversation_id: str = Field(description="conversation_id")


class GenCoverResp(BaseModel):
    first_frame_img_url: str = Field(description="first_frame_url", default="")
    cover_img_url: str = Field(description="cover_url", default="")
    dance_first_frame_img_url: str = Field(description="dance_first_frame_img_url", default="")
    sing_first_frame_img_url: str = Field(description="sing_first_frame_img_url", default="")
    figure_first_frame_img_url: str = Field(description="figure_first_frame_img_url", default="")


class Cover(SubTask):
    input: GenCoverImgReq
    output: GenCoverResp | None = Field(description="cover", default=None)


class Audio(SubTask):
    input: GenXAudioReq
    output: list[TwitterTTSResp] = Field(description="audio", default_factory=list)


class GenerateLyricsRequest(BaseModel):
    """Request for generating lyrics from Twitter URL"""
    twitter_url: str = Field(description="Twitter/X post URL. default user cover x link")
    style: str = Field(description="Music style used")


class GenerateLyricsReq(BaseModel):
    """Request for generating lyrics from Twitter URL"""
    task_id: str = Field(description="task_id")


class GenerateMusicRequest(BaseModel):
    """Request for generating music from lyrics"""
    lyrics: str = Field(description="Lyrics text to generate music from")
    style: str = Field(
        description="Music style (pop, rock, jazz, classical, electronic, folk, blues, country, hip_hop, ambient, custom)")
    reference_audio_url: str = Field(description="Audio url")
    voice: str = Field(description="TTS voice to use", default="alloy")
    model: str = Field(description="TTS model to use", default="tts-1")
    response_format: str = Field(description="Audio format", default="mp3")
    speed: float = Field(description="Speech speed", default=1.0, ge=0.25, le=4.0)


class GenMusicReq(GenerateMusicRequest):
    """"""
    task_id: str = Field(description="task_id")


class GenerateLyricsResp(BaseModel):
    """Response for lyrics generation"""
    lyrics: str = Field(description="Generated lyrics text")
    title: str = Field(description="Extracted title from lyrics", default="")


class GenerateMusicResp(BaseModel):
    """Response for music generation"""
    audio_url: str = Field(description="Generated music audio URL")
    lyrics: str = Field(description="Original lyrics used")
    style: str = Field(description="Music style used")
    voice: str = Field(description="TTS voice used")
    model: str = Field(description="TTS model used")
    response_format: str = Field(description="Audio format")
    speed: float = Field(description="Speech speed used")


class Lyrics(SubTask):
    input: GenerateLyricsReq
    output: GenerateLyricsResp | None = Field(description="lyrics", default=None)


class Music(SubTask):
    input: GenMusicReq
    output: GenerateMusicResp | None = Field(description="lyrics", default=None)


class VideoKeyType(StrEnum):
    TURN = "turn"
    SAYING = "saying"
    GOGO = "gogo"
    DANCE = "dance"
    ANGRY = "angry"
    DEFAULT = "default"
    THINK = "think"
    SING = "sing"
    SPEECH = "speech"
    FIGURE = "figure"


class GenVideoReq(BaseModel):
    task_id: str = Field(description="task_id")
    key: VideoKeyType = Field(description="Unique key")
    # scenario: str = Field(description="Scenario Description")


class GenVideoResp(BaseModel):
    out_id: str = Field(description="out_id")
    view_url: str = Field(description="view url")
    download_url: str = Field(description="download url")


class Video(SubTask):
    input: GenVideoReq
    output: GenVideoResp | None = Field(description="video url", default=None)


class AIGCTask(AIGCTaskID, TaskAndHuman):
    tenant_id: str = Field(description="tenant_id")
    cover: Cover | None = Field(description="cover", default=None)
    lyrics: Lyrics | None = Field(description="lyrics", default=None)
    music: Music | None = Field(description="music", default=None)
    videos: list[Video] = Field(description="videos", default_factory=list)
    audio: Audio | None = Field(description="audio", default=None)
    created_at: datetime.datetime = Field(description="created_at", default=None)
    updated_at: datetime.datetime | None = Field(description="Last update time", default=None)

    def check_all_ready(self):
        if not self.cover or not self.cover.output or not self.cover.status == TaskStatus.DONE:
            raise_error("cover not ready")

        if not self.lyrics or not self.lyrics.output or not self.lyrics.status == TaskStatus.DONE:
            raise_error("lyrics not ready")

        if not self.music or not self.music.output or not self.music.status == TaskStatus.DONE:
            raise_error("music not ready")

        if not self.audio:
            raise_error("audio not ready")
        elif self.audio.status == TaskStatus.FAILED and not self.audio.history:
            raise_error("audio not ready")

        if not self.videos or len(self.videos) == 0:
            raise_error("videos not ready")

        for video in self.videos:
            if not video or not video.output or not video.status == TaskStatus.DONE:
                raise_error(f"{video.input.key} video not ready")


class TwitterTTSRequest(BaseModel):
    """Request model for creating Twitter TTS task"""
    twitter_url: str = Field(description="Twitter/X post URL")
    task_type: Optional[TaskType] = Field(default=TaskType.TTS, description="Task type (tts, voice_clone, music_gen)")
    voice: Optional[str] = Field(default=None, description="TTS voice to use")
    model: Optional[str] = Field(default=None, description="TTS model to use")
    response_format: Optional[str] = Field(default=None, description="Audio format")
    speed: Optional[float] = Field(default=None, description="Speech speed")
    voice_id: Optional[str] = Field(default=None, description="Optional voice ID for TTS")
    audio_url: Optional[str] = Field(default=None, description="Optional audio URL for TTS")
    username: Optional[str] = Field(default=None, description="Username for the TTS task")
    style: Optional[str] = Field(default=None,
                                 description="Music style for music generation tasks (pop, rock, jazz, classical, electronic, folk, blues, country, hip_hop, ambient, custom)")


class TwitterTTSResponse(BaseModel):
    """Response for Twitter TTS task"""
    task_id: str = Field(description="Generated task ID")
    status: TaskStatus = Field(description="Task status")
    message: str = Field(description="Response message")


class TwitterTTSTask(BaseModel):
    """Twitter TTS task model"""
    task_id: str = Field(description="Unique task ID")
    tenant_id: str = Field(description="Tenant ID")
    read_content: str = Field(description="read_content", default="")
    twitter_url: str = Field(description="Twitter/X post URL", default="")
    tweet_id: str | None = Field(description="Extracted tweet ID", default="")
    task_type: TaskType = Field(default=TaskType.TTS, description="Task type (tts, voice_clone, music_gen)")
    voice: Optional[str] | None = Field(description="TTS voice", default=None)
    model: Optional[str] | None = Field(description="TTS model", default=None)
    response_format: Optional[str] = Field(description="Audio format", default=None)
    speed: Optional[float] = Field(description="Speech speed", default=None)
    status: TaskStatus | None = Field(description="Task status", default=None)
    created_at: datetime.datetime | None = Field(description="Task creation time", default=None)
    updated_at: datetime.datetime | None = Field(description="Last update time", default=None)
    title: str | None = Field(description="TTS title", default=None)
    tweet_content: str | None = Field(description="Extracted tweet content", default=None)
    voice_id: Optional[str] = Field(default=None, description="Optional voice ID for TTS")
    audio_url_input: Optional[str] = Field(default=None, description="Optional audio URL for TTS")
    audio_url: str | None = Field(description="Generated audio file URL", default=None)
    error_message: str | None = Field(description="Error message if failed", default=None)
    processing_started_at: datetime.datetime | None = Field(description="Processing start time", default=None)
    completed_at: datetime.datetime | None = Field(description="Completion time", default=None)
    username: Optional[str] | None = Field(default=None, description="Username for the TTS task")
    style: Optional[str] | None = Field(default=None, description="Music style for music generation tasks")
    digital_human_id: Optional[str] | None = Field(default=None, description="Digital human ID")


class TwitterTTSTaskListResponse(BaseModel):
    """Response for Twitter TTS task list"""
    tasks: list[TwitterTTSTask] = Field(description="List of tasks")
    total: int = Field(description="Total number of tasks")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")


class TwitterTTSTaskQuery(BaseModel):
    """Query parameters for Twitter TTS tasks"""
    tenant_id: str = Field(description="Tenant ID")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=20, description="Page size")
    status: TaskStatus | None = Field(default=None, description="Filter by status")


class PredefinedVoice(BaseModel):
    """Predefined voice model"""
    voice_id: str = Field(description="Unique voice identifier")
    name: str = Field(description="Voice display name")
    audio_url: Optional[str] = Field(default=None, description="Sample audio URL for preview")
    description: Optional[str] = Field(default=None, description="Voice description")
    category: Optional[str] = Field(default=None, description="Voice category")
    is_active: bool = Field(default=True, description="Whether the voice is available")
    created_at: datetime.datetime = Field(description="Creation time")
    updated_at: Optional[datetime.datetime] = Field(default=None, description="Last update time")


class PredefinedVoiceListResponse(BaseModel):
    """Response for predefined voice list"""
    voices: list[PredefinedVoice] = Field(description="List of predefined voices")
    total: int = Field(description="Total number of voices")


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict
    access_token_expires_in: int  # in seconds
    refresh_token_expires_in: int  # in seconds


class NonceResponse(BaseModel):
    """Response containing nonce for wallet signature"""
    nonce: str
    message: str


class WalletLoginResponse(BaseModel):
    """Response for successful wallet login"""
    access_token: str
    refresh_token: str
    user: dict
    is_new_user: bool
    access_token_expires_in: int  # in seconds
    refresh_token_expires_in: int  # in seconds


class TokenResponse(BaseModel):
    """Response containing new access token"""
    access_token: str
    refresh_token: str
    access_token_expires_in: int  # in seconds
    refresh_token_expires_in: int  # in seconds
    user: dict


class DigitalVideo(BaseModel):
    key: str = Field(description="key")
    view_url: str = Field(description="video url")


# New DTOs for lyrics and music generation APIs


class DigitalHuman(TaskAndHuman):
    id: str = Field(description="Digital human ID")
    from_task_id: str = Field(description="from_task_id")
    from_tenant_id: str = Field(description="from_tenant_id")
    digital_name: str = Field(description="Digital human name")
    publisher_wallet_address: str = Field(description="publisher_wallet_address")
    adopted: bool = Field(description="Adopted", default=False)
    cover_img: str = Field(description="cover_img")
    dance_image: str = Field(description="dance image", default="")
    sing_image: str = Field(description="sing_image", default="")
    figure_image: str = Field(description="figure image", default="")
    first_frame_image: str = Field(description="first frame image", default="")
    videos: list[DigitalVideo] = Field(description="videos", default_factory=list)
    songs: dict[str, Any] = Field(description="songs", default_factory=dict)
    audios: list[TwitterTTSResp] = Field(description="audios", default_factory=list)
    chat_count: int = Field(description="chat_count", default=0)
    fee: list[Fee] = Field(description="fee", default_factory=list)
    created_at: datetime.datetime = Field(description="created_at")
    updated_at: datetime.datetime = Field(description="updated_at")


class PointsDetails(BaseModel):
    points: int = Field(description="points", default=0)
    type: str = Field(description="type", default="add")
    remark: str = Field(description="remark", default="")
    created_at: datetime.datetime = Field(description="created_at")


class Profile(BaseModel):
    tenant_id: str = Field(description="Tenant ID", default="")
    wallet_address: str = Field(description="wallet_address", default="")
    chain_type: str = Field(description="Chain type", default="")
    verified_x_username: str = Field(description="Verified x username", default="")
    verified_x_user_id: str = Field(description="verified_x_user_id", default="")
    verified_x_avatar_url: str = Field(description="verified_x_avatar_url", default="")
    adopted: bool = Field(description="Adopted", default=False)
    total_points: int = Field(description="Total points", default=0)
    points_details: List[PointsDetails] = Field(description="Points details", default_factory=list)
    follow_digital_human_ids: list[str] = Field(description="Follow digital humans", default_factory=list)
    invitation_code: str = Field(description="Invitation code", default="")
    from_invitation_code: str = Field(description="From invitation code", default="")


class GenerateLyricsResponse(BaseModel):
    """Response for lyrics generation"""
    lyrics: str = Field(description="Generated lyrics text")
    title: str = Field(description="Extracted title from lyrics", default="")
    twitter_url: str = Field(description="Original Twitter URL")
    generated_at: str = Field(description="Generation timestamp")


class GenerateMusicResponse(BaseModel):
    """Response for music generation"""
    audio_url: str = Field(description="Generated music audio URL")
    lyrics: str = Field(description="Original lyrics used")
    style: str = Field(description="Music style used")
    voice: str = Field(description="TTS voice used")
    model: str = Field(description="TTS model used")
    response_format: str = Field(description="Audio format")
    speed: float = Field(description="Speech speed used")
    generated_at: str = Field(description="Generation timestamp")
