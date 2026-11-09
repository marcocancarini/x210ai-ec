# Tiny 8051 assembler helpers shared by the patch scripts (no external deps)


def LCALL(address): return [0x12, address >> 8, address & 255]
def LJMP(address): return [0x02, address >> 8, address & 255]
def DPTR(address): return [0x90, address >> 8, address & 255]


def assemble(items, base):
    # items are byte lists, 'label:' strings or (opcode..., 'label') tuples with a rel8 last
    labels, pc = {}, base
    for item in items:
        if isinstance(item, str):
            labels[item[:-1]] = pc
        else:
            pc += len(item)
    code, pc = [], base
    for item in items:
        if isinstance(item, str):
            continue
        pc += len(item)
        if isinstance(item, tuple):
            offset = labels[item[-1]] - pc
            assert -128 <= offset <= 127, item
            code += list(item[:-1]) + [offset & 255]
        else:
            code += item
    return bytes(code), labels
