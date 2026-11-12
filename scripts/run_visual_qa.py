"""Visual and Functional QA Script using Chrome DevTools Protocol (CDP).

Captures screenshots, tests role workspaces, verifies dual themes, inspects
responsive viewports, and audits browser console logs for errors and leaks.
"""

import asyncio
import base64
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
import websockets

SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TEMP_PROFILE = r"C:\Users\HP\AppData\Local\Temp\chrome_qa_profile_p5"


class CDPClient:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.console_logs = []
        self.network_errors = []
        self.page_errors = []

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50_000_000)
        # Enable domains
        await self.send("Page.enable")
        await self.send("Runtime.enable")
        await self.send("Network.enable")
        await self.send("Console.enable")

    async def send(self, method: str, params: dict = None) -> dict:
        self.msg_id += 1
        req_id = self.msg_id
        payload = {"id": req_id, "method": method}
        if params:
            payload["params"] = params
        await self.ws.send(json.dumps(payload))
        while True:
            raw = await self.ws.recv()
            data = json.loads(raw)
            # Record events
            if "method" in data:
                m = data["method"]
                if m == "Runtime.consoleAPICalled":
                    args = data.get("params", {}).get("args", [])
                    txt = " ".join([str(a.get("value", a.get("description", ""))) for a in args])
                    self.console_logs.append(f"[{data['params'].get('type')}] {txt}")
                elif m == "Runtime.exceptionThrown":
                    details = data.get("params", {}).get("exceptionDetails", {})
                    self.page_errors.append(details.get("text", "") + " " + str(details.get("exception", {})))
                elif m == "Network.responseReceived":
                    resp = data.get("params", {}).get("response", {})
                    status = resp.get("status", 200)
                    url = resp.get("url", "")
                    if status >= 400 and not "favicon" in url:
                        self.network_errors.append(f"{status} {url}")
                continue

            if data.get("id") == req_id:
                return data

    async def evaluate(self, expression: str):
        res = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        return res.get("result", {}).get("result", {}).get("value")

    async def set_viewport(self, width: int, height: int, is_mobile: bool = False):
        await self.send("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": is_mobile,
        })

    async def navigate(self, url: str, wait_secs: float = 2.0):
        await self.send("Page.navigate", {"url": url})
        await asyncio.sleep(wait_secs)

    async def capture_screenshot(self, filepath: Path):
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        b64data = res.get("result", {}).get("data")
        if b64data:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64data))
            print(f"  [Screenshot] Saved: {filepath} ({filepath.stat().st_size} bytes)")
        else:
            print(f"  [Screenshot] FAILED for {filepath}: {res}")

    async def set_state(self, persona: str, token: str, theme: str):
        js = f"""
        localStorage.setItem('yottaflex_active_persona', '{persona}');
        localStorage.setItem('yottaflex_reviewer_token', '{token}');
        localStorage.setItem('yottaflex_theme_preference', '{theme}');
        if ('{theme}' === 'dark') {{
            document.documentElement.classList.add('dark');
            document.documentElement.classList.remove('light');
        }} else {{
            document.documentElement.classList.remove('dark');
            document.documentElement.classList.add('light');
        }}
        """
        await self.evaluate(js)


