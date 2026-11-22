#!/bin/bash
# Produce kernel-uapi-headers.tar.gz (usr/include/...) from the merc kernel source with Kbuild `headers_install`,
# the same layout AOSP's Kleaf dist ships for GKI. MediaTek's Kleaf dist target does not emit it.
# Runs in the same Docker image as build.sh; host tools (fixdep, unifdef) are linked against the
# hermetic glibc 2.17 sysroot + gcc 4.8.3 crt/libgcc from prebuilts, so the container needs no libc6-dev.
set -euo pipefail
KB="${KB:-$(cd "$(dirname "$0")" && pwd)/workspace}"
IMAGE="${IMAGE:-edge70-kleaf:ubuntu24}"
OUT="${OUT:-out-uapi}"   # relative to $KB/kernel
run() { if [ "${DOCKER:-1}" = "1" ]; then docker run --rm -v "$KB:/kb" -w /kb/kernel -e OUT="$OUT" "$IMAGE" bash -c "$1"; else cd "$KB/kernel" && OUT="$OUT" bash -c "${1//\/kb\/kernel/$KB/kernel}"; fi; }
run 'set -e; G=/kb/kernel/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8; SR=$G/sysroot; GL=$G/lib/gcc/x86_64-linux/4.8.3
export PATH=/kb/kernel/prebuilts/clang/host/linux-x86/clang-r510928/bin:/kb/kernel/prebuilts/build-tools/linux-x86/bin:/kb/kernel/prebuilts/build-tools/path/linux-x86:$PATH
rm -rf "$OUT"; mkdir -p "$OUT"
make -C kernel-6.6 O=/kb/kernel/$OUT ARCH=arm64 LLVM=1 HOSTCC="clang --sysroot=$SR" HOSTCXX="clang++ --sysroot=$SR" \
     HOSTLDFLAGS="--sysroot=$SR -fuse-ld=lld -B$GL -L$GL -L$G/x86_64-linux/lib64" \
     INSTALL_HDR_PATH=/kb/kernel/$OUT/usr headers_install > /kb/kernel/$OUT/make.log 2>&1
cd "$OUT" && tar czf kernel-uapi-headers.tar.gz usr
echo "built $PWD/kernel-uapi-headers.tar.gz ($(stat -c %s kernel-uapi-headers.tar.gz) bytes, $(find usr/include -name "*.h" | wc -l) headers)"'
