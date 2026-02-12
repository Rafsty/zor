import re
import requests
import time
import random
from faker import Faker
from playwright.sync_api import sync_playwright

fake = Faker()


def read_mail_credentials():
    """Baca email|password dari file mail.txt"""
    try:
        with open('mail.txt', 'r') as f:
            line = f.readline().strip()
            email, password = line.split('|')
            return email.strip(), password.strip()
    except Exception as e:
        print(f"Error reading mail.txt: {e}")
        return None, None


def login_mailtm(email, password):
    r = requests.post(
        "https://api.mail.tm/token",
        json={"address": email, "password": password}
    )
    return r.json().get("token")


def check_inbox_mailtm(token):
    r = requests.get(
        "https://api.mail.tm/messages",
        headers={"Authorization": f"Bearer {token}"}
    )
    for msg in r.json().get("hydra:member", []):
        code = read_email_message(token, msg["id"])
        if code:
            return code
    return None


def read_email_message(token, msg_id):
    r = requests.get(
        f"https://api.mail.tm/messages/{msg_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    text = r.json().get("text", "")
    match = re.search(r"\b\d{6}\b", text)
    return match.group(0) if match else None


def test_generate_and_post_image_on_zora():
    email, password = read_mail_credentials()
    if not email or not password:
        print("Gagal membaca mail.txt")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        # 1. Buka website Zora
        print("1. Membuka zora.co...")
        page.goto("https://zora.co", wait_until="networkidle", timeout=45000)
        print(f"Menggunakan email: {email}")

        # 2. Klik tombol "+"
        print("2. Mencari tombol +...")
        page.wait_for_timeout(3000)

        plus_selectors = [
            'button:has(svg path[stroke="currentColor"][d*="128"])',
            'button.Actionable_root__B89VV.Button_--color-neutral',
            'button[style*="padding: 12px"]',
            'button:has(svg)',
            '[data-testid="create-button"]'
        ]

        plus_clicked = False
        for selector in plus_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  ✓ Ditemukan dengan selector: {selector}")
                    page.locator(selector).first.click()
                    plus_clicked = True
                    break
            except Exception:
                continue

        if not plus_clicked:
            print("❌ Tombol + tidak ditemukan")
            page.pause()
            return

        # 3. Klik "Continue with email"
        print("3. Mencari tombol Continue with email...")
        page.wait_for_timeout(2000)

        email_selectors = [
            'button:has-text("Continue with email")',
            'button:has(div:has-text("Continue with email"))',
            'button.login-method-button',
            'button:has(svg):has(div:has-text("email"))',
            '[class*="login-method-button"]'
        ]

        email_clicked = False
        for selector in email_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  ✓ Ditemukan dengan selector: {selector}")
                    page.locator(selector).first.click(force=True)
                    email_clicked = True
                    break
            except Exception:
                continue

        if not email_clicked:
            print("❌ Tombol email tidak ditemukan")
            page.pause()
            return

        # 4. Isi email
        print("4. Mengisi email...")
        page.locator("input#email-input").wait_for(state="visible", timeout=10000)
        page.locator("input#email-input").fill(email)

        # 5. Klik Submit
        print("5. Klik Submit...")
        submit_selectors = [
            'button.StyledEmbeddedButton-sc-172643dd-6',
            'button:has(span:has-text("Submit"))',
            'button:has-text("Submit")',
            'button[type="submit"]',
            '[class*="StyledEmbeddedButton"]'
        ]

        submit_clicked = False
        for selector in submit_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  ✓ Submit ditemukan dengan selector: {selector}")
                    page.locator(selector).first.click(force=True)
                    submit_clicked = True
                    break
            except Exception:
                continue

        if not submit_clicked:
            print("❌ Tombol Submit tidak ditemukan")
            page.pause()
            return

        # 6. Mail.tm OTP logic
        print("6. Menunggu OTP...")
        token = login_mailtm(email, password)
        if not token:
            print("Gagal login mail.tm")
            browser.close()
            return

        otp_code = None
        for i in range(30):
            otp_code = check_inbox_mailtm(token)
            if otp_code:
                print(f"OTP ditemukan: {otp_code}")
                break
            print(f"Mencari OTP... ({i + 1}/30)")
            time.sleep(6)

        if not otp_code:
            print("OTP tidak ditemukan")
            browser.close()
            return

        # 7. Isi OTP
        print("7. Mengisi OTP...")
        for i, digit in enumerate(otp_code):
            page.locator(f'input[name="code-{i}"]').fill(digit)
            time.sleep(0.2)

        page.wait_for_timeout(3000)

        # 8. Cek & klik "Start trading" jika ada
        print("8. Cek tombol Start trading...")
        trading_selectors = [
            'button:has-text("Start trading")',
            'button.Button_--color-primary:has(span:has-text("Start trading"))',
            'button:has(span:has-text("Start trading"))'
        ]

        trading_clicked = False
        for selector in trading_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  ✓ Tombol Start trading ditemukan! Selector: {selector}")
                    page.locator(selector).first.click(force=True)
                    trading_clicked = True
                    print("  ✓ Start trading berhasil diklik!")
                    page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        if not trading_clicked:
            print("  ⏭️ Tombol Start trading tidak ada, lanjutkan...")
            page.wait_for_timeout(1500)

        # 9. Cek tombol + pre-generate
        print("9. Cek tombol + pre-generate...")
        pregenerate_plus_selectors = [
            'button:has(svg path[d*="M40 128h176M128 40v176"])',
            'button.Actionable_root__B89VV.Button_--color-neutral__iK_CE.Button_--variant-ghost__QGLMd',
            'button[style*="padding: 12px"][style*="background-color: var(--rs-color-background-neutral-faded)"]',
            'button:has(svg):has([class*="Icon_root__E_X7_"])',
            'button:has(span[aria-hidden="true"] svg)'
        ]

        pregenerate_plus_clicked = False
        for selector in pregenerate_plus_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  ✓ Tombol + pre-generate ditemukan! Selector: {selector}")
                    page.locator(selector).first.click(force=True)
                    pregenerate_plus_clicked = True
                    print("  ✓ Tombol + pre-generate berhasil diklik!")
                    page.wait_for_timeout(45000)
                    break
            except Exception:
                continue

        if not pregenerate_plus_clicked:
            print("  ⏭️ Tombol + pre-generate tidak ada, lanjutkan...")
            page.wait_for_timeout(45000)

        # 10. Cek tombol Generate (ghost)
        print("10. Cek tombol Generate (ghost)...")
        generate_ghost_selectors = [
            'button.Button_--color-neutral-faded__Wn8DX:has-text("Generate")',
            'button.Actionable_root__B89VV.Button_--color-neutral-faded__Wn8DX:has(span:has-text("Generate"))',
            'button.Button_--variant-ghost:has(span:has-text("Generate"))'
        ]

        generate_ghost_clicked = False
        for selector in generate_ghost_selectors:
            try:
                if page.locator(selector).count() > 0:
                    print(f"  ✓ Generate ghost ditemukan! Selector: {selector}")
                    page.locator(selector).first.click(force=True)
                    generate_ghost_clicked = True
                    print("  ✓ Generate ghost berhasil diklik!")
                    page.wait_for_timeout(2000)
                    break
            except Exception:
                continue

        if not generate_ghost_clicked:
            print("  ⏭️ Tombol Generate ghost tidak ada, lanjutkan...")
            page.wait_for_timeout(1500)

        # 11. RANDOM STYLE SELECTOR
        print("11. Pilih style secara random...")
        # More reliable selector - targets all style buttons by their common structure
        style_buttons = page.locator('button.Actionable_root__B89VV:has(div.Text_root__LZy0C)')

        button_count = style_buttons.count()
        print(f"  Total style buttons found: {button_count}")

        if button_count > 0:
            random_index = random.randint(0, button_count - 1)
            print(f"  Memilih style #{random_index + 1}")
    
            # Scroll into view first for better reliability
            style_buttons.nth(random_index).scroll_into_view_if_needed()
            page.wait_for_timeout(200)
    
            style_buttons.nth(random_index).click(force=True)
            print("  ✓ Style random berhasil dipilih!")
            page.wait_for_timeout(1500)  # Increased wait for UI update
        else:
            print("  Tidak ada style buttons ditemukan, skip...")
            # Debug: Print all buttons with Actionable class
            all_actionable = page.locator('button.Actionable_root__B89VV')
            print(f"  Debug: Total Actionable buttons: {all_actionable.count()}")
            page.wait_for_timeout(1000)

        # 12. Isi prompt
        print("12. Mengisi prompt...")
        page.locator(
            'textarea[name="prompt"], textarea[placeholder*="prompt"]'
        ).fill(fake.sentence(nb_words=10))
        page.wait_for_timeout(1500)

         # 13. Generate utama
        print("13. Generate utama...")
        generate_selectors = [
            'button.Button_--color-primary:has-text("Generate")',
            'button.Button_--variant-solid:has-text("Generate")',
            'button.Button_--size-xlarge:has-text("Generate")',
            'button[type="submit"]:has-text("Generate")',
            'button:has-text("Generate")'
        ]

        generate_clicked = False
        for selector in generate_selectors:
            try:
                generate_btn = page.locator(selector).first
                if generate_btn.count() > 0:
                    generate_btn.wait_for(state="visible", timeout=5000)
                    if generate_btn.is_enabled():
                        generate_btn.click(force=True)
                        print(f"  ✓ Generate berhasil! Selector: {selector}")
                        generate_clicked = True
                        break
            except Exception as e:
                print(f"  Skip selector {selector}: {e}")
                continue

        if not generate_clicked:
            print("  ❌ Semua Generate selector gagal")
            page.pause()
            return

        # TAMBAHAN: Tunggu image generate
        print("Menunggu image generate...")
        page.wait_for_load_state("networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        # 14. Isi title & ticker (BUKAN displayName!)
        print("14. Isi title & ticker...")

        # Title field
        random_title = fake.word().capitalize()
        page.locator('input[name="title"]').fill(random_title)
        print(f"Title: {random_title}")
        page.wait_for_timeout(1000)

        # TICKER field (yang kamu tunjukkan)
        random_ticker = ''.join(fake.word().lower() for _ in range(3))[:12]  # 3 huruf, max 12 char
        page.locator('input[name="ticker"]').fill(random_ticker)
        print(f"Ticker: {random_ticker}")
        page.wait_for_timeout(1000)

        # 15. Post
        print("15. Posting...")
        page.get_by_role("button", name="Post").first.click()
        print("✅ Posting berhasil!")

        page.wait_for_timeout(5000)
        browser.close()


if __name__ == "__main__":
    test_generate_and_post_image_on_zora()
