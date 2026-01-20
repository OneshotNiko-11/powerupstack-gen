import requests
import random
import string
import threading
import time
import os
import re
from colorama import init, Fore

init()

def load_proxies():
    try:
        with open("proxies.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            if proxies:
                print(Fore.YELLOW + f"[*] {len(proxies)} proxies")
            return proxies
    except:
        return []

def get_proxy(proxies, index):
    if not proxies:
        return None
    return proxies[index % len(proxies)]

def setup_session_proxy(session, proxy_str):
    if proxy_str:
        try:
            session.proxies.update({
                'http': f'socks5://{proxy_str}',
                'https': f'socks5://{proxy_str}'
            })
        except:
            pass
    return session

def create_temp_inbox(session):
    try:
        url = 'https://api.internal.temp-mail.io/api/v3/email/new'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        payload = {"min_name_length": 10, "max_name_length": 10}
        response = session.post(url, headers=headers, json=payload, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        email = data.get('email')
        return email
    except:
        return None

def get_temp_mail_messages(session, email):
    try:
        url = f'https://api.internal.temp-mail.io/api/v3/email/{email}/messages'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        response = session.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
        return []
    except:
        return []

def extract_verification_link(messages):
    for message in messages:
        subject = message.get('subject', '').lower()
        body_text = message.get('body_text', '')

        if 'verify' in subject or 'confirm' in subject:
            pattern = r'https://www\.powerupstack\.com/verify-email/[a-f0-9]+'
            match = re.search(pattern, body_text)
            if match:
                return match.group(0)

    return None

def wait_for_verification_link(session, email, max_wait=120):
    print(Fore.YELLOW + f"[*] waiting for verify link...")

    for check in range(1, int(max_wait/5) + 1):
        #print(Fore.CYAN + f"[*] check {check}")

        messages = get_temp_mail_messages(session, email)

        if messages:
            print(Fore.MAGENTA + f"[*] {len(messages)} messages")

        link = extract_verification_link(messages)
        if link:
            print(Fore.GREEN + f"[✓] VERIFY LINK")
            return link

        time.sleep(5)

    #print(Fore.RED + f"[-] no verify link")
    return None

def generate_username():
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

def generate_password(username):
    # Generate password different from username
    while True:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(12))
        if password.lower() != username.lower():
            return password

def create_account(proxies, target_accounts, accounts_created, lock, running, proxy_index_counter, use_proxies, verify_email):
    while running[0]:
        with lock:
            if accounts_created[0] >= target_accounts:
                break
            proxy_index = proxy_index_counter[0]
            proxy_index_counter[0] += 1

        proxy = get_proxy(proxies, proxy_index) if use_proxies else None
        session = requests.Session()
        if proxy:
            session = setup_session_proxy(session, proxy)

        try:
            email = create_temp_inbox(session)
            if not email:
                #print(Fore.RED + "[-] email fail")
                continue

            print(Fore.CYAN + f"[+] EMAIL: {email}")

            username = email.split('@')[0]
            password = generate_password(username)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/json',
                'Origin': 'https://www.powerupstack.com',
                'Referer': 'https://www.powerupstack.com/',
            }

            print(Fore.YELLOW + "[*] registering...")

            url = 'https://www.powerupstack.com/v1/auth/register'

            data = {
                'acceptTerms': True,
                'email': email,
                'password': password
            }

            response = session.post(url, headers=headers, json=data, timeout=15)

            print(Fore.MAGENTA + f"[*] status: {response.status_code}")

            if response.status_code != 200:
                print(Fore.RED + f"[-] register fail: {response.status_code}")
                #print(Fore.RED + f"[*] response: {response.text[:200]}")
                continue

            try:
                result = response.json()
                print(Fore.MAGENTA + f"[*] response: {result}")
            except:
                #print(Fore.RED + "[-] json parse fail")
                continue

            access_token = result.get('accessToken')
            if not access_token:
                #print(Fore.RED + "[-] no access token")
                continue

            print(Fore.GREEN + f"[✓] REGISTERED")
            print(Fore.GREEN + f"[✓] TOKEN: {access_token[:30]}...")

            if verify_email:
                print(Fore.YELLOW + "[*] waiting for verification email...")
                verify_link = wait_for_verification_link(session, email)

                if verify_link:
                    print(Fore.YELLOW + "[*] clicking verify link...")
                    verify_headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    }

                    response = session.get(verify_link, headers=verify_headers, timeout=15)

                    if response.status_code == 200:
                        print(Fore.GREEN + f"[✓] EMAIL VERIFIED")
                    else:
                        print(Fore.RED + f"[-] verify fail: {response.status_code}")
                else:
                    print(Fore.RED + "[-] no verify link found")

            with lock:
                if accounts_created[0] < target_accounts:
                    accounts_created[0] += 1
                    with open("powerupstack_accs.txt", "a") as f:
                        f.write(f"{email}:{password}|{access_token}\n")
                    print(Fore.GREEN + f"[✓] ACCOUNT SAVED: {email}")

        except:
            continue

        delay = random.uniform(5, 10)
        print(Fore.CYAN + f"[*] wait {delay:.1f} sec")
        time.sleep(delay)

