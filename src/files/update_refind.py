import subprocess
import logging

def check_packages() -> bool:
    logging.debug("Checking if the packages refind, mokutil, sbsigntools are installed")
    required_packages = ["refind", "mokutil", "sbsigntools", "shim-signed"]

    for package in required_packages:

        cmd = "pacman -Q " + package
        check_code = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode

        if check_code:
            if package == "shim-signed":
                logging.error("Package shim-signed is not installed, install it from aur first and run 'sudo python /etc/refind.d/update_refind.py'!")
                return False

            logging.warning("Package %s is not installed, installing", package)
            
            cmd = "yes | pacman -S " + package
            install_result = subprocess.run(cmd, shell=True).returncode
            
            if install_result:
                logging.error("Failed to install package %s. Aborting!", package)

                return False

    logging.info("Required packages are installed.")    
    return True

def get_refind_data() -> list:
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

def find_esp(refind_data: list) -> str:
    esp_partuuid = refind_data[0][1]
    logging.debug("Trying to find partition with PARTUUID %s", esp_partuuid)
    cmd = "lsblk --output NAME,PARTUUID | grep " + esp_partuuid
    
    lsblk_ouput = subprocess.run(cmd,shell=True, stdout=subprocess.PIPE).stdout.decode("utf-8")
    esp_part = "/dev/" + lsblk_ouput.split(" ")[0].replace("├─","").replace("└─","")
    logging.info("Found ESP Partition %s", esp_part)

    return esp_part

def delete_entries(refind_data: list) -> None:
    logging.debug("Deleting rEFInd entries")

    for entry in refind_data:
        cmd = "efibootmgr --delete-bootnum --bootnum " + entry[0]
        subprocess.run(cmd, shell=True)

def mount_esp(esp_partition: str) -> bool:
    logging.debug("Trying to mount ESP Partition %s to %s", esp_partition, "/boot/efi")

    cmd = "mount " + esp_partition + " /boot/efi"
    run_code = subprocess.run(cmd, shell=True).returncode
    
    if run_code:
        logging.error("Failed to mount %s to /boot/efi!", esp_partition)
        
        return False
    
    logging.info("Mounted successfully")
    return True
    
def unmount_esp() -> None:
    logging.debug("Unmounting ESP Partiton")

    cmd = "umount -R /boot/efi"
    subprocess.run(cmd, shell=True)

def refind_install() -> bool:
    logging.debug("Running refind-install to upgrade rEFInd installation.")
    
    cmd = "refind-install --shim /usr/share/shim-signed/shimx64.efi --localkeys"
    install_code = subprocess.run(cmd, shell=True).returncode

    if install_code:
        logging.error("refind-install failed!")
        return False
    
    return True


def main() -> None:
    logging.basicConfig(format="%(levelname)s:%(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if not check_packages():
        logging.error("Failed to upgrade rEFInd, please run the steps manually!")
        exit(1)

    rd = get_refind_data()

    if rd == None:
        logging.error("Aborting! Please install rEFInd Boot Loader first!")
        exit(2)

    esp_part = find_esp(rd)

    if  not mount_esp(esp_part):
        logging.error("Failed to upgrade rEFInd, please run the steps manually!")
        exit(3)

    delete_entries(rd)
    
    if not refind_install():
        logging.error("Failed to upgrade rEFInd, please run the steps manually!")
        exit(4)
    
    unmount_esp()
    logging.info("rEFInd upgraded successfully!")

    exit(0)

if __name__ == "__main__":
    main()
