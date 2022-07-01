__version__ = "1.0.0"
"""A tool to scrape the TBGs.""" # __doc__
PAGENAME = "TBGScraper"
import json, sys, time, getopt, random, requests, os, sqlite3
from shutil import copyfile
try: from tqdm import tqdm
except: 
    #print("Failed importing tqdm")
    loading = False
else: loading = True
print(PAGENAME+"\nYour friendly post scraper for the TBGs.")

# Initialize variables
output = "posts.db"
backup = "backup.json"
checkpoint = 500
verbose = 0
parser = ""
start = None
end = None
delay = 0
skip = False
help = None
clean = True
info = f'''
Usage: 
    scraper.py <args> <start> <end>

Arguments:
    File related:
        -o, --output <path>       : File to save all the posts. (default "{output}")
        -b, --backup <path>       : File for backup the last state. (default "{backup}")
        -c, --checkpoint <num>    : Set checkpoint (at what PID will TBGMiner backup) (default every {checkpoint} posts)
        -D, --clean <bool>        : Remove backups after scraping is done (default {clean})
    
    Scraper:
        -p, --parser <num>        : Choose a parser. (Available parsers in the "parsers" directory)
        -d, --delay <time>        : Random delay to avoid spam (default {delay} seconds)
        -r, --rng <time>          : Range of RDTAS (default {range} seconds)
    
    Miscellanous:
        -h                        : Send help
        -v, --verbose <num>       : Give more output. (default {verbose}, -1 for quiet)
        -l, --loading <bool>      : Show loading bar. (uses tqdm)
        -s, --skip <bool>         : Skip postID if a critical error occured (default {skip})
'''.strip()
allowed={
    'output':'o',
    'checkpoint':'c',
    'verbose':'v',
    'parser':'p',
    'loading':'l',
    'delay':'d',
    'rng':'r',
    'skip':'s',
    'clean':'D'
}
smallow=":".join(list(allowed.values()))+":"+"h"
if loading: allowed["loading"]="l"

# Get arguments
try: opt, args = getopt.getopt(sys.argv[1:], smallow, list(x+"=" for x in allowed.keys())+["help"])
except getopt.GetoptError:
    print(info)
    sys.exit(2)
#finally: print(f"Parsed arguments: {opt} {args}")

# Start/end
args = args[:2]
if len(args) == 1: start = int(args[0])
elif len(args) == 2: 
    start, end = args
    start = int(start)
    end = int(end)

# Variables
for o, a in opt:
    if o in ("-h", "--help"):
        print(info)
        exit()
    if o.strip("-") not in list(allowed.keys())+list(allowed.values()): continue
    elif len(o)==2:
        # oof
        search = list(filter(lambda a: o[1] == a[0], allowed.values()))[0]
        search = list(filter(lambda a: allowed[a] == search, allowed.keys()))[0]
        if search: 
            globals()[search.strip("=")]=a
    else: 
        globals()[o[2:]]=a

# Convert from string
if type(loading)==str: loading = loading.lower() in "true 1 yes".split()
if type(clean)==str: clean = clean.lower() in "true 1 yes".split()
if type(checkpoint)==str: checkpoint = int(checkpoint)
if type(verbose)==str: verbose = int(verbose)
if type(delay)==str: delay = float(delay)
if type(range)==str: range = float(range)

# Choose parser
if parser=="":
    try: from parsers import lxml as p
    except ImportError:
        try: from parsers import html as p
        except ImportError:
            if verbose <= 0:raise ImportError("Cannot find a suitable HTML parser.") from None
            else: raise ImportError("Cannot find a suitable HTML parser.")
        else: print("Using HTMLParser as HTML parser")
    else: print("Using lxml as HTML parser")
    finally: getPost = p.getPost
