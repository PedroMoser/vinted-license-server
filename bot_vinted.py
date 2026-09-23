import os
import json
import uuid
import asyncio
import subprocess
import requests
from playwright.async_api import async_playwright

API_URL = "https://vinted-sales-api.onrender.com"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "SUA_CHAVE_OPENAI_AQUI")


def obter_hwid():
    return str(uuid.getnode())


def carregar_config_cliente():
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Erro ao ler config.json: {e}")
    return {
        "prompt_ia": "Atua como um vendedor simpático e profissional na Vinted.",
        "desconto_maximo": 10
    }


def obter_produto_ativo():
    if os.path.exists("produtos.json"):
        try:
            with open("produtos.json", "r", encoding="utf-8") as f:
                produtos = json.load(f)
                for prod in produtos:
                    if prod.get("status") in ["Ativo", "Na Fila"]:
                        return prod
        except Exception as e:
            print(f"⚠️ Erro ao carregar produtos.json: {e}")
    return None


def atualizar_status_produto(titulo_prod, novo_status):
    if os.path.exists("produtos.json"):
        try:
            with open("produtos.json", "r", encoding="utf-8") as f:
                produtos = json.load(f)
            
            for prod in produtos:
                if prod.get("titulo") == titulo_prod:
                    prod["status"] = novo_status
                    break
            
            with open("produtos.json", "w", encoding="utf-8") as f:
                json.dump(produtos, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ Erro ao atualizar status no produtos.json: {e}")


def gerar_descricao_com_ia(produto):
    desc_utilizador = produto.get("descricao", "").strip()
    titulo = produto.get("titulo", "")
    marca = produto.get("marca", "")
    tamanho = produto.get("tamanho", "")
    estado = produto.get("condicao") or produto.get("estado", "")

    prompt = f"""
Cria uma descrição atrativa e curta para vender este artigo na Vinted:
- Título: {titulo}
- Marca: {marca}
- Tamanho: {tamanho}
- Estado: {estado}
- Detalhes adicionais: {desc_utilizador if not desc_utilizador.startswith("Detalhes adicionais") else "Nenhuns"}

Inclui emojis adequados e 5 hashtags relevantes no fim.
    """

    if OPENAI_API_KEY and OPENAI_API_KEY != "SUA_CHAVE_OPENAI_AQUI":
        try:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ Erro na IA: {e}")

    texto_extra = desc_utilizador if not desc_utilizador.startswith("Detalhes adicionais") else ""
    return f"{titulo}\n\n• Marca: {marca}\n• Tamanho: {tamanho}\n• Estado: {estado}\n\n{texto_extra}\n\nQualquer dúvida está à vontade para enviar mensagem! 😊"


def obter_lista_fotos(item_fotos):
    if not item_fotos:
        return []
    
    caminhos_validos = []
    if isinstance(item_fotos, list):
        for f in item_fotos:
            caminho_abs = os.path.abspath(f)
            if os.path.exists(caminho_abs):
                caminhos_validos.append(caminho_abs)
    elif isinstance(item_fotos, str) and os.path.exists(item_fotos):
        caminho_abs = os.path.abspath(item_fotos)
        if os.path.isdir(caminho_abs):
            extensoes = ('.png', '.jpg', '.jpeg', '.webp')
            caminhos_validos = [os.path.join(caminho_abs, img) for img in os.listdir(caminho_abs) if img.lower().endswith(extensoes)]
        elif os.path.isfile(caminho_abs):
            caminhos_validos = [caminho_abs]
            
    return caminhos_validos


def garantir_chrome_aberto():
    try:
        requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        return True
    except Exception:
        print("🌐 A iniciar sessão do Chrome...")
        try:
            caminho_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            caminho_perfil = os.path.join(os.getenv("LOCALAPPDATA"), "Google", "Chrome", "User Data", "VintedBotProfile")
            
            subprocess.Popen([
                caminho_chrome,
                "--remote-debugging-port=9222",
                f"--user-data-dir={caminho_perfil}",
                "https://www.vinted.pt"
            ])
            return True
        except Exception as e:
            print(f"❌ Erro ao abrir Chrome: {e}")
            return False


async def publicar_produto_vinted(pagina, produto):
    print(f"\n📦 A iniciar publicação de: '{produto.get('titulo')}'")

    # Definir timeout padrão do Playwright para 4 segundos
    pagina.set_default_timeout(4000)

    # 1. Navegar
    await pagina.goto("https://www.vinted.pt/items/new", wait_until="domcontentloaded")
    await asyncio.sleep(2)

    # 2. Aceitar Cookies (se existir)
    try:
        await pagina.click('#onetrust-accept-btn-handler', timeout=2000)
    except Exception:
        pass

    # 3. Carregar Fotos
    fotos = obter_lista_fotos(produto.get("fotos") or produto.get("pasta_fotos"))
    if fotos:
        print(f"📸 A carregar {len(fotos)} foto(s)...")
        try:
            await pagina.set_input_files('input[type="file"]', fotos)
            await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️ Não foi possível anexar fotos: {e}")

    # 4. Título
    titulo = produto.get("titulo", "")
    if titulo:
        print("📝 A preencher título...")
        try:
            await pagina.fill('input[name="title"]', titulo)
        except Exception as e:
            print(f"⚠️ Erro no título: {e}")

    # 5. Descrição
    print("🤖 A gerar descrição com IA...")
    descricao_ia = gerar_descricao_com_ia(produto)
    try:
        await pagina.fill('textarea[name="description"]', descricao_ia)
    except Exception as e:
        print(f"⚠️ Erro na descrição: {e}")

    # 6. Abrir menu da Categoria
    categoria = produto.get("categoria", "Homem")
    print(f"🏷️ A tentar abrir menu de Categoria ({categoria})...")
    try:
        await pagina.click('text="Seleciona uma categoria"', timeout=3000)
        await asyncio.sleep(1)
        await pagina.click(f'text="{categoria}"', timeout=3000)
    except Exception:
        print("⚠️ Categoria não selecionada automaticamente. Podes selecionar manualmente no Chrome.")

    # 7. Preço (Com captura segura de erros)
    preco = str(produto.get("preco", ""))
    if preco:
        print(f"💰 A tentar preencher preço ({preco}€)...")
        try:
            await pagina.fill('input[name="price"]', preco, timeout=3000)
            print("✅ Preço preenchido com sucesso!")
        except Exception:
            print("ℹ️ O campo de preço só fica ativo depois de escolheres a categoria no Chrome.")

    atualizar_status_produto(produto.get("titulo"), "Processado")
    print("\n✅ Automação concluída sem bloqueios! Termina a seleção da categoria no Chrome e clica em Publicar.")


async def iniciar_bot_vinted(licenca):
    config = carregar_config_cliente()
    prod_ativo = obter_produto_ativo()

    if not prod_ativo:
        print("\n📦 Nenhum produto ativo na fila com estado 'Ativo' ou 'Na Fila'.")
        return

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            contexto = browser.contexts[0]
            pagina = contexto.pages[0] if contexto.pages else await contexto.new_page()

            await publicar_produto_vinted(pagina, prod_ativo)

        except Exception as e:
            print(f"\n❌ Erro na execução: {e}")