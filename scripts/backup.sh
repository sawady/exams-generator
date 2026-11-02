#!/usr/bin/env bash
# Off-site backup of the exams directory as a tarball, sent with rsync.
# The exams directory is already a git repository (one commit per change);
# with a remote and EXAMS_GIT_PUSH=true you may not need this at all.
#
#   BACKUP_TARGET=user@backup-host:/srv/exams-backups ./scripts/backup.sh
#
# Example cron line:
#   0 3 * * *  BACKUP_TARGET=... /opt/exams-generator/scripts/backup.sh >> /var/log/exams-backup.log 2>&1
set -euo pipefail

EXAMS_DIR="${EXAMS_DIR:-./exams}"
TARGET="${BACKUP_TARGET:-}"
if [ -z "$TARGET" ]; then
  echo "BACKUP_TARGET not set; nothing to do." >&2
  exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="$(mktemp -d)/exams-${STAMP}.tar.gz"

tar -czf "$ARCHIVE" -C "$(dirname "$EXAMS_DIR")" "$(basename "$EXAMS_DIR")"
rsync -av --remove-source-files "$ARCHIVE" "$TARGET/"
echo "Backup sent to ${TARGET}/$(basename "$ARCHIVE")"
