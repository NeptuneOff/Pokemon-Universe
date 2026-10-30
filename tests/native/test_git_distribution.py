"""Round-trip Git packages and exercise the real Windows launcher with a tiny exe."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

from tools.native.build_git_distribution import build_distribution, digest
from tools.native.prepare_platinum import ROOT, RELEASE


def fixture(base, executable=b'test executable', story=b'first investigation'):
    runtime = base / 'prepared'
    runtime.mkdir(exist_ok=True)
    package = base / 'upstream.zip'
    with zipfile.ZipFile(package, 'w') as archive:
        archive.writestr('main.exe', executable)
    (runtime / 'main.exe').write_bytes(executable)
    resources = {'graphic/world.narc': b'unchanged scenery', 'msgdata/pl_msg.narc': story}
    for name, data in resources.items():
        path = runtime / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_bytes(data)
    (runtime / 'universe-install.json').write_text(json.dumps({
        'platform': 'windows', 'upstream_release': RELEASE,
        'resources_sha256': {name: digest(data) for name, data in resources.items()}}), encoding='utf-8')
    return runtime, package


def build(runtime, package, target):
    with patch.dict('tools.native.build_git_distribution.PACKAGES', {
            'windows': ('upstream.zip', digest(package.read_bytes()), 'main.exe')}):
        return build_distribution(runtime, package, target)


class GitDistributionTests(unittest.TestCase):
    def test_deterministic_packages_round_trip_without_saves_or_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            runtime, package = fixture(base)
            for name in ('save.bin', 'personal.nds', 'debug.log', 'sim_config.ini'):
                (runtime / name).write_bytes(b'private data')
            first, second = base / 'one', base / 'two'
            self.assertEqual(build(runtime, package, first), build(runtime, package, second))
            release = json.loads((first / 'release.json').read_text())
            files = {f['path']: f for f in release['files']}
            self.assertFalse(set(files) & {'save.bin', 'personal.nds', 'debug.log', 'sim_config.ini'})
            self.assertIn('licenses/libntr.txt', files)
            for path in first.rglob('*'):
                if path.is_file():
                    self.assertEqual(path.read_bytes(), (second / path.relative_to(first)).read_bytes())
            seen = set()
            for pack in release['packages']:
                parts = []
                for part in pack['chunks']:
                    data = (first / part['path']).read_bytes()
                    self.assertEqual(len(data), part['bytes'])
                    self.assertEqual(digest(data), part['sha256'])
                    parts.append(data)
                data = b''.join(parts)
                self.assertEqual(len(data), pack['bytes'])
                self.assertEqual(digest(data), pack['sha256'])
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    for name in archive.namelist():
                        self.assertNotIn(name, seen)
                        seen.add(name)
                        payload = archive.read(name)
                        self.assertEqual(files[name]['sha256'], digest(payload))
                        self.assertEqual(files[name]['bytes'], len(payload))
                        self.assertEqual(files[name]['package'], pack['id'])
            self.assertEqual(set(files), seen)

    def test_changed_story_keeps_engine_and_art_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            runtime, package = fixture(base)
            build(runtime, package, base / 'one')
            story = runtime / 'msgdata/pl_msg.narc'
            story.write_bytes(b'second investigation')
            manifest = json.loads((runtime / 'universe-install.json').read_text())
            manifest['resources_sha256']['msgdata/pl_msg.narc'] = digest(story.read_bytes())
            (runtime / 'universe-install.json').write_text(json.dumps(manifest))
            build(runtime, package, base / 'two')
            a, b = [json.loads((base / name / 'release.json').read_text()) for name in ('one', 'two')]
            self.assertNotEqual(a['build_id'], b['build_id'])
            self.assertEqual(a['packages'][:2], b['packages'][:2])
            self.assertNotEqual(a['packages'][2], b['packages'][2])

    def test_refuses_changed_files_existing_destination_and_private_manifest_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            runtime, package = fixture(base)
            build(runtime, package, base / 'one')
            with self.assertRaisesRegex(ValueError, 'Destination'):
                build(runtime, package, base / 'one')
            (runtime / 'graphic/world.narc').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'Fichier modifie'):
                build(runtime, package, base / 'bad')
            self.assertFalse((base / 'bad').exists())
            runtime, package = fixture(base)
            manifest_path = runtime / 'universe-install.json'
            manifest = json.loads(manifest_path.read_text())
            for name in ('save.bin', 'sim_config.ini', 'personal.nds', '../escape'):
                manifest['resources_sha256'] = {name: digest(b'private')}
                manifest_path.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):
                    build(runtime, package, base / 'bad')

    def test_refuses_unpinned_engine_and_case_collisions(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            runtime, package = fixture(base)
            with self.assertRaisesRegex(ValueError, 'Paquet moteur'):
                build_distribution(runtime, package, base / 'bad')
            manifest_path = runtime / 'universe-install.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['resources_sha256']['MAIN.EXE'] = digest(b'collision')
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Collision'):
                build(runtime, package, base / 'bad')


@unittest.skipUnless(os.name == 'nt' and shutil.which('powershell.exe'), 'Windows PowerShell 5.1 integration')
class WindowsGitLauncherTests(unittest.TestCase):
    powershell = ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File']

    @classmethod
    def setUpClass(cls):
        cls.compiler_folder = tempfile.TemporaryDirectory(prefix='universe-exe-')
        base = Path(cls.compiler_folder.name)
        script = base / 'fixture.ps1'
        script.write_text("""$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.IO;
