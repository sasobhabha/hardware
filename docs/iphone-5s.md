# iPhone 5S

The iPhone 5S is an Apple A7 (`S5L8960X`, CPID `0x8960`). That is the same SoC as the iPad mini 2 (`J85` / `J86` / `J87`), the iPad mini 3, and the iPad Air. The bring-up already in this repository is the iPad 6 Wi-Fi, board J71b, product `iPad7,5`, SoC A10 / T8010, CPID `0x8010`, BDID `0x18`.

The pinned kernel already builds the A7 board trees, including `s5l8960x-n51.dtb` and `s5l8960x-n53.dtb`. This port selects those trees, records the DFU identities, and builds a tethered RAM-only recovery image. It does not retarget the J71b installer. Nothing here has been booted on a phone.

## Boards

| Profile | Product | Board | DFU chip | DFU board | Device tree |
| --- | --- | --- | --- | --- | --- |
| `n51` | `iPhone6,1` | N51AP | `0x8960` | `0x00` | `s5l8960x-n51.dtb` |
| `n53` | `iPhone6,2` | N53AP | `0x8960` | `0x02` | `s5l8960x-n53.dtb` |

DFU identities match libirecovery. Root compatibles are `apple,n51` and `apple,n53`, each followed in the device tree by `apple,s5l8960x`.

## Build

```sh
./kernel/build n51 --output out/kernel-n51
./kernel/build n53 --output out/kernel-n53
./boot/m1n1/build n51 --output out/m1n1-n51.bin
./boot/m1n1/build n53 --output out/m1n1-n53.bin
python3 boot/initramfs/j71b/busybox/build.py --output out/busybox
python3 image/a7recovery.py --profile n51 --busybox out/busybox \
  --loader out/m1n1-n51.bin --kernel out/kernel-n51/Image.gz \
  --dtb out/kernel-n51/n51.dtb --output out/n51-recovery.img
```

A7 implements 4KB translation granules. The J71b configuration is 16KB pages, so `n51` and `n53` do not apply the J71b kernel patches and do not reuse that configuration. `kernel/configs/n51/config` is the resolved 4KB configuration for the unpatched pin. `kernel/configs/n53/config` links to it. The device-tree builder copies the upstream A7 DTB and refuses a blob that contains `apple,j71b`.

`boot/m1n1/build n51` and `n53` still apply the J71b loader series. Those changes run only when the live tree is `apple,j71b` or contains an `nvme-hmb` node, so they are a no-op on these boards. Build that loader, not the quiet launcher: the quiet build clears the screen.

The RAM image is `python3 image/a7recovery.py`. It packs a shell that accepts only `apple,n51` or `apple,n53`, never opens a block device, and starts a USB gadget only when the board matches. N51 announces `N51 Recovery` (`05ac:5a51`). N53 announces `N53 Recovery` (`05ac:5a53`). The device address is `172.16.42.1/30` and DHCP offers the host `172.16.42.2`. `support.usb_serial` and `support.usb_network` describe that gadget. They do not mean a phone has enumerated it.

The framebuffer node in the pinned tree stays disabled until the loader fills its `reg`. Boot arguments put the console on `tty0` with `fbcon=map:0`. If the USB PHY probe fails, the gadget exits and the screen shell stays up.

## Load

`out/n51-recovery.img` is one file: m1n1, boot arguments, DTB, `Image.gz`, and a gzip newc initramfs framed by `m1n1_initramfs`. Do not concatenate another kernel or a raw initramfs onto it.

On macOS, enter a PongoOS shell with checkra1n, which covers A7:

```sh
checkra1n -k Pongo.bin
printf '/send out/n51-recovery.img\nbootm\n' | pongoterm
```

Build that `Pongo.bin` from checkra1n's pongoOS without `-DQUIET_BOOT`. The Pongo in `boot/quiet/` is the J71b launcher and clears the screen. palera1n's current readme starts at A8, so it can refuse a 5S. Hoolock's pongoOS tutorial uses `PALERA1N_BYPASS_PASSCODE_CHECK=1 palera1n -lp -k Pongo.bin` and the same `/send` plus `bootm` sequence; use that only if the 5S is actually accepted. `pongoterm` comes from the pongoOS tree.

