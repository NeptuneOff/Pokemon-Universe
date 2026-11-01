"""Opening biomes in Platinum's native wild encounter archive.

Layout: pinned WildEncounters and tools/jsoncnv/encounter.py. Only species
words change: levels, rates, water, fishing, radar and dual-slot data stay put.
"""
import hashlib
import json
from pathlib import Path
import re
import struct

if __package__:
    from .patch_intro import ROOT, narc_members, replace_narc_member
else:
    from patch_intro import ROOT, narc_members, replace_narc_member

ARCHIVE = 'fielddata/encountdata/pl_enc_data.narc'
DEFINITION = 'content/native/habitats.fr.json'
SLOT_WEIGHTS = (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1)


def validate(definition):
    if definition.get('schema') != 1 or definition.get('archive') != ARCHIVE:
        raise ValueError('Unsupported habitat definition')
    if definition.get('slots_percent') != list(SLOT_WEIGHTS):
        raise ValueError('Habitat probabilities differ from the native engine')
    if type(definition.get('member_count')) is not int or not 1 <= definition['member_count'] <= 1024:
        raise ValueError('Invalid native encounter archive size')
    if not re.fullmatch(r'[a-z0-9-]+', definition.get('id', '')):
        raise ValueError('Invalid habitat revision')
    areas = definition.get('areas')
    if not isinstance(areas, list) or not areas:
        raise ValueError('Missing habitat areas')
    seen, names = set(), set()
    for item in areas:
        index = item.get('member')
        if type(index) is not int or not 0 <= index < definition['member_count'] or index in seen:
            raise ValueError('Duplicate or invalid encounter member')
        if not item.get('id') or item['id'] in names or not item.get('title') or not item.get('biome'):
            raise ValueError('Missing or duplicate habitat identity')
        seen.add(index)
        names.add(item['id'])
        if not re.fullmatch('[0-9a-f]{64}', item.get('source_sha256', '')):
            raise ValueError('Missing source encounter checksum')
        for key, count in [('grass', 12), ('day', 2), ('night', 2)]:
            species = item.get(key)
            if not isinstance(species, list) or len(species) != count or any(type(s) is not int or not 1 <= s <= 493 for s in species):
                raise ValueError('Habitat species must use complete native species 1..493')
    if not re.fullmatch('[0-9a-f]{64}', definition.get('source_sha256', '')):
        raise ValueError('Missing source archive checksum')


def apply_habitats(archive, definition=None):
    definition = definition or json.loads((ROOT / DEFINITION).read_text(encoding='utf-8'))
    validate(definition)
    current_sha = hashlib.sha256(archive).hexdigest()
    already_applied = current_sha == definition.get('patched_sha256')
    if current_sha != definition['source_sha256'] and not already_applied:
        raise ValueError('The native encounter archive differs from the reviewed source')
    members, _ = narc_members(archive)
    if len(members) != definition['member_count']:
        raise ValueError('The native encounter member count changed')
    replacements = []
    for area in definition['areas']:
        before = members[area['member']]
        if len(before) != 424 or (not already_applied and hashlib.sha256(before).hexdigest() != area['source_sha256']):
            raise ValueError('Incompatible habitat table: ' + area['id'])
        if not 1 <= struct.unpack_from('<I', before)[0] <= 100:
            raise ValueError('This area has no native grass encounters')
        after = bytearray(before)
        for slot, species in enumerate(area['grass']):
            if not 1 <= struct.unpack_from('<I', before, 4 + 8 * slot)[0] <= 100:
                raise ValueError('Invalid native encounter level')
            struct.pack_into('<I', after, 8 + 8 * slot, species)
        struct.pack_into('<2I', after, 108, *area['day'])
        struct.pack_into('<2I', after, 116, *area['night'])
        replacements.append((area['member'], bytes(after)))
    # Validate every area before constructing any changed archive.
    result = archive
    for index, data in replacements:
        result = replace_narc_member(result, index, data)
    if definition.get('patched_sha256') and hashlib.sha256(result).hexdigest() != definition['patched_sha256']:
        raise ValueError('The habitat result differs from the reviewed archive')
    return result, {
        'id': definition['id'], 'archive': ARCHIVE,
        'source_sha256': definition['source_sha256'],
        'patched_sha256': hashlib.sha256(result).hexdigest(),
        'areas': [{'id': a['id'], 'title': a['title'], 'member': a['member']} for a in definition['areas']],
    }


def distribution_by_time(area):
    """Exact ordinary-slot percentages; no radar/swarm/ability modifiers."""
    result = {}
    for time in ('morning', 'day', 'night'):
        slots = list(area['grass'])
        if time != 'morning':
            slots[2:4] = area[time]
        totals = {}
        for species, weight in zip(slots, SLOT_WEIGHTS):
            totals[species] = totals.get(species, 0) + weight
        result[time] = totals
    return result
