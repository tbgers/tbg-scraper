"""A tool to convert the older, JSON-based database into a SQLite-based one."""
import json, sqlite3, sys, re
try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda a: a

fromfile = sys.argv[1] if len(sys.argv) > 1 else "posts.json"
tofile = sys.argv[2] if len(sys.argv) > 2 else (re.match(r"((?:.*/)*.*)\..*", fromfile)[1] + ".db")

# Confirm the user to do this
_ = input(
    f"This will load {re.sub(r'.*/','',fromfile)} "
    f"and clear up {re.sub(r'.*/','',tofile)}.\n"
    f"Are you sure you want to convert? [y/N] "
)
if _ != "y":
    exit()

# Proceed conversion
with open(fromfile, "r") as f:
    jsdb = json.load(f)
sqdb = sqlite3.connect(tofile)
cur = sqdb.cursor()

# Clear the table
try: # too lazy
    cur.execute("drop table posts")
except sqlite3.OperationalError:
    pass
finally:
    cur.execute("create table posts (rawHTML text, pID number primary key, tID number, fID number, user text, text text, time timestamp)")

# Convert!
for k, v in tqdm(jsdb.items()):
    cur.execute("insert into posts values (:rawHTML, :pid, :tid, :fid, :user, :text, :time)", v)
    
# Done!
sqdb.commit()
sqdb.close()