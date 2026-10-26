"""The portable archive must not include personal saves or require Python."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools.native.prepare_platinum import ROOT, RELEASE
from tools.native.package_windows import package_windows


class PortableTests(unittest.TestCase):
    def test_package_uses_only_verified_entries_and_excludes_personal_files(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            runtime = base / 'game'
            runtime.mkdir()
            package = base / 'upstream.zip'
            with zipfile.ZipFile(package, 'w') as archive:
                archive.writestr('main.exe', b'test executable')
            (runtime / 'main.exe').write_bytes(b'test executable')
            (runtime / 'world.narc').write_bytes(b'personal game resource')
            (runtime / 'save.bin').write_bytes(b'do not publish my progress')
            (runtime / 'personal.nds').write_bytes(b'do not include a ROM')
            (runtime / 'debug.log').write_bytes(b'do not include logs')
            (runtime / 'sim_config.ini').write_text('[General]\n')
            (runtime / 'universe-install.json').write_text(json.dumps({
                'platform': 'windows', 'upstream_release': RELEASE,
                'resources_sha256': {'world.narc': hashlib.sha256(b'personal game resource').hexdigest()}}))
            before = {p.name: p.read_bytes() for p in runtime.iterdir()}
            with patch.dict('tools.native.package_windows.PACKAGES', {'windows': (
                    'upstream.zip', hashlib.sha256(package.read_bytes()).hexdigest(), 'main.exe')}):
                output = base / 'portable.zip'
                package_windows(runtime, package, output)
                with zipfile.ZipFile(output) as archive:
                    names = archive.namelist()
                    self.assertIn('Pokemon-Universe/JOUER.cmd', names)
                    self.assertIn('Pokemon-Universe/Lancer-Universe.ps1', names)
                    self.assertEqual(archive.read('Pokemon-Universe/world.narc'), b'personal game resource')
                    self.assertFalse(any(n.endswith(('.nds', '.sav', '.log', 'save.bin')) for n in names))
                    self.assertNotIn(b'python', archive.read('Pokemon-Universe/JOUER.cmd').lower())
                self.assertEqual(before, {p.name: p.read_bytes() for p in runtime.iterdir()})
                (runtime / 'main.exe').write_bytes(b'changed executable')
                with self.assertRaisesRegex(ValueError, 'Fichier modifie'):
                    package_windows(runtime, package, base / 'bad.zip')
                self.assertFalse((base / 'bad.zip').exists())

    @unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows PowerShell test')
    def test_windows_launcher_preserves_saves_and_stops_on_a_corrupt_backup(self):
        with tempfile.TemporaryDirectory(prefix='universe-') as folder:
            runtime = Path(folder) / 'jeu francais avec espaces'
            runtime.mkdir()
            launcher = runtime / 'Lancer-Universe.ps1'
            shutil.copyfile(ROOT / 'content/native/portable/Lancer-Universe.ps1', launcher)
            # An independent executable exercises the real launcher, including a
            # nonzero game exit. It is a test fixture, not a compiled game build.
            fixture = runtime / 'build-fixture.ps1'
            fixture.write_text("""$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Add-Type -TypeDefinition @'
using System;
using System.IO;
public class Program {
    public static int Main() {
        File.WriteAllBytes("save.bin", System.Text.Encoding.ASCII.GetBytes("new progress"));
        return 3;
    }
}
'@ -OutputAssembly (Join-Path $PSScriptRoot 'main.exe') -OutputType ConsoleApplication
""", encoding='utf-8')
            powershell = ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File']
            build = subprocess.run(powershell + [str(fixture)], capture_output=True, text=True, timeout=60)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            save = runtime / 'save.bin'
            old, new = b'old progress', b'new progress'
            save.write_bytes(old)
            run = subprocess.run(powershell + [str(launcher)], cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 3, run.stdout + run.stderr)
            self.assertEqual(save.read_bytes(), new)
            for data in (old, new):
                self.assertEqual((runtime / 'universe-backups' / (hashlib.sha256(data).hexdigest() + '.sav')).read_bytes(), data)
            save.write_bytes(old)
            (runtime / 'universe-backups' / (hashlib.sha256(old).hexdigest() + '.sav')).write_bytes(b'corrupt backup')
            run = subprocess.run(powershell + [str(launcher)], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(save.read_bytes(), old)


if __name__ == '__main__':
    unittest.main()
