"""iPhone 5S identities stay on the A7 board trees and off the J71b installer."""
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

try:
    import tomllib
except ImportError:
    import tomli as tomllib

HARDWARE = Path(__file__).resolve().parents[1]
BOARDS = {
    'n51': {
        'product': 'iPhone6,1',
        'name': 'iPhone 5S (GSM)',
        'board': 0x00,
        'compatible': 'apple,n51',
        'dtb': 's5l8960x-n51.dtb',
    },
    'n53': {
        'product': 'iPhone6,2',
        'name': 'iPhone 5S (Global)',
        'board': 0x02,
        'compatible': 'apple,n53',
        'dtb': 's5l8960x-n53.dtb',
    },
}


def fdt(compatible):
    return b'\xd0\x0d\xfe\xed' + b'pad' + (compatible + '\0').encode() + b'apple,s5l8960x\0'


class IPhone5S(unittest.TestCase):
    def test_dfu_identity_and_empty_firmware_recipe(self):
        for profile, expect in BOARDS.items():
            with self.subTest(profile=profile):
                device_path = HARDWARE / 'devices' / profile / 'device.toml'
                device = tomllib.loads(device_path.read_text())
                self.assertEqual(device['device']['profile'], profile)
                self.assertEqual(device['device']['name'], expect['name'])
                self.assertEqual(device['device']['apple_products'], [expect['product']])
                self.assertEqual(device['device']['dt_compatible'], [expect['compatible']])
                self.assertEqual(device['match']['dfu'], {'chip': 0x8960, 'board': expect['board']})
                self.assertEqual(device['match']['linux'], {'product': profile.upper() + ' Recovery'})
                self.assertEqual(device['boot']['methods'], ['checkm8-pongo'])
                self.assertNotIn('launch_manifest', device['boot'])
                self.assertEqual(device['support'], {'wifi': False, 'usb_serial': True, 'usb_network': True})
                recipe_path = device_path.parent / device['firmware']['recipe']
                recipe = json.loads(recipe_path.read_text())
                self.assertEqual(recipe['device'], expect['product'])
                self.assertEqual(recipe['files'], [])
                self.assertEqual(recipe['extracted_inputs'], [])
                self.assertEqual(recipe['generated'], [])
                self.assertNotIn('ipsw_url', recipe)
                self.assertFalse(recipe_path.is_symlink())

    def test_kernel_is_unpatched_4k_and_loader_series_stays_conditional(self):
        n51 = HARDWARE / 'kernel/configs/n51/config'
        n53 = HARDWARE / 'kernel/configs/n53/config'
        j71b = HARDWARE / 'kernel/configs/j71b/config'
        self.assertFalse(n51.is_symlink())
        self.assertTrue(n53.is_symlink())
        self.assertEqual(n53.resolve(), n51.resolve())
        self.assertNotEqual(n51.resolve(), j71b.resolve())
        text = n51.read_text()
        self.assertIn('CONFIG_ARM64_4K_PAGES=y\n', text)
        self.assertIn('# CONFIG_ARM64_16K_PAGES is not set\n', text)
        self.assertIn('CONFIG_PAGE_SIZE_4KB=y\n', text)
        self.assertIn('CONFIG_PAGE_SHIFT=12\n', text)
        self.assertNotIn('CONFIG_ARM64_16K_PAGES=y', text)
        self.assertNotIn('CONFIG_PAGE_SIZE_16KB=y', text)
        for symbol in (
            'CONFIG_PCIE_APPLE_H9P',
            'CONFIG_TOUCHSCREEN_APPLE_J71B_READINESS',
            'CONFIG_APPLE_T8010_WLAN',
            'CONFIG_COMMON_CLK_APPLE_T8010_TOUCH',
            'CONFIG_APPLE_SIO',
        ):
            self.assertNotIn(symbol, text)
        self.assertIn('# CONFIG_NVME_APPLE is not set\n', text)
        self.assertIn('CONFIG_ARM64_16K_PAGES=y\n', j71b.read_text())
        for profile in BOARDS:
            with self.subTest(profile=profile):
                self.assertFalse((HARDWARE / 'kernel/patches' / profile / 'series').exists())
                series = (HARDWARE / 'boot/m1n1/patches' / profile / 'series').read_text().strip()
                self.assertEqual(series, 'j71b')
                self.assertFalse((HARDWARE / 'kernel/modules' / profile).exists())

    def test_device_tree_builder_copies_only_the_matching_a7_fdt(self):
        for profile, expect in BOARDS.items():
            script = HARDWARE / 'kernel/devicetree' / profile / 'build'
            self.assertTrue(script.stat().st_mode & stat.S_IXUSR)
            text = script.read_text()
            self.assertIn(expect['dtb'], text)
            self.assertIn(expect['compatible'], text)
            self.assertNotIn('fdtoverlay', text)
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / 'build/arch/arm64/boot/dts/apple' / expect['dtb']
                source.parent.mkdir(parents=True)
                source.write_bytes(fdt(expect['compatible']))
                headers = root / 'include/dt-bindings/pinctrl'
                headers.mkdir(parents=True)
                (headers / 'apple.h').write_text('/* test */\n')
                output = root / (profile + '.dtb')
                subprocess.run(
                    [str(script), '--kernel-build', str(root / 'build'),
                     '--headers', str(root / 'include'), '--output', str(output)],
                    check=True, cwd=root)
                self.assertEqual(output.read_bytes(), source.read_bytes())
                foreign = root / 'foreign.dtb'
                source.write_bytes(fdt(expect['compatible']) + b'apple,j71b\0')
                completed = subprocess.run(
                    [str(script), '--kernel-build', str(root / 'build'),
                     '--headers', str(root / 'include'), '--output', str(foreign)],
                    cwd=root, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 1)
                self.assertIn('J71b', completed.stderr)
                self.assertFalse(foreign.exists())

    def test_installed_system_writer_remains_j71b(self):
        init = (HARDWARE / 'boot/initramfs/j71b/recovery/init').read_text()
        self.assertIn('apple,j71b', init)
        self.assertIn('No internal storage is mounted or written', init)
        recovery = (HARDWARE / 'image/recovery.py').read_text()
        self.assertIn("boot/initramfs/j71b/recovery", recovery)
        self.assertIn('blockdev', (HARDWARE / 'runtime/j71b/handoff.py').read_text())
        self.assertEqual(
            tomllib.loads((HARDWARE / 'devices/j71b/device.toml').read_text())['match']['dfu'],
            {'chip': 0x8010, 'board': 0x18})

    def test_build_scripts_parse(self):
        scripts = [
            HARDWARE / 'kernel/build',
            HARDWARE / 'boot/m1n1/build',
            HARDWARE / 'kernel/devicetree/n51/build',
            HARDWARE / 'kernel/devicetree/n53/build',
        ]
        for script in scripts:
            subprocess.run(['bash', '-n', str(script)], check=True)
        kernel = (HARDWARE / 'kernel/build').read_text()
        loader = (HARDWARE / 'boot/m1n1/build').read_text()
        self.assertIn('patch_dir/series', kernel)
        self.assertIn('patches/$device/series', loader)
        self.assertIn('patch_manifest', kernel)
        self.assertNotIn('kernel/patches/n51/series', kernel)

    def test_ram_recovery_image_never_opens_storage(self):
        init_path = HARDWARE / 'boot/initramfs/a7/recovery/init'
        gadget_path = HARDWARE / 'boot/initramfs/a7/recovery/usb-gadget'
        self.assertTrue(init_path.stat().st_mode & stat.S_IXUSR)
        self.assertTrue(gadget_path.stat().st_mode & stat.S_IXUSR)
        init = init_path.read_text()
        gadget = gadget_path.read_text()
        for banned in ('handoff', 'blockdev', 'mke2fs', 'sfdisk', 'nvme', 'modprobe',
                       'apple,j71b', 'J71b Recovery'):
            self.assertNotIn(banned, init)
            self.assertNotIn(banned, gadget)
        self.assertIn('apple,n51|apple,n53', init)
        self.assertIn("name='N51 Recovery'; product_id=0x5a51", gadget)
        self.assertIn("name='N53 Recovery'; product_id=0x5a53", gadget)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            busybox = root / 'busybox'
            busybox.write_bytes(b'busybox-test')
            busybox.chmod(0o755)
            loader = root / 'm1n1.bin'
            loader.write_bytes(b'm1n1-test')
            kernel = root / 'Image.gz'
            kernel.write_bytes(b'\x1f\x8btest-kernel')
            dtb = root / 'n51.dtb'
            dtb.write_bytes(fdt('apple,n51'))
            output = root / 'n51-recovery.img'
            subprocess.run(
                [sys.executable, str(HARDWARE / 'image/a7recovery.py'),
                 '--profile', 'n51', '--busybox', str(busybox),
                 '--loader', str(loader), '--kernel', str(kernel),
                 '--dtb', str(dtb), '--output', str(output)],
                check=True)
            image = output.read_bytes()
            self.assertIn(b'chosen.bootargs=n51.recovery=1 ', image)
            self.assertIn(b'apple,n51\0', image)
            self.assertIn(b'apple,s5l8960x\0', image)
            self.assertIn(b'm1n1_initramfs', image)
            self.assertNotIn(b'j71b.recovery', image)
            self.assertNotIn(b'handoff.py', image)
            self.assertNotIn(b'apple,j71b\0', image)
            foreign = root / 'foreign.dtb'
            foreign.write_bytes(fdt('apple,n51') + b'apple,j71b\0')
            refused = subprocess.run(
                [sys.executable, str(HARDWARE / 'image/a7recovery.py'),
                 '--profile', 'n51', '--busybox', str(busybox),
                 '--loader', str(loader), '--kernel', str(kernel),
                 '--dtb', str(foreign), '--output', str(root / 'refused.img')],
                capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn('J71b', refused.stderr)
            self.assertFalse((root / 'refused.img').exists())


if __name__ == '__main__':
    unittest.main()
