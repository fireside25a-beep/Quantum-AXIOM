#!/usr/bin/env python3
"""Stage-0 constructor for ANF64; subsequent compiler generations are native.

The production compiler is compiler.anf, written in the language it compiles.
This independent constructor is kept for bootstrap provenance and comparison.
"""
from pathlib import Path
import argparse
import struct

ARITY={'label':1,'code':0,'bss':0,'space':1,'db':1,'dq':1,
       'imm':2,'addr':2,'mov':2,'add':2,'sub':2,'xor':2,'and':2,'or':2,'cmp':2,'test':2,
       'load':2,'load8':2,'store':2,'store8':2,'shl':2,'shr':2,'sar':2,'mul':2,
       'div':1,'not':1,'neg':1,'inc':1,'dec':1,'push':1,'pop':1,
       'jmp':1,'call':1,'jz':1,'jnz':1,'jb':1,'jae':1,'jbe':1,'ja':1,'jl':1,'jge':1,'jle':1,'jg':1,
       'ret':0,'syscall':0,'cpuid':0,'rdseed':1}
BRANCH={'jz':0x84,'jnz':0x85,'jb':0x82,'jae':0x83,'jbe':0x86,'ja':0x87,
        'jl':0x8c,'jge':0x8d,'jle':0x8e,'jg':0x8f}
BIN={'mov':0x89,'add':0x01,'sub':0x29,'xor':0x31,'and':0x21,'or':0x09,'cmp':0x39,'test':0x85}

def integer(s):
    n=int(s,10)
    if not -(1<<63)<=n<1<<64:raise ValueError('integer overflow')
    return n&((1<<64)-1)

def reg(s):
    n=integer(s)
    if n>15:raise ValueError('invalid register')
    return n

def assemble(source):
    raw=source.encode('ascii')
    if len(raw)>262144:raise ValueError('oversized source')
    tokens=[]
    for line in source.splitlines():tokens.extend(line.split('#',1)[0].split())
    if any(len(s)>63 for s in tokens):raise ValueError('oversized token')
    program=[];i=0
    while i<len(tokens):
        op=tokens[i];i+=1
        if op not in ARITY:raise ValueError('unknown instruction '+op)
        n=ARITY[op]
        if i+n>len(tokens):raise ValueError('missing operands')
        program.append((op,tokens[i:i+n]));i+=n
    symbols={}
    for phase in (0,1):
        output=bytearray();bss=0;section=0
        def emit(data):
            if section:raise ValueError('instruction in bss')
            if len(output)+len(data)>1048576-4096:raise ValueError('code overflow')
            output.extend(data)
        def address(name):
            if name not in symbols:
                if phase:raise ValueError('undefined symbol '+name)
                return 0
            return symbols[name]
        for op,a in program:
            if op=='label':
                value=0x800000+bss if section else 0x401000+len(output)
                if phase:
                    if symbols.get(a[0])!=value:raise ValueError('inconsistent symbol')
                else:
                    if a[0] in symbols or len(symbols)>=4096:raise ValueError('duplicate/too many symbols')
                    symbols[a[0]]=value
                continue
            if op in ('code','bss'):section=int(op=='bss');continue
            if op=='space':
                n=integer(a[0])
                if not section or bss+n>8388608:raise ValueError('bss overflow')
                bss+=n;continue
            if op=='db':
                n=integer(a[0])
                if n>255:raise ValueError('invalid byte')
                emit(bytes([n]));continue
            if op=='dq':emit(struct.pack('<Q',integer(a[0])));continue
            if op in ('imm','addr'):
                d=reg(a[0]);v=integer(a[1]) if op=='imm' else address(a[1])
                emit(bytes([0x48|(d>>3),0xb8+(d&7)])+struct.pack('<Q',v));continue
            if op in BIN:
                d,s=map(reg,a);emit(bytes([0x48|((s>>3)<<2)|(d>>3),BIN[op],0xc0|((s&7)<<3)|(d&7)]));continue
            if op in ('load','load8','store','store8'):
                x,y=map(reg,a);base,d=(y,x) if op.startswith('load') else (x,y)
                prefix=0x48|((d>>3)<<2)|(base>>3)
                opcode=bytes([0x0f,0xb6]) if op=='load8' else bytes([0x8b if op=='load' else 0x88 if op=='store8' else 0x89])
                emit(bytes([prefix])+opcode+bytes([0x80|((d&7)<<3)|(base&7)])+(b'\x24' if base&7==4 else b'')+b'\0'*4);continue
            if op=='mul':
                d,s=map(reg,a);emit(bytes([0x48|((d>>3)<<2)|(s>>3),0x0f,0xaf,0xc0|((d&7)<<3)|(s&7)]));continue
            if op in ('shl','shr','sar'):
                d=reg(a[0]);n=integer(a[1])
                if n>63:raise ValueError('shift out of range')
                emit(bytes([0x48|(d>>3),0xc1,0xc0|({'shl':4,'shr':5,'sar':7}[op]<<3)|(d&7),n]));continue
            if op in ('div','not','neg','inc','dec','rdseed'):
                d=reg(a[0]);group={'div':6,'not':2,'neg':3,'inc':0,'dec':1,'rdseed':7}[op]
                opcode=b'\x0f\xc7' if op=='rdseed' else bytes([0xff if op in ('inc','dec') else 0xf7])
                emit(bytes([0x48|(d>>3)])+opcode+bytes([0xc0|(group<<3)|(d&7)]));continue
            if op in ('push','pop'):
                d=reg(a[0]);emit((b'\x41' if d>=8 else b'')+bytes([(0x50 if op=='push' else 0x58)+(d&7)]));continue
            if op in BRANCH or op in ('jmp','call'):
                prefix=bytes([0x0f,BRANCH[op]]) if op in BRANCH else bytes([0xe9 if op=='jmp' else 0xe8])
                delta=address(a[0])-(0x401000+len(output)+len(prefix)+4)
                emit(prefix+struct.pack('<i',delta));continue
            emit({'ret':b'\xc3','syscall':b'\x0f\x05','cpuid':b'\x0f\xa2'}[op])
    if not output:raise ValueError('empty program')
    image=bytearray(4096)+output
    image[:16]=b'\x7fELF'+bytes([2,1,1,0])+bytes(8)
    struct.pack_into('<HHIQQQIHHHHHH',image,16,2,62,1,0x401000,64,0,0,64,56,3,0,0,0)
    struct.pack_into('<IIQQQQQQ',image,64,1,5,0,0x400000,0x400000,len(image),len(image),4096)
    struct.pack_into('<IIQQQQQQ',image,120,1,6,0,0x800000,0x800000,0,max(bss,4096),4096)
    struct.pack_into('<IIQQQQQQ',image,176,0x6474e551,6,0,0,0,0,0,16)
    return bytes(image)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();a.output.write_bytes(assemble(a.source.read_text(encoding='ascii')));a.output.chmod(0o755)
