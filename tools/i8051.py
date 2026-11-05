#!/usr/bin/env python3
# Minimal Intel 8051 disassembler (no external deps)
import sys

# opcode table: opcode -> (mnemonic, operand_fmt, len)
# operand_fmt: '' none, 'a' A, 'r' Rn, 'd' direct, 'i' #imm, 'b' bit addr,
# 'rel' rel8, 'addr11' 11-bit, 'addr16' 16-bit
def T(m, f='', l=1): return (m, f, l)

OPS = {}
def defop(start, end, m, f='', l=1):
    for o in range(start, end+1): OPS[o] = (m, f, l)

defop(0x00,0x00,'NOP'); defop(0x01,0x07,'AJMP','addr11',2)
defop(0x02,0x02,'LJMP','addr16',3); defop(0x03,0x03,'RR','A'); defop(0x04,0x04,'INC','A')
defop(0x05,0x05,'INC','d',2); defop(0x06,0x07,'INC','r',1)
defop(0x08,0x0F,'INC','r',1); defop(0x10,0x10,'JBC','b_rel',3); defop(0x11,0x11,'ACALL','addr11',2)
defop(0x12,0x12,'LCALL','addr16',3); defop(0x13,0x13,'RRC','A'); defop(0x14,0x14,'DEC','A')
defop(0x15,0x15,'DEC','d',2); defop(0x16,0x1F,'DEC','r',1); defop(0x20,0x20,'JB','b_rel',3); defop(0x21,0x21,'AJMP','addr11',2)
defop(0x22,0x22,'RET'); defop(0x23,0x23,'RL','A'); defop(0x24,0x24,'ADD','A_i',2); defop(0x25,0x25,'ADD','A_d',2)
defop(0x26,0x27,'ADD','A_r',1); defop(0x28,0x2F,'ADD','A_r',1); defop(0x30,0x30,'JNB','b_rel',3)
defop(0x31,0x31,'ACALL','addr11',2); defop(0x32,0x32,'RETI'); defop(0x33,0x33,'RLC','A'); defop(0x34,0x34,'ADDC','A_i',2)
defop(0x35,0x35,'ADDC','A_d',2); defop(0x36,0x37,'ADDC','A_r',1); defop(0x38,0x3F,'ADDC','A_r',1)
defop(0x40,0x40,'JC','rel',2); defop(0x41,0x41,'AJMP','addr11',2); defop(0x42,0x42,'ORL','d_A',2); defop(0x43,0x43,'ORL','d_i',3)
defop(0x44,0x44,'ORL','A_i',2); defop(0x45,0x45,'ORL','A_d',2); defop(0x46,0x47,'ORL','A_r',1); defop(0x48,0x4F,'ORL','A_r',1)
defop(0x50,0x50,'JNC','rel',2); defop(0x51,0x51,'ACALL','addr11',2); defop(0x52,0x52,'ANL','d_A',2); defop(0x53,0x53,'ANL','d_i',3)
defop(0x54,0x54,'ANL','A_i',2); defop(0x55,0x55,'ANL','A_d',2); defop(0x56,0x57,'ANL','A_r',1); defop(0x58,0x5F,'ANL','A_r',1)
defop(0x60,0x60,'JZ','rel',2); defop(0x61,0x61,'AJMP','addr11',2); defop(0x62,0x62,'XRL','d_A',2); defop(0x63,0x63,'XRL','d_i',3)
defop(0x64,0x64,'XRL','A_i',2); defop(0x65,0x65,'XRL','A_d',2); defop(0x66,0x67,'XRL','A_r',1); defop(0x68,0x6F,'XRL','A_r',1)
defop(0x70,0x70,'JNZ','rel',2); defop(0x71,0x71,'ACALL','addr11',2); defop(0x72,0x72,'ORL','C_b',2); defop(0x73,0x73,'JMP','@A+DPTR')
defop(0x74,0x74,'MOV','A_i',2); defop(0x75,0x75,'MOV','d_i',3); defop(0x76,0x77,'MOV','r_i',2); defop(0x78,0x7F,'MOV','r_i',2)
defop(0x80,0x80,'SJMP','rel',2); defop(0x81,0x81,'AJMP','addr11',2); defop(0x82,0x82,'ANL','C_b',2)
defop(0x83,0x83,'MOVC','A_@A+PC'); defop(0x84,0x84,'MOVC','A_@A+DPTR'); defop(0x85,0x85,'MOV','d_d',3)
defop(0x86,0x87,'MOV','d_r',2); defop(0x88,0x8F,'MOV','d_r',2)
defop(0x90,0x90,'MOV','DPTR_i',3); defop(0x91,0x91,'ACALL','addr11',2); defop(0x92,0x92,'MOV','b_C',2)
defop(0x93,0x93,'MOVC','A_@A+DPTR'); defop(0x94,0x94,'SUBB','A_i',2); defop(0x95,0x95,'SUBB','A_d',2)
defop(0x96,0x97,'SUBB','A_r',1); defop(0x98,0x9F,'SUBB','A_r',1)
defop(0xA0,0xA0,'ORL','C_b',2); defop(0xA1,0xA1,'AJMP','addr11',2); defop(0xA2,0xA2,'MOV','C_b',2); defop(0xA3,0xA3,'INC','DPTR')
defop(0xA4,0xA4,'MUL','AB'); defop(0xA5,0xA5,'RESERVED'); defop(0xA6,0xA7,'MOV','r_d',2); defop(0xA8,0xAF,'MOV','r_d',2)
defop(0xB0,0xB0,'ANL','C_b',2); defop(0xB1,0xB1,'ACALL','addr11',2); defop(0xB2,0xB2,'CPL','b',2)
defop(0xB3,0xB3,'CPL','C'); defop(0xB4,0xB4,'CJNE','A_i_rel',3); defop(0xB5,0xB5,'CJNE','A_d_rel',3)
defop(0xB6,0xB7,'CJNE','r_i_rel',3); defop(0xB8,0xBF,'CJNE','r_i_rel',3)
defop(0xC0,0xC0,'PUSH','d',2); defop(0xC1,0xC1,'AJMP','addr11',2); defop(0xC2,0xC2,'CLR','b',2); defop(0xC3,0xC3,'CLR','C')
defop(0xC4,0xC4,'SWAP','A'); defop(0xC5,0xC5,'XCH','A_d',2); defop(0xC6,0xC7,'XCH','A_r',1); defop(0xC8,0xCF,'XCH','A_r',1)
defop(0xD0,0xD0,'POP','d',2); defop(0xD1,0xD1,'ACALL','addr11',2); defop(0xD2,0xD2,'SETB','b',2); defop(0xD3,0xD3,'SETB','C')
defop(0xD4,0xD4,'DA','A'); defop(0xD5,0xD5,'DJNZ','d_rel',3); defop(0xD6,0xD7,'XCHD','A_r',1); defop(0xD8,0xDF,'DJNZ','r_rel',2)
defop(0xE0,0xE0,'MOVX','A_@DPTR'); defop(0xE1,0xE1,'AJMP','addr11',2); defop(0xE2,0xE3,'MOVX','A_@r',1)
defop(0xE4,0xE4,'CLR','A'); defop(0xE5,0xE5,'MOV','A_d',2); defop(0xE6,0xE7,'MOV','A_r',1); defop(0xE8,0xEF,'MOV','A_r',1)
defop(0xF0,0xF0,'MOVX','@DPTR_A'); defop(0xF1,0xF1,'ACALL','addr11',2); defop(0xF2,0xF3,'MOVX','@r_A',1)
defop(0xF4,0xF4,'CPL','A'); defop(0xF5,0xF5,'MOV','d_A',2); defop(0xF6,0xF7,'MOV','r_A',1); defop(0xF8,0xFF,'MOV','r_A',1)

