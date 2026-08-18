#!/usr/bin/env bash
set -euo pipefail
WORKTREES="${1:-worktrees}"
VROOT="${2:-.finishline-venvs}"
STATE="${3:-.finishline-stack}"
source "$STATE/urls.env"
export QDW_RESTART_COMMAND="bash lab/scripts/restart_qdw_service.sh '$WORKTREES' '$VROOT' '$STATE'"
bash lab/scripts/v11_restart.sh
