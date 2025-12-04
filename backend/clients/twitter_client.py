import logging

from config import SETTINGS

logger = logging.getLogger('twitter_client')

host = f"https://{SETTINGS.TWITTER241_HOST}"

headers = {
    f"x-{SETTINGS.TWITTER241}-host": SETTINGS.TWITTER241_HOST,
    f"x-{SETTINGS.TWITTER241}-key": SETTINGS.TWITTER241_KEY
}

# async def twitter_fetch_user(username: str):
#     url = f"{host}/user?username={username}"
#     logger.info(f"Fetching {url}")
#
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url, headers=headers) as response:
#             response.raise_for_status()
#             if response.status == 200:
#                 return await response.json()
#
#     return None


# async def twitter_fetch_user_tweets(id: str):
#     url = f"{host}/user-tweets?user={id}&count=10"
#     logger.info(f"Fetching {url}")
#
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url, headers=headers) as response:
#             response.raise_for_status()
#             if response.status == 200:
#                 return await response.json()
#
#     return {}


# async def twitter_fetch_tweet_details(pid: str):
#     """
#     Fetch tweet information by PID (tweet ID)
#
#     Args:
#         pid: Tweet ID to fetch
#
#     Returns:
#         Tweet data dictionary or None if failed
#     """
#     url = f"{host}/tweet-v2?pid={pid}"
#     logger.info(f"Fetching tweet {pid} from {url}")
#
#     try:
#         async with aiohttp.ClientSession() as session:
#             async with session.get(url, headers=headers) as response:
#                 if response.status == 200:
#                     data = await response.json()
#                     logger.info(f"Successfully fetched tweet {pid}")
#                     return data
#                 else:
#                     logger.error(f"Failed to fetch tweet {pid}, status: {response.status}")
#                     return None
#     except Exception as e:
#         logger.error(f"Error fetching tweet {pid}: {e}", exc_info=True)
#         return None


# async def get_tweet_summary(pid: str) -> Optional[dict]:
#     """
#     Get a summary of tweet information by PID
#
#     Args:
#         pid: Tweet ID (PID)
#
#     Returns:
#         Dictionary with tweet summary, or None if failed
#     """
#     try:
#         # Fetch tweet data
#         tweet_data = await twitter_fetch_tweet_details(pid)
#         if not tweet_data:
#             return None
#
#         # Extract content
#         content = await extract_tweet_content(tweet_data)
#         if not content:
#             return None
#
#         return {
#             'pid': pid,
#             'content': content,
#             'raw_data': tweet_data
#         }
#
#     except Exception as e:
#         logger.error(f"Error getting tweet summary: {e}", exc_info=True)
#         return None


# async def extract_tweet_content(tweet_data: dict) -> Optional[dict]:
#     """
#     Extract key tweet content from the raw Twitter API response
#     Args:
#         tweet_data: Raw tweet data from Twitter API
#     Returns:
#         Dictionary with extracted tweet content, or None if failed
#     """
#     try:
#         if not tweet_data or 'result' not in tweet_data:
#             return None
#
#         tweet_result = tweet_data.get('result', {}).get('tweetResult', {}).get('result', {})
#         if not tweet_result or tweet_result.get('__typename') != 'Tweet':
#             return None
#
#         return {
#             'tweet_id': tweet_result.get('rest_id'),
#             'full_text': tweet_result.get('legacy', {}).get('full_text'),
#             'created_at': tweet_result.get('legacy', {}).get('created_at'),
#             'user': {
#                 'screen_name': tweet_result.get('core', {}).get('user_results', {}).get('result', {}).get('legacy',
#                                                                                                           {}).get(
#                     'screen_name'),
#                 'name': tweet_result.get('core', {}).get('user_results', {}).get('result', {}).get('legacy', {}).get(
#                     'name'),
#                 'profile_image_url': tweet_result.get('core', {}).get('user_results', {}).get('result', {}).get(
#                     'legacy', {}).get('profile_image_url_https')
#             },
#             'stats': {
#                 'favorite_count': tweet_result.get('legacy', {}).get('favorite_count'),
#                 'retweet_count': tweet_result.get('legacy', {}).get('retweet_count'),
#                 'reply_count': tweet_result.get('legacy', {}).get('reply_count'),
#                 'quote_count': tweet_result.get('legacy', {}).get('quote_count'),
#                 'view_count': tweet_result.get('views', {}).get('count')
#             },
#             'media': tweet_result.get('legacy', {}).get('extended_entities', {}).get('media', [])
#         }
#     except Exception as e:
#         logger.error(f"Error extracting single tweet content: {e}", exc_info=True)
#         return None


