"""Fail-closed Win32 backend for confined coordination artifact I/O.

Python's ``dir_fd`` and ``O_NOFOLLOW`` facilities are unavailable on Windows.
This module pins the coordination root, traverses and creates descendants with
handle-relative NT calls, rejects reparse points by handle, and renames or
deletes only through file handles.  Callers must pass an already-confined
absolute target path.
"""

from __future__ import annotations

import ctypes
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from ctypes import wintypes
from pathlib import Path
from typing import Any, NoReturn

logger = logging.getLogger(__name__)

_DELETE = 0x00010000
_FILE_LIST_DIRECTORY = 0x00000001
_FILE_READ_ATTRIBUTES = 0x00000080
_GENERIC_WRITE = 0x40000000
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_FILE_SHARE_DELETE = 0x00000004
_LOCKED_DIRECTORY_SHARE_MODE = (
    _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE
)
_LOCKED_FILE_SHARE_MODE = _FILE_SHARE_READ | _FILE_SHARE_WRITE
_OPEN_EXISTING = 3
_FILE_ATTRIBUTE_DIRECTORY = 0x00000010
_FILE_ATTRIBUTE_NORMAL = 0x00000080
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_SYNCHRONIZE = 0x00100000
_FILE_OPEN = 1
_FILE_CREATE = 2
_FILE_DIRECTORY_FILE = 0x00000001
_FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
_FILE_NON_DIRECTORY_FILE = 0x00000040
_FILE_OPEN_REPARSE_POINT = 0x00200000
_OBJ_CASE_INSENSITIVE = 0x00000040
_OBJ_DONT_REPARSE = 0x00001000
_FILE_ATTRIBUTE_TAG_INFO_CLASS = 9
_FILE_DISPOSITION_INFO_CLASS = 4
_FILE_RENAME_INFORMATION_CLASS = 10
_ERROR_FILE_NOT_FOUND = 2
_ERROR_PATH_NOT_FOUND = 3
_ERROR_FILE_EXISTS = 80
_ERROR_ALREADY_EXISTS = 183
_INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
_RESERVED_STEMS = {
    "AUX",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class _FileAttributeTagInfo(ctypes.Structure):
    _fields_ = [
        ("FileAttributes", wintypes.DWORD),
        ("ReparseTag", wintypes.DWORD),
    ]


class _FileDispositionInfo(ctypes.Structure):
    _fields_ = [("DeleteFile", wintypes.BOOLEAN)]


class _FileRenameInfoHeader(ctypes.Structure):
    _fields_ = [
        ("ReplaceIfExists", wintypes.BOOLEAN),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
        ("FileName", wintypes.WCHAR * 1),
    ]


class _IoStatusBlock(ctypes.Structure):
    _fields_ = [
        ("Status", ctypes.c_void_p),
        ("Information", ctypes.c_size_t),
    ]


class _UnicodeString(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    ]


class _ObjectAttributes(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(_UnicodeString)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", wintypes.LPVOID),
        ("SecurityQualityOfService", wintypes.LPVOID),
    ]


_kernel32: Any = None
_ntdll: Any = None
_ctypes_symbols = vars(ctypes)

if os.name == "nt":
    win_dll = _ctypes_symbols["WinDLL"]
    _kernel32 = win_dll("kernel32", use_last_error=True)
    _ntdll = win_dll("ntdll", use_last_error=True)
    _kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _kernel32.GetFileInformationByHandleEx.restype = wintypes.BOOL
    _kernel32.WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _kernel32.WriteFile.restype = wintypes.BOOL
    _kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.SetFileInformationByHandle.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    ]
    _kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    _ntdll.NtSetInformationFile.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_IoStatusBlock),
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.c_int,
    ]
    _ntdll.NtSetInformationFile.restype = ctypes.c_long
    _ntdll.NtCreateFile.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_ObjectAttributes),
        ctypes.POINTER(_IoStatusBlock),
        wintypes.LPVOID,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.LPVOID,
        wintypes.ULONG,
    ]
    _ntdll.NtCreateFile.restype = ctypes.c_long
    _ntdll.RtlNtStatusToDosError.argtypes = [ctypes.c_long]
    _ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG
def _require_windows() -> None:
    if _kernel32 is None:
        raise RuntimeError("Windows confined I/O backend used off Windows")


