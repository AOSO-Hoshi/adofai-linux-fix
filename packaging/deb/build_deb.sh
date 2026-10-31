#!/usr/bin/env bash
# ==============================================================================
# 构建 .deb 包 (Architecture: all)
# 产物: packaging/deb/build/adofai-linux-fix_<ver>_all.deb
# 仅需要 dpkg-deb; 包内容为 Python 脚本 + 预编译产物, 不在构建期编译。
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

VERSION="1.0.1"
PKG="adofai-linux-fix"
MAINTAINER="AOSO-Hoshi <349151525+AOSO-Hoshi@users.noreply.github.com>"
HOMEPAGE="https://github.com/AOSO-Hoshi/adofai-linux-fix"
BUILD="$SCRIPT_DIR/build/$PKG"
APP="/usr/lib/$PKG"

if ! command -v dpkg-deb &>/dev/null; then
    echo "[-] Error: dpkg-deb not found." >&2
    exit 1
fi

rm -rf "$BUILD"
mkdir -p "$BUILD/DEBIAN" \
         "$BUILD$APP" \
         "$BUILD/usr/bin" \
         "$BUILD/usr/share/applications" \
         "$BUILD/usr/share/icons/hicolor/256x256/apps" \
         "$BUILD/usr/share/doc/$PKG"

# ---------------------------------------------------------------- 应用文件
cp "$ROOT_DIR/adofai_fix.py" "$BUILD$APP/"
cp -r "$ROOT_DIR/src" "$ROOT_DIR/scripts" "$ROOT_DIR/dist" "$ROOT_DIR/doorstop" "$BUILD$APP/"
find "$BUILD$APP" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
chmod -R a+rX "$BUILD$APP"

INSTALLED_SIZE=$(du -sk "$BUILD/usr" | cut -f1)

# ---------------------------------------------------------------- control
cat > "$BUILD/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: games
Priority: optional
Architecture: all
Installed-Size: $INSTALLED_SIZE
Depends: python3 (>= 3.8)
Recommends: mono-mcs, zip
Suggests: steam
Maintainer: $MAINTAINER
Homepage: $HOMEPAGE
Description: ADOFAI Linux native fix and mod toolkit
 Toolkit for A Dance of Fire and Ice on Linux and Steam Deck.
 Installs the shader-warmup crash fix mod, repairs the UMM assembly
 injector, fixes CJK fonts, and checks the environment.
EOF

# ---------------------------------------------------------------- copyright
MIT_TEXT="Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the \"Software\"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."

cat > "$BUILD/usr/share/doc/$PKG/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: $PKG
Source: $HOMEPAGE

Files: *
Copyright: 2026 AOSO-Hoshi
License: MIT
$MIT_TEXT

Files: usr/lib/$PKG/dist/dnlib.dll
Copyright: Jonas Nyrup
License: MIT
 dnlib is MIT licensed; redistributed here because the injector binary
 resolves it next to the executable at runtime.
 (See above for the full MIT license text.)

License: MIT
$MIT_TEXT
EOF

# ---------------------------------------------------------------- 启动器
cat > "$BUILD/usr/bin/adofai-fix" <<EOF
#!/bin/sh
exec python3 $APP/adofai_fix.py "\$@"
EOF
chmod 755 "$BUILD/usr/bin/adofai-fix"


# ---------------------------------------------------------------- 打包
OUT="$SCRIPT_DIR/build/${PKG}_${VERSION}_all.deb"
rm -f "$OUT"
dpkg-deb --build --root-owner-group "$BUILD" "$OUT"
dpkg-deb --info "$OUT" | head -12
echo "[+] $OUT"
