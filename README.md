Stream Detective

Example crontab:
```
MAILTO=""
*/5 * * * * python3 ~/StreamDetective/StreamDetective.py >> ~/StreamDetective.log 2>&1
0 0 1 * * mv -f ~/StreamDetective.log ~/StreamDetective.old.log
```
