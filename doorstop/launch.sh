#!/bin/sh
# Re-hook Unity Mod Manager on every Steam launch.
# Launch option: /path/to/launch.sh %command%
# Steam prepends this script to steam-launch-wrapper, so the first
# executable is the runtime wrapper. Match the game binary by name.
set -e
BASE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
exe=
for arg in "$@"; do
    if [ -f "$arg" ] && [ -x "$arg" ] && [ "$(basename "$arg")" = "ADanceOfFireAndIce" ]; then
        exe=$arg
        break
    fi
done
if [ -z "$exe" ]; then
    echo "adofai-doorstop: no game executable in arguments: $*" >&2
    exit 1
fi
game_dir=$(CDPATH= cd -- "$(dirname "$exe")" && pwd)
data="$game_dir/$(basename "$exe")_Data"
live="$data/Managed/UnityModManager"
stash="$BASE/backup/UnityModManager"
if [ ! -f "$live/UnityModManager.dll" ]; then
    if [ ! -f "$stash/UnityModManager.dll" ]; then
        echo "adofai-doorstop: Unity Mod Manager is missing from $live" >&2
        exit 1
    fi
    echo "adofai-doorstop: restoring UnityModManager into $live" >&2
    mkdir -p "$live"
    cp -a "$stash/." "$live/"
fi
exec "$BASE/run.sh" "$@" \
    --doorstop-enabled true \
    --doorstop-target-assembly "$live/UnityModManager.dll" \
    --doorstop-mono-dll-search-path-override "$live"
