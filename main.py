from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Vinted AI Manager")

# --- MODELOS DE DADOS ---

class PerfilVendedor(BaseModel):
    nome_loja: str
    tom_de_voz: str
    usar_emojis: bool = True
    regras_extra: str

class ProdutoCreate(BaseModel):
    titulo: str
    marca: str
    preco_anunciado: float
    preco_minimo: float

class Produto(ProdutoCreate):
    id: int
    status: str

class RegraAutomatica(BaseModel):
    id: Optional[int] = None
    palavra_chave: str  # ex: "medidas", "foto no corpo", "defeitos"
    resposta_personalizada: str
    foto_url: Optional[str] = None  # URL ou nome do ficheiro da foto

class OfertaChat(BaseModel):
    produto_id: int
    mensagem_comprador: str
    valor_ofertado: float


# --- ESTADO EM MEMÓRIA ---

perfil_vendedor = PerfilVendedor(
    nome_loja="Pedro Vintage Store",
    tom_de_voz="Muito simpático, jovem e descontraído",
    usar_emojis=True,
    regras_extra="Envio rápido em 24h. Não aceito trocas."
)

produtos_db: List[Produto] = []
regras_db: List[RegraAutomatica] = [
    RegraAutomatica(
        id=1,
        palavra_chave="medidas",
        resposta_personalizada="Olá! Este artigo tem 52cm de cava a cava e 70cm de comprimento total! Segue a foto com a fita métrica 😊",
        foto_url="https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=400"
    ),
    RegraAutomatica(
        id=2,
        palavra_chave="defeitos",
        resposta_personalizada="O artigo está em excelente estado, sem manchas, rasgos ou borbototo! Praticamente como novo.",
        foto_url=None
    )
]

id_counter = 1
id_regra_counter = 3


# --- INTERFACE GRÁFICA / PAINEL VISUAL (FRONTEND) ---

