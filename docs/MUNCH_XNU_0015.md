# Munch XNU0015: Apple syslogd and local message delivery

XNU0014 confirmed launchd restart, UID0 and RAM state generation2. The user
prefers continuing with screen photos; no host communication channel is
required. This image adds a useful real daemon, the Apple restore syslogd.

The same official restore dependency extractor stages /usr/sbin/syslogd
alongside launchd/xpcproxy. The closure contains87 plain ARM64 files,
101552464 bytes; strong dependencies are present. Apple inputs remain
ignored. Kernel and bootstrap executable are unchanged.

The launchd job supplies com.apple.system.logger, ASL_DISABLE=1 to prevent
recursive library logging, console diagnostics and a NetworkListener socket.
The listener is a local AF_UNIX datagram socket at
/var/run/munch-syslog.sock, not a network listener exposed to other hosts.
Apple's input module accepts launchd-supplied descriptors and parses the
BSD syslog text. An ASL rule selects Sender=munch-probe and writes raw
messages to /var/log/munch-syslog.log on the RAM root.

The service variant retries a local socket connection, sends one unique
MUNCH_SYSLOG_PIPELINE_OK token per service generation, then polls the log
file. It only prints `MUNCH SYSLOG: daemon wrote token OK` after finding
that token in the file. Merely sending a datagram does not count as success.
Existing restart/RAM state behavior remains. Success proves at least one
message path, not every log record or long-term daemon stability.

Configuration design was checked against Apple OSS syslog source revision
69d8586e9a599c304e1b702a9c2830e2f78126d5:
https://github.com/apple-oss-distributions/syslog
The restore binary contains NetworkListener, /etc/asl.conf and the logger
Mach service name. Actual daemon startup/delivery still requires testing.

```sh
python3 tools/munch-extract-userland.py /tmp/munch-apfs-read research/munch/restore-20H392.apfs research/munch/syslog-userland --entry /sbin/launchd --entry /usr/libexec/xpcproxy --entry /usr/sbin/syslogd
bash tools/build-munch-init.sh syslog
python3 tools/mkmunchroot.py research/munch/hfsprogs/newfs_hfs.tproj/newfs_hfs /tmp/munch-hfsplus shim/out/munch-init-0012/init.macho shim/out/munch-init-0015/root.hfs --userland research/munch/syslog-userland --launchd --system-version research/munch/launchd-SystemVersion.plist --accounts research/munch/restore-accounts --service shim/out/munch-service-0015/init.macho --syslog
bash shim/munch/build-xnu.sh research/munch/xnu-run-39582602130/kernel.development.sweet ../live.dtb shim/out/munch-init-0015/root.hfs
```

Image: shim/out/munch-xnu-0015/testios.img,125480960 bytes,SHA256
`e8ad5d86fd65f860d355a4f8db3a80ea510ab0eaed72bc83c726908521ca2a84`.
Daemon/config extraction comparisons, socket/job policy, service signature
hashes, boot roundtrip, RAM audit, cross-build, loader host cases and
repository checks pass. No physical0015 result yet. Preserve0014.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\shim\out\munch-xnu-0015\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

Photograph MUNCH SYSLOG output or daemon errors/panic. This test uses only
local IPC and RAM storage. Temporary boot only.
