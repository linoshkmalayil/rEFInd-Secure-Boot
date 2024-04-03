#!/bin/bash

echo "Checking if kernel /boot/vmlinuz-linux is signed"
SIGNED=$(sbverify --list /boot/vmlinuz-linux)

if [ -z "$SIGNED" ];
then
    echo "Kernel /boot/vmlinuz-linux is not signed!"
    echo "Checking for unsigned kernel backup..."

    if [ -f "/boot/vmlinuz-linux-unsigned" ];
    then
        echo "Old unsigned kernel /boot/vmlinuz-linux-unsigned found!"
        echo "Deleting..."
        rm /boot/vmlinuz-linux-unsigned
    else
        echo "No backups found!"
    fi

    echo "Creating unsigned kernel backup..."
    cp /boot/vmlinuz-linux /boot/vmlinuz-linux-unsigned
    echo "Unsigned backup /boot/vmlinuz-linux-unsigned created"
    
    echo "Signing the kernel..."
    sbsign --key /etc/refind.d/keys/refind_local.key --cert /etc/refind.d/keys/refind_local.crt --output /boot/vmlinuz-linux /boot/vmlinuz-linux
    
    echo "Verifying signature..."
    SIGNED=$(sbverify --list /boot/vmlinuz-linux)
    if [ ! -z "$SIGNED" ];
    then
        echo "Kernel /boot/vmlinuz-linux-unsigned signed successfully!"
    else
        echo "Failed to sign the kernel!"
    fi
else
    echo "Kernel /boot/vmlinuz-linux-unsigned already signed, skipping!"
fi

echo "Checking SecureBoot state..."
SECUREBOOT=$(mokutil --sb-state)

if [ "$SECUREBOOT" == "SecureBoot enabled" ];
then
    echo "SecureBoot is enabled!"
else
    echo "SecureBoot is disabled! Go to UEFI Firmware settings to Enable!"
fi
