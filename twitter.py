import tweepy
import os
from dotenv import load_dotenv

load_dotenv()

consumer_key = os.getenv('consumer_key')
consumer_secret = os.getenv('consumer_secret')
access_token = os.getenv('access_token')
access_token_secret = os.getenv('access_token_secret')

client = tweepy.Client(
    consumer_key=consumer_key, consumer_secret=consumer_secret,
    access_token=access_token, access_token_secret=access_token_secret
)

def tweet(content):
    response = client.create_tweet(
        text=content
    )
    print(f"https://twitter.com/user/status/{response.data['id']}")
    return response.data['id']

def reply(content, id):
    response = client.create_tweet(
        text=content,
        in_reply_to_tweet_id=id
    )
    print(f"https://twitter.com/user/status/{response.data['id']}")
    return response.data['id']