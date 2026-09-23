import asyncio
from playwright.async_api import async_playwright

async def login_stealth():
    async with async_playwright() as p:
        # Lança o Google Chrome REAL em vez do Chromium genérico do Playwright
        browser = await p.chromium.launch(
            channel="chrome",  # Usa o teu Chrome instalado
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled", # Esconde que é um browser controlado por bot
                "--start-maximized",
                "--no-sandbox"
            ]
        )
        
        # Cria o contexto simulando um utilizador real
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport=None
        )
        
        page = await context.new_page()

        # Remove a marca de automação do Javascript
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        print("🌐 A abrir a Vinted no Google Chrome...")
        await page.goto("https://www.vinted.pt", wait_until="networkidle")

        print("⏳ Fazer o Login:")
        print("💡 DICA IMPORTANTE: Faz login com Email e Palavra-passe (não uses o botão 'Continuar com Google').")
        
        # Dá 2 minutos para fazeres o login na janela que abriu
        await asyncio.sleep(120)

        # Guarda a sessão
        await context.storage_state(path="state.json")
        print("✅ Sessão guardada com sucesso em 'state.json'!")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(login_stealth())