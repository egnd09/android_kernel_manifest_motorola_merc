#!/bin/bash
# Compile the merc device trees the way Kbuild does (cpp + dtc -@), outside Bazel:
# MediaTek's Kleaf rules do not build dts; Motorola's Android build runs Kbuild `dtbs`.
# Output: $OUT/mt6899.dtb (base, goes into vendor_boot) and $OUT/mt6899-merc-evb-overlay.dtbo + dtbo.img.
set -euo pipefail
WS="${WS:-$(cd "$(dirname "$0")" && pwd)/workspace/kernel}"
OUT="${OUT:-$WS/out/dts}"; mkdir -p "$OUT" "$OUT/inc/merc_evb"
K="$WS/kernel-6.6"; DM="$WS/kernel_device_modules-6.6"; DTS="$DM/arch/arm64/boot/dts/mediatek"
CLANG="$WS/prebuilts/clang/host/linux-x86/clang-r510928/bin/clang"
DTC="$WS/prebuilts/kernel-build-tools/linux-x86/bin/dtc"
MKDTIMG="$WS/prebuilts/kernel-build-tools/linux-x86/bin/mkdtboimg"
# <merc_evb/cust.dtsi> is included by the overlay but not in any published repo (generated in Motorola's tree); empty stand-in.
[ -s "$OUT/inc/merc_evb/cust.dtsi" ] || echo "/* stand-in: merc_evb/cust.dtsi is not published */" > "$OUT/inc/merc_evb/cust.dtsi"
INC=(-I"$DM/include" -I"$K/scripts/dtc/include-prefixes" -I"$DM/arch/arm64/boot/dts" -I"$DTS" -I"$DM/arch/arm64/boot/dts/mediatek" -I"$OUT/inc" -I"$K/include")
WARN=(-Wno-interrupt_provider -Wno-unique_unit_address -Wno-unit_address_vs_reg -Wno-avoid_unnecessary_addr_size -Wno-alias_paths -Wno-graph_child_address -Wno-simple_bus_reg)
build() { # src out extra-dtc-flags
  local src="$1" out="$2"; shift 2
  "$CLANG" -E -nostdinc "${INC[@]}" -undef -D__DTS__ -x assembler-with-cpp -o "$out.pre.dts" "$src"
  "$DTC" -O dtb -o "$out" -b 0 -i "$DTS" -i "$(dirname "$src")" "${WARN[@]}" "$@" -d "$out.d" "$out.pre.dts"
  echo "built $out ($(stat -c %s "$out") bytes)"
}
build "$DTS/mt6899.dts" "$OUT/mt6899.dtb" -@
build "$DTS/mt6899-merc-evb-overlay.dts" "$OUT/mt6899-merc-evb-overlay.dtbo" -@
"$MKDTIMG" create "$OUT/dtbo.img" --page_size=4096 "$OUT/mt6899-merc-evb-overlay.dtbo" && echo "built $OUT/dtbo.img ($(stat -c %s "$OUT/dtbo.img") bytes)"
