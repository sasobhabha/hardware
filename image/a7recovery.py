#!/usr/bin/env python3
"""Assemble a RAM-only iPhone 5S image. It never stages the J71b installer."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / 'boot/initramfs/a7/recovery'
BOARDS = {
    'n51': {'compatible': b'apple,n51\0', 'foreign': b'apple,j71b\0'},
    'n53': {'compatible': b'apple,n53\0', 'foreign': b'apple,j71b\0'},
}


def require_file(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError('Missing regular input: ' + str(path))


def require_dtb(path, profile):
    require_file(path)
    data = path.read_bytes()
    board = BOARDS[profile]
    if data[:4] != b'\xd0\x0d\xfe\xed':
        raise ValueError('Device tree is not an FDT')
    if board['compatible'] not in data or b'apple,s5l8960x\0' not in data:
        raise ValueError('Device tree is not the ' + profile + ' board')
    if board['foreign'] in data:
        raise ValueError('Refusing a J71b device tree for ' + profile)


def stage(root, busybox):
    require_file(busybox)
    if root.exists():
        raise ValueError('Choose a new staging directory')
    for name in ('bin', 'sbin', 'usr/bin', 'usr/sbin', 'etc', 'proc', 'sys', 'dev', 'run', 'tmp', 'root'):
        (root / name).mkdir(parents=True)
    shutil.copyfile(busybox, root / 'bin/busybox')
    (root / 'bin/busybox').chmod(0o755)
    for source, target in (('init', 'init'), ('usb-gadget', 'sbin/recovery-usb')):
        shutil.copyfile(RECOVERY / source, root / target)
        (root / target).chmod(0o755)
    shutil.copyfile(RECOVERY / 'udhcpd.conf', root / 'etc/udhcpd.conf')
    (root / 'etc/udhcpd.conf').chmod(0o644)
    (root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/sh\n')
    (root / 'etc/group').write_text('root:x:0:\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=tuple(BOARDS), required=True)
    for name in ('busybox', 'loader', 'kernel', 'dtb', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('choose a new output path')
    manifest = RECOVERY / ('boot-' + args.profile + '.json')
    bootargs = json.loads(manifest.read_text())['bootargs']
    if (not bootargs.startswith('chosen.bootargs=' + args.profile + '.recovery=1 ')
            or 'j71b.recovery' in bootargs or not bootargs.endswith('\n')):
        parser.error('unexpected boot arguments')
    try:
        for path in (args.busybox, args.loader, args.kernel):
            require_file(path)
        require_dtb(args.dtb, args.profile)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='a7-recovery-', dir=args.output.parent) as temporary:
        stage_dir = Path(temporary) / 'root'
        initramfs = Path(temporary) / 'initramfs.gz'
        stage(stage_dir, args.busybox)
        subprocess.run([sys.executable, str(ROOT / 'boot/initramfs/pack.py'),
                        '--root', str(stage_dir), '--output', str(initramfs)], check=True)
        subprocess.run([sys.executable, str(ROOT / 'boot/assemble.py'),
                        '--manifest', str(manifest), '--loader', str(args.loader),
                        '--dtb', str(args.dtb), '--kernel', str(args.kernel),
                        '--initramfs', str(initramfs), '--output', str(args.output)], check=True)


if __name__ == '__main__':
    main()
