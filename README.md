# Red Flagged Hacker News

This project is a crawler, website builder. It crawls [hackers news](https://news.ycombinator.com/news) and puts information about each story in an sql table (postgress for that matter).
The point of the crawler is to display stories that were flagged, hence its name.

Here is the generated page [red flagged hackers news](https://mosermichael.github.io/flagged-hn/page_1.html)

The HN moderators are doing a good job, mostly - as you can see.

let's wait and see what the reaction at the proper HN will be...
    
# Running the stuff

## running the crawler

this program requires postgresql and  ```psycopg2``` package.

I installed this stuff as follows:

```
brew install postgresql
pip3 install psycopg2-binary --force-reinstall --no-cache-dir
```

To start the postress server locally

```
brew services start postgresql
```

To create the db

```
createdb rf-hn
```

To create the db table, run the crawler with the ```-i``` option, ```-c``` option runs the crawler.
(there are additional options to change the db host, db name, etc).

```
./crawler -c -i
```

Run the crawler for the newest page (crawls a maximum of 300 pages)

```
./crawl.py -v -c  -m 300
``` 

Run the crawler for the main page (crawls a maximum of 300 pages)

```
./crawl.py -v -c -t 1 -m 300
```

Run the page generator, (after the crawler)

```
./crawl.py -f
```

Here is the help blurb:

```
./crawl.py -h
usage: crawl.py [-h] [--verbose] [--db DB] [--user USER] [--host HOST] [--init] [--crawl] [--maxpage MAXPAGE] [--tab TAB] [--format]

Scanner for 'hacker news - red flag eddition' project

optional arguments:
  -h, --help            show this help message and exit

scann and build the page:
  --verbose, -v         trace all commands, verbose output (default: False)
  --db DB, -b DB        set posgress db name (for db connect) (default: rf-hn)
  --user USER, -u USER  set posgress db name (for db connect) (default: michaelmo)
  --host HOST, -n HOST  set postgress host (for db connect) (default: localhost)
  --init, -i            first run, create db table (default: False)
  --crawl, -c           crawl the hn site (default: False)
  --maxpage MAXPAGE, -m MAXPAGE
                        maximum number of pages to crawl (default: 4000)
  --tab TAB, -t TAB     tab to crawl (0 - newest, 1 - new, 2 - ask, 3 - show) (default: 0)
  --format, -f          format the page from db content (default: False)

```

