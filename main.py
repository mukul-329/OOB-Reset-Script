import paramiko
import time
import re
import os

CSV_FILE = "oob.csv"

USERNAME = os.getenv("OOB_USERNAME")
PASSWORD = os.getenv("OOB_PASSWORD")

WAIT_AFTER_RESET = 120
RETRY_INTERVAL = 10
MAX_RETRIES = 12


def load_hosts_from_csv(file_path):
    with open(file_path, "r") as f:
        content = f.read().strip()
        hosts = [h.strip() for h in content.split("\n") if h.strip()]
    return hosts


def run_command(client, command):
    stdin, stdout, stderr = client.exec_command(command)
    return stdout.read().decode(), stderr.read().decode()


def get_modem_id(output):
    match = re.search(r'/Modem/(\d+)', output)
    return match.group(1) if match else None


def process_host(host):
    print(f"\n🔗 Connecting to {host}...")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=USERNAME, password=PASSWORD, timeout=10)

        # Step 1: Get modem
        output, _ = run_command(client, "mmcli -L")
        modem_id = get_modem_id(output)

        if not modem_id:
            print(f"❌ [{host}] No modem found")
            return

        print(f"✅ [{host}] Modem ID: {modem_id}")

        # Step 2: Reset
        print(f"🔄 [{host}] Resetting modem...")
        run_command(client, f"mmcli -m {modem_id} --reset")

        #time.sleep(WAIT_AFTER_RESET)---Commenting out for optimization, will rely on retries to detect modem instead of fixed wait


        # Step 3: Detect new modem
        new_modem_id = None
        for attempt in range(MAX_RETRIES):
            time.sleep(RETRY_INTERVAL)
            output, _ = run_command(client, "mmcli -L")
            new_modem_id = get_modem_id(output)

            new_modem_id= new_modem_id if new_modem_id != modem_id else None

            if new_modem_id:
                break

        if not new_modem_id:
            print(f"❌ [{host}] New modem not detected")
            return

        print(f"✅ [{host}] New Modem: {new_modem_id}")

        # Step 4: Enable
        run_command(client, f"mmcli -m {new_modem_id} --enable")
        print(f"🚀 [{host}] Modem enabled successfully")

        client.close()

    except Exception as e:
        print(f"⚠️ [{host}] Error: {str(e)}")


def main():
    hosts = load_hosts_from_csv(CSV_FILE)

    print("\n⚠️ You are about to reset modems on the following hosts:\n")
    print(f"📄 Loaded {len(hosts)} hosts \n {hosts}")
    if input("\nType 'yes' to continue: ").strip().lower() != "yes":
        print("Aborting...")
        return
    for host in hosts:
        process_host(host)

if __name__ == "__main__":
    main()