# import asyncio
# import logging
# from datetime import datetime
# from typing import Optional
# from abc import ABC, abstractmethod
#
# from entities.dto import TwitterTTSTask, TaskType, TaskStatus
# from infra.db import twitter_tts_task_save
# from services import twitter_tts_service
#
# logger = logging.getLogger(__name__)
#
#
# class TaskProcessorStrategy(ABC):
#     """Abstract base class for task processing strategies"""
#
#     @abstractmethod
#     async def process(self, task: TwitterTTSTask) -> bool:
#         """Process a task and return success status"""
#         pass
#
#
# class TTSTaskProcessor(TaskProcessorStrategy):
#     """Processor for standard TTS tasks"""
#
#     async def process(self, task: TwitterTTSTask) -> bool:
#         """Process TTS task using the original logic"""
#         return await twitter_tts_service._process_tts_task(task)
#
#
# class VoiceCloneTaskProcessor(TaskProcessorStrategy):
#     """Processor for voice cloning tasks"""
#
#     async def process(self, task: TwitterTTSTask) -> bool:
#         """Process voice cloning task"""
#         return await twitter_tts_service._process_voice_clone_task(task)
#
#
# class MusicGenTaskProcessor(TaskProcessorStrategy):
#     """Processor for music generation tasks"""
#
#     async def process(self, task: TwitterTTSTask) -> bool:
#         """Process music generation task"""
#         return await twitter_tts_service._process_music_gen_task(task)
#
#
# class TaskProcessorFactory:
#     """Factory for creating task processors based on task type"""
#
#     _processors = {
#         TaskType.TTS: TTSTaskProcessor(),
#         TaskType.VOICE_CLONE: VoiceCloneTaskProcessor(),
#         TaskType.MUSIC_GEN: MusicGenTaskProcessor(),
#     }
#
#     @classmethod
#     def get_processor(cls, task_type: TaskType) -> TaskProcessorStrategy:
#         """Get processor for the specified task type"""
#         return cls._processors.get(task_type, cls._processors[TaskType.TTS])
#
#
# class TwitterTTSProcessor:
#     """Background processor for Twitter TTS tasks"""
#
#     def __init__(self, processing_interval: int = 30):
#         """
#         Initialize the processor
#
#         Args:
#             processing_interval: Interval between processing cycles in seconds
#         """
#         self.processing_interval = processing_interval
#         self.is_running = False
#         self.processing_task: Optional[asyncio.Task] = None
#
#     async def start(self):
#         """Start the background processor"""
#         if self.is_running:
#             logger.warning("Twitter TTS processor is already running")
#             return
#
#         self.is_running = True
#         self.processing_task = asyncio.create_task(self._process_loop())
#         logger.info("Twitter TTS processor started")
#
#     async def stop(self):
#         """Stop the background processor"""
#         if not self.is_running:
#             logger.warning("Twitter TTS processor is not running")
#             return
#
#         self.is_running = False
#         if self.processing_task:
#             self.processing_task.cancel()
#             try:
#                 await self.processing_task
#             except asyncio.CancelledError:
#                 pass
#         logger.info("Twitter TTS processor stopped")
#
#     async def _process_loop(self):
#         """Main processing loop"""
#         while self.is_running:
#             try:
#                 await self._process_pending_tasks()
#                 await asyncio.sleep(self.processing_interval)
#             except asyncio.CancelledError:
#                 break
#             except Exception as e:
#                 logger.error(f"Error in Twitter TTS processing loop: {e}", exc_info=True)
#                 await asyncio.sleep(self.processing_interval)
#
#     async def _process_pending_tasks(self):
#         """Process all pending Twitter TTS tasks"""
#         try:
#             # Get pending tasks
#             pending_tasks = await twitter_tts_service.get_pending_twitter_tts_tasks()
#
#             if not pending_tasks:
#                 logger.debug("No pending Twitter TTS tasks to process")
#                 return
#
#             logger.info(f"Processing {len(pending_tasks)} pending Twitter TTS tasks")
#
#             # Process tasks concurrently (with limit to avoid overwhelming the system)
#             semaphore = asyncio.Semaphore(3)  # Process max 3 tasks concurrently
#
#             async def process_single_task(task: TwitterTTSTask):
#                 async with semaphore:
#                     try:
#                         # Use strategy pattern to process task based on type
#                         processor = TaskProcessorFactory.get_processor(task.task_type)
#                         await processor.process(task)
#                     except Exception as e:
#                         logger.error(f"Error processing task {task.task_id}: {e}", exc_info=True)
#                         # Update task with error
#                         task.status = TaskStatus.FAILED
#                         task.error_message = str(e)
#                         task.updated_at = datetime.now()
#                         await twitter_tts_task_save(task)
#
#             # Create tasks for concurrent processing
#             tasks = [process_single_task(task) for task in pending_tasks]
#
#             # Wait for all tasks to complete
#             await asyncio.gather(*tasks, return_exceptions=True)
#
#             logger.info(f"Completed processing {len(pending_tasks)} Twitter TTS tasks")
#
#         except Exception as e:
#             logger.error(f"Error in _process_pending_tasks: {e}", exc_info=True)
#
#     async def process_single_task(self, task_id: str) -> bool:
#         """
#         Process a single Twitter TTS task by ID
#
#         Args:
#             task_id: Task ID to process
#
#         Returns:
#             True if successful, False otherwise
#         """
#         try:
#             task = await twitter_tts_service.get_twitter_tts_task(task_id)
#             if not task:
#                 logger.error(f"Task {task_id} not found")
#                 return False
#
#             if task.status != "in_progress":
#                 logger.warning(f"Task {task_id} is not in progress status: {task.status}")
#                 return False
#
#             # Use strategy pattern to process task based on type
#             processor = TaskProcessorFactory.get_processor(task.task_type)
#             return await processor.process(task)
#
#         except Exception as e:
#             logger.error(f"Error processing single task {task_id}: {e}", exc_info=True)
#             return False
#
#
# # Global processor instance
# twitter_tts_processor = TwitterTTSProcessor()
#
#
# async def start_twitter_tts_processor():
#     """Start the Twitter TTS processor"""
#     await twitter_tts_processor.start()
#
#
# async def stop_twitter_tts_processor():
#     """Stop the Twitter TTS processor"""
#     await twitter_tts_processor.stop()
#
#
# async def process_twitter_tts_task_immediately(task_id: str) -> bool:
#     """
#     Process a Twitter TTS task immediately without waiting for the background processor
#
#     Args:
#         task_id: Task ID to process
#
#     Returns:
#         True if successful, False otherwise
#     """
#     return await twitter_tts_processor.process_single_task(task_id)
