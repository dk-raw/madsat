import tweepy
import os
from dotenv import load_dotenv
import tweepy.client

load_dotenv()

consumer_key = os.getenv('consumer_key')
consumer_secret = os.getenv('consumer_secret')
access_token = os.getenv('access_token')
access_token_secret = os.getenv('access_token_secret')

clientV2 = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)

authV1 = tweepy.OAuth1UserHandler(
    consumer_key, consumer_secret, access_token, access_token_secret
)

api = tweepy.API(authV1)

def tweet(content):
    res = clientV2.create_tweet(
        text=content
    )
    print(f"https://twitter.com/user/status/{res.data['id']}")
    return res.data['id']

def reply(content, id, media_id):
    res = clientV2.create_tweet(
        text=content,
        in_reply_to_tweet_id=id,
        media_ids=media_id
    )
    print(f"https://twitter.com/user/status/{res.data['id']}")
    return res.data['id']

def upload(filename):
    res = api.media_upload(filename)
    print("Media uploaded successfully.")
    return res.media_id