# Munch XNU0011: DEVELOPMENT iOS binary launch

XNU0010 photo 5388958027244838697.jpg shows HFS root and PID1 working,
but child PID2 exits with raw wait status 0x00000009 (SIGKILL). There is
no successful cat output. PID1 remains alive. The photo alone does not
provide the kernel exit-reason namespace/code.

Offline, /bin/cat has LC_BUILD_VERSION platform 2 (iOS). The shared early
kernel uses XNU_TARGET_OS_OSX. Its kern_exec.c rejects iOS binaries without
spawn platform attributes or the DEVELOPMENT unentitled_ios_sim_launch
boot argument (EXEC_EXIT_REASON_WRONG_PLATFORM). Upstream historical
notes record this same boundary. XNU0011 adds unentitled_ios_sim_launch=1
to exercise the existing DEVELOPMENT path; kernel and root files are unchanged.
This is a targeted hypothesis to confirm on the phone, not a claim that
all possible SIGKILL causes have been eliminated.

```sh
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0010/root.hfs
```

Output: shim/out/munch-xnu-0011/testios.img,33206272 bytes,SHA256
`28cfdb92accbf27dfc2b0aaaab5e6a2e1f13495615c187c92800efcda075513f`.
Boot roundtrip, packed boot-argument contents, cross-build, RAM audit,
loader host cases and repository validation pass. No physical 0011 result yet.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0011\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Capture the Allowing spawn of iOS binary line and subsequent child output,
wait status, dyld error or panic. Temporary boot only.
