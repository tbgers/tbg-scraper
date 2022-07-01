"""A tool to convert the current SQLite-based database into JSON."""
import json, sqlite3, sys, re
try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda a: a

fromfile = sys.argv[1] if len(sys.argv) > 1 else "posts.db"
tofile = sys.argv[2] if len(sys.argv) > 2 else (re.match(r"((?:.*/)*.*)\..*", fromfile)[1] + ".json")

# Confirm the user to do this
_ = input(
    f"This will convert {re.sub(r'.*/','',fromfile)} to {re.sub(r'.*/','',tofile)}.\n"
    f"Are you sure you want to convert? [y/N] "
)
if _ != "y":
    exit()

# Proceed conversion
sqdb = sqlite3.connect(fromfile)
cur = sqdb.cursor()
jsdb = {}

# Convert!
for rec in tqdm(cur.execute("select * from posts")):
    r = dict(zip(["rawHTML", "pid", "tid", "fid", "user", "text", "time"], rec))
    jsdb[rec[1]] = r
    
# Save the JSON file
with open(tofile, "w") as f:
    json.dump(jsdb, f)
    
# Done!
sqdb.commit()
sqdb.close()
