#!/usr/bin/env python3
"""Drop Kleaf module labels from mgk_64.bzl whose package is absent in this workspace.

Motorola published only part of vendor/mediatek/kernel_modules; the MediaTek rules
reference every package unconditionally, so Bazel fails on 'no such package'.
Usage: prune-missing.py <workspace> [--apply]
"""
import os, re, sys, shutil
ws = sys.argv[1]; apply = '--apply' in sys.argv
path = os.path.join(ws, 'kernel_device_modules-6.6/kernel/kleaf/mgk_64.bzl')
src = open(path).read()
labels = sorted(set(re.findall(r'"(//(?:vendor/mediatek/kernel_modules|motorola/kernel/modules)/[^":]+)', src)))
def exists(l):
    d = os.path.join(ws, l[2:])
    return os.path.isdir(d) and (os.path.exists(d + '/BUILD.bazel') or os.path.exists(d + '/BUILD'))
missing = [l for l in labels if not exists(l)]
line_re = re.compile(r'^[ \t]*(?:mgk_64_kleaf(?:_eng|_userdebug|_user)?_modules\.(?:append|remove)\()?"(//[^":]+):[^"]*"[,)]*[ \t]*\n', re.M)
out = []; dropped = []
for line in src.splitlines(keepends=True):
    m = line_re.match(line)
    if m and m.group(1) in missing:
        dropped.append(line.strip()); continue
    out.append(line)
print(f"labels={len(labels)} missing_packages={len(missing)} lines_dropped={len(dropped)}")
for l in missing: print("  missing:", l)
if apply:
    if not os.path.exists(path + '.orig'): shutil.copy(path, path + '.orig')
    open(path, 'w').write(''.join(out)); print("applied ->", path)
