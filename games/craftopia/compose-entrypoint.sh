#!/bin/bash
set -euo pipefail

if [[ "${FORCE_UPDATE:-false}" == "true" ]]; then
    /home/steam/steamcmd/steamcmd.sh +quit
    /home/steam/steamcmd/steamcmd.sh \
        +force_install_dir /opt/craftopia \
        +login anonymous \
        +app_update 1670340 validate \
        +quit
fi

export FORCE_UPDATE=false
exec /docker-entrypoint.sh "$@"