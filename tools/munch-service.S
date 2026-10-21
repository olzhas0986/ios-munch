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
#ifdef MUNCH_SYSLOG_PROBE
    mov x26, #0
#endif
heartbeat:
    mov x0, #0
    mov x1, #0
    mov x2, #0
    mov x3, #0
    adr x4, timeout
    mov x16, #93
    svc #0x80
    add x21, x21, #1
#ifdef MUNCH_SYSLOG_PROBE
    bl syslog_probe
#endif
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

#ifdef MUNCH_SYSLOG_PROBE
.p2align 2
/* AF_UNIX datagram -> Apple syslogd -> a file containing our unique token. */
syslog_probe:
    mov x28, x30
    cmp x26, #2
    b.eq syslog_return
    cbnz x26, syslog_read
    mov x0, #1 /* AF_UNIX */
    mov x1, #2 /* SOCK_DGRAM */
    mov x2, #0
    mov x16, #97 /* socket */
    svc #0x80
    b.cs syslog_return
    mov x22, x0
    adr x1, syslog_address
    mov x2, #(syslog_address_end - syslog_address)
    mov x16, #98 /* connect */
    svc #0x80
    b.cs syslog_close_socket
    mov x0, x22
    adr x1, syslog_message
    mov x2, #(syslog_message_end - syslog_message)
    mov x16, #4 /* datagram write */
    svc #0x80
    b.cs syslog_close_socket
    cmp x0, #(syslog_message_end - syslog_message)
    b.ne syslog_close_socket
    mov x26, #1
    adr x1, syslog_sent
    adr x2, syslog_sent_end
    sub x2, x2, x1
    bl write_console
syslog_close_socket:
    mov x0, x22
    mov x16, #6
    svc #0x80
    cbz x26, syslog_return
syslog_read:
    adr x0, syslog_file
    mov x1, #0
    mov x2, #0
    mov x16, #5
    svc #0x80
    b.cs syslog_return
    mov x22, x0
    sub sp, sp, #512
    mov x1, sp
    mov x2, #512
    mov x16, #3
    svc #0x80
    b.cs syslog_read_done
    mov x27, x0
    cmp x27, #(syslog_token_end - syslog_token)
    b.lo syslog_read_done
    sub x12, x27, #(syslog_token_end - syslog_token)
    add x12, x12, #1
    mov x9, #0
syslog_scan:
    adr x10, syslog_token
    mov x11, #0
syslog_compare:
    add x13, x9, x11
    ldrb w14, [sp, x13]
    ldrb w15, [x10, x11]
    cmp w14, w15
    b.ne syslog_next
    add x11, x11, #1
    cmp x11, #(syslog_token_end - syslog_token)
    b.ne syslog_compare
    mov x26, #2
    adr x1, syslog_ok
    adr x2, syslog_ok_end
    sub x2, x2, x1
    bl write_console
    b syslog_read_done
syslog_next:
    add x9, x9, #1
    cmp x9, x12
    b.lo syslog_scan
syslog_read_done:
    add sp, sp, #512
    mov x0, x22
    mov x16, #6
    svc #0x80
syslog_return:
    mov x30, x28
    ret
syslog_address:
    .byte syslog_address_end - syslog_address, 1
    .asciz "/var/run/munch-syslog.sock"
syslog_address_end:
syslog_message:
    .ascii "<13>Oct 21 00:00:00 munch munch-probe: MUNCH_SYSLOG_PIPELINE_OK\n"
syslog_message_end:
syslog_file:
    .asciz "/var/log/munch-syslog.log"
syslog_token:
    .ascii "MUNCH_SYSLOG_PIPELINE_OK"
syslog_token_end:
syslog_sent:
    .ascii "MUNCH SYSLOG: datagram sent\n"
syslog_sent_end:
syslog_ok:
    .ascii "MUNCH SYSLOG: daemon wrote token OK\n"
syslog_ok_end:
#endif
