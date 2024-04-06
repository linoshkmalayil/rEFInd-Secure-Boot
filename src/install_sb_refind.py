import subprocess
import logging

from os import path

def check_secureboot():
    logging.debug("Checking if SecureBoot is on")
    cmd = "mokutil --sb-state"
    secureboot_state = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")

    if "SecureBoot enabled\n" == secureboot_state:
        return True
    
    return False

def check_packages():
    logging.debug("Updating pacman database...")
    cmd = "sudo pacman -Sy"

    logging.debug("Checking if the packages refind, mokutil, sbsigntools are installed")
    required_packages = ["refind", "mokutil", "sbsigntools"]

    for package in required_packages:
        cmd = "pacman -Q " + package
        check_code = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode

        if check_code:
            logging.warning("Package %s is not installed, installing", package)
            
            cmd = "yes | sudo pacman -S " + package
            install_result = subprocess.run(cmd, shell=True).returncode
            
            if install_result:
                logging.error("Failed to install package %s. Aborting!", package)

                return False
            
    logging.debug("Checking if shim-signed is installed")
    cmd = "pacman -Q shim-signed"
    check_code = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode

    if check_code:
        logging.warning("Package shim-signed is not installed, installing from aur")

        cmd = "git clone https://aur.archlinux.org/shim-signed.git && cd shim-signed && makepkg -si && cd .. && rm -rf shim-signed"
        install_result = subprocess.run(cmd, shell=True).returncode
        if install_result:
            logging.error("Failed to install package shim-signed. Aborting!")
        
            return False

    logging.info("Required packages are installed.")    
    return True

def get_refind_data():
    logging.debug("Finding rEFInd Boot Entries")

    efi_output = subprocess.run("efibootmgr | grep rEFInd ", shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")
    refind_entries = efi_output.split("\n")
    if "" in refind_entries:
        refind_entries.remove("") 

    if refind_entries == []:
        logging.error("No rEFInd entries found!")
        return

    logging.info("Found entries:\n%s", "\n".join(refind_entries))
    
    refind_data = list()
    for entry in refind_entries:
        entry_data = (entry.split(" ")[0].strip("Boot").strip("*"), entry.split(",")[2])
        refind_data.append(entry_data)

    return refind_data

def find_esp(refind_data: list):
    esp_partuuid = refind_data[0][1]
    logging.debug("Trying to find partition with PARTUUID %s", esp_partuuid)
    cmd = "lsblk --output NAME,PARTUUID | grep " + esp_partuuid
    
    lsblk_ouput = subprocess.run(cmd,shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")
    esp_part = "/dev/" + lsblk_ouput.split(" ")[0].replace("├─","").replace("└─","")
    logging.info("Found ESP Partition %s", esp_part)

    return esp_part

def delete_entries(refind_data: list):
    logging.debug("Deleting rEFInd entries")

    for entry in refind_data:
        cmd = "sudo efibootmgr --delete-bootnum --bootnum " + entry[0]
        subprocess.run(cmd, shell=True)
    
def mount_esp(esp_partition: str):
    logging.debug("Trying to mount ESP Partition %s to %s", esp_partition, "/boot/efi")

    if not path.isdir("/boot/efi"):
        logging.debug("Directory /boot/efi not found, creating...")
        efi_mkdir_cmd = "sudo mkdir /boot/efi"
        subprocess.run(efi_mkdir_cmd, shell=True)

    cmd = "sudo mount " + esp_partition + " /boot/efi"
    run_code = subprocess.run(cmd, shell=True).returncode
    
    if run_code:
        logging.error("Failed to mount %s to /boot/efi", esp_partition)
        
        return False
    
    logging.info("Mounted successfully")
    return True
    
def unmount_esp():
    logging.debug("Unmounting ESP Partiton")

    cmd = "sudo umount -R /boot/efi"
    subprocess.run(cmd, shell=True)

def refind_install():
    logging.debug("Running refind-install to upgrade rEFInd installation.")
    
    cmd = "sudo refind-install --shim /usr/share/shim-signed/shimx64.efi --localkeys"
    install_code = subprocess.run(cmd, shell=True).returncode

    if install_code:
        logging.error("refind-install failed!")
        return False
    
    return True

def sign_linux_kernel():
    logging.debug("Creating unsigned backup of kernel image /boot/vmlinuz-linux")
    copy_cmd = "sudo cp /boot/vmlinuz-linux /boot/vmlinuz-linux-unsigned"
    subprocess.run(copy_cmd, shell=True)

    logging.debug("Signing Linux Kernel /boot/vmlinuz-linux")
    
    sign_cmd = "sudo sbsign --key /etc/refind.d/keys/refind_local.key --cert /etc/refind.d/keys/refind_local.crt --output /boot/vmlinuz-linux /boot/vmlinuz-linux"
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
    current_dir = path.dirname(path.abspath(__file__))

    logging.debug("Copying updater scripts to /etc/refind.d")

    if not path.isdir("/etc/refind.d"):
        logging.debug("Directory /etc/refind.d not found, creating...")
        refind_mkdir_cmd = "sudo mkdir /etc/refind.d"
        subprocess.run(refind_mkdir_cmd, shell=True)

    copy_refind_updater = "sudo cp " + current_dir + "/files/update_refind.py " + "/etc/refind.d/update_refind.py"
    copy_kernel_signer = "sudo cp " + current_dir + "/files/sign_kernel.sh " + "/etc/refind.d/sign_kernel.sh"
    subprocess.run(copy_refind_updater + " && " + copy_kernel_signer, shell=True)

    logging.debug("Adding execute permission to /etc/refind.d/sign_kernel.sh")
    chmod_cmd = "sudo chmod +x /etc/refind.d/sign_kernel.sh"
    subprocess.run(chmod_cmd, shell=True)

    logging.debug("Copying hooks to /etc/pacman.d/hooks")

    if not path.isdir("/etc/pacman.d/hooks"):
        logging.debug("Directory /etc/pacman.d/hooks not found, creating...")
        hooks_mkdir_cmd = "sudo mkdir -p /etc/pacman.d/hooks"
        subprocess.run(hooks_mkdir_cmd, shell=True)
    
    copy_refind_hook = "sudo cp " + current_dir + "/files/refind.hook " + "/etc/pacman.d/hooks/refind.hook"
    copy_linux_hook = "sudo cp " + current_dir + "/files/linux.hook " + "/etc/pacman.d/hooks/linux.hook"
    subprocess.run(copy_refind_hook + " && " + copy_linux_hook, shell=True)


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
    
    rd = get_refind_data()

    if rd == None:
        logging.error("Aborting! Please install rEFInd Boot Loader first!")
        exit(2)

    esp_part = find_esp(rd)

    if not mount_esp(esp_part):
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(3)

    delete_entries(rd)
    
    if not refind_install():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(4)
    
    unmount_esp()
    logging.info("rEFInd installed successfully!")

    if not sign_linux_kernel():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(5)

    copy_files()

    if sb_state:
        logging.info("SecureBoot is Enabled, please reboot the system.")
    else:
        logging.info("SecureBoot is Disabled, please enable it in the firmware settings.")

    exit(0)

if __name__ == "__main__":
    main()
