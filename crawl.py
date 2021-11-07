#!/usr/bin/env python3
import os
import re
import sys
from datetime import datetime
import argparse
import getpass
import subb
import psycopg2


class DBLayer:
    def __init__(self, verbose, dbparams):
        self.conn = psycopg2.connect(
            f"dbname='{dbparams['dbname']}' user='{dbparams['user']}' host='{dbparams['host']}' password='{dbparams['pass']}'"
        )
        self.cursor = self.conn.cursor()
        self.verbose = verbose

    def make_tbl(self):
        print("creating db tables...")
        create_query = (
            "CREATE TABLE posts("
            "   entryid BIGINT PRIMARY KEY NOT NULL,"
            "   tab INTEGER,"
            "   nscore INTEGER,"
            "   ncomments INTEGER,"
            "   author VARCHAR(30),"
            "   created_at TIMESTAMPTZ,"
            "   status INTEGER,"
            "   ispost BOOLEAN,"
            "   title TEXT"
            ")"
        )
        print(create_query)
        self.cursor.execute(create_query)

        create_index = "create index posts_status on posts(status)"
        print(create_index)
        self.cursor.execute(create_index)

        create_index = "create index posts_tab on posts(tab)"
        print(create_index)
        self.cursor.execute(create_index)

        create_index = "create index posts_created_at on posts(created_at)"
        print(create_index)
        self.cursor.execute(create_index)

        self.conn.commit()
        print("db tables created!")

    def find_non_active(self, ispost):
        self.cursor.execute(
            """SELECT entryid, tab, title, nscore, ncomments, author, created_at, status, ispost FROM posts pst WHERE pst.status <> 1 AND pst.ispost is %s ORDER BY pst.created_at DESC""", (ispost,)
            #"""SELECT entryid, tab, title, nscore, ncomments, author, created_at, status, ispost FROM posts pst WHERE pst.status <> 1 ORDER BY pst.created_at"""
        )
        return self.cursor.fetchall()

    def find_post_latest(self, latest):
        if latest:
            self.cursor.execute(
                """SELECT entryid, tab, title, nscore, ncomments, author, created_at, status, ispost FROM posts pst WHERE pst.created_at = (SELECT MAX(created_at) from posts)"""
            )
        else:
            self.cursor.execute(
                """SELECT entryid, tab, title, nscore, ncomments, author, created_at, status, ispost FROM posts pst WHERE pst.created_at = (SELECT MIN(created_at) from posts)"""
            )
        ret = self.cursor.fetchall()
        if self.verbose:
            print(ret)
        if len(ret) == 0:
            return None
        return ret[0][0]



    def find_post(self, entry_id):
        self.cursor.execute(
            """SELECT entryid, tab, title, nscore, ncomments, author, created_at, status, ispost FROM posts pst WHERE pst.entryid = %s""", (entry_id,)
        )
        rows = self.cursor.fetchall()

        if len(rows) != 0:
            if self.verbose:
                print("key: ", entry_id, "found entry: ", rows)
            row = rows[0]
            return {
                "entry_id": row[0],
                "tab": row[1],
                "title": row[2],
                "nscore": int(row[3]),
                "ncomments": int(row[4]),
                "author": row[5],
                "created_at": row[6],
                "status": int(row[7]),
                "ispost": row[8]
            }

        return None

    def insert_post(self, rec, tab):
        if self.verbose:
            print("insert post record: ", rec, "tab:", tab)
        insert_query = """INSERT INTO posts (entryid, tab, title, nscore, ncomments, author, created_at, status, ispost) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        item_tuple = (
            rec["entry_id"],
            tab,
            rec["title"],
            rec["nscore"],
            rec["ncomments"],
            rec["author"],
            rec["created_at"],
            rec["status"],
            rec["ispost"]
        )
        self.cursor.execute(insert_query, item_tuple)
        self.conn.commit()

    def update_post(self, rec, tab):
        update_query = """UPDATE posts SET (tab, title, nscore, ncomments, author, created_at, status, ispost) = (%s, %s, %s, %s, %s, %s, %s, %s) WHERE entryid = %s"""
        item_tuple = (
            tab,
            rec["title"],
            rec["nscore"],
            rec["ncomments"],
            rec["author"],
            rec["created_at"],
            rec["status"],
            rec["ispost"],
            rec["entry_id"]
        )
        self.cursor.execute(update_query, item_tuple)
        self.conn.commit()


# tool to help construct web crawlers
class CrawlerUtil:
    def __init__(self, verbose):
        self.cmd = subb.RunCommand() #trace_on=verbose)
        self.verbose = verbose

    def fetch_url(self, url):
        self.cmd.run("curl " + url)
        return self.cmd.exit_code == 0

    def page(self):
        return self.cmd.output

    def find_between(self, from_str, to_str):
        find_pos = self.cmd.output.find(from_str)
        if find_pos == -1:
            if self.verbose:
                print("can't find to_str:", to_str)
            return None
        find_pos_end = self.cmd.output.find(to_str, find_pos + len(from_str))
        if find_pos_end == -1:
            if self.verbose:
                print("can't find to_str:", to_str)
            return None
        return self.cmd.output[find_pos + len(from_str) : find_pos_end]

    def find_between_r(self, from_str, to_str):
        find_pos = self.cmd.output.find(from_str)
        if find_pos == -1:
            if self.verbose:
                print("can't find from_str:", from_str)
            return None
        find_pos_end = self.cmd.output.rfind(to_str, 0, find_pos)
        if find_pos_end == -1:
            if self.verbose:
                print("can't find to_str:", to_str)
            return None

        print("find_pos_end:", find_pos_end, "len:", len(to_str), "find_pos:", find_pos)
        return self.cmd.output[find_pos_end + len(to_str) : find_pos]

# common hn crawler stuff
class HNCrawlerUtil:
    STATUS_ACTIVE = 1
    STATUS_FLAGGED = 2
    STATUS_DELETED = 3

    TAB_NEWEST = 0
    TAB_MAIN = 1
    TAB_ASK = 2
    TAB_SHOW = 3

    urls = [
        "https://news.ycombinator.com/newest",
        "https://news.ycombinator.com/news",
        "https://news.ycombinator.com/ask",
        "https://news.ycombinator.com/show",
    ]

    def __init__(self, verbose, crawl):
        self.verbose = verbose
        self.crawl = crawl

    def fetch_entry_ids(self, url):
        self.crawl.fetch_url(url)
        ret = re.findall(r'href="item\?id=(\d*)"', self.crawl.page())
        if self.verbose:
            print("items in page: ", url, "items:", ret)
        return ret

    def fetch_item(self, entry_id):
        url = "https://news.ycombinator.com/item?id=" + entry_id
        if self.verbose:
            print("fetch item url:", url)
        self.crawl.fetch_url(url)

        valid = True
        title = ""
        status = 0
        post_time = ""
        author = ""
        num_score = ""
        num_comments = ""
        is_post = False

        try:
            title = self.crawl.find_between('<td class="title">', "</td>")
            if title is None:
                title = self.crawl.find_between('<td class="default">', '<div class="comment">')
                if title is None:
                    print("can't find title for url " + url)
                    return None
            else:
                is_post = True

            status = HNCrawlerUtil.STATUS_ACTIVE
            if title.find("[flagged]") != -1:
                status = HNCrawlerUtil.STATUS_FLAGGED
            if title.find("[deleted]") != -1:
                status = HNCrawlerUtil.STATUS_DELETED

            post_time = self.crawl.find_between(
                '<span class="age" title="', '"'
            )  # 2021-07-14T09:24:32
            if post_time is None:
                print("can't find post time for url " + url)
                raise ValueError()

            author = self.crawl.find_between('class="hnuser">', "</a>")
            if author is None:
                author = ""

            score_raw = self.crawl.find_between('<span class="score"', "points</span>")
            if score_raw is None or score_raw == "":
                num_score = "0"
            else:
                pos = score_raw.find(">")
                num_score = score_raw[pos + 1 :]

            num_comments = self.crawl.find_between_r("&nbsp;comments</a>", '">')
            if num_comments is None or num_comments == "":
                num_comments = "0"

        except ValueError:
            valid = False

        if self.verbose:
            print("Raw post fields: valid:", valid, "entry_id:", entry_id,  "nscore:", num_score, "ncomments:", num_comments, "author:", author, "created_at:", post_time, "status:", status, "ispost:", is_post, "title:", title)

        return {
            "valid": valid,
            "entry_id": entry_id,
            "title": title,
            "nscore": int(num_score),
            "ncomments": int(num_comments),
            "author": author,
            "created_at": datetime.fromisoformat(post_time),
            "status": status,
            "ispost": is_post
        }

class HHCrawlerOnEntryIdRange:
    def __init__(self, verbose, entry_id_from, entry_id_to, dbparams):
        self.entry_id_from = entry_id_from
        self.entry_id_to = entry_id_to
        self.verbose = verbose
        self.dblayer = DBLayer(verbose, dbparams)

        crawl = CrawlerUtil(verbose)

        self.crawl = crawl
        self.hncrawl = HNCrawlerUtil(verbose, crawl)
        self.epoch_seconds_now = int(datetime.now().strftime("%s"))


    def scan(self):
        if self.entry_id_from == -1:
            self.entry_id_from = self.find_highest_entry_id()

        while self.entry_id_from > self.entry_id_to:

            entry_id = str(self.entry_id_from)
            self.entry_id_from -= 1

            rec = self.dblayer.find_post(entry_id)
            if rec is None:
                # new post
                rec = self.hncrawl.fetch_item(entry_id)
                if rec is None:
                    continue
                if rec["valid"]:
                    if self.verbose:
                        print("post scanned: ", rec)
                    self.dblayer.insert_post(rec, 0)
            else:
                if self.verbose:
                    print("existing post:", rec)
                # created_at = datetime.fromisoformat(rec['created_at'])

                epoch_seconds_post = int(rec["created_at"].strftime("%s"))
                if (self.epoch_seconds_now - epoch_seconds_post) < (10 * 24 * 3600):
                    # re check posts not older than ten days
                    check_rec = self.hncrawl.fetch_item(entry_id)
                    if check_rec is None:
                        continue
                    if check_rec["valid"]:
                        status_changed = False
                        if check_rec["status"] != rec["status"]:
                            if self.verbose:
                                print(
                                    "status of ",
                                    rec["entry_id"],
                                    "changed from: ",
                                    rec["status"],
                                    "to:",
                                    check_rec["status"],
                                )
                                status_changed = True
                        if (
                            status_changed
                            or rec["nscore"] != check_rec["nscore"]
                            or rec["ncomments"] != check_rec["ncomments"]
                        ):
                            self.dblayer.update_post(check_rec, 0)



    def find_highest_entry_id(self):
        url = "https://news.ycombinator.com/newcomments"
        all_match = self.hncrawl.fetch_entry_ids(url)
        max_entry = -1
        for match in all_match:
            if max_entry < int(match):
                max_entry = int(match)

        if self.verbose:
            print("Highest entry_id: ", self.entry_id_from)

        if max_entry == -1:
            print("Error: can't find highest entry id")
            sys.exit(1)

        return max_entry

class HNCrawlerFollowNextPage:
    def __init__(self, verbose, dbparams):

        self.dblayer = DBLayer(verbose, dbparams)
        crawl = CrawlerUtil(verbose)

        self.verbose = verbose
        self.crawl = crawl
        self.hncrawl = HNCrawlerUtil(verbose, crawl)
        self.epoch_seconds_now = int(datetime.now().strftime("%s"))

    def scan(self, pages, tab):

        print("starting the crawl: 'Forwaerts immer, rueckwaerts nimmer!'/'forward ever backward never' Erich Honecker ... max-page: ", pages)

        insert_or_up = 0

        for page in range(1, pages):

            print("scanning page:", page)

            url = HNCrawlerUtil.urls[tab]

            if tab == HNCrawlerUtil.TAB_NEWEST:
                if page > 1:
                    url += f"?next={next_id}&n={next_n}"
            else:
                if page > 1:
                    url += "?p=" + str(page)

            all_match = self.hncrawl.fetch_entry_ids(url)

            if tab == HNCrawlerUtil.TAB_NEWEST:
                match = re.search(
                    r'href="newest.next=(\d*)&amp;n=(\d+)"', self.crawl.page()
                )
                if match is None:
                    if self.verbose:
                        print(f"no next page! url: {url} page {page}")
                    return page
                next_id = match.group(1)
                next_n = match.group(2)

            # remove duplicates
            all_match = list(set(all_match))

            if self.verbose:
                print("page:",url, "posts:", all_match)

            insert_or_update = self.process_items(all_match, tab)
            if insert_or_update == 0:
                insert_or_up += 1
#                if insert_or_up == 2:
#                    return page
            else:
                insert_or_up = 0

        return pages

    def process_items(self, all_match, tab):
        insert_or_update = 0

        for entry_id in all_match:

            rec = self.dblayer.find_post(entry_id)
            if rec is None:
                # new post
                rec = self.hncrawl.fetch_item(entry_id)
                if rec is None: 
                    continue 

                if rec["valid"]:
                    if self.verbose:
                        print("post scanned: ", rec)
                    self.dblayer.insert_post(rec, tab)
                    insert_or_update += 1
            else:
                if self.verbose:
                    print("existing post:", rec)
                # created_at = datetime.fromisoformat(rec['created_at'])

                epoch_seconds_post = int(rec["created_at"].strftime("%s"))
                if (self.epoch_seconds_now - epoch_seconds_post) < (10 * 24 * 3600):
                    # re check posts not older than ten days
                    check_rec = self.hncrawl.fetch_item(entry_id)
                    if check_rec is None:
                        continue
                    if check_rec["valid"]:
                        status_changed = False
                        if check_rec["status"] != rec["status"]:
                            if self.verbose:
                                print(
                                    "status of ",
                                    rec["entry_id"],
                                    "changed from: ",
                                    rec["status"],
                                    "to:",
                                    check_rec["status"],
                                )
                                status_changed = True
                        if (
                            status_changed
                            or rec["nscore"] != check_rec["nscore"]
                            or rec["ncomments"] != check_rec["ncomments"]
                        ):
                            self.dblayer.update_post(check_rec, tab)
                            insert_or_update += 1
        return insert_or_update


class FormatPage:
    def __init__(self, verbose, dbparams):
        self.verbose = verbose
        self.dblayer = DBLayer(verbose, dbparams)
        self.page_file = None


    def format(self):
        print("'Nobody has any intention of building a wall' Walter Ulbricht")

        rows = self.dblayer.find_non_active(true)

        item = 0
        page_count = 1
        for row in rows:
            if item ==0 or item % 31 == 0:
                self.show_page_header(page_count)
                page_count += 1

            self.show_item((item + 1) % 30, row)

            if item != 0 and item % 30 == 0:
                self.show_page_footer(page_count+1)
            item += 1

        if (item - 1) % 30 == 0:
            self.show_page_footer(page_count)


    def show_item(self, item_num, row):
        if self.verbose:
            print("item:", item_num, "row:", row)

        entry_id = row[0]
        title = row[2]
        nscore = int(row[3])
        ncomments = int(row[4])
        author = row[5]
        created_at = row[6]
        time_str = created_at.strftime("%d/%m/%y")
        time_str_hint = created_at.strftime("%Y-%m-%d%z%H:%M:%S")

        #dirty hack, to fix hn link to items from the same site.
        title=title.replace("from?site=", "https://news.ycombinator.com/from?site=")

        print(f"""
