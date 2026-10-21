#include <stdint.h>
#include "guard.h"

static uint32_t be32(const unsigned char *p)
{
    return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 |
           (uint32_t)p[2] << 8 | p[3];
}

static int eq(const unsigned char *p, size_t n, const char *s)
{
    size_t i = 0;
    while (i < n && s[i] && p[i] == (unsigned char)s[i]) i++;
    return i < n && !s[i] && !p[i];
}

int munch_splash_allowed(const void *dtb, size_t available)
{
    const unsigned char *b = dtb;
    if (!b || available < 40 || be32(b) != 0xd00dfeed) return 0;
    size_t total = be32(b + 4), pos = be32(b + 8), strings = be32(b + 12);
    size_t ns = be32(b + 32), structure = be32(b + 36);
    if (total > available || total < 40 || pos < 40 || pos > total ||
        strings < 40 || strings > total || ns > total - strings ||
        structure > total - pos) return 0;
    size_t end = pos + structure;
    int depth = 0, reserved = 0, splash = 0, board_ok = 0, region_ok = 0;
    while (pos <= end && end - pos >= 4) {
        uint32_t token = be32(b + pos); pos += 4;
        if (token == 1) {
            size_t name = pos;
            while (pos < end && b[pos]) pos++;
            if (pos == end || depth >= 64) return 0;
            depth++;
            if (depth == 2) reserved = eq(b + name, pos - name + 1, "reserved-memory");
            if (depth == 3 && reserved)
                splash = eq(b + name, pos - name + 1, "cont_splash_region@9c000000");
            pos = (pos + 4) & ~(size_t)3;
        } else if (token == 2) {
            if (!depth) return 0;
            if (depth == 3) splash = 0;
            if (depth == 2) reserved = 0;
            depth--;
        } else if (token == 3) {
            if (!depth || end - pos < 8) return 0;
            size_t len = be32(b + pos), noff = be32(b + pos + 4); pos += 8;
            if (len > end - pos || noff >= ns) return 0;
            size_t n = noff;
            while (n < ns && b[strings + n]) n++;
            if (n == ns) return 0;
            const unsigned char *name = b + strings + noff;
            size_t namesize = n - noff + 1;
            if (depth == 1 && eq(name, namesize, "qcom,board-id"))
                board_ok = len == 8 && be32(b + pos) == 0x32 && !be32(b + pos + 4);
            if (depth == 3 && reserved && splash && eq(name, namesize, "reg"))
                region_ok = len == 16 && !be32(b + pos) &&
                    be32(b + pos + 4) == 0x9c000000 && !be32(b + pos + 8) &&
                    be32(b + pos + 12) >= 1080U * 2400U * 4U;
            pos = (pos + len + 3) & ~(size_t)3;
        } else if (token == 9) {
            return depth == 0 && board_ok && region_ok;
        } else if (token != 4) return 0;
    }
    return 0;
}
