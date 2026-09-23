import hashlib
import platform
import uuid
import requests

def obter_hwid_dispositivo():
    """Gera um identificador único e seguro do computador do cliente."""
    string_unica = f"{platform.node()}-{platform.processor()}-{uuid.getnode()}"
    return hashlib.sha256(string_unica.encode()).hexdigest()

SERVER_URL = "https://a-tua-api-saas.com"  # O teu servidor na nuvem

def validar_licenca_local(chave_licenca: str) -> bool:
    hwid = obter_hwid_dispositivo()
    
    try:
        res = requests.post(
            f"{SERVER_URL}/api/v1/validar-licenca",
            json={"chave": chave_licenca, "hwid": hwid},
            timeout=5
        )
        dados = res.json()
        
        if res.status_code == 200 and dados.get("valido"):
            print("✅ Licença válida e dispositivo autorizado!")
            return True
        else:
            print(f"❌ Acesso negado: {dados.get('mensagem')}")
            return False
            
    except Exception as e:
        print(f"⚠️ Erro ao validar licença: {e}")
        return False