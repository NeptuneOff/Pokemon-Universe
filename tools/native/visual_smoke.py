"""Capture the actual Windows game under Wine/Xvfb, for developer CI only.

Uses a fresh, verified installation and a fresh Wine prefix. Never reads a
player's installation or saves. Images are captures, without redrawing.
"""
import argparse
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

from publish_linked_candidate import pack_bytes
from prepare_platinum import safe_path
from visual_checkpoint import write_checkpoint, restore_checkpoint
from visual_live import poll_batch, publish_evidence


def install(distribution, output):
    if output.exists():
        raise ValueError('The visual test requires a fresh installation')
    release = json.loads((distribution / 'release.json').read_text(encoding='utf-8'))
    expected = {f['path']: f for f in release['files']}
    seen = set()
    output.mkdir(parents=True)
    try:
        for package in release['packages']:
            with zipfile.ZipFile(io.BytesIO(pack_bytes(distribution, package))) as archive:
                for entry in archive.infolist():
                    name = entry.filename
                    parts = safe_path(name).parts
                    if name not in expected or name in seen or entry.is_dir() or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Unexpected runtime file: ' + name)
                    spec, data = expected[name], archive.read(entry)
                    if spec['package'] != package['id'] or len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
                        raise ValueError('Runtime checksum mismatch: ' + name)
                    path = output.joinpath(*parts)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                    seen.add(name)
        if seen != set(expected):
            raise ValueError('The Git runtime is incomplete')
        (output / 'sim_config.ini').write_text(release['default_config'], encoding='utf-8')
        return release
    except Exception:
        shutil.rmtree(output)
        raise


