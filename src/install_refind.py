import subprocess
import logging

from os import path

def check_packages() -> bool:
    logging.debug("Updating pacman database...")
    cmd = "sudo pacman -Sy"
    subprocess.run(cmd, shell=True)

    logging.debug("Checking if the packages refind and efibootmgr are installed")
    required_packages = ["refind", "efibootmgr"]

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

    logging.info("Required packages are installed.")    
    return True


def detect_esp() -> str:
    logging.debug("Searching for ESP Partitions...")

    detect_cmd = "sudo fdisk --list | grep 'EFI System'"
    detect_output = subprocess.run(detect_cmd, shell=True, stdout=subprocess.PIPE).stdout.decode("UTF-8")

    data = detect_output.split("\n")
    if "" in data:
        data.remove("")
    esp_entries = [entry.split(" ")[0] for entry in data]
    
    choice = 0
    if len(esp_entries) > 1:
        logging.info("Multiple ESP Paritions found, please choose one")
        
        for i in range(0, len(esp_entries)):
            logging.info("%s) %s", i+1, esp_entries[i])

        choice = len(esp_entries) + 1
        while(choice > len(esp_entries)):
            choice = int(input("Enter choice: "))
    
    logging.info("Using ESP Partition %s.", esp_entries[choice-1])
    return esp_entries[choice-1]

    
def mount_esp(esp_partition: str) -> bool:
    logging.debug("Trying to mount ESP Partition %s to %s", esp_partition, "/boot/efi")

    if not path.isdir("/boot/efi"):
        logging.debug("Directory /boot/efi not found, creating...")
        efi_mkdir_cmd = "sudo mkdir /boot/efi"
        subprocess.run(efi_mkdir_cmd, shell=True)

    cmd = "sudo mount " + esp_partition + " /boot/efi"
    run_code = subprocess.run(cmd, shell=True).returncode
    
    if run_code:
        logging.error("Failed to mount %s to /boot/efi!", esp_partition)
        
        return False
    
    logging.info("Mounted successfully")
    return True

def unmount_esp() -> None:
    logging.debug("Unmounting ESP Partiton")

    cmd = "sudo umount -R /boot/efi"
    subprocess.run(cmd, shell=True)

def refind_install() -> bool:
    logging.debug("Running refind-install to install refind")
    
    cmd = "sudo refind-install"
    install_code = subprocess.run(cmd, shell=True).returncode

    if install_code:
        logging.error("refind-install failed!")
        return False
    
    logging.info("refind successfully installed.")
    return True

def find_root_uuid() -> str:
    logging.debug("Finding root UUID...")

    with open("/etc/fstab", "r") as fp:
        partition_data = fp.read()

    for entry in partition_data.split("\n"):
        if "/" in entry.split():
            root_uuid = entry.split()[0].split("=")[1]
    
    if not root_uuid:
        logging.error("Failed to find root partition UUID!")
        return None

    logging.info("Found root UUID: %s.", root_uuid)
    return root_uuid

def update_refind_linux_conf(root_uuid: str) -> None:
    REFIND_ENTRY = """
"Boot with standard options"  "rw root=UUID={uuid} initrd=/boot/initramfs-linux.img {microcode_initrd}"
"Boot to single-user mode"    "rw root=UUID={uuid} initrd=/boot/initramfs-linux.img {microcode_initrd} single"
"Boot with minimal options"   "rw root=UUID={uuid}"
"""
    
    logging.debug("Checking if microcode image is found in /boot")
    if path.isfile("/boot/intel-ucode.img"):
        logging.info("Intel Microcode image found (/boot/intel-ucode.img)")
        REFIND_ENTRY = REFIND_ENTRY.format(uuid=root_uuid, microcode_initrd="initrd=/boot/intel-ucode.img")
    elif path.isfile("/boot/amd-ucode.img"):
        logging.info("AMD Microcode image found (/boot/amd-ucode.img)")
        REFIND_ENTRY = REFIND_ENTRY.format(uuid=root_uuid, microcode_initrd="initrd=/boot/amd-ucode.img")
    else:
        logging.info("No Microcode images found. Skipping...")
        REFIND_ENTRY = REFIND_ENTRY.format(uuid=root_uuid, microcode_initrd="")

    logging.debug("Updating /boot/refind_linux.conf...")
    with open("/boot/refind_linux.conf", "w") as fp:
        fp.write(REFIND_ENTRY)

    logging.info("Updated /boot/refind.conf.")

def main() -> None:
    logging.basicConfig(format="%(levelname)s:%(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if not check_packages():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(1)

    esp_part = detect_esp()
    root_uuid = find_root_uuid()

    if root_uuid == None:
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(2)

    if not mount_esp(esp_part):
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(3)
    
    if not refind_install():
        logging.error("Failed to install rEFInd, please run the steps manually!")
        exit(4)
    
    update_refind_linux_conf(root_uuid)

    unmount_esp()
    logging.info("rEFInd installed successfully!")

    exit(0)

if __name__ == "__main__":
    main()