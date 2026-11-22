# Kernel manifest for the Motorola Edge 70 Pro (merc, MediaTek MT6899)

Everything needed to build the merc kernel, device trees and modules from the source Motorola
published, outside Motorola's Android tree. Nothing here touches a device.

Motorola released the merc kernel source on 2026-07-01 (Android 16, tag `MMI-W3WM36.40-46-2`,
"Merc push for Android 16") and 2026-11-19 (Android 17, tag `MMI-A171WMH.44-25`) across these
repositories under [MotorolaMobilityLLC](https://github.com/MotorolaMobilityLLC):
`kernel-mtk` (GKI android15-6.6 + Motorola patches; 6.6.89 at the A16 tag, exactly the `uname`
of the shipped device), `kernel-kernel_device_modules-6.6` (MediaTek drivers and the
`mt6899-merc-*` device trees), `motorola-kernel-modules`, `kernel-build-kernel` (Kleaf),
`kernel-build-bazel_mgk_rules`, `kernel-prebuilts-kernel-build-tools` and the
`vendor-mediatek-kernel_modules-*` repos listed in `default.xml`. The AOSP prebuilts and
externals Kleaf needs come from `main-kernel-build-2024`, as in AOSP's `common-android15-6.6`
manifest.

## Quick start

```
git clone https://github.com/egnd09/android_kernel_manifest_motorola_merc
cd android_kernel_manifest_motorola_merc
./sync.py                                   # ~15 GB into workspace/kernel (plain git, no `repo` needed)
docker build -t edge70-kleaf:ubuntu24 docker
./build.sh                                  # kernel + modules, ~1 h on 12 threads, ~20 GB in workspace/kernel/out
./build-dts.sh                              # mt6899.dtb, mt6899-merc-evb-overlay.dtbo, dtbo.img
```

`sync.py` reads `default.xml`, shallow-clones every project at its revision, fetches only the two
directories of `prebuilts/clang/host/linux-x86` Kleaf uses (`clang-r510928`, `kleaf`), sparse-checks
out the NDK r26 sysroot, creates the symlinks MediaTek's `build.sh` expects
(`WORKSPACE`, `tools/bazel`, `../vendor -> kernel/vendor`, the two Motorola config overlays in
`kernel/configs/`) and runs `prune-missing.py` (below). `./sync.py --revision MMI-A171WMH.44-25`
syncs the Android 17 tag instead. `default.xml` is also a valid `repo` manifest if you prefer
`repo init -u <this repo>`; then do the clang fetch, the symlinks and the prune by hand.

`build.sh` runs Motorola's own entry point with Motorola's own variables:

```
PROJECT=mgk_64_k66 MODE=user DEFCONFIG_OVERLAYS="moto-mgk_64_k66.config moto-mgk_64_k66-merc.config" \
BUILD_CONFIG=kernel_device_modules-6.6/build.config.mtk.aarch64 OUT_DIR=out \
  bash kernel_device_modules-6.6/build.sh
```

inside a Docker container as root (`docker/Dockerfile`, Ubuntu 24.04 with a handful of host tools;
the toolchain is hermetic). Root in a container is deliberate: Bazel refuses an output root it does
not own, which is every directory on an NTFS volume. `DOCKER=0 ./build.sh` runs directly on a
filesystem you own. Config: `gki_defconfig` + `mgk_64_k66_defconfig` + the generic Motorola overlay
`ext_config/moto-mgk_64_k66.config` (drops MediaTek reference panels etc.) + the device overlay
`ext_config/moto-mgk_64_k66-merc.config` (+ `sign.config`). `SANDBOX=1` is required: `SANDBOX=0`
(`--config=local`) assumes the Android-tree layout (`../kernel/...`).

Outputs land in `workspace/kernel/out/dist/kernel_device_modules-6.6/`:
`mgk_64_k66_kernel_aarch64.user/` (Image, Image.lz4, vmlinux, System.map, GKI modules),
`mgk_64_k66.user/` (in-tree modules) and `mgk_64_k66_customer_modules_install.user/` (external
modules). MediaTek's Kleaf rules do not build device trees (Motorola's Android build runs Kbuild
`dtbs`), so `build-dts.sh` compiles them the Kbuild way (`clang -E` + `dtc -@`) into
`workspace/kernel/out/dts/`. The dtbo is `mt6899-merc-evb-overlay.dts` (board-id 0x41/0xA100,
the same the stock `dtbo.img` carries). `<merc_evb/cust.dtsi>` is included by the overlay but not
published (generated inside Motorola's tree); an empty stand-in is used.

## How close to stock

Built from the A16 tag and compared with the RETEU `W3WM36.40-75-5` firmware (2026-11-23):

| Artifact | Result |
|---|---|
| `Image` | same size (36 592 128 bytes), same header, 98.6 % of strings identical; only the version string differs (Motorola's internal git hash and `BUILD_NUMBER` are not reproducible: `-maybe-dirty` vs `-gdcee9aa4fcbc-ab14676413`) |
| `mt6899.dtb` | byte-identical |
| dtbo | same overlay; stock `40-75-5` already carries the charger values of the A17 tag and fragments from the unpublished `merc_evb/cust.dtsi` (449 vs 424 fragments) |
| modules | 526 of the 529 module names in stock; after `llvm-strip --strip-debug` the sizes match on every one spot-checked (Goodix touch, Egis FOD, CSOT panel, NXP NFC) |

## Known gaps

Motorola did not publish MediaTek's customer modules `fpsgo_cus`, `sched_cus`, `task_turbo_cus`,
`msync2_frd_cus`, `afs_*`, `hbt_driver_cus`; `default.xml` takes them from the Xiaomi MT6899
`rodin` drop ([mt6899-devs](https://github.com/mt6899-devs), same SoC), except `fpsgo_cus`, which
does not link against this kernel (undefined `engine_cooler_*`). Also missing: `cpufreq_cus`
(`cpufreq_sugov_ext.ko`), `game_cus` (`game.ko`), `mtk_input/*`, `wwan`, `thinmd_exception`,
`met_drv_secure_v3` and every `*_int` package. `prune-missing.py` drops those labels from
`kernel/kleaf/mgk_64.bzl` (keeping `.orig`) so the rest builds; `fpsgo.ko`, `game.ko`,
`cpufreq_sugov_ext.ko` and `moto_swap5.ko` have to stay prebuilt from stock.
`kernel-uapi-headers.tar.gz` is not produced by the MediaTek dist target.

Android 16 → 17 tag diff: no hardware change; `merc-charger.dtsi` (11 lines, battery ids),
`CONFIG_SCHED_MOTO_BINDERTRANS=y`, `moto_swap` → `moto_swap5`, aw86938s haptics (12 lines),
GKI 6.6.89 → 6.6.118.

## Why

Groundwork for a LineageOS bring-up of the Edge 70 Pro. A device tree and vendor tree are being
prepared separately; they will consume these artifacts as prebuilts until the kernel can be built
in-tree.

License: Apache-2.0 for the scripts in this repository; the synced sources keep their own.
