/*
 * First userspace program for MUNCH bring-up: mockfs serves the RAM disk
 * itself as /sbin/launchd, so this static binary is PID 1. It proves that
 * exec, the user/kernel boundary, devfs and the console all work, then
 * stays alive (init exiting panics the kernel).
 *
 * tools/mkinit.py wraps the assembled text into a static Mach-O, so this
 * must stay position independent with no relocations and no writable data:
 * every reference is adr (PC-relative), the PID digit lives on the stack.
 *
 * Raw XNU syscalls: number in x16, svc #0x80, carry set on error.
 */
#define SYS_read	3
#define SYS_write	4
#define SYS_open	5
#define SYS_getpid	20
#define SYS_select	93
#define O_RDWR		2

	.text
	.globl	_start
	.p2align 2
_start:
	/*
	 * The kernel enters a static binary with sp at argc, aligned only to
	 * what the argument/apple strings happened to need. Using a misaligned
	 * sp as a base register raises an SP alignment fault (SIGBUS) on real
	 * hardware (QEMU does not check), so align it like crt0/dyld do.
	 */
	mov	x9, sp
	and	x9, x9, #~15
	mov	sp, x9

	adr	x0, path
	mov	x1, #O_RDWR
	mov	x2, #0
	mov	x16, #SYS_open
	svc	#0x80
	b.cs	hang			/* no console: nothing to report to */
	mov	x19, x0

	adr	x1, hello
	adr	x2, hello_tail
	sub	x2, x2, x1
	bl	write_console

	mov	x16, #SYS_getpid
	svc	#0x80
	add	w0, w0, #'0'		/* PID 1 expected: one digit */
	sub	sp, sp, #16
	strb	w0, [sp]
	mov	x1, sp
	mov	x2, #1
	bl	write_console
	add	sp, sp, #16

	adr	x1, hello_tail
	adr	x2, alive
	sub	x2, x2, x1
	bl	write_console

#ifdef MUNCH_HFS_PROBE
	/* Read a separate catalog file: mockfs cannot provide this path. */
	adr x0, marker_path
	mov x1, #0
	mov x2, #0
	mov x16, #SYS_open
	svc #0x80
	b.cs marker_failed
	mov x20, x0
	sub sp, sp, #128
	mov x1, sp
	mov x2, #128
	mov x16, #SYS_read
	svc #0x80
	b.cs marker_read_failed
	cbz x0, marker_read_failed
	mov x2, x0
	mov x1, sp
	bl write_console
	add sp, sp, #128
	b marker_done
marker_read_failed:
	add sp, sp, #128
marker_failed:
	adr x1, marker_error
	adr x2, marker_error_end
	sub x2, x2, x1
	bl write_console
marker_done:
#endif

