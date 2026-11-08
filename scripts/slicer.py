#!/usr/bin/env python3
"""slicer — drive a running 3D Slicer from the command line (part of the `slicer` skill).

  python slicer.py --status                 # is the bridge alive?
  python slicer.py --info                   # Slicer version, extensions, module count
  python slicer.py --code "print(1+1)"      # run one snippet
  python slicer.py --file task.py           # run a script file
  python slicer.py --start | --restart      # launch / relaunch Slicer with the bridge

The code runs on Slicer's main thread; a trailing expression is returned REPL-style.
Override paths with DSH_SLICER_BRIDGE / DSH_SLICER_EXE if Slicer moves.
"""
import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
import uuid

_HERE = os.path.dirname(os.path.abspath(__file__))

def _default_bridge():
    """Where the bridge queue lives: explicit env, then the skill-local one (fresh installs),
    then this machine's long-standing location."""
    for candidate in (os.path.join(os.path.dirname(_HERE), "bridge"), r"D:\SlicerModules\bridge"):
        if os.path.isdir(candidate):
            return candidate
    return r"D:\SlicerModules\bridge"

BRIDGE_DIR = os.environ.get("DSH_SLICER_BRIDGE") or _default_bridge()
SLICER_EXE = os.environ.get("DSH_SLICER_EXE") or r"D:\Slicer 5.12.4\Slicer.exe"
INBOX = os.path.join(BRIDGE_DIR, "inbox")
OUTBOX = os.path.join(BRIDGE_DIR, "outbox")
HEARTBEAT = os.path.join(BRIDGE_DIR, "heartbeat.json")
AUTOLOAD = os.path.join(BRIDGE_DIR, "bridge_autoload.py")
FRESH_SECONDS = 15

INFO_CODE = """
import json as _json
_m = slicer.app.extensionsManagerModel()
{"version": slicer.app.applicationVersion,
 "revision": slicer.app.revision,
 "python": __import__("sys").version.split()[0],
 "extensions": sorted(_m.installedExtensions),
 "modules": len([n for n in dir(slicer.modules) if not n.startswith("_")])}
"""


def _pid_alive(pid):
    if not pid:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return bool(ok) and code.value == 259
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _read_heartbeat():
    try:
        with open(HEARTBEAT, encoding="utf-8") as f:
            info = json.load(f)
        return info, time.time() - os.path.getmtime(HEARTBEAT)
    except (OSError, ValueError):
        return None, None


def is_running():
    info, age = _read_heartbeat()
    return bool(info) and age is not None and age < FRESH_SECONDS and _pid_alive(info.get("pid"))


def status(quiet=False):
    info, age = _read_heartbeat()
    if not info:
        print("bridge: NOT RUNNING - start 3D Slicer (the bridge loads automatically)")
        return 1
    alive = _pid_alive(info.get("pid"))
    if alive and age is not None and age < FRESH_SECONDS:
        state, code = "RUNNING", 0
    elif alive:
        state, code = "SLOW (Slicer main thread is busy)", 1
    else:
        state, code = "STOPPED (Slicer pid %s is gone)" % info.get("pid"), 1
    print("bridge: %s%s" % (state, "" if age is None else "  (beat %.1fs ago)" % age))
    print("  Slicer %s rev %s  Python %s  pid %s" % (
        info.get("slicerVersion"), info.get("revision"), info.get("python"), info.get("pid")))
    return code


def start(restart=False):
    if restart:
        _kill_slicer()
    if is_running():
        print("bridge already running")
        return 0
    old_pid = (_read_heartbeat()[0] or {}).get("pid")
    try:
        os.remove(HEARTBEAT)
    except OSError:
        pass
    if not os.path.isfile(SLICER_EXE):
        print("Slicer not found: %s (set DSH_SLICER_EXE)" % SLICER_EXE, file=sys.stderr)
        return 2
    subprocess.Popen([SLICER_EXE, "--no-splash", "--python-script", AUTOLOAD],
                     close_fds=True, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    print("starting Slicer; waiting for the bridge...")
    deadline = time.time() + 180
    while time.time() < deadline:
        info, _ = _read_heartbeat()
        if info and info.get("pid") != old_pid and is_running():
            print("bridge ready (pid %s)" % info.get("pid"))
            return 0
        time.sleep(1)
    print("timed out waiting for the bridge", file=sys.stderr)
    return 1


def _kill_slicer():
    if os.name != "nt":
        return
    subprocess.run(["taskkill", "/F", "/IM", "Slicer.exe"], capture_output=True)
    subprocess.run(["taskkill", "/F", "/IM", "SlicerApp-real.exe"], capture_output=True)
    time.sleep(4)


def run(code, timeout=120.0):
    for d in (INBOX, OUTBOX):
        os.makedirs(d, exist_ok=True)
    job = uuid.uuid4().hex[:12]
    job_path = os.path.join(INBOX, job + ".py")
    out_path = os.path.join(OUTBOX, job + ".json")
    with open(job_path, "w", encoding="utf-8") as f:
        f.write(code)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.isfile(out_path):
            with open(out_path, encoding="utf-8") as f:
                payload = json.load(f)
            try:
                os.remove(out_path)
            except OSError:
                pass
            return payload
        time.sleep(0.05)
    try:
        os.remove(job_path)
    except OSError:
        pass
    return {"ok": False, "result": None, "stdout": "",
            "error": "timeout after %ss (Slicer busy or bridge down)" % timeout, "elapsed": timeout}


def main():
    ap = argparse.ArgumentParser(description="Drive a running 3D Slicer")
    ap.add_argument("--code")
    ap.add_argument("--file")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--info", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--restart", action="store_true")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.status:
        sys.exit(status())
    if args.start or args.restart:
        sys.exit(start(restart=args.restart))

    if args.info:
        if not is_running():
            status()
            sys.exit(2)
        payload = run(INFO_CODE, args.timeout)
        print(json.dumps(payload.get("result") if payload.get("ok") else payload,
                         ensure_ascii=False, indent=2))
        sys.exit(0 if payload.get("ok") else 1)

    code = args.code
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            code = f.read()
    if not code:
        ap.error("need --code, --file, --status, --info, --start or --restart")

    if not is_running():
        status()
        sys.exit(2)

    payload = run(code, args.timeout)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload.get("stdout"):
            print(payload["stdout"], end="" if payload["stdout"].endswith("\n") else "\n")
        if payload.get("result") is not None:
            print(payload["result"])
        if payload.get("error"):
            print(payload["error"], file=sys.stderr)
    sys.exit(0 if payload.get("ok") else 1)


if __name__ == "__main__":
    main()
