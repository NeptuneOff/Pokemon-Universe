"""Small assembler for Universe events executed by Platinum's native script VM.

Encoding reference: the pinned engine's asm/macros/scrcmd.inc and
include/data/scripts/scrcmd.h. This does not compile or modify the PC engine.
Only the instructions needed by the first investigation are supported.
"""
import struct


COMMANDS = {
    'end': (0x02, ''), 'compare': (0x11, 'HH'),
    'set': (0x28, 'HH'), 'message': (0x2c, 'B'),
    'wait': (0x31, ''), 'close': (0x34, ''),
    'menu': (0x41, 'BBBBH'), 'option': (0x42, 'BB'),
    'show_menu': (0x43, ''), 'lock': (0x60, ''),
    'release': (0x61, ''), 'face': (0x68, ''),
    'add_item': (0x7b, 'HHH'), 'random': (0x1b7, 'HH'),
}


def entry_targets(bank, count):
    """Read the fixed original entry table, whose offsets are PC-relative."""
    if len(bank) < count * 4 + 2 or bank[count * 4:count * 4 + 2] != b'\x13\xfd':
        raise ValueError('Table des événements incompatible.')
    targets = [4 * i + 4 + struct.unpack_from('<i', bank, 4 * i)[0] for i in range(count)]
    if any(not count * 4 + 2 <= target < len(bank) for target in targets):
        raise ValueError('Entrée de script hors limites.')
    return targets


def assemble(instructions, *, base=0, symbols=None, external_labels=None):
    """Two passes, strict argument widths, and signed relative branch fixups."""
    symbols = symbols or {}
    labels = dict(external_labels or {})
    code, fixups = bytearray(), []

    def number(value):
        value = symbols.get(value, value) if isinstance(value, str) else value
        if type(value) is not int:
            raise ValueError('Symbole numérique inconnu : ' + str(value))
        return value

    for instruction in instructions:
        if not isinstance(instruction, list) or not instruction:
            raise ValueError('Instruction de scénario invalide.')
        op, *args = instruction
        if op == 'label':
            if len(args) != 1 or not isinstance(args[0], str) or args[0] in labels:
                raise ValueError('Étiquette absente ou dupliquée.')
            labels[args[0]] = base + len(code)
        elif op in ('goto', 'if_eq'):
            if len(args) != 1 or not isinstance(args[0], str):
                raise ValueError('Destination de branchement invalide.')
            code.extend(struct.pack('<H', 0x16 if op == 'goto' else 0x1c))
            if op == 'if_eq':
                code.append(1)
            fixups.append((len(code), args[0]))
            code.extend(b'\0' * 4)
        elif op in COMMANDS:
            opcode, fmt = COMMANDS[op]
            try:
                code.extend(struct.pack('<H' + fmt, opcode, *(number(arg) for arg in args)))
            except struct.error as error:
                raise ValueError('Arguments invalides pour ' + op) from error
        else:
            raise ValueError('Commande inconnue : ' + str(op))
    for position, label in fixups:
        if label not in labels:
            raise ValueError('Destination inconnue : ' + label)
        struct.pack_into('<i', code, position, labels[label] - (base + position + 4))
    return bytes(code), labels


def append_events(bank, entries, instructions, symbols, count):
    """Redirect selected entries; leave original code and other entries intact."""
    targets = entry_targets(bank, count)
    extra, labels = assemble(instructions, base=len(bank), symbols=symbols,
                             external_labels={f'original_{i}': p for i, p in enumerate(targets)})
    patched = bytearray(bank + extra)
    for entry, label in entries.items():
        index = int(entry)
        if not 0 <= index < count or label not in labels or labels[label] < len(bank):
            raise ValueError('Redirection de scénario invalide.')
        struct.pack_into('<i', patched, index * 4, labels[label] - (index * 4 + 4))
    return bytes(patched)
