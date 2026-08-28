"""Model-free crash-consistency primitives for MM-005 Browser Research v2."""

from __future__ import annotations

import hashlib
import os
import secrets
import stat
from pathlib import Path
from typing import BinaryIO

MAX_PROGRESS_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


class RecoveryIOError(RuntimeError):
    """Stable local I/O failure for the v2 recovery lifecycle."""


class ProgressLease:
    """Hold the single-writer lease on the append-only progress journal."""

    def __init__(self, path: Path) -> None:
        self.path = Path(os.path.abspath(path))
        self.handle: BinaryIO | None = None
        self.identity: tuple[int, int, int, int] | None = None

    def __enter__(self) -> ProgressLease:
        self.open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def open(self) -> None:
        if self.handle is not None:
            raise RecoveryIOError("progress lease already open")
        before = _regular_file_metadata(self.path, "progress journal")
        handle = _open_exclusive_progress(self.path)
        try:
            opened = os.fstat(handle.fileno())
            identity = _stable_identity(before)
            if _stable_identity(opened) != identity:
                raise RecoveryIOError("progress journal identity changed while opening")
            self.handle = handle
            self.identity = identity
            self.verify()
        except BaseException:
            handle.close()
            self.handle = None
            self.identity = None
            raise

    def close(self) -> None:
        if self.handle is not None:
            try:
                _unlock_progress(self.handle)
            finally:
                self.handle.close()
        self.handle = None
        self.identity = None

    def verify(self) -> None:
        if self.handle is None or self.identity is None:
            raise RecoveryIOError("progress lease is not open")
        observed = _regular_file_metadata(self.path, "progress journal")
        opened = os.fstat(self.handle.fileno())
        if (
            _stable_identity(observed) != self.identity
            or _stable_identity(opened) != self.identity
        ):
            raise RecoveryIOError("progress journal identity changed")
        if opened.st_size > MAX_PROGRESS_BYTES:
            raise RecoveryIOError("progress journal exceeds byte limit")

    def read(self) -> bytes:
        self.verify()
        assert self.handle is not None
        self.handle.seek(0)
        payload = self.handle.read(MAX_PROGRESS_BYTES + 1)
        self.handle.seek(0, os.SEEK_END)
        if len(payload) > MAX_PROGRESS_BYTES:
            raise RecoveryIOError("progress journal exceeds byte limit")
        return payload

    def append(self, payload: bytes) -> bytes:
        if not payload or not payload.endswith(b"\n"):
            raise RecoveryIOError("progress frame must be LF-terminated")
        before = self.read()
        if len(before) + len(payload) > MAX_PROGRESS_BYTES:
            raise RecoveryIOError("progress journal exceeds byte limit")
        assert self.handle is not None
        self.handle.seek(0, os.SEEK_END)
        written = self.handle.write(payload)
        if written != len(payload):
            raise RecoveryIOError("short progress journal write")
        self.handle.flush()
        os.fsync(self.handle.fileno())
        after = self.read()
        if after != before + payload:
            raise RecoveryIOError("progress journal append verification failed")
        return after

    def truncate_to_authenticated_prefix(self, prefix: bytes) -> bytes:
        current = self.read()
        if not prefix or not prefix.endswith(b"\n") or not current.startswith(prefix):
            raise RecoveryIOError("invalid authenticated progress prefix")
        assert self.handle is not None
        self.handle.seek(0)
        written = self.handle.write(prefix)
        if written != len(prefix):
            raise RecoveryIOError("short progress prefix rewrite")
        self.handle.truncate(len(prefix))
        self.handle.flush()
        os.fsync(self.handle.fileno())
        if self.read() != prefix:
            raise RecoveryIOError("progress prefix rewrite verification failed")
        return prefix