def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    print(Fore.LIGHTYELLOW_EX + "POWERUPSTACK ACC GEN")
    print(Fore.YELLOW + "[*] Saves as email:password|accessToken")
    print(Fore.RED + "[!] Once a few accounts have been made on one IP, it doesn't let you create another one for a few days - use different proxies instead of the same ones")

    proxies = []
    use_proxies = False

    use_proxy_input = input(Fore.LIGHTCYAN_EX + "Use proxies? (y/n): " + Fore.WHITE).lower()
    if use_proxy_input == 'y':
        proxies = load_proxies()
        if not proxies:
            print(Fore.RED + "[!] no proxies.txt")
            return
        use_proxies = True
        print(Fore.GREEN + "[+] PROXIES")
    else:
        print(Fore.YELLOW + "[*] NO PROXIES")

    verify_email_input = input(Fore.LIGHTCYAN_EX + "Verify email? (y/n) (optional, not recommended cuz their bot sends emails super slow): " + Fore.WHITE).lower()
    verify_email = verify_email_input == 'y'

    if verify_email:
        print(Fore.YELLOW + "[*] WITH EMAIL VERIFICATION")
    else:
        print(Fore.YELLOW + "[*] WITHOUT EMAIL VERIFICATION")

    try:
        target_accounts = int(input(Fore.LIGHTCYAN_EX + "Accounts to make: " + Fore.WHITE))
        threads_count = int(input(Fore.LIGHTCYAN_EX + "Threads: " + Fore.WHITE))
    except:
        return

    accounts_created = [0]
    running = [True]
    lock = threading.Lock()
    proxy_index_counter = [0]
    threads = []

    for i in range(threads_count):
        thread = threading.Thread(target=create_account, args=(proxies, target_accounts, accounts_created, lock, running, proxy_index_counter, use_proxies, verify_email), daemon=True)
        threads.append(thread)
        thread.start()
        print(Fore.YELLOW + f"[*] Thread {i+1}")

    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1)
            with lock:
                current = accounts_created[0]
            print(Fore.LIGHTMAGENTA_EX + f"\r[*] PROGRESS: {current}/{target_accounts}", end="")
            if current >= target_accounts:
                running[0] = False
                break
    except KeyboardInterrupt:
        running[0] = False
        print(Fore.RED + "\n\n[!] STOP")

    print(Fore.LIGHTGREEN_EX + f"\n\n✅ DONE: {accounts_created[0]} accounts")
    print(Fore.LIGHTBLUE_EX + f"[*] saved to powerupstack_accs.txt")

if __name__ == "__main__":
    main()
