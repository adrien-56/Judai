import requests
import random
import string
import time
import os
import imaplib
import email
import re
from datetime import datetime
from colorama import Fore, Style, init
from zendriver import ZenDriver

# === ADVANCED CONFIGURATION ===
MAILTM_API = "https://api.mail.tm"
IMAP_SERVER = "imap.mail.tm"
IMAP_PORT = 993
MAIL_SUBJECT_KEYWORD = "verify"
WAIT_TIMEOUT = 180
POLL_INTERVAL = 5
DISCORD_PASSWORD_LENGTH = 16
DISCORD_PASSWORD_CHARS = string.ascii_letters + string.digits + "!@#$%^&*-_"
DISCORD_REGISTRATION_URL = "https://discord.com/register"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BIRTH_YEAR_RANGE = (1990, 2005)
BIRTH_MONTHS = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
]

# --- TOGGLE/SETTINGS ---
USE_PROXY = True            # Toggle proxy use (True/False)
HEADLESS = False            # Toggle headless browser (True/False)
PROXY_LIST_FILE = "proxies.txt"  # Place proxies (one per line, ip:port or user:pass@ip:port)
DISCORD_BOT_WEBHOOK = "https://discord.com/api/webhooks/WEBHOOKID/TOKEN"  # Replace with your webhook url

banner = f'''
██████╗ ██╗██╗   ██╗███████╗██████╗ 
██╔══██╗██║██║   ██║██╔════╝██╔══██╗
██████╔╝██║██║   ██║█████╗  ██████╔╝
██╔══██╗██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
██║  ██║██║ ╚████╔╝ ███████╗██║  ██║
╚═╝  ╚═╝╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝                                                     
            Ricer
      by .kevhhh
'''

def timestamp():
    return f"{Fore.LIGHTBLACK_EX}[{datetime.now().strftime('%H:%M:%S %d-%m-%Y')}]"

def random_password(length=DISCORD_PASSWORD_LENGTH):
    return ''.join(random.choices(DISCORD_PASSWORD_CHARS, k=length))

