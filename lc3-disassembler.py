#!/bin/python3
import sys, argparse, pathlib

def parse_hex(x):
    if x[0] == 'x': x = x[1:]
    return int(x, base=16)

def parse_2scompl(bits):
    if bits[0] == '1':
        return -(pow(2,len(bits)) - int(bits, 2))
    else:
        return int(bits, 2)


def decode_hex(x):
    return hex(int(x, 2))[1:]

def decode_int(bits):
    return '#{}'.format(parse_2scompl(bits))

def decode_reg(bits):
    return 'R{}'.format(int(bits, 2))

def decode_conditions(bits):
    r = ''
    if bits[0] == '1':
        r += 'n'
    if bits[1] == '1':
        r += 'z'
    if bits[2] == '1':
        r += 'p'
    return r

def decode_pcoffset(n, bits):
    return n + parse_2scompl(bits) + 1

class Asm:
    def __init__(self, location, opcode, operands = None, label = None):
        self.location = location
        self.opcode = opcode
        self.operands = operands
        self.label = label

def decode_instruction(n, i):
    if len(i) != 16:
            print("Invalid instruction length {} of '{}' on location {}!".format(len(i), i, n))
            exit()
    match i[0:4]:
        case '0001': 
            if i[10] == '1':
                return Asm(n, 'ADD', [decode_reg(i[4:7]), decode_reg(i[7:10]), decode_int(i[11:16])])
            else:
                return Asm(n, 'ADD', [decode_reg(i[4:7]), decode_reg(i[7:10]), decode_reg(i[13:16])])
        case '0101':
            if i[10] == '1':
                return Asm(n, 'AND', [decode_reg(i[4:7]), decode_reg(i[7:10]), decode_int(i[11:16])])
            else:
                return Asm(n, 'AND', [decode_reg(i[4:7]), decode_reg(i[7:10]), decode_reg(i[13:16])])
        case '1001':
            return Asm(n, 'NOT', [decode_reg(i[4:7]), decode_reg(i[7:10])])
        case '0000':
            return Asm(n, 'BR' + decode_conditions(i[4:7]), label=decode_pcoffset(n, i[7:16]))
        case '1100':
            reg = decode_reg(i[7:10])
            if reg == 'R7': 
                return Asm(n, 'RET')
            else:
                return Asm(n, 'JMP', [reg])
        case '0100': 
            if i[4] == '1':
                return Asm(n, 'JSR', label=decode_pcoffset(n, i[5:16]))
            else:
                return Asm(n, 'JSRR', [decode_reg(i[7:10])])
        case '1000':
            return Asm('RTI')
        case '1110':
            return Asm(n, 'LEA', [decode_reg(i[4:7])], decode_pcoffset(n, i[7:16]))
        case '0010':
            return Asm(n, 'LD', [decode_reg(i[4:7])], decode_pcoffset(n, i[7:16]))
        case '1010':
            return Asm(n, 'LDI', [decode_reg(i[4:7])], decode_pcoffset(n, i[7:16]))
        case '0110':
            return Asm(n, 'LDR', [decode_reg(i[4:7]), decode_reg(i[7:10])], decode_pcoffset(i[10:16]))
        case '0011':
            return Asm(n, 'ST', [decode_reg(i[4:7])], decode_pcoffset(n, i[7:16]))
        case '1011':
            return Asm(n, 'STI', [decode_reg(i[4:7])], decode_pcoffset(n, i[7:16]))
        case '0111':
            return Asm(n, 'STR', [decode_reg(i[4:7]), decode_reg(i[7:10])], decode_pcoffset(i[10:16]))
        case '1111':
            trapvec = decode_hex(i[8:16])
            shorthand = None
            match trapvec:
                case 'x20':
                    shorthand = 'GETC'
                case 'x21':
                    shorthand = 'OUT'
                case 'x22':
                    shorthand = 'PUTS'
                case 'x23':
                    shorthand = 'IN'
                case 'x24':
                    shorthand = 'PUTSP'
                case 'x25':
                    shorthand = 'HALT'
            if shorthand:
                return Asm(n, shorthand)
            else:
                return Asm(n, 'TRAP', [trapvec])
        case _:
            print("Invalid opcode or instruction '{}' on location {}!".format(i, n))
            exit()


def fill_instruction(n, i):
    return Asm(n, '.FILL', [decode_hex(i)])

def disassemble(instructions, auto_fill):
    asm_lines = []
    labels = set()
    asm_lines.append(Asm(None, '.ORIG', ['x3000']))
    n = 0
    after_halt = False
    for instr in instructions:
        if not after_halt:
            asm = decode_instruction(n, instr)
            if asm.label:
                labels.add(asm.label)
            asm_lines.append(asm)
            if asm.opcode == 'HALT' and auto_fill:
                after_halt = True
        else:
            asm_lines.append(fill_instruction(n, instr))
        n += 1

    asm_lines.append(Asm(None, '.END'))

    n = 0
    label_names = {}
    for l in sorted(list(labels)):
        label_names[l] = "LABEL{}".format(n)
        n += 1

    for asm in asm_lines:
        print(label_names[asm.location].ljust(8) if asm.location in label_names else 8 * ' ', end='') 
        print(asm.opcode.ljust(6), end='')
        params = []
        if asm.operands:
            params.extend(asm.operands)
        if asm.label:
            params.append(label_names[asm.label])
        if len(params) > 0:
            print(' ', ', '.join(params), end='')
        print('')


parser = argparse.ArgumentParser(
        prog = 'LC-3 Disassembler',
        description = 'Disassemble LC-3 machine code',
        epilog = 'By Rijk van Putten <rijk@rijkvp.nl>')
parser.add_argument('-f', '--fill', action='store_true', help='instructions after halt are interpreted as .FILL')
args = parser.parse_args()

instructions = []

for line in sys.stdin:
    if line[0] == 'x':
        instr_val = parse_hex(line)
        instructions.append("{0:b}".format(instr_val).zfill(16))
    else:
        instructions.append(line.strip())

disassemble(instructions, args.fill)
