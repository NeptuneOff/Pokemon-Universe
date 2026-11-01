import copy
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

from tools.native.build_git_distribution import deterministic_archive, digest
from tools.native.patch_habitats import ARCHIVE, DEFINITION, SLOT_WEIGHTS, apply_habitats, distribution_by_time
from tools.native.patch_intro import ROOT, narc_members
from tools.native.publish_linked_candidate import pack_bytes
from tools.native.refresh_habitats import rebuild
from test_resources import archive


def fixture_table():
    data = bytearray(bytes(range(212)) * 2)
    struct.pack_into('<I', data, 0, 30)
    for i in range(12):
        struct.pack_into('<II', data, 4 + i * 8, 2 + i % 5, 399)
    return bytes(data)


def fixture_definition():
    table = fixture_table()
    original = archive([table, b'untouched encounter member'])
    definition = {
        'schema': 1, 'id': 'test-opening', 'archive': ARCHIVE, 'member_count': 2,
        'source_sha256': digest(original), 'slots_percent': list(SLOT_WEIGHTS),
        'areas': [{'id': 'meadow', 'title': 'Prairie', 'biome': 'prairie', 'member': 0,
                   'source_sha256': digest(table),
                   'grass': [396, 399, 16, 161, 263, 265, 191, 10, 396, 399, 261, 406],
                   'day': [16, 187], 'night': [163, 261]}],
    }
    updated, _ = apply_habitats(original, definition)
    definition['patched_sha256'] = digest(updated)
    return definition, original