# async def get_user_profile_summary(username: str) -> Optional[dict]:
#     """
#     Get a summary of user profile information for music generation
#
#     Args:
#         username: Twitter username
#
#     Returns:
#         Dictionary with user profile summary, or None if failed
#     """
#     try:
#         # Fetch user data
#         user_data = await twitter_fetch_user(username)
#         if not user_data:
#             return None
#
#         # Extract key profile information
#         profile = await extract_user_profile(user_data)
#         if not profile:
#             return None
#
#         return profile
#
#     except Exception as e:
#         logger.error(f"Error getting user profile summary: {e}", exc_info=True)
#         return None


# async def extract_user_profile(user_data: dict) -> Optional[dict]:
#     """
#     Extract key user profile information from the raw Twitter API response
#
#     Args:
#         user_data: Raw user data from Twitter API
#
#     Returns:
#         Dictionary with extracted user profile, or None if failed
#     """
#     try:
#         if not user_data or 'result' not in user_data:
#             return None
#
#         user_result = (
#             user_data.get('result', {})
#             .get('data', {})
#             .get('user', {})
#             .get('result', {})
#         )
#
#         if not user_result or user_result.get('__typename') != 'User':
#             return None
#
#         legacy = user_result.get('legacy', {})
#         professional = user_result.get('professional', {})
#
#         profile = {
#             'user_id': user_result.get('rest_id'),
#             'username': user_result.get('core', {}).get('screen_name'),
#             'display_name': user_result.get('core', {}).get('name'),
#             'description': legacy.get('description'),
#             'location': user_result.get('location', {}).get('location'),
#             'followers_count': legacy.get('followers_count'),
#             'following_count': legacy.get('friends_count'),
#             'tweets_count': legacy.get('statuses_count'),
#             'created_at': user_result.get('core', {}).get('created_at'),
#             'verified': user_result.get('is_blue_verified', False)
#                         or user_result.get('verification', {}).get('verified', False),
#             'profile_image_url': user_result.get('avatar', {}).get('image_url'),
#             'profile_banner_url': legacy.get('profile_banner_url'),
#             'website': legacy.get('url'),
#             'professional_type': professional.get('professional_type'),
#             'professional_category': (
#                 professional.get('category', [{}])[0].get('name')
#                 if professional.get('category')
#                 else None
#             )
#         }
#
#         return profile
#
#     except Exception as e:
#         logger.error(f"Error extracting user profile: {e}", exc_info=True)
#         return None


# async def get_user_tweets_summary(user_id: str, count: int = 10) -> Optional[dict]:
#     """
#     Get a summary of user's recent tweets for music generation
#
#     Args:
#         user_id: Twitter user ID
#         count: Number of tweets to fetch (default: 10)
#
#     Returns:
#         Dictionary with tweets summary, or None if failed
#     """
#     try:
#         # Fetch user tweets
#         tweets_data = await twitter_fetch_user_tweets(user_id)
#         if not tweets_data:
#             return None
#
#         # Extract key tweets information
#         tweets = await extract_user_tweets(tweets_data, count)
#         if not tweets:
#             return None
#
#         return {
#             'user_id': user_id,
#             'tweets_count': len(tweets),
#             'tweets': tweets
#         }
#
#     except Exception as e:
#         logger.error(f"Error getting user tweets summary: {e}", exc_info=True)
#         return None


# async def extract_user_tweets(tweets_data: dict, max_count: int = 10) -> Optional[list]:
#     """
#     Extract key tweets information from the raw Twitter API response
#
#     Args:
#         tweets_data: Raw tweets data from Twitter API
#         max_count: Maximum number of tweets to extract
#
#     Returns:
#         List of extracted tweets, or None if failed
#     """
#     try:
#         if not tweets_data or 'result' not in tweets_data:
#             return None
#
#         timeline = tweets_data.get('result', {}).get('timeline', {})
#         instructions = timeline.get('instructions', [])
#
#         tweets = []
#
#         # Find timeline entries
#         for instruction in instructions:
#             if instruction.get('type') == 'TimelineAddEntries':
#                 entries = instruction.get('entries', [])
#
#                 for entry in entries:
#                     if len(tweets) >= max_count:
#                         break
#
#                     # Extract tweet from entry
#                     tweet = await extract_tweet_from_entry(entry)
#                     if tweet:
#                         tweets.append(tweet)
#
#         return tweets[:max_count]
#
#     except Exception as e:
#         logger.error(f"Error extracting user tweets: {e}", exc_info=True)
#         return None


