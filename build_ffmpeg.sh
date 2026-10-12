#!/usr/bin/env bash
# Cross-compiles a small ffmpeg (with MP3/LAME) for Android arm64 and
# saves it as libs/arm64-v8a/libffmpeg.so
set -euo pipefail
ROOT="$(pwd)"
OUT="$ROOT/libs/arm64-v8a/libffmpeg.so"
[ -f "$OUT" ] && { echo "ffmpeg already built"; exit 0; }

NDK="${ANDROID_NDK_LATEST_HOME:-${ANDROID_NDK_HOME:-}}"
[ -d "$NDK" ] || { echo "NDK not found"; exit 1; }
TC="$NDK/toolchains/llvm/prebuilt/linux-x86_64"
API=24
export CC="$TC/bin/aarch64-linux-android${API}-clang"
export AR="$TC/bin/llvm-ar" RANLIB="$TC/bin/llvm-ranlib"
export STRIP="$TC/bin/llvm-strip" NM="$TC/bin/llvm-nm"
PREFIX="$ROOT/ffbuild/out"
mkdir -p "$ROOT/ffbuild" "$PREFIX" && cd "$ROOT/ffbuild"

# ---- LAME (MP3 encoder) ----
for i in 1 2 3; do
  curl -fL --retry 3 -o lame.tgz "https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz" && break || sleep 5
done
tar xzf lame.tgz && cd lame-3.100
ac_cv_func_malloc_0_nonnull=yes ac_cv_func_realloc_0_nonnull=yes \
./configure --host=aarch64-linux-android --prefix="$PREFIX" \
  --disable-shared --enable-static --disable-frontend --disable-decoder --with-pic
make -j"$(nproc)" && make install
cd ..

# ---- FFmpeg ----
curl -fL --retry 3 -o ffmpeg.tar.xz "https://ffmpeg.org/releases/ffmpeg-6.1.1.tar.xz"
tar xf ffmpeg.tar.xz && cd ffmpeg-6.1.1
./configure --prefix="$PREFIX" \
  --enable-cross-compile --target-os=android --arch=aarch64 \
  --cc="$CC" --ar="$AR" --ranlib="$RANLIB" --strip="$STRIP" --nm="$NM" \
  --enable-pic --disable-shared --enable-static \
  --disable-doc --disable-debug --disable-ffplay --disable-ffprobe \
  --disable-avdevice --disable-network --disable-autodetect \
  --enable-libmp3lame \
  --extra-cflags="-I$PREFIX/include" --extra-ldflags="-L$PREFIX/lib"
make -j"$(nproc)"
mkdir -p "$(dirname "$OUT")"
cp ffmpeg "$OUT"
"$STRIP" "$OUT"
ls -l "$OUT"
