# rEFInd SecureBoot Installer Scripts

Simple script that installs rEFInd Boot Loader with Secure Boot

This project is still work in progress

## Requirements

This script currently only requires the built-in Python 3 `python` package

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
* The installer assumes pre-existing installation of rEFInd doesn't exist
* Other boot loaders have not signed the kernel for their use with Secure Boot 
