"""Bounded live input and Git evidence for disposable graphical CI sessions."""
import json
import os
from pathlib import Path
import shutil
import subprocess

CONTROL_BRANCH = 'codex/visual-input'
PROOF_BRANCH = 'builds/windows-visual-qa'


def decode_batch(payload, run_id, previous):
    if payload.get('run_id') != int(run_id):
        return None
    sequence = payload.get('sequence')
    if type(sequence) is not int or sequence < 1:
        raise ValueError('Invalid live input sequence')
    if sequence <= previous:
        return None
    steps = payload.get('steps', [])
    if not isinstance(steps, list) or len(steps) > 150 or any(not isinstance(s, dict) for s in steps):
        raise ValueError('Invalid live input steps')
    if type(payload.get('finish', False)) is not bool:
        raise ValueError('Invalid live input finish flag')
    return {'sequence': sequence, 'steps': steps, 'finish': payload.get('finish', False)}


def git(repo, *args, env=None):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True,
                                   stderr=subprocess.PIPE, env=env, timeout=40).strip()


def poll_batch(repo, run_id, previous, seen_sha):
    line = git(repo, 'ls-remote', 'origin', 'refs/heads/' + CONTROL_BRANCH)
    if not line:
        return None, seen_sha
    sha = line.split()[0]
    if sha == seen_sha:
        return None, seen_sha
    git(repo, 'fetch', '--no-tags', 'origin', sha)
    payload = json.loads(git(repo, 'show', sha + ':visual-control.json'))
    return decode_batch(payload, run_id, previous), sha


def publish_evidence(repo, evidence, run_id, sequence):
    if not str(run_id).isdigit():
        raise ValueError('Invalid visual run number')
    repo, evidence = Path(repo).resolve(), Path(evidence).resolve()
    relative = 'docs/evidence/linked-port-' + str(run_id)
    folder = repo / relative
    folder.mkdir(parents=True, exist_ok=True)
    for path in evidence.iterdir():
        if path.is_file() and not path.is_symlink() and path.suffix in {'.png', '.log', '.json'}:
            shutil.copyfile(path, folder / path.name)
    env = os.environ.copy()
    env.update(GIT_INDEX_FILE=str(evidence.parent / 'proof.index'),
               GIT_AUTHOR_NAME='github-actions[bot]', GIT_COMMITTER_NAME='github-actions[bot]',
               GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
               GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
    line = git(repo, 'ls-remote', 'origin', 'refs/heads/' + PROOF_BRANCH)
    parent = line.split()[0] if line else None
    if parent:
        git(repo, 'fetch', '--no-tags', 'origin', parent)
        git(repo, 'read-tree', parent, env=env)
    else:
        git(repo, 'read-tree', '--empty', env=env)
    git(repo, 'add', '-f', relative, env=env)
    tree = git(repo, 'write-tree', env=env)
    parents = ['-p', parent] if parent else []
    sha = git(repo, 'commit-tree', tree, *parents, '-m',
              f'Capture live native session {run_id}, batch {sequence}', env=env)
    git(repo, 'push', 'origin', sha + ':refs/heads/' + PROOF_BRANCH)
    return sha
