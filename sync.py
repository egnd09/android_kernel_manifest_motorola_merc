#!/usr/bin/env python3
"""Sync the merc (Motorola Edge 70 Pro, MT6899) Kleaf kernel workspace with plain git.

Reads default.xml (repo-manifest format), shallow-clones every project at its revision,
creates the <linkfile> symlinks, fetches the two prebuilts/clang/host/linux-x86 directories
Kleaf needs from gitiles (the full project is tens of GB), sparse-checks-out the NDK sysroot,
creates the workspace symlinks MediaTek's build.sh expects and prunes mgk_64.bzl labels
whose packages are not published (prune-missing.py).

  ./sync.py                       # everything into ./workspace/kernel
  ./sync.py --top /big/disk       # elsewhere (needs ~15 GB + ~20 GB for the build)
  ./sync.py --only build/kernel   # a subset (repeatable); extras are addressed by their path too
  ./sync.py --revision MMI-A171WMH.44-25   # Android 17 tag for the Motorola projects

Existing project directories are left alone (delete one to re-sync it).
"""
import argparse, base64, json, os, subprocess, sys, tarfile, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GITILES_CLANG = "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86"
CLANG_REV = "refs/heads/main-kernel-build-2024"
CLANG_DIRS = ("clang-r510928", "kleaf")   # build.config.constants: CLANG_VERSION=r510928
SPARSE = {"prebuilts/ndk-r26": ["toolchains/llvm/prebuilt/linux-x86_64/sysroot"]}
SYMLINKS = [  # (link relative to workspace/kernel, target)
    ("WORKSPACE", "build/bazel_mgk_rules/kleaf/bazel.WORKSPACE"),
    ("tools/bazel", "../build/kernel/kleaf/bazel.sh"),
    ("../vendor", "kernel/vendor"),                       # MediaTek's WORKSPACE refers to ../vendor/mediatek
    ("kernel_device_modules-6.6/kernel/configs/moto-mgk_64_k66.config",
     "../../arch/arm64/configs/ext_config/moto-mgk_64_k66.config"),       # Motorola's defconfig.mk does this
    ("kernel_device_modules-6.6/kernel/configs/moto-mgk_64_k66-merc.config",
     "../../arch/arm64/configs/ext_config/moto-mgk_64_k66-merc.config"),
]

def run(*cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)

def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

def parse_manifest(path):
    root = ET.parse(path).getroot()
    remotes = {r.get("name"): r.get("fetch") for r in root.findall("remote")}
    d = root.find("default")
    projects = []
    for p in root.findall("project"):
        projects.append({
            "path": p.get("path"), "name": p.get("name"),
            "url": remotes[p.get("remote", d.get("remote"))] + p.get("name"),
            "revision": p.get("revision", d.get("revision")),
            "depth": p.get("clone-depth", d.get("clone-depth")),
            "linkfiles": [(l.get("src"), l.get("dest")) for l in p.findall("linkfile")],
        })
    return projects

def clone(ws, p, revision_override):
    dest = os.path.join(ws, p["path"])
    rev = p["revision"]
    if revision_override and p["url"].startswith("https://github.com/MotorolaMobilityLLC/"):
        rev = "refs/tags/" + revision_override
    branch = rev.split("/", 2)[2] if rev.startswith("refs/") else rev
    if os.path.isdir(os.path.join(dest, ".git")):
        print(f"= {p['path']} (exists)"); 
    else:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        cmd = ["git", "-c", "advice.detachedHead=false", "clone", "--branch", branch]
        if p["depth"]: cmd += ["--depth", p["depth"]]
        if p["path"] in SPARSE: cmd += ["--filter=blob:none", "--sparse"]
        run(*cmd, p["url"], dest)
        if p["path"] in SPARSE:
            run("git", "-C", dest, "sparse-checkout", "set", "--no-cone", *SPARSE[p["path"]])
    for src, link in p["linkfiles"]:
        symlink(os.path.join(ws, link), os.path.relpath(os.path.join(dest, src), os.path.dirname(os.path.join(ws, link))))

def symlink(link, target):
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.path.islink(link):
        if os.readlink(link) == target: return
        os.unlink(link)
    elif os.path.exists(link):
        print(f"! {link} exists and is not a symlink; leaving it"); return
    os.symlink(target, link); print(f"@ {link} -> {target}")

def fetch_clang(ws):
    base = os.path.join(ws, "prebuilts/clang/host/linux-x86")
    d = os.path.join(base, CLANG_DIRS[0])
    if not os.path.isdir(d):
        os.makedirs(base, exist_ok=True)
        url = f"{GITILES_CLANG}/+archive/{CLANG_REV}/{CLANG_DIRS[0]}.tar.gz"
        print("+ fetching", url, "(~3 GB)", flush=True)
        # stream into tar; gitiles builds the archive on the fly, no Content-Length
        with urllib.request.urlopen(url, timeout=300) as r, tarfile.open(fileobj=r, mode="r|gz") as t:
            t.extractall(d)
    else:
        print(f"= {d} (exists)")
    k = os.path.join(base, CLANG_DIRS[1])
    if not os.path.isdir(k):   # +archive of this directory returns something that is not a tarball; fetch file by file
        os.makedirs(k)
        listing = fetch(f"{GITILES_CLANG}/+/{CLANG_REV}/{CLANG_DIRS[1]}/?format=JSON").decode()
        entries = json.loads(listing.split("\n", 1)[1])["entries"]
        for e in entries:
            if e["type"] != "blob": continue
            data = base64.b64decode(fetch(f"{GITILES_CLANG}/+/{CLANG_REV}/{CLANG_DIRS[1]}/{e['name']}?format=TEXT"))
            open(os.path.join(k, e["name"]), "wb").write(data)
        print(f"+ {k}: {len(entries)} files")
    else:
        print(f"= {k} (exists)")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", default=os.path.join(HERE, "workspace"), help="holds kernel/ and vendor -> kernel/vendor")
    ap.add_argument("--manifest", default=os.path.join(HERE, "default.xml"))
    ap.add_argument("--only", action="append", default=[], help="sync only these project paths")
    ap.add_argument("--revision", help="tag for the Motorola projects (default: the manifest's)")
    ap.add_argument("--no-prune", action="store_true", help="do not run prune-missing.py --apply")
    a = ap.parse_args()
    ws = os.path.join(a.top, "kernel"); os.makedirs(ws, exist_ok=True)
    want = lambda path: not a.only or path in a.only
    for p in parse_manifest(a.manifest):
        if want(p["path"]): clone(ws, p, a.revision)
    if want("prebuilts/clang/host/linux-x86"): fetch_clang(ws)
    for link, target in SYMLINKS:
        if os.path.exists(os.path.normpath(os.path.join(ws, os.path.dirname(link), target))) or link.startswith(".."):
            symlink(os.path.normpath(os.path.join(ws, link)), target)
    if not a.only and not a.no_prune:
        run(sys.executable, os.path.join(HERE, "prune-missing.py"), ws, "--apply")
    print("done:", ws)

if __name__ == "__main__":
    main()
