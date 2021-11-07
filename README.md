# Red Flagged Hacker News

This project is a crawler, website builder. It crawls [hackers news](https://news.ycombinator.com/news) and puts information about each story in an sql table (postgress for that matter).
The point of the crawler is to display stories that were flagged, hence its name.

Here is the generated page [red flagged hackers news](https://mosermichael.github.io/flagged-hn/page_1.html)

The HN moderators are doing a good job, mostly - as you can see.

let's wait and see what the reaction at the proper HN will be... Here is the [HN submission](https://news.ycombinator.com/item?id=29113079), let's see if it ends up being flagged too ;-)

Wow! I did cause them to change: now they flag stories, but they also delete the title from the story, like [here](https://news.ycombinator.com/item?id=29134228) ; someone has been reading my submission. Now you only see [flagged] in the title. That makes my little exercise here much less useful. That's also a lesson: crawlers can be made ineffective by slight changes in the input. At least i had some fun at making this little exercise...


On the other side: it makes [HN](https://news.ycombinator.com/) a bit less interesting.  I am sorry for having caused this, i had the best of intentions.

# Running the stuff

There is still a point to use this stuff, if you want to create your own database of HN post: here is the usage.

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
./crawler crawl -i
```

Run the page generator, (after the crawler)

```
./crawl.py format
```

Here is the help blurb:

```
usage: crawl.py [-h] [--verbose] [--db DB] [--user USER] [--host HOST]
                [--prompt]
                {crawl,oldcrawl,format,db} ...

Scanner for 'hacker news - red flag eddition' project

positional arguments:
  {crawl,oldcrawl,format,db}
    crawl               crawl hn (new crawler, crawls a range of entry ids
    oldcrawl            crawl hn (old crawler, crawl the front page, then
                        crawl the next page, etc)
    format              format the site
    db                  db commands

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         trace all commands, verbose output (default: False)
  --db DB, -b DB        set posgress db name (for db connect) (default: rf-hn)
  --user USER, -u USER  set posgress db name (for db connect) (default:
                        michaelmo)
  --host HOST, -n HOST  set postgress host (for db connect) (default:
                        localhost)
  --prompt, -p          prompts for the db password (default: False)

```

Help for ``crawl``` sub command
```
usage: crawl.py crawl [-h] [--from FROM_ENTRY] [--to TO_ENTRY] [--init]

optional arguments:
  -h, --help            show this help message and exit
  --from FROM_ENTRY, -f FROM_ENTRY
                        set highest entry id to start crawl (default: find the
                        highest and start with it)
  --to TO_ENTRY, -t TO_ENTRY
                        set lowest entry id to start crawl
  --init, -i            first run, create db table

```

Help for ```oldcrawl``` subcommand

```
usage: crawl.py oldcrawl [-h] [--init] [--maxpage MAXPAGE] [--tab TAB]

optional arguments:
  -h, --help            show this help message and exit
  --init, -i            first run, create db table
  --maxpage MAXPAGE, -m MAXPAGE
                        maximum number of pages to crawl
  --tab TAB, -t TAB     tab to crawl (0 - newest, 1 - new, 2 - ask, 3 - show)
```
Help for ```format``` subcommand

```
usage: crawl.py format [-h] [--format]

optional arguments:
  -h, --help    show this help message and exit
  --format, -f  format the page from db content
usage: crawl.py db [-h] [--min-entryid] [--max-entryid]

optional arguments:
  -h, --help         show this help message and exit
  --min-entryid, -m  show entry_id of the oldest entry
  --max-entryid, -x  show entry_id of the earliest entry
```