def reg(op):
    # opcodes with low nibble 6 or 7 use indirect @R0/@R1, the others R0-R7
    return f'@R{op & 1}' if op & 0xF in (6, 7) else f'R{op & 7}'

def disasm(data, base, start, end, out):
    pc = start
    while pc < end:
        off = pc - base
        op = data[off]
        if op not in OPS:
            out.append(f'{pc:04X}: {op:02X}        ???')
            pc += 1
            continue
        m, f, l = OPS[op]
        raw = data[off:off+l]
        args = ''
        if f == 'addr16':
            args = f'0x{(raw[1]<<8)|raw[2]:04X}'
        elif f == 'addr11':
            a = ((op & 0xE0) << 3) | raw[1] | (0)  # high bits from opcode + low 8
            # for AJMP/ACALL: addr = ((op&0xE0)<<3) | raw[1]; page from pc
            a = (((pc+2) & 0xF800) | ((op & 0xE0) << 3) | raw[1])
            args = f'0x{a:04X}'
        elif f == 'rel':
            r = raw[1] if raw[1] < 128 else raw[1]-256
            args = f'0x{(pc+2+r) & 0xFFFF:04X}'
        elif f == 'b_rel':
            r = raw[2] if raw[2] < 128 else raw[2]-256
            args = f'0x{raw[1]:02X}, 0x{(pc+3+r)&0xFFFF:04X}'
        elif f == 'b':
            args = f'0x{raw[1]:02X}'
        elif f == 'd':
            args = f'0x{raw[1]:02X}'
        elif f == 'i':
            args = f'#0x{raw[1]:02X}'
        elif f == 'r':
            args = f'{reg(op)}'
        elif f == 'A':
            args = 'A'
        elif f == 'C':
            args = 'C'
        elif f == 'A_i':
            args = f'A, #0x{raw[1]:02X}'
        elif f == 'A_d':
            args = f'A, 0x{raw[1]:02X}'
        elif f == 'A_r':
            args = f'A, {reg(op)}'
        elif f == 'd_A':
            args = f'0x{raw[1]:02X}, A'
        elif f == 'd_i':
            args = f'0x{raw[1]:02X}, #0x{raw[2]:02X}'
        elif f == 'd_d':
            args = f'0x{raw[2]:02X}, 0x{raw[1]:02X}'
        elif f == 'd_r':
            args = f'0x{raw[1]:02X}, {reg(op)}'
        elif f == 'r_i':
            args = f'{reg(op)}, #0x{raw[1]:02X}'
        elif f == 'r_d':
            args = f'{reg(op)}, 0x{raw[1]:02X}'
        elif f == 'r_A':
            args = f'{reg(op)}, A'
        elif f == 'r_rel':
            r = raw[1] if raw[1] < 128 else raw[1]-256
            args = f'{reg(op)}, 0x{(pc+2+r)&0xFFFF:04X}'
        elif f == 'd_rel':
            r = raw[2] if raw[2] < 128 else raw[2]-256
            args = f'0x{raw[1]:02X}, 0x{(pc+3+r)&0xFFFF:04X}'
        elif f == 'A_i_rel':
            r = raw[2] if raw[2] < 128 else raw[2]-256
            args = f'A, #0x{raw[1]:02X}, 0x{(pc+3+r)&0xFFFF:04X}'
        elif f == 'A_d_rel':
            r = raw[2] if raw[2] < 128 else raw[2]-256
            args = f'A, 0x{raw[1]:02X}, 0x{(pc+3+r)&0xFFFF:04X}'
        elif f == 'r_i_rel':
            r = raw[2] if raw[2] < 128 else raw[2]-256
            args = f'{reg(op)}, #0x{raw[1]:02X}, 0x{(pc+3+r)&0xFFFF:04X}'
        elif f == 'DPTR_i':
            args = f'#0x{(raw[1]<<8)|raw[2]:04X}'
        elif f == 'b_C':
            args = f'0x{raw[1]:02X}, C'
        elif f == 'C_b':
            args = f'C, 0x{raw[1]:02X}'
        elif f == 'A_@A+PC':
            args = 'A+PC'
        elif f == 'A_@A+DPTR':
            args = 'A+DPTR'
        elif f == 'A_@DPTR':
            args = '@DPTR'
        elif f == 'A_@r':
            args = f'@R{op & 1}'
        elif f == '@DPTR_A':
            args = '@DPTR, A'
        elif f == '@r_A':
            args = f'@R{op & 1}, A'
        elif f == 'AB':
            args = 'AB'
        elif f == '@A+DPTR':
            args = '@A+DPTR'
        hexb = ' '.join(f'{b:02X}' for b in raw)
        out.append(f'{pc:04X}: {hexb:<8}  {m} {args}'.rstrip())
        pc += l

if __name__ == '__main__':
    path = sys.argv[1]
    base = int(sys.argv[2], 16)
    start = int(sys.argv[3], 16)
    end = int(sys.argv[4], 16)
    data = open(path, 'rb').read()
    out = []
    disasm(data, base, start, end, out)
    print('\n'.join(out))