def _raise_last_error(action: str, path: Path) -> NoReturn:
    code = _ctypes_symbols["get_last_error"]()
    detail = _ctypes_symbols["WinError"](code)
    raise OSError(code, f"{action} failed for {path}: {detail}", str(path)) from detail


def _raise_ntstatus(action: str, path: Path, status: int) -> NoReturn:
    assert _ntdll is not None
    code = int(_ntdll.RtlNtStatusToDosError(status))
    detail = _ctypes_symbols["WinError"](code)
    raise OSError(code, f"{action} failed for {path}: {detail}", str(path)) from detail


def _windows_error_code(exc: OSError) -> int | None:
    winerror = getattr(exc, "winerror", None)
    return int(winerror) if winerror is not None else exc.errno


def _extended_path(path: Path) -> str:
    raw = str(path)
    if raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw.lstrip("\\")
    return "\\\\?\\" + raw


def _validate_component(name: str) -> None:
    stem = name.split(".", 1)[0].upper()
    if (
        not name
        or name in {".", ".."}
        or any(character in name for character in ("/", "\\", "\x00", ":"))
        or name.endswith((" ", "."))
        or stem in _RESERVED_STEMS
    ):
        raise ValueError(f"Refusing unsafe Windows artifact path component: {name!r}")


def _open_handle(
    path: Path,
    *,
    access: int,
    creation: int,
    flags: int,
    share_mode: int = _LOCKED_FILE_SHARE_MODE,
) -> int:
    _require_windows()
    assert _kernel32 is not None
    raw_handle = _kernel32.CreateFileW(
        _extended_path(path),
        access,
        share_mode,
        None,
        creation,
        flags,
        None,
    )
    if raw_handle in {None, _INVALID_HANDLE_VALUE}:
        _raise_last_error("CreateFileW", path)
    return int(raw_handle)


