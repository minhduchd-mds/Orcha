"""Shared data location and serialized, atomic persistence for the desktop runtime."""
from __future__ import annotations
import contextlib
import functools
import json
import os
from pathlib import Path
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('ORCHA_DATA_DIR') or os.environ.get('KIMIK3_DATA_DIR') or ROOT / 'data').expanduser().resolve()
_lock = threading.RLock()
_local = threading.local()


@contextlib.contextmanager
def transaction():
    """A reentrant transaction shared by threads and cooperating desktop processes.

    Lock read/modify/write together, not just replacement. Keep model/network calls
    outside this lock. Each JSON document is its own atomic commit.
    """
    with _lock:
        if getattr(_local, 'depth', 0):
            _local.depth += 1
            try:
                yield
            finally:
                _local.depth -= 1
            return
        DATA.mkdir(parents=True, exist_ok=True)
        with (DATA / '.storage.lock').open('a+b') as stream:
            stream.seek(0, 2)
            if not stream.tell():
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX)
            _local.depth = 1
            try:
                yield
            finally:
                _local.depth = 0
                stream.seek(0)
                if os.name == 'nt':
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)


def serialized(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        with transaction():
            return fn(*args, **kwargs)
    return wrapped


def read_json(path, default):
    """Read authoritative JSON. Corruption fails loudly by design."""
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default
    except (ValueError, OSError) as exc:
        raise RuntimeError(f'Cannot read persistent data: {path}') from exc


@serialized
def read_json_derived(path, default):
    """Read rebuildable/derived JSON using backup-and-skip corruption policy.

    Authoritative state must continue to use read_json(). If a derived record is
    malformed, preserve the bytes under a .bak-* sibling and return the supplied
    default so the application can boot and rebuild the projection/cache.
    """
    p = Path(path)
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default
    except (ValueError, OSError):
        if not p.exists():
            return default
        stamp = time.strftime('%Y%m%d%H%M%S', time.gmtime())
        backup = p.with_name(p.name + f'.bak-{stamp}-{uuid.uuid4().hex[:8]}')
        try:
            os.replace(p, backup)
        except OSError as exc:
            raise RuntimeError(f'Cannot quarantine corrupt derived data: {p}') from exc
        return default


def atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with tmp.open('w', encoding='utf-8', newline='\n') as stream:
            stream.write(text); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2))


@contextlib.contextmanager
def runtime_lease():
    """Only one desktop runtime may recover or execute against this data directory."""
    DATA.mkdir(parents=True,exist_ok=True)
    with (DATA/'.runtime.lock').open('a+b') as stream:
        stream.seek(0,2)
        if not stream.tell():stream.write(b'0');stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:raise RuntimeError('Another Orcha runtime is using this data directory') from exc
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream,fcntl.LOCK_UN)
