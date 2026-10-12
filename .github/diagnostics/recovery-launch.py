import runpy, sys, time
from pathlib import Path
sys.path.insert(0, 'Tests')
import split_view as sv
original = sv.launch
def launch():
    before = sv.running()
    try:
        original()
    finally:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            owners = (sv.running() - before) & sv.holding()
            sv.started.update(owners)
            if owners and Path(sv.SOCK).exists():
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Owned probe socket not ready')
sv.launch = launch
sys.argv = ['Tests/ExtensionWorkerRecovery/live.py']
runpy.run_path(sys.argv[0], run_name='__main__')
