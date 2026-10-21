# Munch XNU0017: iOS dyld entry point correction

Photo5388958027244839062.jpg shows graphics PID3 terminated with
`main executable is missing LC_MAIN`. The managed cat job succeeds.
The graphics program did not reach its own code, so this result does not
establish whether the IOSurface implementation works on the phone.

The generated executable used LC_UNIXTHREAD. Apple's dyldMain.cpp rejects
that entry path when SUPPPORT_PRE_LC_MAIN is disabled, matching the observed
error. Replace it with LC_MAIN, entryoff0x800, stacksize0. The program never
returns and needs no startup arguments. Existing imports and drawing code
remain unchanged. Kernel CI39615713929 is reused without modification.

Image: shim/out/munch-xnu-0017/testios.img,125538304bytes,SHA256
`049d0ed6a539f9b5b71f343ca75e00a8b33c6c8c2dc255edd683dfc425d7cb5c`.

Checks pass: twelve imports resolved against the restore libraries,
LC_MAIN present with correct entry/no LC_UNIXTHREAD, all signature page
hashes, root executable extraction, boot-v3 roundtrip, RAM reservations,
loader host five alignment scenarios and eight malformed-input rejections.
No phone result yet. Expected output and failure stages follow XNU0016.

Build with tools/build-munch-graphics.sh, the XNU0016 root recipe using
0017 paths, and shim/munch/build-xnu.sh with the same CI kernel.
Temporary boot only: fastboot boot testios.img. Preserve0014.
