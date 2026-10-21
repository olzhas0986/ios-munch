#pragma once
#include <stddef.h>
/* Only allow the splash experiment on the identified board/reservation. */
int munch_splash_allowed(const void *dtb, size_t available);
