# N51 device tree

`build` copies `s5l8960x-n51.dtb` from the kernel build. It checks the FDT magic and the `apple,n51` / `apple,s5l8960x` compatible strings, and it refuses a tree that carries `apple,j71b`. No overlay is applied.
