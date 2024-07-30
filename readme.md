# rEFInd SecureBoot Installer Scripts

Simple Two-stage scripts that installs rEFInd Boot Loader with Secure Boot

This project is still work in progress

## Requirements

These script requires the following packages installed
* `git` (To clone this repo)
* `python` (This installer is running on python afterall)
* `base-devel` (To setup the Arch Build Environment to build and aur package)

## Running the Scripts
There is a two stage process to run these scripts.

**STEP-1**
Go into the UEFI firmware settings and disable Secure Boot. (Refer the manual of the motherboard or computer for the detailed steps)

**STEP-2**
The first script is designed to run in chroot mode during the install process.

To run this script, run the following on the terminal:
```
git clone https://github.com/linoshkmalayil/rEFInd-Secure-Boot.git
cd rEFInd-Secure-Boot/src
python install_refind.py
```
This first script will install basic rEFInd install so that you can boot from it.

**NOTE**: Secure Boot is not setup at this stage only the bootloader is installed.

**STEP-3**
The second script is the one that sets up Secure Boot for rEFInd and it must be run by a user with sudo root privileges. (This script uses the AUR and hence it cannot be run as root or chroot)

To run this script just run the following on the terminal in the same directory as first script:
```
python install_sb_refind.py
```
This script will setup Secure Boot keys, sign the bootloader and kernel and setup the boot entries to use updated Secure Boot loader. This script will also add updater scripts to resign the kernel and bootloader whenever there is an update to these packages.

**STEP-4**
Reboot the system and go into your UEFI firmware settings and enable Secure Boot. And upon booting the MOK utility should boot first.

Load the key from `\EFI\refind\keys\refind_local.cer`

Load the hash from `\EFI\refind\keys\grubx64.efi`

After that exit and you should be good to go.

## Important to Note
These scripts assumes the following:
* The kernel used is the default `linux` kernel.
(Support for other kernels are being worked on)
* The folder to mount the ESP Partition is `/boot/efi`.
* Other boot loaders have not signed the kernel for their use with Secure Boot.
