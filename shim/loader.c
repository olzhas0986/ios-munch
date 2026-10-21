/*
 * Milestone 4: act as iBoot for xnu.
 *
 * mkpayload.py already resolved the kernel's chained fixups and built the
 * ADT, so this only has to: find the payload in the ABL ramdisk, copy the
 * segments to phys_base + (vmaddr - virt_base), place the ADT and
 * boot_args behind the kernel, and jump to the entry point with the MMU
 * and caches off, x0 = boot_args (physical).
 */
#include <stdint.h>
#include "console.h"
#include "fdt.h"
#include "loader.h"

#define BOOT_LINE_LENGTH	608
#define PAGE_16K		0x4000UL

#ifdef MUNCH_XNU
#define PAYLOAD_PACKED __attribute__((packed))
#else
#define PAYLOAD_PACKED
#endif

struct payload_seg {
	uint64_t vmaddr, vmsize, file_off, file_size;
} PAYLOAD_PACKED;

struct payload {
	char magic[8];
	uint32_t version, nsegs;
	uint64_t virt_base, entry_va, adt_off, adt_size, kernel_end;
	uint64_t phys_base, mem_size;
	char cmdline[BOOT_LINE_LENGTH];
	struct payload_seg segs[];
} PAYLOAD_PACKED;

/* pexpert/pexpert/arm64/boot.h, Revision/Version 2 */
struct boot_video {
	uint64_t v_baseAddr, v_display, v_rowBytes, v_width, v_height, v_depth;
};

struct boot_args {
	uint16_t Revision, Version;
	uint64_t virtBase, physBase, memSize, topOfKernelData;
	struct boot_video Video;
	uint32_t machineType;
	uint64_t deviceTreeP;
	uint32_t deviceTreeLength;
	char CommandLine[BOOT_LINE_LENGTH];
	uint64_t bootFlags, memSizeActual;
};

_Static_assert(__builtin_offsetof(struct payload, segs) == 0x2a8, "payload header layout");
_Static_assert(__builtin_offsetof(struct boot_args, Video) == 40, "boot_args layout");
_Static_assert(__builtin_offsetof(struct boot_args, CommandLine) == 108, "boot_args layout");
_Static_assert(sizeof(struct boot_args) == 736, "boot_args layout");

/* MMU off: everything is Device memory, so copy in aligned 8-byte words. */
static void copy64(uintptr_t dst, uintptr_t src, uint64_t n)
{
#ifdef MUNCH_XNU
	/* Boot-v3 vendor ramdisk prefixes can leave the payload byte-aligned. */
	if (src & 7) {
		volatile uint8_t *d8 = (volatile uint8_t *)dst;
		volatile const uint8_t *s8 = (volatile const uint8_t *)src;
		for (uint64_t i = 0; i < n; i++) d8[i] = s8[i];
		for (uint64_t i = n; i < ((n + 7) & ~7ULL); i++) d8[i] = 0;
		return;
	}
#endif
	volatile uint64_t *d = (volatile uint64_t *)dst;
	volatile const uint64_t *s = (volatile const uint64_t *)src;
	for (uint64_t i = 0; i < (n + 7) / 8; i++)
		d[i] = s[i];
}

static void zero64(uintptr_t dst, uint64_t n)
{
	volatile uint64_t *d = (volatile uint64_t *)dst;
	for (uint64_t i = 0; i < n / 8; i++)
		d[i] = 0;
}

static int magic_ok(const char *m)
{
	static const char want[] = "SWEETXNU";
	for (int i = 0; i < 8; i++)
		if (m[i] != want[i])
			return 0;
	return 1;
}

typedef void (*xnu_entry_t)(uint64_t boot_args_pa);

