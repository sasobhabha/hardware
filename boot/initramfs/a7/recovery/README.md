# iPhone 5S RAM recovery

This image boots N51 or N53 to a shell on the screen and, when the USB gadget binds, on `ttyGS0`. The device address is `172.16.42.1/30`. The host address offered by DHCP is `172.16.42.2`.

The init process does not open a block device or NAND. It does not include the J71b storage tools, NVMe modules, touch modules, or PID 1 handoff. This image has not been booted on a phone. The load sequence is in [docs/iphone-5s.md](../../../../docs/iphone-5s.md).

Build BusyBox with `python3 boot/initramfs/j71b/busybox/build.py --output out/busybox`, then:

```sh
python3 image/a7recovery.py \
  --profile n51 \
  --busybox out/busybox \
  --loader out/m1n1-n51.bin \
  --kernel out/kernel-n51/Image.gz \
  --dtb out/kernel-n51/n51.dtb \
  --output out/n51-recovery.img
```

Use `n53` and `s5l8960x-n53.dtb` for the Global phone. Load the resulting image from Pongo with `bootm`. Do not concatenate another kernel onto it.