class DirectoryTreeGuard:
    """Bind a repository-relative directory and every parent to stable identities."""

    def __init__(self, root: Path, target: Path) -> None:
        self.root = Path(os.path.abspath(root))
        self.target = Path(os.path.abspath(target))
        try:
            relative = self.target.relative_to(self.root)
        except ValueError as exc:
            raise RecoveryIOError("guarded directory escapes repository") from exc
        self.identities: list[tuple[Path, tuple[int, int, int]]] = []
        current = self.root
        self.identities.append(
            (current, _directory_path_identity(current, "repository root"))
        )
        for part in relative.parts:
            current /= part
            self.identities.append(
                (current, _directory_path_identity(current, "guarded directory"))
            )
        self.verify()

    def verify(self) -> None:
        for path, expected in self.identities:
            if _directory_path_identity(path, "guarded directory") != expected:
                raise RecoveryIOError("guarded directory identity changed")


def write_exclusive_fsync(path: Path, payload: bytes) -> bytes:
    """Create one regular file exclusively and verify its exact bytes."""

    if not isinstance(payload, bytes) or len(payload) > MAX_ARTIFACT_BYTES:
        raise RecoveryIOError("artifact payload exceeds byte limit")
    _validate_parent(path)
    with path.open("xb") as handle:
        written = handle.write(payload)
        if written != len(payload):
            raise RecoveryIOError("short exclusive artifact write")
        handle.flush()
        os.fsync(handle.fileno())
    observed = read_regular_file(path, max_bytes=max(len(payload), 1))
    if observed != payload:
        raise RecoveryIOError("exclusive artifact verification failed")
    return observed


def ensure_lock_file(path: Path, marker: bytes) -> bytes:
    """Create a persistent lock inode before consumption, or verify the existing one."""

    if not marker or len(marker) > 4096:
        raise RecoveryIOError("invalid lifecycle lease marker")
    if not os.path.lexists(path):
        try:
            write_exclusive_fsync(path, marker)
        except FileExistsError:
            pass
    return validate_lock_file(path, marker)


def ensure_lock_directory(path: Path, marker: bytes) -> bytes:
    """Atomically publish a complete persistent lease directory before claim."""

    lease_directory = path.parent
    if os.path.lexists(lease_directory):
        return validate_lock_file(path, marker)
    _validate_parent(lease_directory)
    staging = lease_directory.with_name(
        f".{lease_directory.name}.staging-{secrets.token_hex(16)}"
    )
    os.mkdir(staging)
    write_exclusive_fsync(staging / path.name, marker)
    try:
        os.rename(staging, lease_directory)
    except OSError:
        if not os.path.lexists(lease_directory):
            raise
    return validate_lock_file(path, marker)


def validate_lock_file(path: Path, marker: bytes) -> bytes:
    observed = read_regular_file(path, max_bytes=max(len(marker), 1))
    if observed != marker:
        raise RecoveryIOError("lifecycle lease marker differs")
    return observed


def write_or_repair_terminal(path: Path, expected: bytes) -> bytes:
    """Create a terminal or finish only an exact canonical byte prefix.

    The terminal-ready progress frame fixes ``expected`` before this function
    runs.  Rewriting is therefore authorized only when the durable file is a
    strict prefix of those already authenticated bytes.
    """

    if not os.path.lexists(path):
        return write_exclusive_fsync(path, expected)
    observed = read_regular_file(path, max_bytes=max(len(expected), 1))
    if observed == expected:
        return observed
    if len(observed) >= len(expected) or not expected.startswith(observed):
        raise RecoveryIOError("terminal artifact is not an exact expected prefix")
    metadata = _regular_file_metadata(path, "partial terminal artifact")
    with path.open("r+b", buffering=0) as handle:
        opened = os.fstat(handle.fileno())
        if _identity(opened) != _identity(metadata):
            raise RecoveryIOError("partial terminal identity changed")
        handle.seek(0)
        written = handle.write(expected)
        if written != len(expected):
            raise RecoveryIOError("short terminal repair write")
        handle.truncate(len(expected))
        handle.flush()
        os.fsync(handle.fileno())
    repaired = read_regular_file(path, max_bytes=len(expected))
    if repaired != expected:
        raise RecoveryIOError("terminal repair verification failed")
    return repaired