#ifdef MUNCH_LAUNCHD_PROBE
	/* Remount only our memory-backed HFS root; no phone storage driver. */
	sub sp, sp, #64
	stp xzr, xzr, [sp]
	stp xzr, xzr, [sp, #16]
	stp xzr, xzr, [sp, #32]
	stp xzr, xzr, [sp, #48]
	adr x0, hfs_type
	adr x1, root_path
	mov x2, #0x10000 /* MNT_UPDATE, without MNT_RDONLY */
	mov x3, sp
	mov x16, #167 /* mount */
	svc #0x80
	add sp, sp, #64
	bl print_status
	mov x0, x19
	mov x1, #1
	mov x16, #90
	svc #0x80
	mov x0, x19
	mov x1, #2
	mov x16, #90
	svc #0x80
	adr x1, launchd_message
	adr x2, launchd_message_end
	sub x2, x2, x1
	bl write_console
	sub sp, sp, #32
	adr x0, launchd_path
	str x0, [sp]
	str xzr, [sp, #8]
	mov x1, sp
	mov x2, #0
	mov x16, #59
	svc #0x80
	add sp, sp, #32
	bl print_status
	b tick
#endif

#ifdef MUNCH_DYLD_PROBE
	mov x21, #0
	mov x0, x19
	mov x1, #1
	mov x16, #90 /* dup2 */
	svc #0x80
	mov x0, x19
	mov x1, #2
	mov x16, #90
	svc #0x80
	mov x16, #2 /* fork: x1=1 in child */
	svc #0x80
	b.cs fork_failed
	cbnz x1, dynamic_child
	mov x21, x0
	b tick
fork_failed:
	adr x1, fork_error
	adr x2, fork_error_end
	sub x2, x2, x1
	bl write_console
	b tick
dynamic_child:
	sub sp, sp, #32
	adr x0, cat_path
	adr x9, dyld_marker_path
	stp x0, x9, [sp]
	str xzr, [sp, #16]
	mov x1, sp
	mov x2, #0
	mov x16, #59 /* execve */
	svc #0x80
	adr x1, exec_error
	adr x2, exec_error_end
	sub x2, x2, x1
	bl write_console
	mov x0, #127
	mov x16, #1 /* _exit */
	svc #0x80
	b hang
#endif

tick:
	/* select(0, NULL, NULL, NULL, &5s) as a portable sleep */
	mov	x0, #0
	mov	x1, #0
	mov	x2, #0
	mov	x3, #0
	adr	x4, five_sec
	mov	x16, #SYS_select
	svc	#0x80

#ifdef MUNCH_DYLD_PROBE
	cbz x21, wait_done
	sub sp, sp, #16
	mov x0, x21
	mov x1, sp
	mov x2, #1 /* WNOHANG */
	mov x3, #0
	mov x16, #7 /* wait4 */
	svc #0x80
	b.cs wait_pending
	cbz x0, wait_pending
	ldr w0, [sp]
	mov x21, #0
	bl print_status
wait_pending:
	add sp, sp, #16
wait_done:
#endif

	adr	x1, alive
	adr	x2, alive_end
	sub	x2, x2, x1
	bl	write_console
	b	tick

/* write(x19, x1, x2) */
write_console:
	mov	x0, x19
	mov	x16, #SYS_write
	svc	#0x80
	ret

hang:
	b	hang

	.p2align 3
five_sec:
	.quad	5			/* tv_sec */
	.quad	0			/* tv_usec (int32 + padding) */
path:
	.asciz	"/dev/console"
hello:
	.ascii	"\n*** MUNCH userspace: init running as PID "
hello_tail:
	.ascii	" ***\n"
alive:
	.ascii	"MUNCH init: still alive\n"
alive_end:

#ifdef MUNCH_HFS_PROBE
marker_path:
	.asciz "/etc/munch-release"
marker_error:
	.ascii "MUNCH HFS: marker read FAILED\n"
marker_error_end:
#endif

#if defined(MUNCH_DYLD_PROBE) || defined(MUNCH_LAUNCHD_PROBE)
/* Report raw wait status without libc; exit(0) is 00000000. */
	.p2align 2
print_status:
	mov x23, x30
	mov w24, w0
	adr x1, status_text
	adr x2, status_text_end
	sub x2, x2, x1
	bl write_console
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
	mov w13, #10
	strb w13, [sp, #8]
	mov x1, sp
	mov x2, #9
	bl write_console
	add sp, sp, #16
	mov x30, x23
	ret
cat_path:
	.asciz "/bin/cat"
dyld_marker_path:
	.asciz "/etc/munch-dyld-test"
fork_error:
	.ascii "MUNCH DYLD: fork FAILED\n"
fork_error_end:
exec_error:
	.ascii "MUNCH DYLD: execve FAILED\n"
exec_error_end:
status_text:
#ifdef MUNCH_LAUNCHD_PROBE
	.ascii "MUNCH LAUNCHD: syscall result 0x"
#else
	.ascii "MUNCH DYLD: child wait status 0x"
#endif
status_text_end:
hex_digits:
	.ascii "0123456789abcdef"
#endif

#ifdef MUNCH_LAUNCHD_PROBE
hfs_type:
	.asciz "hfs"
root_path:
	.asciz "/"
launchd_path:
	.asciz "/usr/libexec/munch-launchd"
launchd_message:
	.ascii "MUNCH LAUNCHD: exec Apple launchd as PID 1\n"
launchd_message_end:
#endif