const char *loader_boot(uintptr_t dtb)
{
	uint64_t rd_start, rd_end;

	if (!fdt_chosen_u64(dtb, "linux,initrd-start", &rd_start) ||
	    !fdt_chosen_u64(dtb, "linux,initrd-end", &rd_end))
		return "no initrd in /chosen";
	con_hex2("INITRD", "lo=", rd_start, "hi=", rd_end);

#ifdef MUNCH_XNU
	if (rd_end < rd_start || rd_end - rd_start < sizeof(struct payload) ||
	    rd_end - rd_start > 128ULL * 1024 * 1024)
		return "invalid combined initrd size";
	/* ABL may concatenate vendor ramdisk and the generic boot ramdisk. */
	uint64_t original_start = rd_start;
	while (rd_start <= rd_end - sizeof(struct payload) &&
	       !magic_ok((const char *)rd_start)) rd_start++;
	if (rd_start > rd_end - sizeof(struct payload)) return "payload not found in initrd";
	con_hex("PREFIX", rd_start - original_start);
#endif
	const struct payload *p = (const struct payload *)rd_start;
	if (!magic_ok(p->magic))
		return "no SWEETXNU payload";
	if (p->version != 1 || (p->adt_off & 7)
#ifndef MUNCH_XNU
	    || (rd_start & 7)
#endif
	    )
		return "bad payload header";

#ifdef MUNCH_XNU
	/* Validate every source/destination before copying anything to upper DDR. */
	uint64_t length = rd_end - rd_start;
	if (!p->nsegs || p->nsegs > 32 || sizeof(*p) + p->nsegs * sizeof(struct payload_seg) > length ||
	    p->phys_base != 0x100000000ULL || p->mem_size != 0x100000000ULL ||
	    !p->adt_size || p->adt_size > 1024 * 1024 || p->adt_off > length ||
	    p->adt_size > length - p->adt_off || p->kernel_end < p->virt_base ||
	    p->entry_va < p->virt_base || p->entry_va >= p->kernel_end)
		return "payload bounds/profile mismatch";
	uint64_t used = p->kernel_end - p->virt_base;
	if (used > p->mem_size || p->adt_size + 2 * PAGE_16K > p->mem_size - used ||
	    (p->kernel_end & (PAGE_16K - 1)))
		return "kernel/ADT outside RAM aperture";
	for (uint32_t i = 0; i < p->nsegs; i++) {
		const struct payload_seg *s = &p->segs[i];
		if (s->vmaddr < p->virt_base || s->vmaddr - p->virt_base > used ||
		    s->vmsize > used - (s->vmaddr - p->virt_base) || (s->vmaddr & 7) ||
		    (s->vmsize & 7) || s->file_size > s->vmsize ||
		    s->file_off > length || s->file_size > length - s->file_off)
			return "segment outside payload/RAM";
	}
#endif
	uint64_t pa_of_va_base = p->phys_base - p->virt_base;	/* pa = va + this */
	con_hex2("PHYS", "base=", p->phys_base, "size=", p->mem_size);
	con_hex("VIRT", p->virt_base);
	con_hex("ENTRY", p->entry_va);

	/* The payload must not overlap where the kernel goes. */
	if (rd_end > p->phys_base && rd_start < p->phys_base + p->mem_size)
		return "ramdisk overlaps kernel memory";

	for (uint32_t i = 0; i < p->nsegs; i++) {
		const struct payload_seg *s = &p->segs[i];
		uintptr_t dst = s->vmaddr + pa_of_va_base;
		copy64(dst, rd_start + s->file_off, s->file_size);
		if (s->vmsize > s->file_size)
			zero64(dst + ((s->file_size + 7) & ~7UL), s->vmsize - ((s->file_size + 7) & ~7UL));
	}
	con_hex2("SEGS", "n=", p->nsegs, "end=", p->kernel_end + pa_of_va_base);

	/* ADT, then boot_args, behind the kernel; everything below topOfKernelData is ours. */
	uintptr_t adt_pa = p->kernel_end + pa_of_va_base;
	copy64(adt_pa, rd_start + p->adt_off, p->adt_size);
	uintptr_t ba_pa = (adt_pa + p->adt_size + PAGE_16K - 1) & ~(PAGE_16K - 1);
	uintptr_t top = ba_pa + PAGE_16K;

	zero64(ba_pa, PAGE_16K);
	volatile struct boot_args *ba = (volatile struct boot_args *)ba_pa;
	ba->Revision = 2;
	ba->Version = 2;
	ba->virtBase = p->virt_base;
	ba->physBase = p->phys_base;
	ba->memSize = p->mem_size;
	ba->topOfKernelData = top;
	ba->Video.v_baseAddr = FB_BASE;
	ba->Video.v_display = 1;
	ba->Video.v_rowBytes = FB_STRIDE;
	ba->Video.v_width = FB_W;
	ba->Video.v_height = FB_H;
	ba->Video.v_depth = 32;
	ba->deviceTreeP = adt_pa - pa_of_va_base;	/* xnu reads it with the MMU on: a VA */
	ba->deviceTreeLength = (uint32_t)p->adt_size;
	for (int i = 0; i < BOOT_LINE_LENGTH; i++)
		ba->CommandLine[i] = p->cmdline[i];
	ba->memSizeActual = p->mem_size;
	con_hex2("BOOTARG", "pa=", ba_pa, "top=", top);

	uintptr_t entry_pa = p->entry_va + pa_of_va_base;
	con_hex("JUMP", entry_pa);
	con_str("XNU", "jumping (fbcon clears screen)");

	/* Everything was written with the MMU and caches off; drop any stale I-cache lines too. */
	__asm__ volatile("dsb sy; ic iallu; dsb sy; isb" ::: "memory");
	((xnu_entry_t)entry_pa)(ba_pa);
	return "xnu returned";
}
