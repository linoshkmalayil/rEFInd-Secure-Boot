# rEFInd SecureBoot Installer Scripts

Simple script that installs rEFInd Boot Loader with Secure Boot

This project is still work in progress

## Requirements

This script requires the following packages installed
* `python` (This installer is running on python afterall)
* `base-devel` (To setup the Arch Build Environment to build and aur package)

## Running the Script

To run this script just run the following:
```
git clone https://github.com/linoshkmalayil/rEFInd-Secure-Boot.git
cd rEFInd-Secure-Boot/src
python install_sb_refind.py
```

## Important to Note
These scripts assumes the following:
* The kernel used is the default `linux` kernel
(Support for other kernels are being worked on)
* The folder to mount the ESP Partition is `/boot/efi`
* That you are already booted into the system in a privileged user. 
(aka not in chroot, not in root user)
* Other boot loaders have not signed the kernel for their use with Secure Boot 
* If you're using the default refind_linux.conf to boot from rEFInd, it still uses the unsigned image backup that is created, must check how to explictly pass a loader image
