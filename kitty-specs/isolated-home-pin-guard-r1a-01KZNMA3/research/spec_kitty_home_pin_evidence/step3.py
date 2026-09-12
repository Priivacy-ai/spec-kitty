import sys, ast
sys.path.insert(0, "/tmp/claude-1000/-home-jeroennouws-dev-sk-missions/ca298d9c-391a-43ff-ab54-419c109c6f77/scratchpad/dbg")
from clf import *
from collections import Counter, defaultdict

files = sorted((ROOT/"tests").rglob("*.py"))
sites = classify(files)
eff = [s for s in sites if s["value"] == ("tmp_path", ("home",))]
print("effect-class sites:", len(eff), "files:", len({s['path'] for s in eff}))

# kind of the *site's innermost def* vs the keyed def
def kind_of(s):
    return s["keyed_isfixture"]

members = {}
for s in eff:
    if s["keyed"] is None:
        print("  !! effect site with NO satisfying def:", s["path"], s["lineno"], s["defchain"])
        continue
    k = (s["path"], s["keyed_qual"], s["keyed_line"])
    members.setdefault(k, []).append(s)
print("MEMBERS (scope-chain attribution):", len(members), "files:", len({k[0] for k in members}))
multi = {k:v for k,v in members.items() if len(v)>1}
print("members with >1 site:", len(multi), list(multi))

# kind split of the 40 effect sites
kc = Counter()
for s in eff:
    kc["fixture" if s["keyed_isfixture"] else ("decorated-nonfixture" if s["keyed_decorated"] else "plain")] += 1
print("effect sites by keyed-def decoration:", dict(kc))

# classify test-body vs helper vs fixture by keyed def name/decorator
kc2 = Counter()
for s in eff:
    if s["keyed_isfixture"]: kc2["fixture"] += 1
    elif s["keyed_qual"].split(".")[-1].startswith("test_"): kc2["test-body"] += 1
    else: kc2["helper"] += 1
print("effect sites fixture/test-body/helper:", dict(kc2))
for s in eff:
    if not s["keyed_isfixture"] and not s["keyed_qual"].split(".")[-1].startswith("test_"):
        print("   HELPER:", s["path"], s["lineno"], s["keyed_qual"], "chain=", s["defchain"])

# innermost attribution
inner_members = {}
for s in eff:
    if s["innermost_member"]:
        inner_members.setdefault((s["path"], s["innermost_qual"]), []).append(s)
print("MEMBERS (innermost attribution):", len(inner_members), "files:", len({k[0] for k in inner_members}))
# symmetric difference by site
sc_sites = {(s["path"], s["lineno"]) for s in eff if s["keyed"]}
in_sites = {(s["path"], s["lineno"]) for s in eff if s["innermost_member"]}
print("sites caught scope-chain:", len(sc_sites), " innermost:", len(in_sites))
print("symmetric difference of SITES:", sorted(sc_sites ^ in_sites))

# decorator-limbed (superseded) predicate: keyed def must be a fixture
dec_members = {k for k,v in members.items() if v[0]["keyed_isfixture"]}
print("members under decorator-limbed predicate (keyed def is fixture):", len(dec_members))

import json
open("/tmp/claude-1000/-home-jeroennouws-dev-sk-missions/ca298d9c-391a-43ff-ab54-419c109c6f77/scratchpad/dbg/members.json","w").write(json.dumps(
    sorted([{"path":k[0],"qual":k[1],"line":k[2],"sites":[s["lineno"] for s in v],"fixture":v[0]["keyed_isfixture"]} for k,v in members.items()], key=lambda d:(d["path"],d["line"])), indent=1))
print("\n== member list ==")
for k,v in sorted(members.items()):
    print(f"  {'FIX' if v[0]['keyed_isfixture'] else '   '} {k[0]}:{k[2]} {k[1]}  sites={[s['lineno'] for s in v]}")