def main():
    from PIL import ImageGrab, ImageStat
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--distribution', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate-commit', required=True)
    parser.add_argument('--recipe', type=Path, required=True)
    parser.add_argument('--checkpoint-dir', type=Path)
    parser.add_argument('--live-seconds', type=int, default=0)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    evidence = root / 'evidence'
    evidence.mkdir()
    runtime = root / 'runtime'
    release = install(args.distribution.resolve(), runtime)
    resumed = args.checkpoint_dir is not None and args.checkpoint_dir.exists()
    if resumed:
        restore_checkpoint(args.checkpoint_dir, runtime, release['build_id'])
    env = os.environ.copy()
    env.update(WINEPREFIX=str(root / 'wine-prefix'), WINEARCH='win64',
               WINEDEBUG='-all', SDL_AUDIODRIVER='dummy', LIBGL_ALWAYS_SOFTWARE='1')
    wine = shutil.which('wine64') or '/usr/lib/wine/wine64'
    log = evidence / 'game.log'
    report = {'candidate_commit': args.candidate_commit, 'build_id': release['build_id'],
              'compiled_from_commit': release['compiled_from_commit'],
              'main_sha256': hashlib.sha256((runtime / 'main.exe').read_bytes()).hexdigest(),
              'environment': 'Windows x64 executable under Wine on Linux, Xvfb and software Mesa',
              'native_windows_desktop_tested': False, 'audio_tested': False,
              'graphical_mega_battle_tested': False, 'captures': [], 'steps': []}
    report['resumed_disposable_flash'] = resumed
    report['wine_version'] = subprocess.check_output([wine, '--version'], env=env, text=True).strip()
    report['glxinfo'] = subprocess.check_output(['glxinfo', '-B'], env=env, text=True)
    (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    diagnostic = subprocess.run([wine, 'main.exe', '--universe-self-test'], cwd=runtime, env=env,
                                capture_output=True, text=True, timeout=90)
    (evidence / 'selftest.log').write_text(diagnostic.stdout + diagnostic.stderr)
    if diagnostic.returncode != 0 or '"universe_native_linked":true' not in diagnostic.stdout:
        raise RuntimeError('The linked executable diagnostic failed')

    def xdo(*cmd, check=True):
        return subprocess.run(['xdotool', *map(str, cmd)], env=env, capture_output=True,
                              text=True, timeout=10, check=check).stdout.strip()

    def grab_window(window):
        geometry = dict(line.split('=', 1) for line in xdo('getwindowgeometry', '--shell', window).splitlines() if '=' in line)
        x, y, w, h = [int(geometry[k]) for k in ('X', 'Y', 'WIDTH', 'HEIGHT')]
        return ImageGrab.grab(bbox=(x, y, x + w, y + h), xdisplay=env['DISPLAY'])

    def read_window_text(window, box=None, psm=11):
        buffer = io.BytesIO()
        screenshot = grab_window(window)
        if box:
            screenshot = screenshot.crop(tuple(box))
        screenshot.save(buffer, format='PNG')
        result = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', str(psm)],
                                input=buffer.getvalue(), env=env, capture_output=True, timeout=15, check=True)
        return result.stdout.decode('utf-8', errors='replace').strip()

    def execute_steps(steps):
        for step in steps:
            if process.poll() is not None:
                raise RuntimeError('The game exited during the visual test')
            if 'until_text' in step:
                for attempt in range(min(step.get('attempts', 30), 60)):
                    observed = read_window_text(window, step.get('ocr_box'), step.get('ocr_psm', 11))
                    if re.search(step['until_text'], observed, re.IGNORECASE):
                        break
                    for key in step.get('advance_keys', [step.get('advance_key', 'z')]):
                        xdo('key', '--clearmodifiers', '--delay', 100, key)
                        time.sleep(0.2)
                    time.sleep(step.get('delay_ms', 700) / 1000)
                else:
                    raise RuntimeError('Required screen text was not observed: ' + step['until_text'])
            if 'key' in step:
                for _ in range(step.get('repeat', 1)):
                    xdo('key', '--clearmodifiers', '--delay', 100, step['key'])
                    time.sleep(step.get('delay_ms', 650) / 1000)
            if 'hold' in step:
                xdo('keydown', step['hold'])
                time.sleep(min(float(step['seconds']), 20))
                xdo('keyup', step['hold'])
            if 'click' in step:
                xdo('mousemove', '--window', window, *step['click'])
                # Hold through several game frames; a zero-duration click
                # can disappear between SDL's mouse-state samples.
                xdo('mousedown', 1)
                time.sleep(0.2)
                xdo('mouseup', 1)
            if 'wait' in step:
                time.sleep(min(float(step['wait']), 45))
            if 'capture' in step:
                name = step['capture']
                if not name.replace('-', '').replace('_', '').isalnum():
                    raise ValueError('Invalid capture name')
                shot = grab_window(window)
                w, h = shot.size
                if max(ImageStat.Stat(shot).stddev) < 2:
                    raise RuntimeError('The captured game window is blank')
                screenshot = evidence / (name + '.png')
                shot.save(screenshot)
                capture = {'file': name + '.png', 'width': w, 'height': h}
                if shutil.which('tesseract'):
                    ocr = subprocess.run(['tesseract', str(screenshot), 'stdout', '--psm', '11'],
                                         env=env, text=True, capture_output=True, timeout=15)
                    capture['observed_ocr_text'] = ocr.stdout.strip()
                report['captures'].append(capture)
            report['steps'].append(step)
            (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')

    process = None
    try:
        with log.open('w') as output:
            process = subprocess.Popen([wine, 'main.exe'], cwd=runtime, env=env,
                                       stdout=output, stderr=subprocess.STDOUT)
            window = None
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError('The game exited before its window opened')
                for wid in xdo('search', '--onlyvisible', '--name', 'POKEMON|libntr', check=False).splitlines():
                    geometry = xdo('getwindowgeometry', '--shell', wid, check=False)
                    values = dict(line.split('=', 1) for line in geometry.splitlines() if '=' in line)
                    if int(values.get('WIDTH', 0)) >= 500 and int(values.get('HEIGHT', 0)) >= 740:
                        window = wid
                        break
                if window:
                    break
                time.sleep(1)
            if not window:
                raise RuntimeError('The game window was not found')
            report['window_title'] = xdo('getwindowname', window)
            xdo('windowfocus', '--sync', window)
            execute_steps(json.loads(args.recipe.read_text(encoding='utf-8')))
            report['actual_startup_hook_observed'] = '[Universe] Native registry linked:' in log.read_text(errors='replace')
            if not report['actual_startup_hook_observed']:
                raise RuntimeError('The actual graphical startup did not reach Universe')
            report['battle_begin_observed'] = 'native extension state initialized.' in log.read_text(errors='replace')
            report['battle_end_observed'] = 'native extension state released.' in log.read_text(errors='replace')
            if args.live_seconds:
                run_id = os.environ['GITHUB_RUN_ID']
                repo = Path(__file__).resolve().parents[2]
                sequence, seen_sha = 0, None
                deadline = time.monotonic() + min(max(args.live_seconds, 0), 1200)
                report['live_state'] = 'waiting'
                report['interactive_sequence'] = sequence
                (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                publish_evidence(repo, evidence, run_id, sequence)
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('The game exited during live control')
                    batch, seen_sha = poll_batch(repo, run_id, sequence, seen_sha)
                    if batch:
                        execute_steps(batch['steps'])
                        sequence = batch['sequence']
                        execute_steps([{'wait': 1, 'capture': 'live-' + str(sequence).zfill(3)}])
                        report['interactive_sequence'] = sequence
                        report['live_state'] = 'finished' if batch['finish'] else 'waiting'
                        report['battle_begin_observed'] = 'native extension state initialized.' in log.read_text(errors='replace')
                        report['battle_end_observed'] = 'native extension state released.' in log.read_text(errors='replace')
                        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                        publish_evidence(repo, evidence, run_id, sequence)
                        if batch['finish']:
                            break
                    time.sleep(2)
                else:
                    report['live_state'] = 'deadline'
            report['completed'] = True
    finally:
        if process and process.poll() is None:
            xdo('windowfocus', window, check=False)
            xdo('key', 'alt+F4', check=False)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        if process:
            report['process_exit'] = process.returncode
        report['disposable_flash_retained'] = write_checkpoint(runtime, root / 'checkpoint', release['build_id'])
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
