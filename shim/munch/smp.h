#pragma once
int munch_smp_probe(void);
#ifdef MUNCH_SMP_HOLD
void munch_smp_secondary_exception(unsigned slot);
#endif
