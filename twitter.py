import sys
import os
import logging
import tweepy
from dotenv import load_dotenv
import tweepy.client

logger = logging.getLogger("liggma")

try:
    load_dotenv()
    consumer_key = os.getenv("consumer_key")
    consumer_secret = os.getenv("consumer_secret")
    access_token = os.getenv("access_token")
    access_token_secret = os.getenv("access_token_secret")
except Exception as e:
    logger.critical(e)
    sys.exit(1)

try:
    clientV2 = tweepy.Client(
        consumer_key=consumer_key, consumer_secret=consumer_secret,
        access_token=access_token, access_token_secret=access_token_secret
    )

    authV1 = tweepy.OAuth1UserHandler(
        consumer_key, consumer_secret, access_token, access_token_secret
    )

    api = tweepy.API(authV1)
except Exception as e:
    logger.critical(e)
    sys.exit(1)

def tweet(content):
    try:
        res = clientV2.create_tweet(
            text=content
        )
        return res.data['id']
    except Exception as e:
        logger.critical(e)
        sys.exit(1)

def reply(content, id, media_id=""):
    try:
        if media_id:
            res = clientV2.create_tweet(
                text=content,
                in_reply_to_tweet_id=id,
                media_ids=media_id
            )
        else:
            res = clientV2.create_tweet(
                text=content,
                in_reply_to_tweet_id=id
            )
        return res.data['id']
    except Exception as e:
        logger.error(e)

def upload(filename):
    try:
        res = api.media_upload(filename)
        return res.media_id
    except Exception as e:
        logger.error(e)
