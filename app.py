import customtkinter as ctk
import threading
import sys
import requests
import json
import os
from tkinter import filedialog
from PIL import Image
import bot_vinted

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"
PRODUTOS_FILE = "produtos.json"

def carregar_configuracoes():
    config_padrao = {
        "licenca": "",
        "prompt_ia": "Atua como um vendedor simpático e profissional na Vinted. Esclarece dúvidas sobre as peças, sê educado e tenta fechar vendas com bom tom.",
        "desconto_maximo": 10
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                config_padrao.update(dados)
        except Exception:
            pass
    return config_padrao

def guardar_configuracoes(dados):
    try:
        config_atual = carregar_configuracoes()
        config_atual.update(dados)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_atual, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Erro ao guardar configurações: {e}")
        return False

def carregar_produtos():
    if os.path.exists(PRODUTOS_FILE):
        try:
            with open(PRODUTOS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def guardar_produtos(lista_produtos):
    try:
        with open(PRODUTOS_FILE, "w", encoding="utf-8") as f:
            json.dump(lista_produtos, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Erro ao guardar produtos: {e}")
        return False

class TextRedirector:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def flush(self):
        pass

class VintedSalesApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Vinted AI Sales Manager")
        self.geometry("560x780")
        self.resizable(False, False)

        self.config_data = carregar_configuracoes()
        self.produtos_lista = carregar_produtos()
        self.fotos_selecionadas_temp = []

        if os.path.exists("logo.ico"):
            self.iconbitmap("logo.ico")

        self.title_label = ctk.CTkLabel(self, text="Vinted AI Sales Manager", font=("Roboto", 20, "bold"))
        self.title_label.pack(pady=(10, 5))

        # Separadores
        self.tabview = ctk.CTkTabview(self, width=520, height=700)
        self.tabview.pack(pady=5)

        self.tab_licenca = self.tabview.add("🔑 Licença e Bot")
        self.tab_ia = self.tabview.add("🤖 Personalizar IA")
        self.tab_produtos = self.tabview.add("📦 Fila de Produtos")

        self.setup_tab_licenca()
        self.setup_tab_ia()
        self.setup_tab_produtos()

        sys.stdout = TextRedirector(self.console_box)

    # ---------------------------------------------------------
    # TAB 1: LICENÇA E BOT
    # ---------------------------------------------------------
    def setup_tab_licenca(self):
        self.license_entry = ctk.CTkEntry(
            self.tab_licenca, 
            placeholder_text="Chave de Licença (ex: CHAVE-TESTE-1234)", 
            width=460
        )
        self.license_entry.insert(0, self.config_data.get("licenca", ""))
        self.license_entry.pack(pady=(15, 10))

        self.start_button = ctk.CTkButton(
            self.tab_licenca, 
            text="🚀 Ligar Assistente de Vendas", 
            font=("Roboto", 14, "bold"),
            fg_color="#1f538d",
            hover_color="#14375e",
            width=460, 
            height=40,
            command=self.start_bot_thread
        )
        self.start_button.pack(pady=10)

        self.console_label = ctk.CTkLabel(self.tab_licenca, text="Atividade em Tempo Real:", font=("Roboto", 12, "bold"))
        self.console_label.pack(anchor="w", padx=25, pady=(10, 2))

        self.console_box = ctk.CTkTextbox(self.tab_licenca, width=460, height=360, font=("Consolas", 11))
        self.console_box.pack(pady=5)
        self.console_box.configure(state="disabled")

        self.status_label = ctk.CTkLabel(self.tab_licenca, text="A aguardar inicialização...", text_color="gray")
        self.status_label.pack(pady=10)

    # ---------------------------------------------------------
    # TAB 2: IA
    # ---------------------------------------------------------
    def setup_tab_ia(self):
        lbl_prompt = ctk.CTkLabel(
            self.tab_ia, 
            text="Instruções para a IA (Personalidade, Regras & Tom):", 
            font=("Roboto", 12, "bold")
        )
        lbl_prompt.pack(anchor="w", padx=25, pady=(15, 5))

        self.prompt_box = ctk.CTkTextbox(self.tab_ia, width=460, height=300, font=("Roboto", 11))
        self.prompt_box.insert("1.0", self.config_data.get("prompt_ia", ""))
        self.prompt_box.pack(pady=5)

        lbl_desc = ctk.CTkLabel(self.tab_ia, text="Desconto Máximo Permitido (%):", font=("Roboto", 12, "bold"))
        lbl_desc.pack(anchor="w", padx=25, pady=(10, 2))

        self.desconto_entry = ctk.CTkEntry(self.tab_ia, width=120)
        self.desconto_entry.insert(0, str(self.config_data.get("desconto_maximo", 10)))
        self.desconto_entry.pack(anchor="w", padx=25, pady=5)

        self.btn_guardar_ia = ctk.CTkButton(
            self.tab_ia, 
            text="💾 Guardar Definições da IA", 
            fg_color="#27ae60", 
            hover_color="#1e8449",
            width=460,
            height=38,
            command=self.salvar_dados_ia
        )
        self.btn_guardar_ia.pack(pady=20)

        self.lbl_status_ia = ctk.CTkLabel(self.tab_ia, text="", text_color="gray")
        self.lbl_status_ia.pack()

    # ---------------------------------------------------------
    # TAB 3: FILA DE PRODUTOS COMPLETA
    # ---------------------------------------------------------
    def setup_tab_produtos(self):
        self.scroll_prod = ctk.CTkScrollableFrame(self.tab_produtos, width=470, height=610)
        self.scroll_prod.pack(pady=5, fill="both", expand=True)

        lbl_titulo_seccao = ctk.CTkLabel(
            self.scroll_prod, 
            text="➕ Adicionar Novo Produto à Fila", 
            font=("Roboto", 14, "bold")
        )
        lbl_titulo_seccao.pack(anchor="w", pady=(5, 10))

        # 1. Título
        self.prod_titulo = ctk.CTkEntry(self.scroll_prod, placeholder_text="Título do Artigo (ex: T-shirt Zara preta M)", width=440)
        self.prod_titulo.pack(pady=4)

        # 2. Categoria e Marca
        frame_linha1 = ctk.CTkFrame(self.scroll_prod, fg_color="transparent")
        frame_linha1.pack(pady=4, fill="x")

        self.prod_categoria = ctk.CTkOptionMenu(
            frame_linha1,
            values=["Homem", "Mulher", "Criança", "Casa", "Entretenimento"],
            width=215
        )
        self.prod_categoria.set("Homem")
        self.prod_categoria.pack(side="left", padx=(0, 10))

        self.prod_marca = ctk.CTkEntry(frame_linha1, placeholder_text="Marca (ex: Nike, Zara, Sem marca)", width=215)
        self.prod_marca.pack(side="left")

        # 3. Preço, Tamanho, Cor
        frame_linha2 = ctk.CTkFrame(self.scroll_prod, fg_color="transparent")
        frame_linha2.pack(pady=4, fill="x")

        self.prod_preco = ctk.CTkEntry(frame_linha2, placeholder_text="Preço (€)", width=135)
        self.prod_preco.pack(side="left", padx=(0, 10))

        self.prod_tamanho = ctk.CTkEntry(frame_linha2, placeholder_text="Tamanho (ex: M, 42)", width=135)
        self.prod_tamanho.pack(side="left", padx=(0, 10))

        self.prod_cor = ctk.CTkEntry(frame_linha2, placeholder_text="Cor (ex: Preto)", width=140)
        self.prod_cor.pack(side="left")

        # 4. Estado do Artigo e Tamanho da Encomenda
        frame_linha3 = ctk.CTkFrame(self.scroll_prod, fg_color="transparent")
        frame_linha3.pack(pady=4, fill="x")

        self.prod_condicao = ctk.CTkOptionMenu(
            frame_linha3, 
            values=["Novo com etiquetas", "Novo sem etiquetas", "Muito bom", "Bom", "Satisfatório"],
            width=215
        )
        self.prod_condicao.set("Muito bom")
        self.prod_condicao.pack(side="left", padx=(0, 10))

        self.prod_pacote = ctk.CTkOptionMenu(
            frame_linha3,
            values=["Pequeno (T-shirts, carteiras)", "Médio (Camisolas, calças)", "Grande (Casacos pesados, lotes)"],
            width=215
        )
        self.prod_pacote.set("Médio (Camisolas, calças)")
        self.prod_pacote.pack(side="left")

        # 5. Descrição / Instruções
        self.prod_desc = ctk.CTkTextbox(self.scroll_prod, width=440, height=80, font=("Roboto", 11))
        self.prod_desc.insert("1.0", "Detalhes adicionais do produto (material, estado real, medidas)...")
        self.prod_desc.pack(pady=5)

        # 6. Seleção de Fotografias
        frame_fotos = ctk.CTkFrame(self.scroll_prod, fg_color="transparent")
        frame_fotos.pack(pady=5, fill="x")

        self.btn_fotos = ctk.CTkButton(
            frame_fotos, 
            text="📷 Selecionar Fotos (até 20)", 
            width=180, 
            command=self.selecionar_fotos
        )
        self.btn_fotos.pack(side="left")

        self.lbl_fotos_count = ctk.CTkLabel(frame_fotos, text="0 foto(s) selecionada(s)", text_color="gray")
        self.lbl_fotos_count.pack(side="left", padx=15)

        # Botão Adicionar à Fila
        self.btn_add_prod = ctk.CTkButton(
            self.scroll_prod, 
            text="📥 Adicionar Produto à Fila", 
            fg_color="#2980b9", 
            hover_color="#1c5980",
            width=440,
            height=38,
            command=self.adicionar_produto_fila
        )
        self.btn_add_prod.pack(pady=12)

        # Divisor da Lista
        lbl_lista_seccao = ctk.CTkLabel(
            self.scroll_prod, 
            text="📋 Fila Atual de Publicação", 
            font=("Roboto", 14, "bold")
        )
        lbl_lista_seccao.pack(anchor="w", pady=(15, 5))

        self.frame_lista_produtos = ctk.CTkFrame(self.scroll_prod, fg_color="transparent")
        self.frame_lista_produtos.pack(fill="x", expand=True)

        self.atualizar_visualizacao_fila()

    # ---------------------------------------------------------
    # FUNÇÕES E LÓGICA DA FILA
    # ---------------------------------------------------------
    def selecionar_fotos(self):
        ficheiros = filedialog.askopenfilenames(
            title="Escolher fotos do artigo (máx. 20)",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")]
        )
        if ficheiros:
            self.fotos_selecionadas_temp = list(ficheiros)[:20]
            self.lbl_fotos_count.configure(
                text=f"{len(self.fotos_selecionadas_temp)} foto(s) selecionada(s)", 
                text_color="#27ae60"
            )

    def adicionar_produto_fila(self):
        titulo = self.prod_titulo.get().strip()
        preco = self.prod_preco.get().strip()
        tamanho = self.prod_tamanho.get().strip()
        categoria = self.prod_categoria.get()
        marca = self.prod_marca.get().strip() or "Sem marca"
        cor = self.prod_cor.get().strip()
        condicao = self.prod_condicao.get()
        pacote = self.prod_pacote.get()
        descricao = self.prod_desc.get("1.0", "end-1c").strip()

        if not titulo or not preco:
            print("⚠️ Preencha pelo menos o Título e o Preço do artigo.")
            return

        novo_prod = {
            "id": len(self.produtos_lista) + 1,
            "titulo": titulo,
            "categoria": categoria,
            "marca": marca,
            "preco": preco,
            "tamanho": tamanho,
            "cor": cor,
            "condicao": condicao,
            "tamanho_pacote": pacote,
            "descricao": descricao,
            "fotos": self.fotos_selecionadas_temp,
            "status": "Ativo" if len(self.produtos_lista) == 0 else "Na Fila"
        }

        self.produtos_lista.append(novo_prod)
        guardar_produtos(self.produtos_lista)

        # Limpar o formulário
        self.prod_titulo.delete(0, "end")
        self.prod_preco.delete(0, "end")
        self.prod_tamanho.delete(0, "end")
        self.prod_marca.delete(0, "end")
        self.prod_cor.delete(0, "end")
        self.prod_desc.delete("1.0", "end")
        self.fotos_selecionadas_temp = []
        self.lbl_fotos_count.configure(text="0 foto(s) selecionada(s)", text_color="gray")

        self.atualizar_visualizacao_fila()

    def apagar_produto(self, index):
        if 0 <= index < len(self.produtos_lista):
            self.produtos_lista.pop(index)
            if self.produtos_lista and not any(p["status"] == "Ativo" for p in self.produtos_lista):
                self.produtos_lista[0]["status"] = "Ativo"
            guardar_produtos(self.produtos_lista)
            self.atualizar_visualizacao_fila()

    def atualizar_visualizacao_fila(self):
        for widget in self.frame_lista_produtos.winfo_children():
            widget.destroy()

        if not self.produtos_lista:
            lbl_vazio = ctk.CTkLabel(self.frame_lista_produtos, text="Nenhum produto na fila.", text_color="gray")
            lbl_vazio.pack(pady=10)
            return

        for idx, prod in enumerate(self.produtos_lista):
            card = ctk.CTkFrame(self.frame_lista_produtos, fg_color="#2b2b2b", corner_radius=8)
            card.pack(fill="x", pady=5, padx=2)

            lbl_info = ctk.CTkLabel(
                card, 
                text=f"#{idx+1} {prod['titulo']} - {prod['preco']}€\nMarca: {prod.get('marca', 'Sem marca')} | Cat: {prod.get('categoria', 'N/A')} | {len(prod['fotos'])} fotos",
                text_color="white",
                justify="left",
                font=("Roboto", 11, "bold")
            )
            lbl_info.pack(side="left", padx=10, pady=8)

            btn_del = ctk.CTkButton(
                card, 
                text="🗑️", 
                width=35, 
                height=28, 
                fg_color="#c0392b", 
                hover_color="#962d22",
                command=lambda i=idx: self.apagar_produto(i)
            )
            btn_del.pack(side="right", padx=10)

    # ---------------------------------------------------------
    # RESTO DAS AÇÕES
    # ---------------------------------------------------------
    def salvar_dados_ia(self):
        prompt = self.prompt_box.get("1.0", "end-1c").strip()
        try:
            desconto = int(self.desconto_entry.get().strip())
        except ValueError:
            desconto = 10

        guardar_configuracoes({"prompt_ia": prompt, "desconto_maximo": desconto})
        self.lbl_status_ia.configure(text="✅ Definições da IA guardadas com sucesso!", text_color="green")

    def start_bot_thread(self):
        self.start_button.configure(state="disabled")
        self.status_label.configure(text="A verificar licença no servidor...", text_color="yellow")
        
        licenca = self.license_entry.get().strip()
        guardar_configuracoes({"licenca": licenca})

        thread = threading.Thread(target=self.run_bot, daemon=True)
        thread.start()

    def run_bot(self):
        licenca = self.license_entry.get().strip()

        if not licenca:
            self.status_label.configure(text="Erro: Insere a tua chave de licença!", text_color="red")
            self.start_button.configure(state="normal")
            return

        meu_hwid = bot_vinted.obter_hwid()
        try:
            resposta = requests.post(
                f"{bot_vinted.API_URL}/api/v1/validar-licenca", 
                json={"chave": licenca, "hwid": meu_hwid}, 
                timeout=30
            )
            dados = resposta.json()

            if resposta.status_code != 200 or not dados.get("valido"):
                msg_erro = dados.get("mensagem", "Licença inválida ou desativada.")
                self.status_label.configure(text=f"Acesso Negado: {msg_erro}", text_color="red")
                self.start_button.configure(state="normal")
                return

        except Exception:
            self.status_label.configure(text="Erro: Não foi possível ligar ao servidor de licenças.", text_color="red")
            self.start_button.configure(state="normal")
            return

        self.status_label.configure(text="🟢 Bot de Vendas Ativo e a Monitorizar!", text_color="green")
        
        try:
            if bot_vinted.garantir_chrome_aberto():
                import asyncio
                asyncio.run(bot_vinted.iniciar_bot_vinted(licenca))
        except Exception as e:
            print(f"\n❌ Erro no Bot: {e}")
            self.status_label.configure(text="Erro na execução do bot.", text_color="red")
        finally:
            self.start_button.configure(state="normal")

if __name__ == "__main__":
    app = VintedSalesApp()
    app.mainloop()