public class Program {
    public static int Main() {
        Console.WriteLine("fixture stdout");
        Console.Error.WriteLine("fixture stderr");
        string old = File.Exists("save.bin") ? File.ReadAllText("save.bin") : "";
        File.WriteAllText("save.bin", old + "|played");
        File.WriteAllText("running.txt", "ready");
        if (Environment.GetEnvironmentVariable("UNIVERSE_TEST_HOLD") == "1")
            System.Threading.Thread.Sleep(8000);
        return Environment.GetEnvironmentVariable("UNIVERSE_TEST_ERROR") == "1" ? 37 : 0;
    }
}
'@ -OutputAssembly (Join-Path $PSScriptRoot 'main.exe') -OutputType ConsoleApplication
""", encoding='utf-8')
        result = subprocess.run(cls.powershell + [str(script)], capture_output=True, text=True, errors='replace', timeout=60)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.executable = (base / 'main.exe').read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.compiler_folder.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-git-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / 'jeu français & espaces'
        (self.repo / 'tools/native').mkdir(parents=True)
        shutil.copyfile(ROOT / 'tools/native/start_windows.ps1', self.repo / 'tools/native/start_windows.ps1')
        shutil.copyfile(ROOT / 'JOUER.bat', self.repo / 'JOUER.bat')
        self.storage = self.repo / 'native-runtime'
        self.distribution = self.repo / 'distribution/windows'
        self.prepared, self.package = fixture(self.base, self.executable)
        self.release = build(self.prepared, self.package, self.distribution)

    def launch(self, *args, env=None, expected=0):
        result = subprocess.run(self.powershell + [str(self.repo / 'tools/native/start_windows.ps1'), *args],
                                cwd=self.base, capture_output=True, text=True, errors='replace', timeout=45, env=env)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def runtime(self):
        return self.storage / 'windows-builds' / self.release['build_id']

    def diagnostic(self):
        return (self.repo / 'logs/dernier-lancement.log').read_text(encoding='utf-8')

    def test_first_launch_repair_and_nonzero_game_exit_are_logged(self):
        self.launch()
        runtime = self.runtime()
        self.assertEqual((runtime / 'save.bin').read_bytes(), b'|played')
        self.assertIn('InternalResolutionScale=1', (runtime / 'sim_config.ini').read_text())
        (runtime / 'graphic/world.narc').write_bytes(b'corrupt installed asset')
        self.launch(env={**os.environ, 'UNIVERSE_TEST_ERROR': '1'}, expected=37)
        self.assertEqual((runtime / 'save.bin').read_bytes(), b'|played|played')
        self.assertEqual((runtime / 'graphic/world.narc').read_bytes(), b'unchanged scenery')
        log = self.diagnostic()
        for marker in ('fixture stdout', 'fixture stderr', 'Code de sortie du jeu : 37', self.release['build_id'], 'duree='):
            self.assertIn(marker, log)
        for data in (b'|played', b'|played|played'):
            self.assertEqual((self.storage / 'universe-backups' / (digest(data) + '.sav')).read_bytes(), data)
        self.assertFalse(list(self.storage.glob('.installation-*')))

    def test_update_and_rollback_preserve_the_most_recent_progress(self):
        self.launch()
        original_runtime = self.runtime()
        (original_runtime / 'sim_config.ini').write_text('[General]\nWindowWidth=999\n')
        old_distribution = self.repo / 'old-distribution'
        self.distribution.rename(old_distribution)
        self.prepared, self.package = fixture(self.base, self.executable, b'new investigation')
        self.release = build(self.prepared, self.package, self.distribution)
        self.launch()
        self.assertEqual((original_runtime / 'save.bin').read_bytes(), b'|played')
        self.assertEqual((self.runtime() / 'save.bin').read_bytes(), b'|played|played')
        self.assertIn('WindowWidth=999', (self.runtime() / 'sim_config.ini').read_text())
        shutil.rmtree(self.distribution)
        old_distribution.rename(self.distribution)
        self.launch()
        self.assertEqual((original_runtime / 'save.bin').read_bytes(), b'|played|played|played')

    def test_admin_isolated_then_explicit_campaign_copy_and_return_to_normal(self):
        self.launch()
        campaign = self.runtime()
        campaign_save = (campaign / 'save.bin').read_bytes()
        normal_config = (campaign / 'sim_config.ini').read_bytes()
        normal_state = (self.storage / 'windows-current.json').read_bytes()
        admin = self.storage / 'windows-admin-builds' / self.release['build_id']
        self.launch('-Admin')
        self.assertEqual((admin / 'save.bin').read_bytes(), b'|played')
        self.assertIn('GUIKey=1073741891', (admin / 'sim_config.ini').read_text())
        self.assertIn('Profil : ADMIN', self.diagnostic())
        self.assertEqual((campaign / 'save.bin').read_bytes(), campaign_save)
        self.assertEqual((campaign / 'sim_config.ini').read_bytes(), normal_config)
        self.assertEqual((self.storage / 'windows-current.json').read_bytes(), normal_state)
        self.launch('-Admin', '-CopyCampaign')
        self.assertEqual((admin / 'save.bin').read_bytes(), campaign_save + b'|played')
        self.assertEqual((campaign / 'save.bin').read_bytes(), campaign_save)
        self.assertTrue((self.storage / 'universe-admin-backups' / (digest(campaign_save) + '.sav')).exists())
        self.launch()
        self.assertEqual((campaign / 'save.bin').read_bytes(), campaign_save + b'|played')
        self.assertEqual((admin / 'save.bin').read_bytes(), campaign_save + b'|played')
        self.assertEqual((campaign / 'sim_config.ini').read_bytes(), normal_config)

    def test_admin_copy_without_a_campaign_fails_and_prepare_does_not_create_progress(self):
        self.launch('-Admin', '-PrepareOnly')
        admin = self.storage / 'windows-admin-builds' / self.release['build_id']
        self.assertFalse((admin / 'save.bin').exists())
        self.assertFalse((self.storage / 'windows-admin-current.json').exists())
        self.launch('-Admin', '-CopyCampaign', expected=1)
        self.assertIn('Aucune sauvegarde de campagne', self.diagnostic())
        self.assertFalse((admin / 'save.bin').exists())
        self.assertFalse((self.storage / 'windows-current.json').exists())

    def test_bad_git_chunk_leaves_legacy_save_untouched(self):
        legacy = self.storage / 'windows-fr'
        legacy.mkdir(parents=True)
        (legacy / 'save.bin').write_bytes(b'my original progress')
        part = next(self.distribution.glob('packages/engine/*.part'))
        damaged = bytearray(part.read_bytes())
        damaged[-1] ^= 1
        part.write_bytes(damaged)
        self.launch(expected=1)
        self.assertIn('Empreinte incorrecte', self.diagnostic())
        self.assertIn(part.name, self.diagnostic())
        self.assertEqual((legacy / 'save.bin').read_bytes(), b'my original progress')
        self.assertFalse((self.storage / 'windows-current.json').exists())
        self.assertFalse((self.runtime() / 'main.exe').exists())
        self.assertFalse(list(self.storage.glob('.installation-*')))

    def test_legacy_import_then_corrupt_backup_stops_before_playing(self):
        legacy = self.storage / 'windows-fr'
        legacy.mkdir(parents=True)
        shutil.copyfile(self.prepared / 'universe-install.json', legacy / 'universe-install.json')
        (legacy / 'save.bin').write_bytes(b'legacy')
        self.launch()
        self.assertEqual((legacy / 'save.bin').read_bytes(), b'legacy')
        self.assertEqual((self.runtime() / 'save.bin').read_bytes(), b'legacy|played')
        backup = self.storage / 'universe-backups' / (digest(b'legacy|played') + '.sav')
        backup.write_bytes(b'corrupt backup')
        self.launch(expected=1)
        self.assertIn('Copie de secours alteree', self.diagnostic())
        self.assertEqual((self.runtime() / 'save.bin').read_bytes(), b'legacy|played')

    def test_single_bat_prepares_from_another_directory_without_creating_a_save(self):
        result = subprocess.run('cmd.exe /d /s /c ""' + str(self.repo / 'JOUER.bat') + '" -PrepareOnly"',
                                cwd=self.base, capture_output=True, text=True, errors='replace', timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.runtime() / 'main.exe').is_file())
        self.assertFalse((self.runtime() / 'save.bin').exists())
        self.assertFalse((self.storage / 'windows-current.json').exists())
        self.launch('-PrepareOnly')
        self.assertIn('Installation verifiee', self.diagnostic())

    def test_second_launch_does_not_replace_running_sessions_log_or_save(self):
        process = subprocess.Popen(self.powershell + [str(self.repo / 'tools/native/start_windows.ps1')],
                                   cwd=self.base, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env={**os.environ, 'UNIVERSE_TEST_HOLD': '1'})
        try:
            deadline = time.monotonic() + 20
            while not (self.runtime() / 'running.txt').exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    self.fail(str(process.communicate(timeout=2)))
                time.sleep(0.1)
            current_log = self.diagnostic()
            self.launch('-PrepareOnly', expected=1)
            self.assertEqual(self.diagnostic(), current_log)
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, repr((stdout, stderr)))
            self.assertEqual((self.runtime() / 'save.bin').read_bytes(), b'|played')
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main()
