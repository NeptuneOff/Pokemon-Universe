"""Capture the actual Windows game under Wine/Xvfb, for developer CI only.

Uses a fresh, verified installation and a fresh Wine prefix. Never reads a
player's installation or saves. Images are captures, without redrawing.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

from publish_linked_candidate import pack_bytes
from prepare_platinum import safe_path


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
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    evidence = root / 'evidence'
    evidence.mkdir()
    runtime = root / 'runtime'
    release = install(args.distribution.resolve(), runtime)
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
            for step in json.loads(args.recipe.read_text(encoding='utf-8')):
                if process.poll() is not None:
                    raise RuntimeError('The game exited during the visual test')
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
                    geometry = dict(line.split('=', 1) for line in xdo('getwindowgeometry', '--shell', window).splitlines() if '=' in line)
                    x, y, w, h = [int(geometry[k]) for k in ('X', 'Y', 'WIDTH', 'HEIGHT')]
                    shot = ImageGrab.grab(bbox=(x, y, x + w, y + h), xdisplay=env['DISPLAY'])
                    if max(ImageStat.Stat(shot).stddev) < 2:
                        raise RuntimeError('The captured game window is blank')
                    shot.save(evidence / (name + '.png'))
                    report['captures'].append({'file': name + '.png', 'width': w, 'height': h})
                report['steps'].append(step)
                (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            report['actual_startup_hook_observed'] = '[Universe] Native registry linked:' in log.read_text(errors='replace')
            if not report['actual_startup_hook_observed']:
                raise RuntimeError('The actual graphical startup did not reach Universe')
            report['battle_begin_observed'] = 'native extension state initialized.' in log.read_text(errors='replace')
            report['battle_end_observed'] = 'native extension state released.' in log.read_text(errors='replace')
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
        (evidence / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