def read_regular_file(path: Path, *, max_bytes: int) -> bytes:
    if max_bytes <= 0:
        raise RecoveryIOError("invalid file byte limit")
    before = _regular_file_metadata(path, "artifact")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if _identity(opened) != _identity(before):
            raise RecoveryIOError("artifact identity changed while opening")
        payload = handle.read(max_bytes + 1)
        after_opened = os.fstat(handle.fileno())
    after = _regular_file_metadata(path, "artifact")
    if len(payload) > max_bytes:
        raise RecoveryIOError("artifact exceeds byte limit")
    if len({_identity(item) for item in (before, opened, after_opened, after)}) != 1:
        raise RecoveryIOError("artifact changed while reading")
    return payload


def sha256_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _open_exclusive_progress(path: Path) -> BinaryIO:
    if os.name != "nt":
        import fcntl

        handle = path.open("r+b", buffering=0)
        try:
            fcntl.flock(  # type: ignore[attr-defined]
                handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,  # type: ignore[attr-defined]
            )
        except BaseException:
            handle.close()
            raise RecoveryIOError("active progress writer still holds the lease")
        return handle

    import ctypes
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    create_file.restype = ctypes.c_void_p
    raw_handle = create_file(
        str(path),
        0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
        0x00000001,  # FILE_SHARE_READ; deny write/delete while held
        None,
        3,  # OPEN_EXISTING
        0x00000080 | 0x00200000,  # NORMAL | OPEN_REPARSE_POINT
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if raw_handle in (None, invalid_handle):
        raise RecoveryIOError("active progress writer still holds the lease")
    try:
        descriptor = msvcrt.open_osfhandle(
            int(raw_handle), os.O_RDWR | getattr(os, "O_BINARY", 0)
        )
    except BaseException:
        kernel32.CloseHandle(ctypes.c_void_p(raw_handle))
        raise
    return os.fdopen(descriptor, "r+b", buffering=0)


def _unlock_progress(handle: BinaryIO) -> None:
    if os.name == "nt":
        return
    import fcntl

    fcntl.flock(  # type: ignore[attr-defined]
        handle.fileno(),
        fcntl.LOCK_UN,  # type: ignore[attr-defined]
    )


def _regular_file_metadata(path: Path, label: str) -> os.stat_result:
    if not os.path.lexists(path):
        raise RecoveryIOError(f"missing {label}")
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or path.is_symlink()
        or _metadata_is_reparse(metadata)
    ):
        raise RecoveryIOError(f"unsafe {label}")
    return metadata


def _validate_parent(path: Path) -> None:
    parent = path.parent
    metadata = parent.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or parent.is_symlink()
        or _metadata_is_reparse(metadata)
    ):
        raise RecoveryIOError("unsafe artifact parent")


def _directory_path_identity(path: Path, label: str) -> tuple[int, int, int]:
    if not os.path.lexists(path):
        raise RecoveryIOError(f"missing {label}")
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_nlink < 1
        or path.is_symlink()
        or _metadata_is_reparse(metadata)
    ):
        raise RecoveryIOError(f"unsafe {label}")
    return metadata.st_dev, metadata.st_ino, metadata.st_mode


def _metadata_is_reparse(metadata: os.stat_result) -> bool:
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
    )


def _stable_identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
    )


__all__ = [
    "MAX_ARTIFACT_BYTES",
    "MAX_PROGRESS_BYTES",
    "DirectoryTreeGuard",
    "ProgressLease",
    "RecoveryIOError",
    "ensure_lock_file",
    "ensure_lock_directory",
    "read_regular_file",
    "sha256_bytes",
    "validate_lock_file",
    "write_exclusive_fsync",
    "write_or_repair_terminal",
]
