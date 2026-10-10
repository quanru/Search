"""Observe hidden native page bounds; this is not a screenshot acceptance test."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, 'Tests')
import split_view as sv
sv.use('page-size-review')
rows = []
try:
    sv.setup()
    before = sv.running()
    try:
        sv.launch()
    finally:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            owners = (sv.running() - before) & sv.holding()
            sv.started.update(owners)
            if Path(sv.SOCK).exists() and owners:
                break
            time.sleep(.2)
        else:
            raise RuntimeError('No owned probe socket within deadline')
    sv.page('page-size')
    for side in ['left', 'right']:
        sv.cmd({'do':'ui','sidebar':True,'side':side,'hides':False,'folded':False})
        for width in [1180, 700, 560, 1180]:
            sv.cmd({'do':'resize','width':width,'height':780,'steps':12})
            deadline = time.monotonic() + 5
            previous = None
            stable = 0
            while time.monotonic() < deadline:
                sample = sv.cmd({'do':'probe'})
                frame = sample.get('activePageFrame')
                stable = stable + 1 if frame and frame == previous else 0
                previous = frame
                if stable >= 3:
                    break
                time.sleep(.2)
            if not frame:
                raise RuntimeError('No active page frame: '+json.dumps(sample))
            windows = [w for w in sample['windows'] if w['kind'] == 'BrowserWindow']
            if len(windows) != 1:
                raise RuntimeError('Expected one owned BrowserWindow: '+json.dumps(sample['windows']))
            actual = windows[0]['frame'][2]
            row = {'side':side,'requestedWidth':width,'actualWidth':actual,'pageFrame':frame,
                   'withinWindow': frame[0]>=-2 and frame[0]+frame[2]<=actual+2}
            rows.append(row)
            print(json.dumps(row),flush=True)
    print('Model bounds only: overlays, visual clipping and animation are not visually verified.',flush=True)
    if not all(r['withinWindow'] for r in rows):
        raise RuntimeError('Page extends outside its owned window')
finally:
    Path('page-size-results.json').write_text(json.dumps(rows,indent=2))
    sv.finish()
