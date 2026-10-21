# Early XNU build with GitHub Actions

Repository: https://github.com/olzhas0986/ios-munch
Workflow: .github/workflows/munch-xnu.yml, **Munch - early XNU**.
First successful kernel build:
https://github.com/olzhas0986/ios-munch/actions/runs/39572263994

## Build scope

XNU-8796.141.3, ARM64 DEVELOPMENT, pinned blacktop builder
663906528d1cd5ea8fde7de6f16de73db9511549. Internal configuration SWEET retains
the existing generic non-Apple ARM implementation. Munch RAM/ADT/timer and
an isolated boot shim are prepared locally after retrieving the artifact.

Only patches0001–0027 and three pinned source-provider scripts are selected.
Sweet UFS0028+, partition writes, USB and input drivers are excluded. Required
patch application failures are fatal. The artifact must be plain ARM64
Mach-O and sweet_ufs.c must be absent. This is a kernel, not testios.img.

Modern IIG targets a different IORPC ABI. The build replays34 generated
DriverKit-286 source files after checking all17 pristine interface hashes,
the complete interface set and the archive/output hashes. Changed interfaces
fail. Provenance and Apple license are under xnu/munch/.

## Running and artifacts

Push to main/munch-bringup triggers the workflow when watched files change.
Alternatively use Actions → Munch - early XNU → Run workflow. Default runner
macos-14 matches the original build family. GitHub retires it2026-11-02;
manual dispatch also offers macos-15, which still needs a successful run.
Runner reference:
https://github.com/actions/runner-images/blob/main/images/macos/macos-14-Readme.md

- munch-xnu-early: kernel.development.sweet, SHA256SUMS and patch/IIG manifests.
- munch-xnu-build-log: captured build output, also uploaded on failure.
- munch-xnu-buildtree: source/generated headers for local checks.

Local validation covered YAML/shell blocks, patch application, no-UFS source,
all generated outputs and changed-interface/repeated-staging rejection.
The first CI additionally compiled and collected the real kernel.
SHA256: b391e0376f6ee6d790b263cee839241474c706b48159e12dbe51610fbc83a597.

Do not flash the artifact. Next is CPU0-only early XNU, restricted audited
RAM, no UFS root, and a separately packaged testios.img.
