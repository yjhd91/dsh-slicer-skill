"""Bridge: lets the DSH chat execute Python inside a running 3D Slicer.

Launch Slicer with:  Slicer.exe --python-script D:\\SlicerModules\\bridge\\bridge_autoload.py

Protocol (file queue, executed on Slicer's main thread):
  inbox/<id>.py   -> script to run
  outbox/<id>.json-> {"ok": bool, "result": ..., "stdout": str, "error": str, "elapsed": float}
  done/<id>.py    -> executed scripts are moved here
  heartbeat.json  -> liveness probe written every poll
"""
import ast
import glob
import io
import json
import os
import sys
import time
import traceback

import qt
import slicer

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(BRIDGE_DIR, "inbox")
OUTBOX = os.path.join(BRIDGE_DIR, "outbox")
DONE = os.path.join(BRIDGE_DIR, "done")
HEARTBEAT = os.path.join(BRIDGE_DIR, "heartbeat.json")
LOG = os.path.join(BRIDGE_DIR, "bridge.log")

for d in (INBOX, OUTBOX, DONE):
    os.makedirs(d, exist_ok=True)


def _log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
    except OSError:
        pass


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _run(source, filename):
    """Executes the script; the value of a trailing expression is returned REPL-style."""
    namespace = {
        "__name__": "__slicer_bridge__",
        "slicer": slicer,
        "qt": qt,
    }
    stdout = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = stdout
    started = time.time()
    try:
        tree = ast.parse(source, filename=filename, mode="exec")
        body, last = tree.body, None
        if body and isinstance(body[-1], ast.Expr):
            body, last = body[:-1], body[-1].value
        if body:
            exec(compile(ast.Module(body=body, type_ignores=[]), filename, "exec"), namespace)
        result = eval(compile(ast.Expression(body=last), filename, "eval"), namespace) if last is not None else None
        return {"ok": True, "result": _jsonable(result), "stdout": stdout.getvalue(),
                "error": "", "elapsed": round(time.time() - started, 3)}
    except Exception:
        return {"ok": False, "result": None, "stdout": stdout.getvalue(),
                "error": traceback.format_exc(), "elapsed": round(time.time() - started, 3)}
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class Bridge:
    INTERVAL_MS = 200

    def __init__(self):
        self.timer = qt.QTimer()
        self.timer.setInterval(self.INTERVAL_MS)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        self._writeHeartbeat()
        print("SlicerBridge: watching %s" % INBOX)

    def _writeHeartbeat(self):
        payload = {
            "alive": True,
            "pid": os.getpid(),
            "slicerVersion": slicer.app.applicationVersion,
            "revision": slicer.app.revision,
            "python": sys.version.split()[0],
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "inbox": INBOX,
        }
        try:
            with open(HEARTBEAT + ".tmp", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(HEARTBEAT + ".tmp", HEARTBEAT)
        except OSError as e:
            _log("heartbeat failed: %r" % (e,))

    def poll(self):
        try:
            for path in sorted(glob.glob(os.path.join(INBOX, "*.py"))):
                self._handle(path)
        except Exception:
            _log("poll failed: " + traceback.format_exc())
        # Beat on every poll, not only after a job: an idle Slicer must still look alive.
        self._writeHeartbeat()

    def _handle(self, path):
        name = os.path.splitext(os.path.basename(path))[0]
        running = path + ".running"
        try:
            os.replace(path, running)
        except OSError:
            return  # another poll picked it up, or it vanished
        try:
            with open(running, encoding="utf-8") as f:
                source = f.read()
            outcome = _run(source, "%s.py" % name)
        except Exception:
            outcome = {"ok": False, "result": None, "stdout": "", "error": traceback.format_exc(), "elapsed": 0}
        try:
            with open(os.path.join(OUTBOX, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(outcome, f, ensure_ascii=False)
        except OSError as e:
            _log("could not write result for %s: %r" % (name, e))
        try:
            os.replace(running, os.path.join(DONE, name + ".py"))
        except OSError:
            pass
        _log("ran %s ok=%s" % (name, outcome["ok"]))
        self._writeHeartbeat()


def _pidAlive(pid):
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False
    import ctypes
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _anotherBridgeIsAlive():
    """Two Slicers sharing one inbox would race each other for jobs."""
    try:
        if not os.path.isfile(HEARTBEAT):
            return False
        with open(HEARTBEAT, encoding="utf-8") as f:
            info = json.load(f)
        pid = info.get("pid")
        return bool(pid) and int(pid) != os.getpid() and _pidAlive(pid)
    except (OSError, ValueError):
        return False


if _anotherBridgeIsAlive():
    print("SlicerBridge: another Slicer instance already serves %s - staying idle here." % INBOX)
    slicerBridge = None
else:
    # Keep a reference so the timer is not garbage collected.
    slicerBridge = Bridge()