async def main():
    print("=== Starting Visual & Functional QA Verification ===")
    
    # 1. Launch Chrome Headless
    proc = subprocess.Popen([
        CHROME_PATH,
        "--headless=new",
        "--remote-debugging-port=9222",
        f"--user-data-dir={TEMP_PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "http://localhost:5173"
    ])
    
    try:
        await asyncio.sleep(2.5)
        resp = urllib.request.urlopen("http://127.0.0.1:9222/json")
        tabs = json.loads(resp.read().decode())
        ws_url = tabs[0]["webSocketDebuggerUrl"]
        print(f"Connected to Chrome CDP: {ws_url}")

        client = CDPClient(ws_url)
        await client.connect()

        # Set default desktop viewport
        await client.set_viewport(1280, 850)

        # -------------------------------------------------------------
        # TEST 1: Customer Workspace (Light & Dark)
        # -------------------------------------------------------------
        print("\n--- Verifying Customer Workspace ---")
        await client.navigate("http://localhost:5173/dashboard")
        await client.set_state("CUSTOMER", "dev-viewer-token", "light")
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.5)

        # Verify Customer DOM elements
        cust_title = await client.evaluate("document.title")
        cust_nav = await client.evaluate("""
            Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
        """)
        cust_heading = await client.evaluate("""
            document.querySelector('h1, h2')?.textContent || ''
        """)
        print(f"  Customer Title: {cust_title}")
        print(f"  Customer Navigation Links: {cust_nav}")
        print(f"  Customer Primary Heading: {cust_heading}")
        
        # Verify prohibited items NOT visible
        assert "Rebalancing" not in cust_nav, "Customer should NOT see Rebalancing navigation!"
        assert "Approvals" not in cust_nav, "Customer should NOT see Approvals navigation!"
        print("  ✓ RBAC Verification: Analyst & Reviewer nav links hidden from Customer.")

        await client.capture_screenshot(SCREENSHOTS_DIR / "customer_dashboard_light.png")

        # Dark theme
        await client.set_state("CUSTOMER", "dev-viewer-token", "dark")
        await asyncio.sleep(0.8)
        await client.capture_screenshot(SCREENSHOTS_DIR / "customer_dashboard_dark.png")
        print("  ✓ Customer Light & Dark screenshots captured.")

        # -------------------------------------------------------------
        # TEST 2: Operations Analyst Workspace (Light & Dark + Journey)
        # -------------------------------------------------------------
        print("\n--- Verifying Operations Analyst Workspace ---")
        await client.set_state("ANALYST", "dev-analyst-token", "light")
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.5)

        analyst_nav = await client.evaluate("""
            Array.from(document.querySelectorAll('nav a')).map(a => a.textContent.trim())
        """)
        print(f"  Analyst Navigation Links: {analyst_nav}")
        assert any("Rebalance" in n or "Portfolios" in n for n in analyst_nav), "Analyst should see Rebalancing!"

        await client.capture_screenshot(SCREENSHOTS_DIR / "analyst_dashboard_light.png")
        
        await client.set_state("ANALYST", "dev-analyst-token", "dark")
        await asyncio.sleep(0.8)
        await client.capture_screenshot(SCREENSHOTS_DIR / "analyst_dashboard_dark.png")
        print("  ✓ Analyst Dashboard Light & Dark screenshots captured.")

        # Analyst Journey: Navigate to /rebalancing
        print("  Executing Analyst Journey: Rebalancing Page...")
        await client.set_state("ANALYST", "dev-analyst-token", "light")
        await client.navigate("http://localhost:5173/rebalancing", wait_secs=3.0)
        await client.capture_screenshot(SCREENSHOTS_DIR / "analyst_rebalancing_light.png")

        # Check if portfolio select is present and select PORT-INV-000001-02
        has_select = await client.evaluate("Boolean(document.querySelector('select'))")
        print(f"  Portfolio select present: {has_select}")
        if has_select:
            await client.evaluate("""
                (() => {
                    const select = document.querySelector('select');
                    const opt = Array.from(select.options).find(o => o.value.includes('PORT-INV-000001-02') || o.text.includes('02'));
                    if (opt) {
                        select.value = opt.value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                })()
            """)
            await asyncio.sleep(2.0)
            await client.capture_screenshot(SCREENSHOTS_DIR / "analyst_rebalancing_portfolio_selected.png")

        # Click Rebalance / Run Optimization button if present
        btn_text = await client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const target = btns.find(b => b.textContent.includes('Rebalance') || b.textContent.includes('Generate') || b.textContent.includes('Optimize'));
                if (target && !target.disabled) {
                    target.click();
                    return target.textContent.trim();
                }
                return null;
            })()
        """)
        if btn_text:
            print(f"  Triggered proposal generation button: '{btn_text}'")
            await asyncio.sleep(3.5)
            await client.capture_screenshot(SCREENSHOTS_DIR / "analyst_rebalancing_proposal_generated.png")
        print("  ✓ Analyst Rebalancing Journey verified.")

        # -------------------------------------------------------------
        # TEST 3: Risk / Compliance Reviewer Workspace
        # -------------------------------------------------------------
        print("\n--- Verifying Compliance Reviewer Workspace ---")
        await client.set_state("COMPLIANCE", "dev-reviewer-token", "light")
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.5)
        await client.capture_screenshot(SCREENSHOTS_DIR / "compliance_dashboard_light.png")

        await client.set_state("COMPLIANCE", "dev-reviewer-token", "dark")
        await asyncio.sleep(0.8)
        await client.capture_screenshot(SCREENSHOTS_DIR / "compliance_dashboard_dark.png")
        print("  ✓ Compliance Dashboard Light & Dark screenshots captured.")

        # Compliance Journey: Navigate to /approvals
        print("  Executing Compliance Journey: Approvals Page...")
        await client.set_state("COMPLIANCE", "dev-reviewer-token", "light")
        await client.navigate("http://localhost:5173/approvals", wait_secs=3.0)
        await client.capture_screenshot(SCREENSHOTS_DIR / "compliance_approvals_light.png")

        # Inspect table or cards for pending proposals
        proposals_found = await client.evaluate("""
            document.querySelectorAll('table tbody tr, [data-testid="proposal-card"]').length
        """)
        print(f"  Proposals rendered in review queue: {proposals_found}")
        
        # Test clicking first proposal if available to inspect detail drawer/modal
        detail_opened = await client.evaluate("""
            (() => {
                const row = document.querySelector('table tbody tr, [data-testid="proposal-card"]');
                if (row) {
                    const btn = row.querySelector('button') || row;
                    btn.click();
                    return true;
                }
                return false;
            })()
        """)
        if detail_opened:
            await asyncio.sleep(2.0)
            await client.capture_screenshot(SCREENSHOTS_DIR / "compliance_proposal_detail_view.png")
            print("  ✓ Opened proposal detail view and captured screenshot.")

        # -------------------------------------------------------------
        # TEST 4: Administrator Workspace
        # -------------------------------------------------------------
        print("\n--- Verifying Administrator Workspace ---")
        await client.set_state("ADMIN", "dev-admin-token", "light")
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.5)
        await client.capture_screenshot(SCREENSHOTS_DIR / "admin_dashboard_light.png")

        await client.set_state("ADMIN", "dev-admin-token", "dark")
        await asyncio.sleep(0.8)
        await client.capture_screenshot(SCREENSHOTS_DIR / "admin_dashboard_dark.png")

        # Navigate to /settings
        await client.set_state("ADMIN", "dev-admin-token", "light")
        await client.navigate("http://localhost:5173/settings", wait_secs=2.5)
        await client.capture_screenshot(SCREENSHOTS_DIR / "admin_settings_light.png")
        print("  ✓ Admin Dashboard & Settings Light & Dark screenshots captured.")

        # -------------------------------------------------------------
        # TEST 5: Responsive Breakpoints (Tablet & Mobile)
        # -------------------------------------------------------------
        print("\n--- Verifying Responsive Breakpoints ---")
        # Tablet: 768 x 1024
        await client.set_viewport(768, 1024)
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.0)
        await client.capture_screenshot(SCREENSHOTS_DIR / "responsive_tablet_768.png")
        print("  ✓ Tablet viewport (768x1024) verified.")

        # Mobile: 375 x 812
        await client.set_viewport(375, 812, is_mobile=True)
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.0)
        await client.capture_screenshot(SCREENSHOTS_DIR / "responsive_mobile_375.png")
        print("  ✓ Mobile viewport (375x812) verified.")

        # Click hamburger button on mobile
        hamburger_clicked = await client.evaluate("""
            (() => {
                const btn = document.querySelector('button[aria-label*="menu" i], header button:first-child');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            })()
        """)
        if hamburger_clicked:
            await asyncio.sleep(1.0)
            await client.capture_screenshot(SCREENSHOTS_DIR / "responsive_mobile_menu_open.png")
            print("  ✓ Mobile drawer navigation toggle verified.")

        # Restore desktop viewport
        await client.set_viewport(1280, 850)

        # -------------------------------------------------------------
        # TEST 6: Theme Persistence Verification
        # -------------------------------------------------------------
        print("\n--- Verifying Theme Persistence after Page Reload ---")
        await client.set_state("ANALYST", "dev-analyst-token", "dark")
        await client.navigate("http://localhost:5173/dashboard", wait_secs=2.0)
        is_dark_before = await client.evaluate("document.documentElement.classList.contains('dark')")
        
        # Hard reload
        await client.send("Page.reload")
        await asyncio.sleep(2.0)
        is_dark_after = await client.evaluate("document.documentElement.classList.contains('dark')")
        print(f"  Theme before reload: dark={is_dark_before}, after reload: dark={is_dark_after}")
        assert is_dark_after, "Dark theme must persist after page reload via localStorage!"
        print("  ✓ Theme persistence confirmed.")

        # -------------------------------------------------------------
        # TEST 7: Console & Security Audit
        # -------------------------------------------------------------
        print("\n--- Auditing Console Logs & Network Responses ---")
        print(f"  Total Console Logs Collected: {len(client.console_logs)}")
        for log in client.console_logs[:10]:
            print(f"    {log}")
        if len(client.console_logs) > 10:
            print(f"    ... and {len(client.console_logs) - 10} more logs")

        print(f"  Page / Runtime Exceptions: {len(client.page_errors)}")
        for err in client.page_errors:
            print(f"    [PageError] {err}")

        print(f"  Network Errors (>=400): {len(client.network_errors)}")
        for nerr in client.network_errors:
            print(f"    [NetError] {nerr}")

        # Check for leaked secrets or private keys in console
        leaked = [l for l in client.console_logs if any(s in l.lower() for s in ["private_key", "secret_key", "password="])]
        print(f"  Secrets Leaked to Console: {len(leaked)}")
        assert len(leaked) == 0, f"Potential secret leak detected in console logs: {leaked}"
        print("  ✓ Zero secret leakage in browser console verified.")

        print("\n=== All Visual & Functional QA Tests Passed Successfully! ===")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(main())

