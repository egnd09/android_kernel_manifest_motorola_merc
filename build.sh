#!/bin/bash
# Build the merc (Motorola Edge 70 Pro, MT6899) kernel + modules with Motorola's Kleaf tree.
# Workspace: ./sync.py (see README.md). Nothing here touches a device.
#
# Runs inside a Docker container as root (image: docker/Dockerfile, build it with: docker build -t edge70-kleaf:ubuntu24 docker) because
# the project disk is NTFS (every file is uid 0) and Bazel refuses an output root it does not
# own. Set DOCKER=0 to run directly (works only on a filesystem owned by the current user).
set -euo pipefail
KB="${KB:-$(cd "$(dirname "$0")" && pwd)/workspace}"   # host path: holds kernel/ (workspace) and vendor -> kernel/vendor
IMAGE="${IMAGE:-edge70-kleaf:ubuntu24}"
ENVS=(PROJECT="${PROJECT:-mgk_64_k66}" MODE="${MODE:-user}"
      DEFCONFIG_OVERLAYS="${DEFCONFIG_OVERLAYS:-moto-mgk_64_k66.config moto-mgk_64_k66-merc.config}"   # generic Motorola overlay first, then the device one (defconfig.mk order)
      BUILD_CONFIG="${BUILD_CONFIG:-kernel_device_modules-6.6/build.config.mtk.aarch64}"
      OUT_DIR="${OUT_DIR:-out}"            # MTK _setup_env.sh needs a workspace-relative path
      KLEAF_GKI_CHECKER=no SANDBOX="${SANDBOX:-1}"   # SANDBOX=0 (--config=local) assumes the Android-tree layout (../kernel/...); Bazel falls back to processwrapper-sandbox in Docker
      SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-0}")
if [ "${DOCKER:-1}" = "1" ]; then
  DARGS=(--rm -v "$KB:/kb" -w /kb/kernel -e TMPDIR=/kb/kernel/tmp)
  for e in "${ENVS[@]}"; do DARGS+=(-e "$e"); done   # values may contain spaces (DEFCONFIG_OVERLAYS)
  exec docker run "${DARGS[@]}" "$IMAGE" bash -c 'mkdir -p "$TMPDIR" "$OUT_DIR"; echo "PROJECT=$PROJECT MODE=$MODE DEFCONFIG_OVERLAYS=$DEFCONFIG_OVERLAYS"; exec bash kernel_device_modules-6.6/build.sh "$@"' _ "$@"
else
  cd "$KB/kernel"; export "${ENVS[@]}" TMPDIR="$KB/kernel/tmp"; mkdir -p "$TMPDIR" "$OUT_DIR"
  exec bash kernel_device_modules-6.6/build.sh "$@"
fi
