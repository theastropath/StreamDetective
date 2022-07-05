Stream Detective

Example crontab:
```
MAILTO=""
* * * * * python3 ~/StreamDetective/StreamDetective.py >> ~/StreamDetective.log
0 0 1 * * mv -f ~/StreamDetective.log ~/StreamDetective.old.log
```