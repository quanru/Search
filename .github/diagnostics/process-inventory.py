import json
import runpy
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, 'Tests')
import split_view as sv
original_launch = sv.launch
def launch():
    before = sv.running()
    try:
        original_launch()
    finally:
        until = time.monotonic() + 60
        while time.monotonic() < until:
            owners = (sv.running() - before) & sv.holding()
            sv.started.update(owners)
            if owners and Path(sv.SOCK).exists():
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Owned probe socket unavailable')
sv.launch = launch
module = runpy.run_path('Tests/ExtensionWorkerRecovery/live.py', run_name='inventory_module')
Live = module['Live']
original_setup = Live.setup_pages
def setup(self, base):
    worker = original_setup(self, base)
    samples = []
    for index in range(3):
        extension = self.extension_state()
        tabs = sv.cmd({'do': 'tabs'})
        row = {'worker': extension.get('diagnosticWorkerProcess'), 'fixtureTabs': self.tabs,
               'tabs': tabs, 'ownedAppProcesses': sv.pids()}
        pids = {int(row['worker'] or 0)}
        for tab in tabs.get('tabs', []):
            pids.add(int(tab.get('process') or 0))
        pids.discard(0)
        row['processDescriptions'] = subprocess.run(
            ['ps', '-p', ','.join(map(str, sorted(pids))), '-o', 'pid=,ppid=,comm='],
            capture_output=True, text=True).stdout if pids else ''
        samples.append(row)
        print('PROCESS_INVENTORY', json.dumps(row, sort_keys=True), flush=True)
        time.sleep(.5)
    Path('worker-process-inventory.json').write_text(json.dumps(samples, indent=2))
    print('READ_ONLY: no signal, suspension, termination or recovery requested.', flush=True)
    return worker
Live.setup_pages = setup
raise SystemExit(module['main'](['--admission-only']))
