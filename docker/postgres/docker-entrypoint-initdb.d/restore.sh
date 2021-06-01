#!/bin/bash
set -e

echo "Running postgres restore script"

if [[ -f "/home/dumps/${MAVEDB_DUMP_FILE}" ]]; then
  echo "Restoring database dump from file ${MAVEDB_DUMP_FILE}"
  pg_restore -Fc -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "/home/dumps/${MAVEDB_DUMP_FILE}"
fi