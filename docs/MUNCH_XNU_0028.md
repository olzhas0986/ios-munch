# Munch 0028: local ACL group resolution test

The 0027 phone photos capture installcoordinat aborting because creating its
data directory fails with NSPOSIXErrorDomain code 13 (EACCES). profiled is
alive in both snapshots: the first includes system-group container file
readability checks, the second MCFileAccessRepairTool and MCDictionaryWriter
access repair/write calls. SpringBoard still waits synchronously in XPC.
The exact private paths and the complete causal chain are not proven.

Patch 0096 adapts upstream 0057: remove config_ext_resolver from the platform
filesystem configuration. This selects built-in UID/GID compatibility group
resolution rather than external identity resolution through a service absent
from this bring-up. It does not strip ACLs, change modes or fake encryption.
The same configuration change addressed ACL-only container access on Sweet.
Whether it resolves the Munch boot-logo wait requires a phone test.

Stage last patch: 96. Outputs: shim/out/munch-xnu-0028/testios.img and optional
0028-profiled/testios.img. Reuse installed root. Validated CI and delivered image are recorded below. Do not boot previous kernels as if they contained this change.

## Validated image

CI39751086547 succeeded for source4120bc5306ed653e729e8c68079ec51de0b04e3f,
artifact12413602552. Image: `shim/out/munch-xnu-0028-profiled/testios.img`
(125612032 bytes), SHA-256:
`24ccd361d78b86f8b697e45feac8df0c86b6d0febd6db4f71011d91a616de481`.
This retains the previous profiled/SpringBoard snapshot arguments.
Manifest96/source hashes, compiled resolver removal, console protection,
boot header/payload, root arguments, ADT and loader checks passed.
Phone result pending. No root reinstall required.

## Phone result

Photo 5390970928092617172.jpg confirms the iOS lock screen on Munch after
this change. The user reports no touch response. Current stage96 includes
neither HID event services0058 nor a Munch touch driver; touch is a separate
bring-up task. Preserve this working display image as a checkpoint. The
remaining profiled AKS31 error does not prevent lock-screen rendering.
