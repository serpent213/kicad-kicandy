#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-}"
if [ -z "${VERSION}" ]; then
  echo "Usage: $0 <version>" >&2
  exit 1
fi

VERSION_TAG="${VERSION}"
VERSION="${VERSION#[Vv]}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ARCHIVE_ROOT="${SCRIPT_DIR}/archive"
PLUGIN_DIR="${ARCHIVE_ROOT}/plugins"
RESOURCES_DIR="${ARCHIVE_ROOT}/resources"
ZIP_BASENAME="KiCandy-PCM-${VERSION}.zip"
ZIP_PATH="${SCRIPT_DIR}/${ZIP_BASENAME}"
METADATA_FILE="${ARCHIVE_ROOT}/metadata.json"
REPO_SLUG="${GITHUB_REPOSITORY:-serpent213/kicad-kicandy}"

echo "Cleaning previous artifacts"
rm -f "${SCRIPT_DIR}"/*.zip || true
rm -rf "${ARCHIVE_ROOT}"

echo "Preparing archive directories"
mkdir -p "${PLUGIN_DIR}" "${RESOURCES_DIR}"

echo "Copying plugin sources"
cp "${REPO_ROOT}/"{kicandy_action.py,icon_fonts.py,icon_repository.py,settings.py,state_store.py} "${PLUGIN_DIR}"
cp "${REPO_ROOT}/plugin.json" "${PLUGIN_DIR}"
cp "${REPO_ROOT}/requirements.txt" "${PLUGIN_DIR}"
cp -R "${REPO_ROOT}/icons" "${PLUGIN_DIR}/icons"
cp -R "${REPO_ROOT}/ui" "${PLUGIN_DIR}/ui"

echo "Writing VERSION file"
printf "%s\n" "${VERSION}" > "${PLUGIN_DIR}/VERSION"

echo "Copying metadata template and icon"
cp "${SCRIPT_DIR}/metadata.template.json" "${METADATA_FILE}"
cp "${REPO_ROOT}/icons/kicandy_64.png" "${RESOURCES_DIR}/icon.png"

echo "Updating metadata version"
sed -i.bak \
  -e "s/VERSION_HERE/${VERSION}/g" \
  -e 's/"kicad_version": "9.0",/"kicad_version": "9.0"/' \
  -e '/SHA256_HERE/d' \
  -e '/DOWNLOAD_SIZE_HERE/d' \
  -e '/DOWNLOAD_URL_HERE/d' \
  -e '/INSTALL_SIZE_HERE/d' \
  "${METADATA_FILE}"
rm -f "${METADATA_FILE}.bak"

echo "Creating PCM archive"
(
  cd "${ARCHIVE_ROOT}"
  zip -9r "${ZIP_PATH}" .
)

echo "Gathering archive metadata"
DOWNLOAD_SHA256=$(shasum --algorithm 256 "${ZIP_PATH}" | awk '{print $1}')
DOWNLOAD_SIZE=$(wc -c < "${ZIP_PATH}" | awk '{print $1}')
INSTALL_SIZE=$(
  python3 - "${ZIP_PATH}" <<'PY'
import sys
import zipfile

zip_path = sys.argv[1]
with zipfile.ZipFile(zip_path) as zf:
    print(sum(info.file_size for info in zf.infolist()))
PY
)
DOWNLOAD_URL="https://github.com/${REPO_SLUG}/releases/download/${VERSION_TAG}/${ZIP_BASENAME}"

if [ -n "${GITHUB_ENV:-}" ]; then
  {
    printf 'VERSION=%s\n' "${VERSION}"
    printf 'DOWNLOAD_SHA256=%s\n' "${DOWNLOAD_SHA256}"
    printf 'DOWNLOAD_SIZE=%s\n' "${DOWNLOAD_SIZE}"
    printf 'DOWNLOAD_URL=%s\n' "${DOWNLOAD_URL}"
    printf 'INSTALL_SIZE=%s\n' "${INSTALL_SIZE}"
  } >> "${GITHUB_ENV}"
fi

echo "Archive ready at ${ZIP_PATH}"
