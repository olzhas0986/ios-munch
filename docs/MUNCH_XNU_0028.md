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
0028-profiled/testios.img. Reuse installed root. Kernel CI and image packaging
are pending. Do not boot previous kernels as if they contained this change.
