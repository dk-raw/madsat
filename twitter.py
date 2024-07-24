import tweepy

# Replace these values with your credentials
API_KEY = '8bmtO48h9rSrbniNFsO4Ni8bF'
API_SECRET_KEY = '1S6JpE1D1gtYcDaAWKOEe5mw4mcOY0VPEZKRaAGJJ3VF0tx7op'
ACCESS_TOKEN = '1324811255018885120-gfdAqYRMNmwvHXFedWU1TIo2GOa3TJ'
ACCESS_TOKEN_SECRET = 'tdscSDTfSQNobj40eyCMxejCtnbOLvMNlbZjkaWJruc4O'

# Authenticate to Twitter
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

# Post a tweet
tweet = "test test test"
try:
    api.update_status(status=tweet)
    print("Tweet posted successfully!")
except tweepy.TweepError as e:
    print(f"Error: {e.reason}")