<!-- item start //-->
 <tr class='athing' id='{entry_id}'>
    <td align="right" valign="top" class="title"><span class="rank">{item_num}.</span></td>
    <td valign="top" class="votelinks">
       <center>
          <a id='up_{entry_id}' href='https://news.ycombinator.com/vote?id={entry_id}&amp;how=up&amp;goto=newest'>
             <div class='votearrow' title='upvote'></div>
          </a>
       </center>
    </td>
    <td class="title">{title}</td>
 </tr>
 <tr>
    <td colspan="2"></td>
    <td class="subtext">
       <span class="score" id="score_{entry_id}">{nscore} points</span> | <span class="score">{ncomments} comments</span> | by <a href="https://news.ycombinator.com/user?id={author}" class="hnuser">{author}</a> | <span class="age" title="{time_str_hint}"><a href="https://news.ycombinator.com/item?id={entry_id}">{time_str}</a></span> <span id="unv_{entry_id}"></span> | <a href="https://news.ycombinator.com/item?id={entry_id}">discuss</a>
    </td>
 </tr>
 <!-- item end //-->
""", file=self.page_file)


    def show_page_footer(self, page_number):
        if self.verbose:
            print(f"show page footer next-page: {page_number}")

        print(f"""
          <tr class="spacer" style="height:5px"></tr>
          <tr class="morespace" style="height:10px"></tr>
          <tr>
            <td colspan="2"></td>
            <td class="title">
              <a
                href="newest?next=29106308&amp;n=31"
                class="morelink"
                rel="page_{page_number+1}.html"
                >More</a
              >
            </td>
          </tr>
      </table>
   </td>