def _open_relative_handle(
    parent_handle: int,
    name: str,
    path: Path,
    *,
    access: int,
    disposition: int,
    options: int,
    share_mode: int,
    file_attributes: int = _FILE_ATTRIBUTE_NORMAL,
) -> int:
    _require_windows()
    assert _ntdll is not None
    _validate_component(name)
    name_buffer = ctypes.create_unicode_buffer(name)
    name_bytes = name.encode("utf-16-le")
    unicode_name = _UnicodeString(
        len(name_bytes),
        len(name_bytes) + ctypes.sizeof(wintypes.WCHAR),
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _ObjectAttributes(
        ctypes.sizeof(_ObjectAttributes),
        parent_handle,
        ctypes.pointer(unicode_name),
        _OBJ_CASE_INSENSITIVE | _OBJ_DONT_REPARSE,
        None,
        None,
    )
    io_status = _IoStatusBlock()
    raw_handle = wintypes.HANDLE()
    status = int(
        _ntdll.NtCreateFile(
            ctypes.byref(raw_handle),
            access | _SYNCHRONIZE,
            ctypes.byref(attributes),
            ctypes.byref(io_status),
            None,
            file_attributes,
            share_mode,
            disposition,
            options | _FILE_SYNCHRONOUS_IO_NONALERT | _FILE_OPEN_REPARSE_POINT,
            None,
            0,
        )
    )
    if status != 0:
        _raise_ntstatus("NtCreateFile", path, status)
    handle_value = raw_handle.value
    if handle_value is None or handle_value == _INVALID_HANDLE_VALUE:
        raise OSError(f"NtCreateFile returned an invalid handle for {path}")
    return int(handle_value)


def _close_handle(handle: int) -> None:
    _require_windows()
    assert _kernel32 is not None
    if not _kernel32.CloseHandle(handle):
        logger.debug("CloseHandle failed for confined artifact handle")


def _attribute_info(handle: int, path: Path) -> _FileAttributeTagInfo:
    _require_windows()
    assert _kernel32 is not None
    info = _FileAttributeTagInfo()
    if not _kernel32.GetFileInformationByHandleEx(
        handle,
        _FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        _raise_last_error("GetFileInformationByHandleEx", path)
    return info


def _reject_reparse_or_wrong_kind(
    handle: int,
    path: Path,
    *,
    require_directory: bool,
) -> int:
    info = _attribute_info(handle, path)
    if info.FileAttributes & _FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(
            "Refusing to access coordination artifact through a Windows reparse point: "
            f"{path}"
        )
    is_directory = bool(info.FileAttributes & _FILE_ATTRIBUTE_DIRECTORY)
    if is_directory != require_directory:
        kind = "directory" if require_directory else "regular file"
        raise ValueError(f"Refusing coordination artifact path that is not a {kind}: {path}")
    return int(info.FileAttributes)


def _open_root_directory(path: Path) -> int:
    handle = _open_handle(
        path,
        access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
        creation=_OPEN_EXISTING,
        flags=_FILE_FLAG_BACKUP_SEMANTICS | _FILE_FLAG_OPEN_REPARSE_POINT,
        share_mode=_LOCKED_DIRECTORY_SHARE_MODE,
    )
    try:
        _reject_reparse_or_wrong_kind(handle, path, require_directory=True)
    except BaseException:
        _close_handle(handle)
        raise
    return handle


def _open_or_create_relative_directory(
    parent_handle: int,
    name: str,
    path: Path,
) -> int:
    """Open a child directory, creating it relative to its pinned parent."""
    try:
        return _open_relative_handle(
            parent_handle,
            name,
            path,
            access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
            disposition=_FILE_OPEN,
            options=_FILE_DIRECTORY_FILE,
            share_mode=_LOCKED_DIRECTORY_SHARE_MODE,
        )
    except OSError as exc:
        if _windows_error_code(exc) not in {
            _ERROR_FILE_NOT_FOUND,
            _ERROR_PATH_NOT_FOUND,
        }:
            raise

    try:
        return _open_relative_handle(
            parent_handle,
            name,
            path,
            access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
            disposition=_FILE_CREATE,
            options=_FILE_DIRECTORY_FILE,
            share_mode=_LOCKED_DIRECTORY_SHARE_MODE,
            file_attributes=_FILE_ATTRIBUTE_DIRECTORY,
        )
    except OSError as exc:
        if _windows_error_code(exc) not in {
            _ERROR_FILE_EXISTS,
            _ERROR_ALREADY_EXISTS,
        }:
            raise
        return _open_relative_handle(
            parent_handle,
            name,
            path,
            access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
            disposition=_FILE_OPEN,
            options=_FILE_DIRECTORY_FILE,
            share_mode=_LOCKED_DIRECTORY_SHARE_MODE,
        )


@contextmanager
def _locked_parent(
    worktree_root: Path,
    target: Path,
    *,
    create_missing: bool = False,
) -> Iterator[int]:
    root = worktree_root.resolve()
    try:
        relative_parent = target.parent.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Refusing Windows artifact path outside coordination worktree: {target}"
        ) from exc

    handles: list[int] = []
    current = root
    try:
        handles.append(_open_root_directory(current))
        for component in relative_parent.parts:
            _validate_component(component)
            current /= component
            if create_missing:
                handle = _open_or_create_relative_directory(
                    handles[-1],
                    component,
                    current,
                )
            else:
                handle = _open_relative_handle(
                    handles[-1],
                    component,
                    current,
                    access=_FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
                    disposition=_FILE_OPEN,
                    options=_FILE_DIRECTORY_FILE,
                    share_mode=_LOCKED_DIRECTORY_SHARE_MODE,
                )
            try:
                _reject_reparse_or_wrong_kind(
                    handle,
                    current,
                    require_directory=True,
                )
            except BaseException:
                _close_handle(handle)
                raise
            handles.append(handle)
        yield handles[-1]
    finally:
        for handle in reversed(handles):
            _close_handle(handle)


def _existing_target_attributes(parent_handle: int, target: Path) -> int | None:
    try:
        handle = _open_relative_handle(
            parent_handle,
            target.name,
            target,
            access=_FILE_READ_ATTRIBUTES,
            disposition=_FILE_OPEN,
            options=0,
            share_mode=_FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE,
        )
    except OSError as exc:
        if _windows_error_code(exc) in {
            _ERROR_FILE_NOT_FOUND,
            _ERROR_PATH_NOT_FOUND,
        }:
            return None
        raise
    try:
        return _reject_reparse_or_wrong_kind(
            handle,
            target,
            require_directory=False,
        )
    finally:
        _close_handle(handle)


def _write_all(handle: int, content: bytes, path: Path) -> None:
    _require_windows()
    assert _kernel32 is not None
    remaining = memoryview(content)
    while remaining:
        chunk = bytes(remaining[: 2**31 - 1])
        buffer = ctypes.create_string_buffer(chunk)
        written = wintypes.DWORD()
        if not _kernel32.WriteFile(
            handle,
            buffer,
            len(chunk),
            ctypes.byref(written),
            None,
        ):
            _raise_last_error("WriteFile", path)
        if written.value == 0:
            raise OSError(f"WriteFile made no progress for {path}")
        remaining = remaining[written.value :]
    if not _kernel32.FlushFileBuffers(handle):
        _raise_last_error("FlushFileBuffers", path)


def _rename_temp_handle(handle: int, parent_handle: int, target_name: str, path: Path) -> None:
    _require_windows()
    assert _ntdll is not None
    _validate_component(target_name)
    encoded_name = target_name.encode("utf-16-le")
    name_offset = _FileRenameInfoHeader.FileName.offset
    buffer_size = max(
        ctypes.sizeof(_FileRenameInfoHeader),
        name_offset + len(encoded_name) + ctypes.sizeof(wintypes.WCHAR),
    )
    buffer = ctypes.create_string_buffer(buffer_size)
    info = _FileRenameInfoHeader.from_buffer(buffer)
    info.ReplaceIfExists = True
    info.RootDirectory = parent_handle
    info.FileNameLength = len(encoded_name)
    ctypes.memmove(ctypes.addressof(buffer) + name_offset, encoded_name, len(encoded_name))
    io_status = _IoStatusBlock()
    status = int(
        _ntdll.NtSetInformationFile(
            handle,
            ctypes.byref(io_status),
            buffer,
            buffer_size,
            _FILE_RENAME_INFORMATION_CLASS,
        )
    )
    if status != 0:
        _raise_ntstatus("NtSetInformationFile(FileRenameInformation)", path, status)


def _mark_delete(handle: int, path: Path) -> None:
    _require_windows()
    assert _kernel32 is not None
    info = _FileDispositionInfo(True)
    if not _kernel32.SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        _raise_last_error("SetFileInformationByHandle(FileDispositionInfo)", path)


def ensure_confined_parent_windows(worktree_root: Path, target: Path) -> None:
    """Create missing parent directories without leaving pinned handles."""
    _require_windows()
    _validate_component(target.name)
    with _locked_parent(worktree_root, target, create_missing=True):
        pass


def write_confined_artifact_bytes_windows(
    worktree_root: Path,
    target: Path,
    content: bytes,
    *,
    tmp_name: str,
) -> None:
    """Atomically replace ``target`` through locked, non-reparse Win32 handles."""
    _require_windows()
    _validate_component(target.name)
    _validate_component(tmp_name)
    temp_path = target.parent / tmp_name
    with _locked_parent(worktree_root, target) as parent_handle:
        _existing_target_attributes(parent_handle, target)
        temp_handle = _open_relative_handle(
            parent_handle,
            tmp_name,
            temp_path,
            access=_GENERIC_WRITE | _FILE_READ_ATTRIBUTES | _DELETE,
            disposition=_FILE_CREATE,
            options=_FILE_NON_DIRECTORY_FILE,
            share_mode=_LOCKED_FILE_SHARE_MODE,
        )
        renamed = False
        try:
            _reject_reparse_or_wrong_kind(
                temp_handle,
                temp_path,
                require_directory=False,
            )
            _write_all(temp_handle, content, temp_path)
            _rename_temp_handle(temp_handle, parent_handle, target.name, temp_path)
            renamed = True
        finally:
            if not renamed:
                try:
                    _mark_delete(temp_handle, temp_path)
                except OSError:
                    logger.debug(
                        "Failed to mark confined Windows temp artifact for deletion: %s",
                        temp_path,
                        exc_info=True,
                    )
            _close_handle(temp_handle)


def unlink_confined_artifact_windows(worktree_root: Path, target: Path) -> None:
    """Delete a regular artifact by handle without following reparse points."""
    _require_windows()
    _validate_component(target.name)
    try:
        with _locked_parent(worktree_root, target) as parent_handle:
            handle = _open_relative_handle(
                parent_handle,
                target.name,
                target,
                access=_DELETE | _FILE_READ_ATTRIBUTES,
                disposition=_FILE_OPEN,
                options=0,
                share_mode=_LOCKED_FILE_SHARE_MODE,
            )
            try:
                _reject_reparse_or_wrong_kind(handle, target, require_directory=False)
                _mark_delete(handle, target)
            finally:
                _close_handle(handle)
    except OSError as exc:
        if _windows_error_code(exc) in {
            _ERROR_FILE_NOT_FOUND,
            _ERROR_PATH_NOT_FOUND,
        }:
            return
        raise
