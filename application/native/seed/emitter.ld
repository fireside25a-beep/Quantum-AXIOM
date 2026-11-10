ENTRY(_start)
PHDRS {
 text PT_LOAD FILEHDR PHDRS FLAGS(5);
 data PT_LOAD FLAGS(6);
 stack PT_GNU_STACK FLAGS(6);
}
SECTIONS {
 . = 0x400000 + SIZEOF_HEADERS;
 .text : { *(.text) *(.rodata) } :text
 . = ALIGN(4096);
 .bss (NOLOAD) : { *(.bss) } :data
 /DISCARD/ : { *(.note*) *(.comment) }
}
