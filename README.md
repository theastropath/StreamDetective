# Stream Detective

This is a bot to give you notifications about Twitch streams based on the category, title, tags, and/or streamer. It was originally created to alert us about streams of Deus Ex Randomizer and our other mods, and also The 7th Guest, The 11th Hour, and The 13th Doll. Stream Detective can send the notifications to Discord, Twitter, Mastodon, and Pushbullet.

Discuss here https://discord.gg/YCGJ8nXtAs (and you can also see it in action in the #streams channel!)

To set up your own instance, copy the `config.example.json` file to `config.json` and adjust the settings as desired. `clientId` and `accessToken` are for the Twitch API. `Searches` is what streams to search for. `NotificationServices` is where it can send notifications to.

Get a Twitch Client ID here https://dev.twitch.tv/console/apps and then you can use https://twitchapps.com/tokengen/ to easily get the access token.

Example crontab:
```
MAILTO=""
*/5 * * * * python3 ~/StreamDetective/StreamDetective.py >> ~/StreamDetective.log 2>&1
0 0 1 * * mv -f ~/StreamDetective.log ~/StreamDetective.old.log
```
