/* Native IOKit/IOSurface userland probe. Import layout: mkmunchgraphics.py. */
.text
.globl _start
.p2align 2
_start:
.Lbase:
    mov x9, sp
    and x9, x9, #~15
    mov sp, x9
    sub sp, sp, #128
    adr x0, console_path
    mov x1, #2
    mov x2, #0
    mov x16, #5
    svc #0x80
    b.cs hang
    mov x19, x0
    mov x26, #1
    adr x1, finding
    adr x2, finding_end
    sub x2, x2, x1
    bl write_console
    adr x0, class_name
    bl call_matching
    cbz x0, failed
    mov x1, x0
    mov x0, #0
    bl call_service
    cbz x0, failed
    mov x26, #2
    adr x9, .Lbase + 0x3800 + 2*8
    ldr x9, [x9]
    ldr w1, [x9] /* imported mach_task_self_ data symbol */
    mov x2, #0
    add x3, sp, #16
    bl call_open
    cbnz w0, failed
    ldr w20, [sp, #16]
    mov x26, #3
    stp xzr, xzr, [sp, #32]
    mov w9, #1
    str w9, [sp, #24]
    mov w0, w20
    mov x1, #3 /* GetLayerDefaultSurface */
    add x2, sp, #32
    mov x3, #2
    add x4, sp, #64
    add x5, sp, #24
    bl call_scalar
    cbnz w0, failed
    ldr w0, [sp, #64]
    mov x26, #4
    bl call_lookup
    cbz x0, failed
    mov x21, x0
    mov x26, #5
    bl call_width
    cmp x0, #1080
    b.ne failed
    mov x0, x21
    bl call_height
    cmp x0, #2400
    b.ne failed
    mov x0, x21
    bl call_stride
    mov x23, x0
    mov x9, #4320
    cmp x0, x9
    b.ne failed
    mov x0, x21
    bl call_base
    cbz x0, failed
    mov x22, x0
    adr x1, mapped
    adr x2, mapped_end
    sub x2, x2, x1
    bl write_console
    mov x24, #0
frame:
    mov x26, #6
    mov x0, x21
    mov x1, #0
    mov x2, #0
    bl call_lock
    cbnz w0, failed
    mov x9, #1700
    madd x9, x9, x23, x22
    mov x10, #240
row:
    mov x11, #0
pixel:
    mov w12, #0xff0000
    cmp x11, #360
    b.lo color
    mov w12, #0xff00
    cmp x11, #720
    b.lo color
    mov w12, #0xff
color:
    cbz x24, store
    eor w12, w12, #0x00ffffff
store:
    str w12, [x9, x11, lsl #2]
    add x11, x11, #1
    cmp x11, #1080
    b.lo pixel
    add x9, x9, x23
    subs x10, x10, #1
    b.ne row
    mov x0, x21
    mov x1, #0
    mov x2, #0
    bl call_unlock
    cbnz w0, failed
    eor x24, x24, #1
    mov x0, #0
    mov x1, #0
    mov x2, #0
    mov x3, #0
    adr x4, timeout
    mov x16, #93
    svc #0x80
    b frame
failed:
    adr x1, error_text
    adr x2, error_end
    sub x2, x2, x1
    bl write_console
    /* Stage is one digit, keeping failures readable without libc. */
    add w9, w26, #'0'
    strb w9, [sp, #96]
    mov w9, #10
    strb w9, [sp, #97]
    add x1, sp, #96
    mov x2, #2
    bl write_console
hang:
    mov x0, #0
    mov x1, #0
    mov x2, #0
    mov x3, #0
    mov x4, #0
    mov x16, #93
    svc #0x80
    b hang
write_console:
    mov x0, x19
    mov x16, #4
    svc #0x80
    ret
.macro import_call name, slot
\name:
    adr x9, .Lbase + 0x3800 + \slot*8
    ldr x9, [x9]
    br x9
.endm
import_call call_matching, 0
import_call call_service, 1
import_call call_open, 3
import_call call_scalar, 4
import_call call_lookup, 5
import_call call_lock, 6
import_call call_base, 7
import_call call_width, 8
import_call call_height, 9
import_call call_stride, 10
import_call call_unlock, 11
.p2align 3
timeout:
    .quad 2, 0
console_path:
    .asciz "/dev/console"
class_name:
    .asciz "AppleCLCD"
finding:
    .ascii "MUNCH GRAPHICS: finding AppleCLCD\n"
finding_end:
mapped:
    .ascii "MUNCH GRAPHICS: IOSurface mapped 1080x2400; drawing bands\n"
mapped_end:
error_text:
    .ascii "MUNCH GRAPHICS: failed at stage "
error_end:
