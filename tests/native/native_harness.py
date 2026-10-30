"""Compile the real native rules sources with strict warnings on both hosts."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def run_native(source):
    with tempfile.TemporaryDirectory(prefix='universe-native-') as folder:
        base = Path(folder)
        harness = base / 'harness.c'
        harness.write_text(source, encoding='utf-8')
        exe = base / ('rules.exe' if os.name == 'nt' else 'rules')
        engine = ROOT / 'native/universe'
        if os.name == 'nt':
            vswhere = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
            paths = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-requires',
                'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-find',
                r'VC\Auxiliary\Build\vcvars64.bat'], text=True).splitlines()
            assert paths, 'A C compiler is required for the native component tests'
            script = base / 'compile.cmd'
            script.write_text('@echo off\ncall "' + paths[0] + '" >nul\nif errorlevel 1 exit /b 1\n'
                'cl /nologo /std:c11 /utf-8 /W4 /WX /I"' + str(engine / 'include') + '" /I"' + str(engine) + '" '
                '/Fe:"' + str(exe) + '" "' + str(engine / 'universe.c') + '" "' + str(engine / 'journey.c') + '" "' + str(engine / 'port_bridge.c') + '" "' + str(harness) + '"\nexit /b %errorlevel%\n')
            command = ['cmd.exe', '/d', '/c', str(script)]
        else:
            compiler = shutil.which('gcc') or shutil.which('clang')
            assert compiler, 'A C compiler is required for the native component tests'
            command = [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                '-I' + str(engine / 'include'), '-I' + str(engine), str(engine / 'universe.c'),
                str(engine / 'journey.c'), str(engine / 'port_bridge.c'), str(harness), '-o', str(exe)]
        built = subprocess.run(command, cwd=base, capture_output=True, text=True, errors='replace', timeout=120)
        assert built.returncode == 0, built.stdout + built.stderr
        run = subprocess.run([str(exe)], cwd=base, capture_output=True, text=True, timeout=30)
        assert run.returncode == 0, run.stdout + run.stderr
        return run
