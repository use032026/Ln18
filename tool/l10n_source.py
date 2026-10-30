#!/usr/bin/env python3
"""Fetch pinned language sources. Maintained in Ln18; vendor unchanged in consumers."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen
import zipfile

sys.dont_write_bytecode = True
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_EXTRACTED_BYTES = 128 * 1024 * 1024


class SourceError(RuntimeError):
    """The pinned source is unavailable or failed validation."""


def add_source_arguments(parser):
    parser.add_argument("--catalog-root", type=Path,
                        help="Explicit local catalog for maintainers; default: pinned remote source")
    parser.add_argument("--cache-dir", type=Path,
                        help="Download cache; default: this project's .l10n-cache")
    parser.add_argument("--offline", action="store_true",
                        help="Use an already verified cache without downloading")


def _read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SourceError(f"Cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SourceError(f"Expected a JSON object: {path}")
    return value


def _consumer_version(root):
    config = _read_json(root / "l10n.resources.json")
    version = config.get("catalogVersion")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise SourceError("Consumer l10n.resources.json has no valid catalogVersion.")
    return version


def _validate_catalog(catalog, version):
    index = _read_json(catalog / "catalog/index.json")
    try:
        pubspec = (catalog / "pubspec.yaml").read_text(encoding="utf-8")
    except OSError as error:
        raise SourceError(f"Catalog pubspec.yaml missing: {catalog}") from error
    declared = re.search(r"(?m)^version:\s*([^\s#]+)", pubspec)
    if index.get("packageVersion") != version or not declared or declared.group(1) != version:
        raise SourceError(f"Catalog version must match consumer {version}: {catalog}")
    if not (catalog / "tools/sync.py").is_file():
        raise SourceError(f"Catalog tools/sync.py missing: {catalog}")


def _source(root, version):
    source = _read_json(root / "l10n.source.json")
    if type(source.get("schemaVersion")) is not int or source["schemaVersion"] != 1:
        raise SourceError("Unsupported l10n.source.json schemaVersion.")
    repository = source.get("repository")
    if not isinstance(repository, str):
        raise SourceError("Source repository must be an HTTPS GitHub URL.")
    match = re.fullmatch(r"https://github\.com/([A-Za-z0-9_-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?", repository)
    if not match or match.group(2) in {".", ".."}:
        raise SourceError("Source repository must be an HTTPS GitHub URL without credentials or a query.")
    revision = source.get("revision")
    checksum = source.get("sha256")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise SourceError("Pin source revision to a full lowercase 40-character commit SHA, not a branch or tag.")
    if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise SourceError("Source sha256 must be the archive's lowercase SHA256 checksum.")
    archive = f"deliverables/im_l10n_catalog-{version}.zip"
    if source.get("catalogVersion") != version or source.get("archive") != archive:
        raise SourceError("Source version/archive must match l10n.resources.json catalogVersion.")
    url = f"https://raw.githubusercontent.com/{match.group(1)}/{match.group(2)}/{revision}/{archive}"
    return source, url


def _archive_files(archive, version):
    """Validate every entry before extracting any file."""
    files, seen, total = {}, set(), 0
    package_name = f"im_l10n_catalog-{version}"
    try:
        for info in archive.infolist():
            name = info.filename
            path = PurePosixPath(name)
            if (not name or "\\" in name or "\0" in info.orig_filename or path.is_absolute()
                    or any(part in {"", ".", ".."} for part in name.rstrip("/").split("/"))
                    or not path.parts or path.parts[0] != package_name):
                raise SourceError(f"Unsafe archive path: {name!r}")
            if name.rstrip("/") in seen:
                raise SourceError(f"Duplicate archive path: {name!r}")
            seen.add(name.rstrip("/"))
            kind = stat.S_IFMT(info.external_attr >> 16)
            if kind not in {0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG}:
                raise SourceError(f"Archive contains a symlink or special file: {name!r}")
            if info.is_dir():
                continue
            if len(path.parts) < 2 or path.parts[1] == ".dart_tool":
                raise SourceError(f"Archive contains unexpected package/dependency state: {name!r}")
            total += info.file_size
            if total > MAX_EXTRACTED_BYTES:
                raise SourceError("Language archive exceeds the extracted size limit.")
            files["/".join(path.parts[1:])] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, OSError) as error:
        raise SourceError(f"Cannot read language archive: {error}") from error
    for required in ["pubspec.yaml", "pubspec.lock", "catalog/index.json", "tools/sync.py"]:
        if required not in files:
            raise SourceError(f"Archive is missing {required}.")
    return files


def _checked_files(archive_path, checksum, version):
    if archive_path.is_symlink() or not archive_path.is_file():
        raise SourceError("Cached language archive is missing or is a symbolic link.")
    data = archive_path.read_bytes()
    if len(data) > MAX_ARCHIVE_BYTES or hashlib.sha256(data).hexdigest() != checksum:
        raise SourceError("Language archive SHA256 mismatch; no consumer files were changed.")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            return _archive_files(archive, version)
    except zipfile.BadZipFile as error:
        raise SourceError("Language archive is not a valid ZIP file.") from error


def _verify_tree(catalog, files):
    if catalog.is_symlink() or not catalog.is_dir():
        raise SourceError("Cached catalog is missing or is a symbolic link.")
    actual = set()
    for directory, dirs, names in os.walk(catalog, followlinks=False):
        current = Path(directory)
        for name in dirs + names:
            if (current / name).is_symlink():
                raise SourceError(f"Cached source contains a symbolic link: {current / name}")
        if current == catalog:
            dirs[:] = [name for name in dirs if name != ".dart_tool"]
        for name in names:
            path = current / name
            relative = path.relative_to(catalog).as_posix()
            actual.add(relative)
            if relative not in files or path.read_bytes() != files[relative]:
                raise SourceError(f"Cached source was changed: {relative}")
    if actual != set(files):
        raise SourceError("Cached source files are missing.")


def _download(url, destination):
    request = Request(url, headers={"User-Agent": "Ln18-language-sync/1"})
    try:
        with urlopen(request, timeout=60) as response, destination.open("wb") as output:
            size = 0
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > MAX_ARCHIVE_BYTES:
                    raise SourceError("Language archive exceeds the download size limit.")
                output.write(block)
    except (URLError, OSError) as error:
        raise SourceError(f"Cannot download pinned language source: {error}. Retry online or use a verified cache with --offline.") from error


def resolve_catalog(consumer_root, catalog_root=None, *, cache_dir=None, offline=False):
    """Resolve an explicit maintainer checkout or a verified, immutable remote package."""
    root = Path(consumer_root).resolve()
    version = _consumer_version(root)
    local = catalog_root or os.environ.get("IM_L10N_CATALOG_ROOT")
    if local:
        catalog = Path(local).expanduser().resolve()
        _validate_catalog(catalog, version)
        return catalog
    source, url = _source(root, version)
    cache = Path(cache_dir).expanduser() if cache_dir is not None else root / ".l10n-cache"
    entry = cache / f"{source['revision']}-{source['sha256'][:16]}"
    catalog = entry / f"im_l10n_catalog-{version}"
    if cache.is_symlink() or entry.is_symlink():
        raise SourceError("Refusing a symbolic link for the language cache directory.")
    try:
        if not entry.exists():
            if offline:
                raise SourceError("Pinned language source is not cached. Run once without --offline to download it.")
            cache.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".fetch-", dir=cache) as temporary:
                stage = Path(temporary)
                _download(url, stage / "archive.zip")
                files = _checked_files(stage / "archive.zip", source["sha256"], version)
                package = stage / catalog.name
                for relative, data in files.items():
                    output = package / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_bytes(data)
                _validate_catalog(package, version)
                try:
                    os.rename(stage, entry)
                except OSError:
                    if not entry.is_dir() or entry.is_symlink():
                        raise
                    # Another invocation may have populated the same immutable pin.
        files = _checked_files(entry / "archive.zip", source["sha256"], version)
        _verify_tree(catalog, files)
        _validate_catalog(catalog, version)
    except (OSError, SourceError) as error:
        raise SourceError(f"{error} Cache: {entry}. Remove that cache entry and retry if damaged.") from error
    return catalog


def ensure_dart_dependencies(catalog, dart, *, offline=False):
    """Prepare only the fetched generator package, including for a cold --check."""
    catalog = Path(catalog)
    if (catalog / ".dart_tool/package_config.json").is_file():
        return
    command = [str(dart), "pub", "get", "--enforce-lockfile"]
    if offline:
        command.append("--offline")
    try:
        subprocess.run(command, cwd=catalog, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise SourceError("Cannot prepare the pinned generator dependencies. Check the Dart executable and dependency cache; retry online if required.") from error
