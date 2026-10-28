# N53 device tree

`build` copies `s5l8960x-n53.dtb` from the kernel build. It checks the FDT magic and the `apple,n53` / `apple,s5l8960x` compatible strings, and it refuses a tree that carries `apple,j71b`. No overlay is applied.
