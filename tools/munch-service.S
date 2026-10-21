/* Launchd stability probe: RAM file I/O, credentials and one controlled restart. */
.text
.globl _start
.p2align 2
_start:
    mov x9, sp
    and x9, x9, #~15
    mov sp, x9
    adr x0, console_path
    mov x1, #2
    mov x2, #0
    mov x16, #5
    svc #0x80
    b.cs hang
    mov x19, x0
    mov w20, #'1'
    adr x0, state_path
    mov x1, #0
    mov x2, #0
    mov x16, #5
    svc #0x80
    b.cc read_opened
    cmp x0, #2 /* ENOENT on first start */
    b.eq save_state
    b state_failed
read_opened:
    mov x22, x0
    sub sp, sp, #16
    mov x1, sp
    mov x2, #1
    mov x16, #3
    svc #0x80
    b.cs read_failed
    cmp x0, #1
    b.ne read_failed
    ldrb w20, [sp]
    cmp w20, #'1'
    b.lo bad_digit
    cmp w20, #'8'
    b.hi bad_digit
    add w20, w20, #1
    b read_done
bad_digit:
    b read_failed
read_done:
    add sp, sp, #16
    mov x0, x22
    mov x16, #6
    svc #0x80
    b save_state
read_failed:
    add sp, sp, #16
    mov x0, x22
    mov x16, #6
    svc #0x80
    b state_failed
save_state:
    adr x0, state_path
    mov x1, #0x601 /* O_WRONLY | O_CREAT | O_TRUNC */
    mov x2, #420 /* 0644 */
    mov x16, #5
    svc #0x80
    b.cs state_failed
    mov x22, x0
    sub sp, sp, #16
    strb w20, [sp]
    mov x1, sp
    mov x2, #1
    mov x16, #4
    svc #0x80
    add sp, sp, #16
    b.cs state_failed
    cmp x0, #1
    b.ne state_failed
    mov x0, x22
    mov x16, #6
    svc #0x80
    adr x1, prefix
    adr x2, prefix_end
    sub x2, x2, x1
    bl write_console
    mov x16, #20 /* getpid */
    svc #0x80
    bl print_hex
    adr x1, uid_text
    adr x2, uid_end
    sub x2, x2, x1
    bl write_console
    mov x16, #24 /* getuid */
    svc #0x80
    bl print_hex
    adr x1, generation_text
    adr x2, generation_end
    sub x2, x2, x1
    bl write_console
    sub sp, sp, #16
    strb w20, [sp]
    mov w9, #10
    strb w9, [sp, #1]
    mov x1, sp
    mov x2, #2
    bl write_console
    add sp, sp, #16
    mov x21, #0
heartbeat:
    mov x0, #0
    mov x1, #0
    mov x2, #0
    mov x3, #0
    adr x4, timeout
    mov x16, #93
    svc #0x80
    add x21, x21, #1
    adr x1, heartbeat_text
    adr x2, heartbeat_end
    sub x2, x2, x1
    bl write_console
    cmp w20, #'1'
    b.ne heartbeat
    cmp x21, #3
    b.lo heartbeat
    adr x1, restart_text
    adr x2, restart_end
    sub x2, x2, x1
    bl write_console
    mov x0, #0
    mov x16, #1
    svc #0x80
    b hang
state_failed:
    adr x1, error_text
    adr x2, error_end
    sub x2, x2, x1
    bl write_console
hang:
    mov x0, #0
    mov x1, #0
    mov x2, #0
    mov x3, #0
    mov x4, #0
    mov x16, #93 /* wait without consuming CPU on a failed probe */
    svc #0x80
    b hang
write_console:
    mov x0, x19
    mov x16, #4
    svc #0x80
    ret
print_hex:
    mov x25, x30
    mov w24, w0
    sub sp, sp, #16
    mov w10, #28
    mov x11, #0
    adr x12, hex_digits
1:
    lsr w13, w24, w10
    and w13, w13, #15
    ldrb w13, [x12, x13]
    strb w13, [sp, x11]
    add x11, x11, #1
    sub w10, w10, #4
    cmp x11, #8
    b.ne 1b
    mov x1, sp
    mov x2, #8
    bl write_console
    add sp, sp, #16
    mov x30, x25
    ret
.p2align 3
timeout:
    .quad 5, 0
console_path:
    .asciz "/dev/console"
state_path:
    .asciz "/tmp/munch-service-generation"
prefix:
    .ascii "MUNCH SERVICE: RAM I/O OK pid=0x"
prefix_end:
uid_text:
    .ascii " uid=0x"
uid_end:
generation_text:
    .ascii " generation="
generation_end:
heartbeat_text:
    .ascii "MUNCH SERVICE: heartbeat\n"
heartbeat_end:
restart_text:
    .ascii "MUNCH SERVICE: requesting one restart\n"
restart_end:
error_text:
    .ascii "MUNCH SERVICE: RAM state I/O FAILED\n"
error_end:
hex_digits:
    .ascii "0123456789abcdef"
