"""Live reproduction of #3571 against current upstream/main.

Mimics `_resolve_active_lanes_manifest` smuggling --base through mission_branch,
then calls allocate_lane_worktree on a coord-topology mission and checks ancestry.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
from specify_cli.lanes.models import ExecutionLane, LanesManifest
from specify_cli.lanes.worktree_allocator import allocate_lane_worktree

def git(repo, *a, check=True):
    return subprocess.run(["git", *a], cwd=repo, check=check, capture_output=True, text=True)

def sha(repo, ref):
    return git(repo, "rev-parse", ref).stdout.strip()

def is_ancestor(repo, anc, desc):
    return subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", anc, desc],
                          capture_output=True).returncode == 0

tmp = Path(tempfile.mkdtemp())
repo = tmp / "repo"
repo.mkdir()
MISSION_SLUG = "demo-feature-01J6XW9K"
MISSION_ID = "01J6XW9KABCDEFGHJKMNPQRSTV"
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}"

git(repo, "init", "-q", "-b", "main")
git(repo, "config", "user.email", "t@example.com")
git(repo, "config", "user.name", "Test")
git(repo, "config", "commit.gpgsign", "false")

# Seed commit on main (this becomes the shared root — we want it NOT shared).
# Build: main -> commit U (unrelated). coordination_branch descends from U.
# Then an explicit-base branch B that diverges BEFORE U (does not contain U).
spec_dir = repo / "kitty-specs" / MISSION_SLUG
spec_dir.mkdir(parents=True)
(spec_dir / "spec.md").write_text("# spec\n")
(spec_dir / "status.events.jsonl").write_text('{"actor":"test","wp_id":"WP01"}\n')
(spec_dir / "status.json").write_text("{}\n")
(spec_dir / "meta.json").write_text(json.dumps({
    "mission_id": MISSION_ID, "mission_slug": MISSION_SLUG,
    "coordination_branch": COORD_BRANCH,
}))
git(repo, "add", ".")
git(repo, "commit", "-q", "-m", "seed (root)")
ROOT = sha(repo, "HEAD")

# Create divergent branch B off ROOT, add a commit unique to B.
git(repo, "branch", "explicit-base", ROOT)
git(repo, "checkout", "-q", "explicit-base")
(repo / "b_only.txt").write_text("only on B\n")
git(repo, "add", "."); git(repo, "commit", "-q", "-m", "B-only commit")
B_TIP = sha(repo, "explicit-base")

# Back on main, add unrelated commit U, then base coordination_branch on U.
git(repo, "checkout", "-q", "main")
(repo / "u_only.txt").write_text("unrelated work U\n")
git(repo, "add", "."); git(repo, "commit", "-q", "-m", "U: unrelated pending work")
U_TIP = sha(repo, "main")
# coordination_branch descends from U (delete stale seed-based branch first if present)
git(repo, "branch", "-D", COORD_BRANCH, check=False)
git(repo, "branch", COORD_BRANCH, "main")   # coord tip == U_TIP

print(f"ROOT={ROOT[:8]}  B_TIP={B_TIP[:8]}  U_TIP={U_TIP[:8]}")
print(f"coordination_branch descends from U: {is_ancestor(repo, U_TIP, COORD_BRANCH)}")
print(f"B contains U? {is_ancestor(repo, U_TIP, 'explicit-base')} (should be False)")

# Mimic _resolve_active_lanes_manifest: patch mission_branch = base ('explicit-base').
manifest = LanesManifest(
    version=1, mission_slug=MISSION_SLUG, mission_id=MISSION_ID,
    mission_branch="explicit-base",          # <-- the smuggled --base override
    target_branch="main",
    lanes=[ExecutionLane(lane_id="lane-a", wp_ids=("WP01",), write_scope=(),
                         predicted_surfaces=(), depends_on_lanes=(), parallel_group=0)],
    computed_at="2026-01-01T00:00:00Z", computed_from="test",
)

wt, branch = allocate_lane_worktree(repo_root=repo, mission_slug=MISSION_SLUG,
                                    wp_id="WP01", lanes_manifest=manifest)
print(f"\nlane branch = {branch}")
b_anc = is_ancestor(repo, B_TIP, branch)
u_anc = is_ancestor(repo, U_TIP, branch)
print(f"(a) --is-ancestor explicit-base(B) lane  -> {b_anc}  (FR-001 wants True)")
print(f"(b) --is-ancestor U lane                 -> {u_anc}  (FR-002 wants False)")

print("\n=== VERDICT ===")
if (not b_anc) and u_anc:
    print("#3571 REPRODUCES on current main: --base ignored; lane descends from unrelated U, not B.")
    sys.exit(0)
else:
    print("#3571 does NOT reproduce — possible supersession. Investigate.")
    sys.exit(2)