## What stays unported

The iPhone 5S profile has an empty firmware recipe. Nothing is extracted from an IPSW.

- Storage on the 5S is NAND. The J71b path is NVMe, and its handoff opens the install partition read-write. A7 internal storage is still unfinished in the Hoolock feature matrix. This profile does not call that handoff and does not stage `nvme.ko`.
- Wi-Fi and Bluetooth are a Murata 339S0205 module, a Broadcom BCM4334-family SDIO combo (teardowns report the die as BCM43342). The J71b recipe is BCM4355 PCIe (`FigaroA`) plus a T8010 SmartIO image. `support.wifi` stays false.
- Touch on the 5S is a Broadcom BCM5976. The J71b touch stack is a T8010 SPI / SmartIO sequence.
- Charging, the display pipe, and the GPU are not ported. There is no published launcher manifest.

Hoolock's A7 matrix covers the device tree, simple framebuffer, buttons, and SMP. USB device mode is marked linux-apple there; the pinned Orchard tree contains the DWC2 and AUSB PHY matches this gadget uses. Display-pipe acceleration, GPU, and internal storage are outside that matrix. A unit test does not boot a phone.

## A7 hardware-map evidence

The [omarchy-hardware-map](https://github.com/theChristopher16/omarchy-hardware-map) catalog publishes hardware observations behind an MCP server. Its approved catalog snapshot has no record for the BCM4334 SDIO combo, the BCM5976 touch controller, or any iPhone. It does carry five owner-run observations from one iPad mini 2 Wi-Fi (A1489/J85) on an experimental Linux RAM boot, 27 October 2026; J85 is the same A7 / S5L8960X SoC as this port. Those five are the project's own `evidence/` notes served alongside its approved catalog, not moderation-verified site records, and they describe a tablet display pipeline that differs from the 5S. Read them through `search_hardware_reports` on a local copy of that server; an owner's tablet observation is not a phone result.

- Storage: the running kernel exposed no internal physical block device on that boot, matching the Hoolock A7 note that internal storage is unfinished. A controller display, device verification, and a recovery plan are prerequisites before this profile can stage any NAND driver.
- Charging: bounded 1 A input-limit trials with an owner-confirmed Apple 10 W adapter reported positive battery current and a 48% to 51% rise, with each cycle restoring the prior setting. That is an owner-confirmed experiment, not automatic source detection; later 500 mA samples discharged. Do not raise any input limit on this profile.
- Touch: the owner confirmed aligned one- and two-finger input after calibration on an earlier A7 touch boot. The later runtime9 boot carried the touch module unloaded and two required private inputs unstaged, which is the same shape as this profile's missing BCM5976 recipe: firmware fragments extracted per device, not a T8010 SmartIO stack.
- Audio: a read-only inventory reported no ALSA sound cards and no PCM devices; codec clock, reset, control bus, and data-path initialization remain open. This profile has no audio recipe.
- GPU: that J85 boot stayed CPU-rendered; its disabled GPU node lacked clock properties and the PowerVR validator rejected the staged firmware image at its first size check. J85 is GX6250-class; the 5S is G6430. That gap does not transfer in either direction, and this profile keeps the framebuffer node CPU-rendered.

## Sources

- Pinned kernel makefile at `6831bc701a6ce059e71e5aaa9488c9195bea6927` lists `s5l8960x-n51.dtb` and `s5l8960x-n53.dtb`.
- [Hoolock setup](https://github.com/HoolockLinux/docs/blob/master/tutorials/SETUP.md) requires `CONFIG_ARM64_4K_PAGES` on A7 and A8.
- [Hoolock pongoOS boot](https://github.com/HoolockLinux/docs/blob/master/tutorials/SETUP_pongoOS.md)
- [Hoolock A7 feature support](https://github.com/HoolockLinux/docs/blob/master/features/A7.md)
- [omarchy-hardware-map J85 A7 evidence](https://github.com/theChristopher16/omarchy-hardware-map/tree/master/evidence/ipad-mini2-j85) surfaced through `search_hardware_reports`; the [draft bring-up report](https://github.com/OrchardLinux/hardware/pull/5) holds the wider boot context.
- DFU chip and board IDs from libirecovery's device table.
