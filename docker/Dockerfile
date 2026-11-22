# Minimal host for Motorola/MediaTek Kleaf kernel builds. The toolchain is hermetic
# (prebuilts/), only the few host tools Kleaf's kleaf_host_tools wants are installed.
# Runs as root on purpose: the project disk is NTFS (all files uid 0) and Bazel
# refuses an output root it does not own.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash perl rsync findutils git python3 bc ca-certificates file xz-utils \
      libc6 libstdc++6 zlib1g procps && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /kb/kernel