def random_username(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_displayname():
    return ''.join(random.choices(string.ascii_letters, k=random.randint(6, 12)))

def random_birthdate():
    day = str(random.randint(1, 28))
    month = random.choice(BIRTH_MONTHS)
    year = str(random.randint(*BIRTH_YEAR_RANGE))
    return day, month, year

def load_proxies():
    if not os.path.exists(PROXY_LIST_FILE):
        print(f"{timestamp()} {Fore.YELLOW}No proxies.txt found, running without proxy.{Style.RESET_ALL}")
        return []
    with open(PROXY_LIST_FILE, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    if not proxies:
        print(f"{timestamp()} {Fore.YELLOW}No proxies loaded, running without proxy.{Style.RESET_ALL}")
    return proxies

def get_random_proxy():
    proxies = load_proxies()
    if not proxies:
        return None
    proxy = random.choice(proxies)
    if "@" in proxy:  # user:pass@host:port
        auth, addr = proxy.split("@")
        host, port = addr.split(":")
        user, pwd = auth.split(":")
        return {
            "http": f"http://{user}:{pwd}@{host}:{port}",
            "https": f"http://{user}:{pwd}@{host}:{port}"
        }
    elif ":" in proxy:
        host, port = proxy.split(":")
        return {
            "http": f"http://{host}:{port}",
            "https": f"http://{host}:{port}"
        }
    return None

def mailtm_create_account(proxies=None):
    session = requests.Session()
    if proxies:
        session.proxies = proxies
    domain_resp = session.get(f"{MAILTM_API}/domains", timeout=30)
    domain_resp.raise_for_status()
    domain = domain_resp.json()['hydra:member'][0]['domain']
    username = random_username()
    email_addr = f"{username}@{domain}"
    password = random_password(14)
    acc_resp = session.post(f"{MAILTM_API}/accounts", json={
        "address": email_addr,
        "password": password
    }, timeout=30)
    acc_resp.raise_for_status()
    print(f"{timestamp()} {Fore.CYAN}Mail.tm account created: {email_addr}{Style.RESET_ALL}")
    return email_addr, password

def wait_for_verification_email_imap(email_addr, password, subject_contains="verify", timeout=WAIT_TIMEOUT, poll_interval=POLL_INTERVAL, proxies=None):
    # IMAP does NOT support proxies natively; use proxychains or similar if needed
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(email_addr, password)
            mail.select('inbox')
            result, data = mail.search(None, 'ALL')
            if result == "OK":
                mail_ids = data[0].split()
                for mail_id in reversed(mail_ids):
                    result, msg_data = mail.fetch(mail_id, '(RFC822)')
                    if result == "OK":
                        msg = email.message_from_bytes(msg_data[0][1])
                        subject = str(email.header.make_header(email.header.decode_header(msg['Subject'])))
                        if subject_contains.lower() in subject.lower():
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    ctype = part.get_content_type()
                                    if ctype == "text/html":
                                        body = part.get_payload(decode=True).decode(errors='ignore')
                                        break
                                    elif ctype == "text/plain" and not body:
                                        body = part.get_payload(decode=True).decode(errors='ignore')
                            else:
                                body = msg.get_payload(decode=True).decode(errors='ignore')
                            mail.logout()
                            return {"subject": subject, "body": body}
            mail.logout()
        except Exception as e:
            print(f"{timestamp()} {Fore.YELLOW}IMAP error: {e}{Style.RESET_ALL}")
        time.sleep(poll_interval)
    raise TimeoutError("No verification email received in time.")

def extract_verification_link_from_html(html):
    links = re.findall(r'https:\/\/[^\s"\'<>]+', html)
    for link in links:
        if "discord.com/verify" in link or "discord.com/email" in link:
            return link
    return links[0] if links else None

def send_token_to_webhook(email, password, token):
    data = {
        "embeds": [
            {
                "title": "New Verified Discord Token",
                "color": 0x00ff00,
                "fields": [
                    {"name": "Token", "value": f"||{token}||", "inline": False},
                    {"name": "Email", "value": f"{email}", "inline": True},
                    {"name": "Password", "value": f"{password}", "inline": True},
                    {"name": "Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": False}
                ],
                "footer": {"text": "Ricer by .kevhhh"}
            }
        ]
    }
    resp = requests.post(DISCORD_BOT_WEBHOOK, json=data)
    if resp.status_code in (200, 204):
        print(f"{timestamp()} {Fore.GREEN}Token sent to Discord webhook!{Style.RESET_ALL}")
    else:
        print(f"{timestamp()} {Fore.RED}Failed to send token to webhook: {resp.status_code} {resp.text}{Style.RESET_ALL}")

def login_and_fetch_token(email, password, proxies=None):
    data = {"email": email, "password": password, "undelete": "false"}
    headers = {
        "content-type": "application/json",
        "user-agent": USER_AGENT,
    }
    session = requests.Session()
    if proxies:
        session.proxies = proxies
    r = session.post("https://discord.com/api/v9/auth/login", json=data, headers=headers, timeout=30)
    if r.status_code == 200:
        token = r.json().get("token")
        if token:
            print(f"{timestamp()} {Fore.GREEN}Token: {token}{Style.RESET_ALL}")
            send_token_to_webhook(email, password, token)
            return True
    elif "captcha-required" in r.text:
        print(f"{timestamp()} {Fore.RED}Discord returned captcha, stopping retry.{Style.RESET_ALL}")
        return False
    else:
        print(f"{timestamp()} {Fore.RED}Failed to fetch token: {r.status_code} {r.text}{Style.RESET_ALL}")
    return False

def pretty_step(msg):
    print(f"{timestamp()} {Fore.MAGENTA}[STEP]{Style.RESET_ALL} {msg}")

def main():
    init(autoreset=True)
    os.system("cls" if os.name == "nt" else "clear")
    print(banner)
    while True:
        proxies = get_random_proxy() if USE_PROXY else None
        username = random_username()
        global_name = random_displayname()
        birth_day, birth_month, birth_year = random_birthdate()
        discord_password = random_password()
        email_addr, email_pass = mailtm_create_account(proxies=proxies)
        pretty_step(
            f"Using temp email: {Fore.BLUE}{email_addr}{Style.RESET_ALL}, "
            f"Username: {Fore.BLUE}{username}{Style.RESET_ALL}, "
            f"Display: {Fore.BLUE}{global_name}{Style.RESET_ALL}, "
            f"Password: {Fore.BLUE}{discord_password}{Style.RESET_ALL}, "
            f"Proxy: {Fore.BLUE}{proxies['http'] if proxies else 'None'}{Style.RESET_ALL}"
        )

        driver = ZenDriver(headless=HEADLESS, proxy=proxies['http'] if proxies else None)
        try:
            driver.goto(DISCORD_REGISTRATION_URL)
            driver.wait_for_selector('input[name="email"]')

            # Fill registration
            driver.type('input[name="email"]', email_addr)
            driver.type('input[name="global_name"]', global_name)
            driver.type('input[name="username"]', username)
            driver.type('input[name="password"]', discord_password)

            # Date of birth selection
            driver.click('#react-select-3-input')
            driver.type('#react-select-3-input', f"{birth_day}\n")
            driver.click('#react-select-2-input')
            driver.type('#react-select-2-input', f"{birth_month}\n")
            driver.click('#react-select-4-input')
            driver.type('#react-select-4-input', f"{birth_year}\n")

            driver.wait_for_selector('button[type="submit"]')
            driver.click('button[type="submit"]')

            pretty_step(
                f"{Fore.YELLOW}Solve the CAPTCHA in the browser, then press Enter here when registration is complete.{Style.RESET_ALL}"
            )
            input()
            pretty_step("Waiting for verification email via IMAP...")

            try:
                mail = wait_for_verification_email_imap(
                    email_addr, email_pass, subject_contains=MAIL_SUBJECT_KEYWORD,
                    timeout=WAIT_TIMEOUT, poll_interval=POLL_INTERVAL
                )
                print(f"{timestamp()} {Fore.GREEN}Verification email received: {mail['subject']}{Style.RESET_ALL}")
                link = extract_verification_link_from_html(mail["body"])
                if link:
                    pretty_step("Opening verification link in browser...")
                    driver.goto(link)
                    print(
                        f"{timestamp()} {Fore.YELLOW}If there is a CAPTCHA on the verification page, solve it. "
                        f"Press Enter once the account is verified in the browser...{Style.RESET_ALL}"
                    )
                    input()
                    time.sleep(5)
                else:
                    print(f"{timestamp()} {Fore.RED}Could not extract verification link from email.{Style.RESET_ALL}")
            except TimeoutError:
                print(f"{timestamp()} {Fore.RED}Verification email did not arrive in time.{Style.RESET_ALL}")

            pretty_step("Trying to fetch Discord token...")
            success = login_and_fetch_token(email_addr, discord_password, proxies=proxies)
            if success:
                print(f"{timestamp()} {Fore.GREEN}Account created and verified! Restarting...{Style.RESET_ALL}")
            else:
                print(f"{timestamp()} {Fore.RED}Failed to fetch the token.{Style.RESET_ALL}")

        except Exception as e:
            print(f"{timestamp()} {Fore.RED}Error: {e}{Style.RESET_ALL}")
        finally:
            driver.close()

if __name__ == "__main__":
    main()