@app.get("/dashboard", response_class=HTMLResponse)
def carregar_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <title>Vinted AI Manager - Painel</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .navbar { background-color: #007782; }
            .card { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
            .btn-vinted { background-color: #007782; color: white; border-radius: 8px; }
            .btn-vinted:hover { background-color: #005c65; color: white; }
            .badge-ativo { background-color: #198754; }
            .badge-fila { background-color: #ffc107; color: #000; }
            .badge-vendido { background-color: #6c757d; }
            .img-preview { max-width: 180px; border-radius: 8px; border: 2px solid #007782; margin-top: 10px; }
        </style>
    </head>
    <body>
        <nav class="navbar navbar-dark mb-4">
            <div class="container">
                <span class="navbar-brand mb-0 h1">🤖 Vinted AI Manager Pro</span>
                <span class="badge bg-light text-dark">Modo: Automático 🟢</span>
            </div>
        </nav>

        <div class="container mb-5">
            <div class="row g-4">
                
                <!-- PERSONALIDADE DA IA -->
                <div class="col-md-4">
                    <div class="card p-3">
                        <h5 class="card-title mb-3">⚙️ Perfil da tua IA</h5>
                        <form id="formPerfil">
                            <div class="mb-2">
                                <label class="form-label small">Nome da Loja</label>
                                <input type="text" id="nomeLoja" class="form-control">
                            </div>
                            <div class="mb-2">
                                <label class="form-label small">Tom de Voz</label>
                                <select id="tomVoz" class="form-select">
                                    <option value="Muito simpático, jovem e descontraído">Muito Simpático & Jovem 😊</option>
                                    <option value="Profissional, direto e formal">Profissional & Direto 💼</option>
                                    <option value="Rude, sem rodeios e focado apenas no preço">Rude, Curto & Direto ⚡</option>
                                </select>
                            </div>
                            <div class="mb-2">
                                <label class="form-label small">Regras / Notas da Loja</label>
                                <textarea id="regras" class="form-control" rows="3"></textarea>
                            </div>
                            <button type="button" onclick="salvarPerfil()" class="btn btn-vinted w-100 mt-2">Guardar Configuração</button>
                        </form>
                    </div>
                </div>

                <!-- ADICIONAR PRODUTO E INVENTÁRIO -->
                <div class="col-md-8">
                    <div class="card p-3 mb-4">
                        <h5 class="card-title mb-3">📦 Adicionar Novo Artigo à Fila</h5>
                        <form id="formProduto" class="row g-2">
                            <div class="col-md-4">
                                <input type="text" id="titulo" class="form-control" placeholder="Ex: Camisola Acne" required>
                            </div>
                            <div class="col-md-3">
                                <input type="text" id="marca" class="form-control" placeholder="Marca" required>
                            </div>
                            <div class="col-md-2">
                                <input type="number" id="precoAnunciado" class="form-control" placeholder="Preço €" required>
                            </div>
                            <div class="col-md-3">
                                <input type="number" id="precoMinimo" class="form-control" placeholder="Mínimo €" required>
                            </div>
                            <div class="col-12 mt-2">
                                <button type="button" onclick="adicionarProduto()" class="btn btn-vinted">Adicionar à Fila Vinted</button>
                            </div>
                        </form>
                    </div>

                    <div class="card p-3">
                        <h5 class="card-title mb-3">📋 Inventário e Fila de Publicação</h5>
                        <table class="table align-middle">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Artigo</th>
                                    <th>Preço</th>
                                    <th>Mínimo</th>
                                    <th>Status</th>
                                    <th>Ação</th>
                                </tr>
                            </thead>
                            <tbody id="tabelaProdutos"></tbody>
                        </table>
                    </div>
                </div>

                <!-- GESTOR DE RESPOSTAS AUTOMÁTICAS E FOTOS -->
                <div class="col-12">
                    <div class="card p-4">
                        <h5 class="card-title mb-3">🎯 Respostas Automáticas & Envio de Fotos (Perguntas Frequentes)</h5>
                        <p class="text-muted small mb-3">Define palavras-chave que a IA irá detetar nas mensagens dos clientes para responder instantaneamente e enviar fotos específicas (ex: fita métrica, etiquetas, fotos no corpo).</p>
                        
                        <div class="row g-2 mb-4 bg-light p-3 rounded">
                            <div class="col-md-3">
                                <input type="text" id="novaPalavraChave" class="form-control" placeholder="Palavra-chave (ex: medidas)">
                            </div>
                            <div class="col-md-5">
                                <input type="text" id="novaResposta" class="form-control" placeholder="Resposta exata da IA">
                            </div>
                            <div class="col-md-4">
                                <input type="text" id="novaFotoUrl" class="form-control" placeholder="URL da foto (opcional)">
                            </div>
                            <div class="col-12 mt-2">
                                <button type="button" onclick="adicionarRegra()" class="btn btn-vinted">Adicionar Regra Automática</button>
                            </div>
                        </div>

                        <h6>Regras Ativas:</h6>
                        <table class="table table-sm align-middle">
                            <thead>
                                <tr>
                                    <th>Gatilho (Palavra-chave)</th>
                                    <th>Resposta Programada</th>
                                    <th>Foto Anexada</th>
                                </tr>
                            </thead>
                            <tbody id="tabelaRegras"></tbody>
                        </table>
                    </div>
                </div>

                <!-- SIMULADOR DE CHAT -->
                <div class="col-12">
                    <div class="card p-4">
                        <h5 class="card-title mb-3">💬 Testar Resposta da IA (Simulador de Chat)</h5>
                        <div class="row g-3">
                            <div class="col-md-2">
                                <label class="form-label">ID Produto</label>
                                <input type="number" id="chatProdId" class="form-control" value="1">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Mensagem do Comprador</label>
                                <input type="text" id="chatMensagem" class="form-control" placeholder="Ex: Qual o valor mínimo? ou Podes mandar as medidas?">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label">Oferta (€)</label>
                                <input type="number" id="chatOferta" class="form-control" value="35">
                            </div>
                            <div class="col-md-2 d-flex align-items-end">
                                <button type="button" onclick="testarChat()" class="btn btn-success w-100">Simular Envio</button>
                            </div>
                        </div>

                        <div id="resultadoChat" class="mt-4 p-3 bg-light rounded d-none">
                            <h6>🤖 Resposta da IA:</h6>
                            <p id="textoResposta" class="lead text-dark mb-2"></p>
                            <div id="containerFotoChat"></div>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <script>
            async function carregarPerfil() {
                const res = await fetch('/perfil');
                const p = await res.json();
                document.getElementById('nomeLoja').value = p.nome_loja;
                document.getElementById('tomVoz').value = p.tom_de_voz;
                document.getElementById('regras').value = p.regras_extra;
            }

            async function salvarPerfil() {
                const payload = {
                    nome_loja: document.getElementById('nomeLoja').value,
                    tom_de_voz: document.getElementById('tomVoz').value,
                    usar_emojis: true,
                    regras_extra: document.getElementById('regras').value
                };
                await fetch('/perfil', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                alert('✅ Configurações da IA guardadas com sucesso!');
            }

            async function carregarProdutos() {
                const res = await fetch('/produtos');
                const produtos = await res.json();
                const tabela = document.getElementById('tabelaProdutos');
                tabela.innerHTML = '';
                
                produtos.forEach(p => {
                    let badgeClass = p.status === 'ativo' ? 'badge-ativo' : (p.status === 'em_fila' ? 'badge-fila' : 'badge-vendido');
                    let acaoBtn = p.status === 'ativo' ? `<button onclick="vender(${p.id})" class="btn btn-sm btn-outline-danger">Simular Venda</button>` : '-';
                    
                    tabela.innerHTML += `
                        <tr>
                            <td>#${p.id}</td>
                            <td><strong>${p.titulo}</strong> (${p.marca})</td>
                            <td>${p.preco_anunciado}€</td>
                            <td>${p.preco_minimo}€</td>
                            <td><span class="badge ${badgeClass}">${p.status.toUpperCase()}</span></td>
                            <td>${acaoBtn}</td>
                        </tr>
                    `;
                });
            }

            async function carregarRegras() {
                const res = await fetch('/regras');
                const regras = await res.json();
                const tabela = document.getElementById('tabelaRegras');
                tabela.innerHTML = '';
                
                regras.forEach(r => {
                    let fotoTxt = r.foto_url ? `📸 Foto Anexada` : 'Sem foto';
                    tabela.innerHTML += `
                        <tr>
                            <td><span class="badge bg-secondary">${r.palavra_chave}</span></td>
                            <td>${r.resposta_personalizada}</td>
                            <td><small class="text-muted">${fotoTxt}</small></td>
                        </tr>
                    `;
                });
            }

            async function adicionarRegra() {
                const payload = {
                    palavra_chave: document.getElementById('novaPalavraChave').value,
                    resposta_personalizada: document.getElementById('novaResposta').value,
                    foto_url: document.getElementById('novaFotoUrl').value || null
                };
                await fetch('/regras', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                document.getElementById('novaPalavraChave').value = '';
                document.getElementById('novaResposta').value = '';
                document.getElementById('novaFotoUrl').value = '';
                carregarRegras();
            }

            async function adicionarProduto() {
                const payload = {
                    titulo: document.getElementById('titulo').value,
                    marca: document.getElementById('marca').value,
                    preco_anunciado: parseFloat(document.getElementById('precoAnunciado').value),
                    preco_minimo: parseFloat(document.getElementById('precoMinimo').value)
                };
                await fetch('/produtos', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                carregarProdutos();
            }

            async function vender(id) {
                await fetch(`/produtos/${id}/vender`, { method: 'POST' });
                carregarProdutos();
            }

            async function testarChat() {
                const payload = {
                    produto_id: parseInt(document.getElementById('chatProdId').value),
                    mensagem_comprador: document.getElementById('chatMensagem').value,
                    valor_ofertado: parseFloat(document.getElementById('chatOferta').value) || 0
                };
                const res = await fetch('/chat/negociar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                document.getElementById('resultadoChat').classList.remove('d-none');
                document.getElementById('textoResposta').innerText = data.resposta_gerada;
                
                const imgContainer = document.getElementById('containerFotoChat');
                if (data.foto_anexa) {
                    imgContainer.innerHTML = `
                        <div class="mt-2">
                            <small class="text-muted d-block">📸 Foto enviada em anexo:</small>
                            <img src="${data.foto_anexa}" class="img-preview" alt="Foto da IA">
                        </div>
                    `;
                } else {
                    imgContainer.innerHTML = '';
                }
            }

            carregarPerfil();
            carregarProdutos();
            carregarRegras();
        </script>
    </body>
    </html>
    """


# --- API BACKEND ---

@app.get("/perfil", response_model=PerfilVendedor)
def obter_perfil():
    return perfil_vendedor

@app.post("/perfil")
def atualizar_perfil(novo: PerfilVendedor):
    global perfil_vendedor
    perfil_vendedor = novo
    return {"sucesso": True}

@app.get("/produtos", response_model=List[Produto])
def listar_produtos():
    return produtos_db

@app.post("/produtos", response_model=Produto)
def adicionar_produto(produto: ProdutoCreate):
    global id_counter
    status_inicial = "ativo" if not any(p.status == "ativo" for p in produtos_db) else "em_fila"
    novo = Produto(
        id=id_counter,
        titulo=produto.titulo,
        marca=produto.marca,
        preco_anunciado=produto.preco_anunciado,
        preco_minimo=produto.preco_minimo,
        status=status_inicial
    )
    produtos_db.append(novo)
    id_counter += 1
    return novo

@app.post("/produtos/{produto_id}/vender")
def vender_produto(produto_id: int):
    for p in produtos_db:
        if p.id == produto_id and p.status == "ativo":
            p.status = "vendido"
            for proximo in produtos_db:
                if proximo.status == "em_fila":
                    proximo.status = "ativo"
                    break
            return {"sucesso": True}
    raise HTTPException(status_code=400, detail="Produto indisponível.")

@app.get("/regras", response_model=List[RegraAutomatica])
def listar_regras():
    return regras_db

@app.post("/regras", response_model=RegraAutomatica)
def adicionar_regra(regra: RegraAutomatica):
    global id_regra_counter
    regra.id = id_regra_counter
    id_regra_counter += 1
    regras_db.append(regra)
    return regra

@app.post("/chat/negociar")
def negociar(oferta: OfertaChat):
    msg_cliente = oferta.mensagem_comprador.lower()

    # 1. VERIFICAR SE EXISTE UMA REGRA DE PALAVRA-CHAVE / FOTO AUTOMÁTICA
    for regra in regras_db:
        if regra.palavra_chave.lower() in msg_cliente:
            return {
                "resposta_gerada": regra.resposta_personalizada,
                "foto_anexa": regra.foto_url
            }

    # 2. SE NÃO FOR UMA PERGUNTA FREQUENTE, ENTRA NA NEGOCIAÇÃO HUMANIZADA
    produto = next((p for p in produtos_db if p.id == oferta.produto_id), None)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    
    val = oferta.valor_ofertado
    tom = perfil_vendedor.tom_de_voz

    # Adaptação dinamica do tom de voz
    if "Rude" in tom or "curto" in tom.lower():
        if val >= produto.preco_minimo:
            resposta = f"Aceito {val:.2f}€. Faz a oferta."
        elif val >= (produto.preco_minimo * 0.85):
            contra = round((produto.preco_minimo + val) / 2, 2)
            resposta = f"Não dá. Mínimo {contra:.2f}€."
        else:
            resposta = f"Não. O mínimo é {produto.preco_minimo:.0f}€."
    
    elif "Profissional" in tom:
        if val >= produto.preco_minimo:
            resposta = f"Bom dia. Agradeço o interesse. Aceito a proposta de {val:.2f}€. Pode formalizar a oferta na aplicação."
        elif val >= (produto.preco_minimo * 0.85):
            contra = round((produto.preco_minimo + val) / 2, 2)
            resposta = f"Boa tarde. De momento não é possível fazer esse valor, mas posso aceitar {contra:.2f}€."
        else:
            resposta = f"Bom dia. Infelizmente o valor mínimo aceitável para este artigo é {produto.preco_minimo:.2f}€."
            
    else:  # Simpático & Jovem (Default)
        if val >= produto.preco_minimo:
            resposta = f"Olá! Aceito perfeitamente os {val:.2f}€! 😊 Podes enviar a oferta pela Vinted que eu aceito já!"
        elif val >= (produto.preco_minimo * 0.85):
            contra = round((produto.preco_minimo + val) / 2, 2)
            resposta = f"Boas! Por esse valor não consigo, mas chego aos {contra:.2f}€! O que dizes? 😊"
        else:
            resposta = f"Olá! Infelizmente só consigo baixar até aos {produto.preco_minimo:.0f}€."

    return {
        "resposta_gerada": resposta,
        "foto_anexa": None
    }

from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ==========================================
# MÓDULO DE LICENÇAS E SEGURANÇA (SaaS)
# ==========================================

base_dados_licencas = {
    "CHAVE-TESTE-1234": {
        "cliente_email": "pedro@email.com",
        "ativa": True,
        "validade": "2026-12-31",
        "hwid_registado": None,
        "ultimo_acesso": None
    }
}

class RequisicaoLicenca(BaseModel):
    chave: str
    hwid: str

@app.post("/api/v1/validar-licenca")
def validar_licenca(req: RequisicaoLicenca):
    try:
        licenca = base_dados_licencas.get(req.chave)
        
        if not licenca:
            raise HTTPException(status_code=404, detail="Chave de licença não encontrada.")
            
        if not licenca["ativa"]:
            return {"valido": False, "mensagem": "Licença expirada ou desativada."}

        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Primeiro acesso: regista este HWID
        if licenca["hwid_registado"] is None:
            licenca["hwid_registado"] = req.hwid
            licenca["ultimo_acesso"] = agora
            print(f"🔑 Licença {req.chave} associada ao HWID: {req.hwid}")
            return {"valido": True, "mensagem": "Licença ativada neste computador com sucesso!"}

        # Acessos seguintes: valida se é o mesmo PC
        if licenca["hwid_registado"] == req.hwid:
            licenca["ultimo_acesso"] = agora
            return {"valido": True, "mensagem": "Acesso permitido."}
        else:
            return {
                "valido": False, 
                "mensagem": "Esta licença já está em uso noutro computador! Apenas 1 dispositivo permitido."
            }
            
    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"❌ Erro interno ao validar licença: {e}")
        raise HTTPException(status_code=500, detail=str(e))