# async def extract_tweet_from_entry(entry: dict) -> Optional[dict]:
#     """
#     Extract tweet information from a timeline entry
#
#     Args:
#         entry: Timeline entry from Twitter API
#
#     Returns:
#         Dictionary with tweet information, or None if not a tweet
#     """
#     try:
#         content = entry.get('content', {})
#
#         # Check if this is a tweet entry
#         if content.get('entryType') != 'TimelineTimelineItem':
#             return None
#
#         item_content = content.get('itemContent', {})
#         if item_content.get('itemType') != 'TimelineTweet':
#             return None
#
#         tweet_results = item_content.get('tweet_results', {})
#         if not tweet_results or 'result' not in tweet_results:
#             return None
#
#         tweet_result = tweet_results.get('result', {})
#         if tweet_result.get('__typename') != 'Tweet':
#             return None
#
#         legacy = tweet_result.get('legacy', {})
#         views = tweet_result.get('views', {})
#
#         # Extract key tweet information for music generation
#         tweet = {
#             'tweet_id': legacy.get('id_str'),
#             'text': legacy.get('full_text'),
#             'created_at': legacy.get('created_at'),
#             'language': legacy.get('lang'),
#             'favorite_count': legacy.get('favorite_count'),
#             'retweet_count': legacy.get('retweet_count'),
#             'reply_count': legacy.get('reply_count'),
#             'quote_count': legacy.get('quote_count'),
#             'view_count': views.get('count') if views else None,
#             'is_quote': legacy.get('is_quote_status', False),
#             'is_reply': bool(legacy.get('in_reply_to_status_id_str')),
#             'has_media': bool(legacy.get('extended_entities', {}).get('media')),
#             'media_type': legacy.get('extended_entities', {}).get('media', [{}])[0].get('type') if legacy.get(
#                 'extended_entities', {}).get('media') else None
#         }
#
#         return tweet
#
#     except Exception as e:
#         logger.error(f"Error extracting tweet from entry: {e}", exc_info=True)
#         return None


# async def get_user_music_generation_context(username: str) -> Optional[dict]:
#     """
#     Get comprehensive user context for music generation including profile and recent tweets
#
#     Args:
#         username: Twitter username
#
#     Returns:
#         Dictionary with user context for music generation, or None if failed
#     """
#     try:
#         # Get user profile
#         profile = await get_user_profile_summary(username)
#         if not profile:
#             logger.error(f"Failed to get profile for user: {username}")
#             return None
#
#         # Get user ID from profile
#         user_id = profile.get('user_id')
#
#         # Get recent tweets
#         tweets_summary = await get_user_tweets_summary(user_id, 10)
#
#         # Combine profile and tweets for music generation context
#         context = {
#             'profile': profile,
#             'recent_tweets': tweets_summary.get('tweets', []) if tweets_summary else [],
#             'total_tweets_fetched': len(tweets_summary.get('tweets', [])) if tweets_summary else 0
#         }
#
#         logger.info(f"Successfully gathered music generation context for user {username}: "
#                    f"profile info + {context['total_tweets_fetched']} recent tweets")
#
#         return context
#
#     except Exception as e:
#         logger.error(f"Error getting user music generation context: {e}", exc_info=True)
#         return None


# async def generate_music_prompt_from_context(user_context: dict, style: str = None):
#     """
#     Generate a music generation prompt from user context
#
#     Args:
#         user_context: User context including profile and tweets
#         style: Optional music style
#
#     Returns:
#         Formatted prompt for music generation
#     """
#     try:
#         profile = user_context.get('profile', {})
#         tweets = user_context.get('recent_tweets', [])
#
#         # Build profile summary
#         profile_summary = f"User: {profile.get('display_name', 'Unknown')} (@{profile.get('username', 'unknown')})\n"
#         profile_summary += f"Description: {profile.get('description', 'No description')}\n"
#         profile_summary += f"Location: {profile.get('location', 'Unknown location')}\n"
#         profile_summary += f"Followers: {profile.get('followers_count', 0):,}\n"
#         profile_summary += f"Professional: {profile.get('professional_type', 'Personal account')}\n"
#         if profile.get('professional_category'):
#             profile_summary += f"Category: {profile.get('professional_category')}\n"
#
#         # Build tweets summary
#         tweets_summary = "Recent tweets:\n"
#         for i, tweet in enumerate(tweets[:5], 1):  # Use first 5 tweets for prompt
#             tweet_text = tweet.get('text', '')
#             if tweet_text:
#                 # Truncate long tweets
#                 if len(tweet_text) > 100:
#                     tweet_text = tweet_text[:100] + "..."
#                 tweets_summary += f"{i}. {tweet_text}\n"
#
#         return style, profile_summary, tweets_summary
#
#     except Exception as e:
#         logger.error(f"Error generating music prompt: {e}", exc_info=True)
#         raise e
