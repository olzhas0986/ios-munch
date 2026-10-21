# Install the Munch iOS root from USB in TWRP

This is the first full Apple userspace attempt. The dedicated16GiB iosroot
partition and working Android installation must already exist. The user
confirmed partition detection in XNU0018 and NTFS USB support in TWRP.

1. Copy the complete research/munch/usb-install-0019 folder to the USB drive.
   It needs approximately6.13GB. Keep all three gzip parts, checksums,
   installer files and ZIP together. A computer prepares/transfers these
   files; the phone performs the actual root partition installation.
2. Boot TWRP, connect the drive by OTG, choose Install and USB OTG storage,
   then usb-install-0019/Install-Munch-iOS.zip. Start the installation.
3. Wait for rootfs installation and readback verification to complete.
   Progress reports bytes written and verified. Failure stops the installer;
   retain its output for diagnosis. It writes only the verified iosroot
   partition and performs no Android boot/userdata/GPT writes.
4. After success, reboot to Bootloader, connect to the PC and temporarily
   boot the included testios.img using fastboot. Capture boot output/photo.

```bat
copy /Y "\\wsl.localhost\archlinux\home\olzhas0986\ios-munch\upstream\research\munch\usb-install-0019\testios.img" C:\platform-tools\testios.img
cd /d C:\platform-tools
fastboot boot testios.img
```

The ZIP reads its own location, so no fixed USB mount path or terminal is
required. Full-system boot and UI remain hardware tests, not established
results. Known-good RAM graphics image0017 and read-only storage image0018
are retained. The kernel selection is temporary fastboot boot; no automatic
boot-selection menu or boot partition flashing is part of this installer.