class HabitatTests(unittest.TestCase):
    def test_native_species_words_change_but_levels_rates_water_and_other_members_do_not(self):
        definition, original = fixture_definition()
        updated, report = apply_habitats(original, definition)
        before, before_blocks = narc_members(original)
        after, after_blocks = narc_members(updated)
        self.assertEqual(before[1:], after[1:])
        self.assertEqual(before_blocks[b'BTNF'], after_blocks[b'BTNF'])
        allowed = set(range(108, 124))
        for slot in range(12):
            allowed.update(range(8 + slot * 8, 12 + slot * 8))
            self.assertEqual(struct.unpack_from('<I', after[0], 8 + slot * 8)[0], definition['areas'][0]['grass'][slot])
            self.assertEqual(struct.unpack_from('<I', after[0], 4 + slot * 8)[0], 2 + slot % 5)
        self.assertEqual(struct.unpack_from('<2I', after[0], 108), (16, 187))
        self.assertEqual(struct.unpack_from('<2I', after[0], 116), (163, 261))
        for offset, (a, b) in enumerate(zip(before[0], after[0])):
            if offset not in allowed:
                self.assertEqual(a, b, 'Unexpected native field change at ' + str(offset))
        self.assertEqual(report['source_sha256'], digest(original))
        self.assertEqual(report['patched_sha256'], digest(updated))
        self.assertEqual(apply_habitats(updated, definition)[0], updated)

    def test_unreviewed_archives_tables_duplicate_members_and_non_native_species_are_rejected(self):
        for fault in ('archive', 'table', 'duplicate', 'egg', 'future', 'zero', 'boolean', 'count', 'result'):
            with self.subTest(fault=fault):
                definition, original = fixture_definition()
                if fault == 'archive': definition['source_sha256'] = 'f' * 64
                if fault == 'table': definition['areas'][0]['source_sha256'] = 'f' * 64
                if fault == 'duplicate': definition['areas'].append(copy.deepcopy(definition['areas'][0]))
                if fault == 'egg': definition['areas'][0]['grass'][0] = 494
                if fault == 'future': definition['areas'][0]['night'][1] = 1025
                if fault == 'zero': definition['areas'][0]['day'][0] = 0
                if fault == 'boolean': definition['areas'][0]['grass'][0] = True
                if fault == 'count': definition['member_count'] = 3
                if fault == 'result': definition['patched_sha256'] = 'f' * 64
                with self.assertRaises(ValueError): apply_habitats(original, definition)

    def test_time_slots_have_exact_native_weights_and_no_lost_probability(self):
        definition, _ = fixture_definition()
        choices = distribution_by_time(definition['areas'][0])
        self.assertEqual(choices['morning'][16], 10)
        self.assertEqual(choices['day'][187], 10)
        self.assertEqual(choices['night'][163], 10)
        self.assertEqual(choices['night'][261], 11)
        self.assertEqual(choices['morning'][396], 24)
        self.assertEqual(choices['day'][399], 24)
        for time in choices:
            self.assertEqual(sum(choices[time].values()), 100)
        self.assertNotIn(163, choices['morning'])

    def test_published_opening_tables_use_complete_native_species_and_match_both_lake_states(self):
        definition = json.loads((ROOT / DEFINITION).read_text(encoding='utf-8'))
        catalog = json.loads((ROOT / 'content/native/expansion/catalog.json').read_text(encoding='utf-8'))
        native = {e['legacy_native_species_id'] for e in catalog['entries'] if e['form'] is None and e['legacy_native_species_id']}
        seen = set()
        for area in definition['areas']:
            for time, values in distribution_by_time(area).items():
                self.assertEqual(sum(values.values()), 100)
                self.assertTrue(set(values) <= native)
                seen.update(values)
        self.assertEqual(len(seen), 40)
        lake = next(a for a in definition['areas'] if a['id'] == 'lake_verity')
        dry = next(a for a in definition['areas'] if a['id'] == 'lake_verity_low_water')
        self.assertEqual(distribution_by_time(lake), distribution_by_time(dry))
        self.assertTrue(any(n <= 151 for n in seen))
        self.assertTrue(any(152 <= n <= 251 for n in seen))
        self.assertTrue(any(252 <= n <= 386 for n in seen))
        self.assertTrue(any(387 <= n <= 493 for n in seen))

    def make_repo(self, root):
        repo = root / 'repo'; repo.mkdir()
        definition, encounters = fixture_definition()
        definition_file = repo / DEFINITION
        definition_file.parent.mkdir(parents=True)
        definition_file.write_text(json.dumps(definition), encoding='utf-8')
        groups = {'engine': {'main.exe': b'unchanged executable'},
                  'assets': {ARCHIVE: encounters, 'tiles.narc': b'Platinum pixels'},
                  'story': {'universe-install.json': json.dumps({'resources_sha256': {
                      ARCHIVE: digest(encounters), 'tiles.narc': digest(b'Platinum pixels')}}).encode(),
                            'script.narc': b'unchanged story and events'}}
        distribution = repo / 'distribution/windows'
        files, packages = [], []
        for group, members in groups.items():
            data = deterministic_archive(members)
            name = 'packages/' + group + '/0000.part'
            path = distribution / name; path.parent.mkdir(parents=True); path.write_bytes(data)
            packages.append({'id': group, 'bytes': len(data), 'sha256': digest(data),
                             'chunks': [{'path': name, 'bytes': len(data), 'sha256': digest(data)}]})
            files.extend({'path': n, 'package': group, 'bytes': len(d), 'sha256': digest(d)} for n, d in members.items())
        release = {'schema': 1, 'platform': 'windows-x64', 'build_id': 'a' * 20, 'resource_count': 2,
                   'files': files, 'packages': packages, 'compiled_from_commit': 'b' * 40}
        (distribution / 'release.json').write_text(json.dumps(release))
        (distribution / 'unlisted.nds').write_bytes(b'not part of this distribution')
        (repo / 'save.bin').write_bytes(b'private flash')
        for cmd in (['git', 'init'], ['git', 'add', '.'], ['git', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'Base']):
            subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
        sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
        return repo, sha, groups, release

    def test_git_repack_changes_only_encounters_and_identity_and_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, sha, before, previous = self.make_repo(root)
            results = []
            for name in ('first', 'second'):
                result = rebuild(repo, sha, root / name)
                results.append(result)
                release = json.loads((root / name / 'release.json').read_text())
                self.assertEqual(release['compiled_from_commit'], previous['compiled_from_commit'])
                self.assertEqual(release['resource_count'], 2)
                self.assertEqual(release['packages'][0], previous['packages'][0])
                found = {}
                for package in release['packages']:
                    with zipfile.ZipFile(io.BytesIO(pack_bytes(root / name, package))) as archive_file:
                        found.update({n: archive_file.read(n) for n in archive_file.namelist()})
                flattened = {n: d for group in before.values() for n, d in group.items()}
                self.assertEqual(set(found), set(flattened))
                self.assertEqual({n for n in found if found[n] != flattened[n]}, {ARCHIVE, 'universe-install.json'})
                self.assertFalse((root / name / 'unlisted.nds').exists())
                identity = json.loads(found['universe-install.json'])
                self.assertEqual(identity['resources_sha256'][ARCHIVE], digest(found[ARCHIVE]))
                for entry in release['files']:
                    self.assertEqual(entry['sha256'], digest(found[entry['path']]))
            self.assertEqual(results[0], results[1])
            with self.assertRaisesRegex(ValueError, 'already exists'): rebuild(repo, sha, root / 'first')

    def test_corrupt_git_chunk_stops_before_creating_the_new_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo, _, _, _ = self.make_repo(root)
            (repo / 'distribution/windows/packages/assets/0000.part').write_bytes(b'broken')
            subprocess.run(['git', 'add', '.'], cwd=repo, check=True, capture_output=True)
            subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                            'commit', '-m', 'Corrupt fixture'], cwd=repo, check=True, capture_output=True)
            sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
            with self.assertRaisesRegex(ValueError, 'Corrupt'): rebuild(repo, sha, root / 'output')
            self.assertFalse((root / 'output').exists())
