import subprocess
import logging
import os

from shutil import copyfile

def check_secureboot():
    logging.debug("Checking if SecureBoot is on")
    cmd = "mokutil --sb-state"
    secureboot_state = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")

    if "SecureBoot enabled\n" == secureboot_state:
        return True
    
    return False

def check_packages():
    logging.debug("Checking if the packages refind, mokutil, sbsigntools are installed")
    required_packages = ["refind", "mokutil", "sbsigntools", "shim"]

    for package in required_packages:
        cmd = "pacman -Q " + package
        check_code = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode

        if check_code:
            logging.warning("Package %s is not installed, installing", package)
            
            cmd = "yes | pacman -S " + package
            install_result = subprocess.run(cmd, shell=True).returncode
            
            if install_result:
                logging.error("Failed to install package %s. Aborting!", package)

                return False
        
    logging.info("Required packages are installed.")    
    return True

def detect_esp():
    logging.debug("Looking for ESP Partitions")

    cmd = "lsblk --output NAME,PARTTYPENAME| grep 'EFI System'"
    part_output = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout.decode("UTF-8")
    
    part_output= part_output.replace("└─","").replace("├─","")
    esp_entries = part_output.split("\n")
    if "" in esp_entries:
        esp_entries.remove("") 
    
    esp_partitions = list()
    for entry in esp_entries:
        esp_partitions.append("/dev/" + entry.split(" ")[0])

    if len(esp_partitions) == 1:
        logging.info("Found ESP Partition on %s", esp_partitions[0])

        return esp_partitions[0]
    else:
        logging.info("Multiple ESP Paritions found, please Choose one:")
        
        for i in range(0,len(esp_partitions)):
            logging.info("%s] %s", i+1, esp_partitions[i])

        choice = len(esp_partitions) + 1
        while((choice < 1) or (choice > len(esp_partitions))):
            choice = int(input("Enter choice: "))

        return esp_partitions[choice - 1]
    
def mount_esp(esp_partition: str):
    logging.debug("Trying to mount ESP Partition %s to %s", esp_partition, "/boot/efi")

    if not os.path.isdir("/boot/efi"):
        logging.debug("Directory /boot/efi not found, creating...")
        os.makedirs("/boot/efi")

    cmd = "mount " + esp_partition + " /boot/efi"
    run_code = subprocess.run(cmd, shell=True).returncode
    
    if run_code:
        logging.error("Failed to mount %s to /boot/efi", esp_partition)
        
        return False
    
    logging.info("Mounted successfully")
    return True
    
def unmount_esp():
    logging.debug("Unmounting ESP Partiton")

    cmd = "umount -R /boot/efi"
    subprocess.run(cmd, shell=True)

def refind_install():
    logging.debug("Running refind-install to upgrade rEFInd installation.")
    
    cmd = "refind-install --shim /usr/share/shim-signed/shimx64.efi --localkeys"
    install_code = subprocess.run(cmd, shell=True).returncode

    if install_code:
        logging.error("refind-install failed!")
        return False
    
    return True

def sign_linux_kernel():
    logging.debug("Creating unsigned backup of kernel image /boot/vmlinuz-linux")
    copyfile("/boot/vmlinuz-linux-unsigned", "/boot/vmlinuz-linux")

    logging.debug("Signing Linux Kernel /boot/vmlinuz-linux")
    
    sign_cmd = "sbsign --key /etc/refind.d/keys/refind_local.key --cert /etc/refind.d/keys/refind_local.crt --output /boot/vmlinuz-linux /boot/vmlinuz-linux"
    subprocess.run(sign_cmd, shell=True)

    logging.debug("Verifying signature on /boot/vmlinuz-linux")
    verify_cmd = "sbverify --list /boot/vmlinuz-linux"
    verify_output = subprocess.run(verify_cmd, shell=True, stdout=subprocess.PIPE).stdout.decode("UTF-8")

    if not verify_output:
        logging.error("Failed to sign the kernel /boot/vmlinuz-linux!")
        return False
    
    logging.info("Sucessfully signed the kernel /boot/vmlinuz-linux")
    return True

def copy_files():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    logging.debug("Copying updater scripts to /etc/refind.d")

    if not os.path.isdir("/etc/refind.d"):
        logging.debug("Directory /etc/refind.d not found, creating...")
        os.makedirs("/etc/refind.d")

    copyfile("/etc/refind.d/update_refind.py", current_dir + "/update_refind.py")
    copyfile("/etc/refind.d/update_refind.py", current_dir + "/sign_kernel.sh")

    logging.debug("Adding execute permission to /etc/refind.d/sign_kernel.sh")
    chmod_cmd = "chmod +x /etc/refind.d/sign_kernel.sh"
    subprocess.run(chmod_cmd, shell=True)

    logging.debug("Copying hooks to /etc/pacman.d/hooks")

    if not os.path.isdir("/etc/pacman.d/hooks"):
        logging.debug("Directory /etc/pacman.d/hooks not found, creating...")
        os.makedirs("/etc/pacman.d/hooks")

    copyfile("/etc/refind.d/update_refind.py", current_dir + "/update_refind.py")
    copyfile("/etc/refind.d/update_refind.py", current_dir + "/sign_kernel.sh")


def main():
    logging.basicConfig(format="%(levelname)s:%(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    sb_state = check_secureboot()

    if sb_state:
        logging.info("SecureBoot is Enabled")
    else:
        logging.info("SecureBoot is Disabled, refind-install might throw some warnings!")

    if not check_packages():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(1)
    
    esp_part = detect_esp()

    if not mount_esp(esp_part):
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(2)
    
    if not refind_install():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(3)
    
    unmount_esp()
    logging.info("rEFInd installed successfully!")

    if not sign_linux_kernel():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(4)

    copy_files()

    if sb_state:
        logging.info("SecureBoot is Enabled, please reboot the system.")
    else:
        logging.info("SecureBoot is Disabled, please enable it in the firmware settings.")

    exit(0)

if __name__ == "__main__":
    main()
