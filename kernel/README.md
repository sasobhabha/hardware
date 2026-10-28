# Kernel build

`build` fetches the pinned Linux revision, applies the selected target's patches
and config, compiles the kernel and external modules, stages the modules, and
runs the target's final-DTB recipe. Git and Podman are required.

```sh
./kernel/build j71b --output out/kernel/j71b
```

Scratch remains in ignored `kernel/.work/j71b/`. `--resume` continues an
interrupted build using that scratch directory; `--output` must name a new
directory. The result contains `Image.gz`, `j71b.dtb`, `kernel.release` and
`lib/modules/`.

`n51` and `n53` (iPhone 5S) do not apply the J71b kernel patches. A7 needs 4KB pages, so both use `kernel/configs/n51/config` (the N53 file links to it), resolved against the unpatched pin. The device-tree step copies `s5l8960x-n51.dtb` or `s5l8960x-n53.dtb`. They do not stage the J71b out-of-tree modules. See [iPhone 5S port](../docs/iphone-5s.md).

The J71b NVMe module has mutually exclusive load modes: `j71b_ro_test=1`
retains the command-level read-only whitelist; `j71b_rw=1` opts into normal
read-write commands. The separate `nvme-core` module also requires `j71b_rw=1`
to stop forcing the J71b namespace read-only. Both matching modules must be
loaded in a fresh recovery boot. The combined mode is compiled, not yet
hardware-proven.