else:
    try: 
        if "\n" in parser or ";" in parser: raise ImportError("Invalid parser name")
        else: exec(f"from parsers import {parser} as p;getPost=p.getPost")
    except ImportError as e: raise ImportError(f"Cannot use HTML parser {parser}: {e}") from None
    else: print(f"Using {parser} as parser")

# Load the database
db = sqlite3.connect(output)
cur = db.cursor()

# Input
recover=False
try:
    # Look if backup exist
    with open(backup,"r") as f:
        if input("Continue from last scraping session?").lower() in ("true", "yes", "y"):
            # Recover from backup
            b=json.loads(f.read())
            start=b["start"]+1
            end=b["end"]
            recover=True
        else: raise ValueError("Aborted")
except (IOError, ValueError) as e:
    # If not, check if scraping result exists
    try:
        cur.execute("select * from posts where pID = (select min(pID) from posts)")
        yes=input(f"{output} already exists. Do you want to append this file?")
        if yes.lower() in ("true", "yes", "y"):
            # Load scraping result
            start=cur.execute("select max(pID) from posts").fetchone()[0] + 1
        else: raise ValueError("Aborted")
    except (IOError, ValueError) as e:
        try:
            cur.execute("create table posts (rawHTML text, pID number primary key, tID number, fID number, user text, text text, time timestamp)")
        except sqlite3.OperationalError:
            pass
        # If not, ask/use start/end pID
        if not start: start=int(input("What pID should the scraping start? "))
    if not end: end=int(input("What pID should the scraping end? "))
    
# Confirmation
if verbose > -1:
    print(f"{PAGENAME} will begin scraping, starting in #{start}, and ends in #{end}.")
    input("Is this correct? If not, break or call an EOF.")

# The scraping!
print(f"{PAGENAME} is scraping now.")
count = range(start,end+1)
if verbose<2 and loading: count=tqdm(count)
for x in count:
    fails=0
    # Get the post
    while True:
        if fails == 10:print("Too many connection errors, are you connected to the Internet?",file=sys.stderr)
        try:
            post = getPost(x)
            cur.execute("insert into posts values (:rawHTML, :pid, :tid, :fid, :user, :text, :time)", post)
        except requests.exceptions.RequestException as e: 
            # Connection problems
            if verbose >= 2: print('An error occured while collecting Post ID %s:\n'%x if verbose>=3 else ''+"%s: %s"%(type(e).__name__,e),file=sys.stderr)
            elif verbose == 1: print("\n".join(e) if type(e)==tuple else type(e).__name__,f"(Attempt {fails})",file=sys.stderr)
            fails += 1
            time.sleep(1)
            continue
        except Exception as e: 
            # Critical error
            if skip: print(f"Failed parsing post ID {x}: {e}",file=sys.stderr)
            else: raise Exception(f"Failed parsing post ID {x}: {e}")
        else:
            # Check post status
            if verbose >= 2:
                if verbose >= 3: 
                    if post["rawHTML"] == "": print(f"Post ID {x} is in limbo.")
                    elif post["time"] == None: 
                        if 'class="msg"' in post["rawHTML"] or "class='msg'" in post["rawHTML"]: print(f"Post ID {x} is in limbo.")
                        else: print(f"Post ID {x} doesn't exist.")
                else: print(f"Post ID {x} is collected without problems.")
            if not loading:
                print(f"Scraped {x} post{'s' if x != 1 else ''} out of {end}", end="\r")
        break
        if delay: time.sleep(random.uniform(delay, delay+rng))
    # Occasional commit
    if (x%checkpoint) == 0:
        with open(backup,"w") as f:
            f.write(json.dumps({"start":x,"end":end}))
        db.commit()
        
# Done!
db.commit()
db.close()
if clean:
    print("Removing backup files")
    try: os.remove(backup)
    except: pass
print(f"{PAGENAME} has done scraping.")
#if recover: print("Since this is a recovered session, you need to merge the backups with \"posts.json\".\nWhy the miner didn't merge it by itself? I don't know.")