</tr>
</table>
""", file=self.page_file)

        self.page_file.close()
        self.page_file = None

    def show_page_header(self, page_number):
        if self.verbose:
            print(f"show page footer {page_number}")

        self.page_file = open(f"page_{page_number}.html", "w")

        print( """
<html lang="en" op="newest">
   <head>
      <meta name="referrer" content="origin">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" type="text/css" href="data/news.css>
      <link rel="shortcut icon" href="favicon.ico">
      <title>New Links | Hacker News</title>
   </head>
<body>
      <center>
        <img src="data/hn3.png" style="width: 75vw"/>
        <table id="hnmain" border="0" cellpadding="0" cellspacing="0" width="85%" bgcolor="#f6f6ef">
            <tr>
               <td bgcolor="#ff6600">
                  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="padding:2px">
                     <tr>
                        <td style="width:18px;padding-right:4px"><a href="https://news.ycombinator.com"><img src="data/y18.gif" width="18" height="18" style="border:1px white solid;"></a></td>
                        <td style="line-height:12pt; height:10px;"><span class="pagetop"><b class="hnname"><a href="https://news.ycombinator.com/news">Hacker News</a></b>
                           <span class="topsel"><a href="https://news.ycombinator.com/newest">new</a></span> | <a href="front">past</a> | <a href="https://news.ycombinator.com/newcomments">comments</a> | <a href="https://news.ycombinator.com/ask">ask</a> | <a href="https://news.ycombinator.com/show">show</a> | <a href="https://news.ycombinator.com/jobs">jobs</a> | <a href="https://news.ycombinator.com/submit">submit</a>            </span>
                        </td>
                        <td style="text-align:right;padding-right:4px;"><span class="pagetop">
                           <a href="https://news.ycombinator.com/login?goto=newest">login</a>
                           </span>
                        </td>
                     </tr>
                  </table>
               </td>
            </tr>
            <tr id="pagespace" title="New Links" style="height:10px"></tr>
            <tr>
               <td>
                  <table border="0" cellpadding="0" cellspacing="0" class="itemlist">

