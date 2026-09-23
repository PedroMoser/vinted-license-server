import secrets
import datetime
from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="Vinted Sales Manager API")

# Dicionário temporário (mais tarde podes ligar a uma base de dados)
banco_licencas = {}


def gerar_chave(plano: str) -> str:
    prefixo = "PRO" if "pro" in plano.lower() else "BASE"
    sufixo = secrets.token_hex(4).upper()
    return f"VINTED-{prefixo}-{sufixo}"


@app.get("/")
def home():
    return {"status": "API Online", "servico": "Vinted Sales Manager"}


# Endpoint chamado pelo Lemon Squeezy após cada pagamento
@app.post("/webhooks/lemon-squeezy")
async def webhook_lemon_squeezy(request: Request):
    try:
        payload = await request.json()
        event_name = payload.get("meta", {}).get("event_name")
        data = payload.get("data", {})

        # 1. Pagamento de Subscrição Concluído com Sucesso
        if event_name in ["order_created", "subscription_created"]:
            attributes = data.get("attributes", {})
            email_cliente = attributes.get("user_email")
            nome_produto = attributes.get("first_order_item", {}).get("product_name", "Base")

            plano = "pro" if "pro" in nome_produto.lower() else "base"
            nova_chave = gerar_chave(plano)

            banco_licencas[nova_chave] = {
                "email": email_cliente,
                "plano": plano,
                "status": "Ativa",
                "hwid": None,
                "validade": (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
            }

            print(f"🎉 [Lemon Squeezy] Nova licença para {email_cliente}: {nova_chave}")
            return {"status": "sucesso", "chave": nova_chave}

        # 2. Cancelamento ou Falha no Pagamento
        elif event_name in ["subscription_cancelled", "subscription_expired"]:
            email_cliente = data.get("attributes", {}).get("user_email")
            for chave, info in banco_licencas.items():
                if info.get("email") == email_cliente:
                    info["status"] = "Inativa"
                    print(f"⛔ Licença {chave} desativada para {email_cliente}")

            return {"status": "desativado"}

        return {"status": "evento_ignorado"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar webhook: {str(e)}")


# Endpoint que o app.py consulta para validar a licença
@app.get("/validar-licenca/{chave}")
def validar_licenca(chave: str, hwid: str = None):
    licenca = banco_licencas.get(chave)

    if not licenca:
        return {"valido": False, "mensagem": "Chave de licença inválida."}

    if licenca.get("status") != "Ativa":
        return {"valido": False, "mensagem": "Licença inativa ou expirada."}

    # Bloqueio por HWID (associa ao primeiro PC que usar)
    hwid_registado = licenca.get("hwid")
    if hwid_registado is None and hwid:
        licenca["hwid"] = hwid
    elif hwid_registado != hwid:
        return {"valido": False, "mensagem": "Esta chave já está a ser usada em outro computador."}

    return {
        "valido": True,
        "plano": licenca.get("plano"),
        "validade": licenca.get("validade")
    }