""", file=self.page_file)




def parse_cmd_line():

    usage = """
Scanner for 'hacker news - red flag eddition' project


"""
    parent_parser = argparse.ArgumentParser(
        description=usage, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # common arguments
    parent_parser.add_argument(
        "--verbose",
        "-v",
        default=False,
        action="store_true",
        dest="verbose",
        help="trace all commands, verbose output",
    )

    parent_parser.add_argument(
        "--db",
        "-b",
        default="rf-hn",
        type=str,
        dest="db",
        help="set posgress db name (for db connect)",
    )

    parent_parser.add_argument(
        "--user",
        "-u",
        default=os.getenv("USER"),
        type=str,
        dest="user",
        help="set posgress db name (for db connect)",
    )

    parent_parser.add_argument(
        "--host",
        "-n",
        default="localhost",
        type=str,
        dest="host",
        help="set postgress host (for db connect)",
    )

    parent_parser.add_argument(
        "--prompt",
        "-p",
        default=False,
        action="store_true",
        dest="prompt_password",
        help="prompts for the db password"
    )

    subparsers = parent_parser.add_subparsers(dest='command')

    parser = subparsers.add_parser('crawl', help='crawl hn (new crawler, crawls a range of entry ids')

    parser.add_argument(
        "--from",
        "-f",
        default=-1,
        type=int,
        dest="from_entry",
        help="set highest entry id to start crawl (default: find the highest and start with it)"
    )

    parser.add_argument(
        "--to",
        "-t",
        default=0,
        type=int,
        dest="to_entry",
        help="set lowest entry id to start crawl"
    )

    parser.add_argument(
        "--init",
        "-i",
        default=False,
        action="store_true",
        dest="init",
        help="first run, create db table",
    )


    parser = subparsers.add_parser('oldcrawl', help='crawl hn (old crawler, crawl the front page, then crawl the next page, etc)')

    parser.add_argument(
        "--init",
        "-i",
        default=False,
        action="store_true",
        dest="init",
        help="first run, create db table",
    )


    parser.add_argument(
        "--maxpage",
        "-m",
        default=4000,
        type=int,
        dest="maxpage",
        help="maximum number of pages to crawl",
    )

    parser.add_argument(
        "--tab",
        "-t",
        default=0,
        type=int,
        dest="tab",
        help="tab to crawl (0 - newest, 1 - new, 2 - ask, 3 - show)"
    )

    parser = subparsers.add_parser('format', help='format the site')

    # formatting of site
    parser.add_argument(
        "--format",
        "-f",
        default=False,
        action="store_true",
        dest="format",
        help="format the page from db content",
    )

    parser = subparsers.add_parser('db', help='db commands')

    parser.add_argument(
        "--min-entryid",
        "-m",
        default=False,
        action="store_true",
        dest="min_entry",
        help="show entry_id of the oldest entry",
    )

    parser.add_argument(
        "--max-entryid",
        "-x",
        default=False,
        action="store_true",
        dest="max_entry",
        help="show entry_id of the earliest entry",
    )


    return parent_parser.parse_args()



def make_site():

    args = parse_cmd_line()

    db_pass = ''
    if args.prompt_password:
        db_pass = getpass.getpass(prompt="DB Password: ")

    dbparams = { 'dbname' : args.db, 'user': args.user, 'host': args.host, 'pass': db_pass }

    if args.command == "format":

        page = FormatPage(args.verbose, dbparams)

        page.format()

    elif args.command == "crawl":

        crawler = HHCrawlerOnEntryIdRange(args.verbose, args.from_entry, args.to_entry, dbparams)

        if args.init:
            crawler.dblayer.make_tbl()

        crawler.scan()


    elif args.command == "oldcrawl":

        crawler = HNCrawlerFollowNextPage(args.verbose, dbparams)

        if args.tab < HNCrawlerUtil.TAB_NEWEST or args.tab > HNCrawlerUtil.TAB_SHOW:
            print("Error: tab value invalid")
            sys.exit(1)

        # scan & crawl
        if args.init:
            crawler.dblayer.make_tbl()

        crawler.scan(args.maxpage, args.tab)

    elif args.command == "db":

        dblayer = DBLayer(args.verbose, dbparams)

        if args.max_entry:
            print( dblayer.find_post_latest(True) )

        if args.min_entry:
            print( dblayer.find_post_latest(False) )

    else:
        print("Error: no action specified")
        sys.exit(1)



if __name__ == '__main__':
    make_site()
