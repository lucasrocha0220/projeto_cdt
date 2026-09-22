import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import requests
import threading
import unicodedata
import re
import json
from io import BytesIO
from datetime import datetime

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False


# ============================================================
# CONFIGURAÇÕES E DADOS DO RESTAURANTE
# ============================================================

DB_NAME = "restaurante.db"

INFO_RESTAURANTE = {
    "nome": "Gourmet Service",
    "endereco": "Av. Paulista, 1000 - Bela Vista, São Paulo - SP",
    "horario_abertura": 12,   # 12:00 PM
    "horario_fechamento": 20, # 8:00 PM
    "taxa_entrega": "Grátis acima de R$ 50,00 (Fixa R$ 7,00 para demais)",
    "tempo_entrega": "30 a 50 minutos"
}

CORES = {
    "dark": {
        "bg": "#121212",
        "card": "#1E1E1E",
        "text": "#FFFFFF",
        "sub": "#BDBDBD",
        "accent": "#693DE2",
        "accent2": "#8B39E7",
        "entry": "#292929",
        "success": "#35C759",
        "danger": "#E53935"
    },
    "light": {
        "bg": "#F4F4F9",
        "card": "#FFFFFF",
        "text": "#111111",
        "sub": "#666666",
        "accent": "#1D46B9",
        "accent2": "#0065D9",
        "entry": "#EEEEF5",
        "success": "#168A32",
        "danger": "#C62828"
    }
}

TEMA = "dark"

PRODUTOS_INICIAIS = [
    ("🍔 HAMBÚRGUERES", "Clássico Smash", 22.00, "2x smash 80g e cheddar.", "https://images.unsplash.com/photo-1550547660-d9450f859349?w=500"),
    ("🍔 HAMBÚRGUERES", "Chicken Crispy", 25.90, "Frango crocante e coleslaw.", "https://images.unsplash.com/photo-1606755962773-d324e0a13086?w=500"),
    ("🍔 HAMBÚRGUERES", "Poderoso Chefão", 34.90, "Blend 180g, gorgonzola e bacon.", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500"),
    ("🍔 HAMBÚRGUERES", "Duplo Bacon", 38.50, "2x blends 180g e triplo bacon.", "https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=500"),
    ("🍕 PIZZAS", "Marguerita", 42.00, "Mussarela, tomate e manjericão.", "https://images.unsplash.com/photo-1579751626657-72bc17010498?w=500"),
    ("🍕 PIZZAS", "Calabresa", 45.00, "Molho, mussarela e calabresa.", "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=500"),
    ("🍕 PIZZAS", "Quatro Queijos", 50.00, "Mussarela, provolone, gorgonzola e parmesão.", "https://images.unsplash.com/photo-1571407970349-bc81e7e96d47?w=500"),
    ("🥤 BEBIDAS", "Refrigerante", 6.50, "Refrigerante gelado 350ml.", "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=500"),
    ("🥤 BEBIDAS", "Soda Artesanal", 12.00, "Soda refrescante e artesanal.", "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=500"),
    ("🥤 BEBIDAS", "Milkshake", 18.00, "Milkshake cremoso 400ml.", "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=500")
]


# ============================================================
# BANCO DE DADOS DINÂMICO
# ============================================================

def criar_banco():
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            descricao TEXT NOT NULL,
            imagem TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            usuario TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            itens TEXT NOT NULL,
            total REAL NOT NULL,
            cep TEXT NOT NULL DEFAULT '',
            endereco TEXT NOT NULL DEFAULT '',
            numero TEXT NOT NULL DEFAULT '',
            forma_pagamento TEXT NOT NULL DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            autor TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_hora TEXT NOT NULL
        )
    """)

    # Garante o Utilizador Fixo Root Master
    cursor.execute("INSERT OR REPLACE INTO usuarios (usuario, nome, senha) VALUES (?, ?, ?)", 
                   ("root", "Root Master", "root"))

    # Inserção de produtos padrão
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO produtos (categoria, nome, preco, descricao, imagem) VALUES (?, ?, ?, ?, ?)",
            PRODUTOS_INICIAIS
        )

    conexao.commit()
    conexao.close()


def carregar_produtos_bd():
    conexao = sqlite3.connect(DB_NAME)
    cursor = conexao.cursor()
    cursor.execute("SELECT categoria, nome, preco, descricao, imagem FROM produtos")
    linhas = cursor.fetchall()
    conexao.close()

    produtos_dict = {}
    for cat, nome, preco, desc, img in linhas:
        if cat not in produtos_dict:
            produtos_dict[cat] = []
        produtos_dict[cat].append({
            "nome": nome,
            "preco": preco,
            "descricao": desc,
            "imagem": img,
            "categoria": cat
        })
    return produtos_dict


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_texto(texto):
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    return re.sub(r"\s+", " ", texto)


def formatar_moeda(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


def restaurante_aberto():
    hora_atual = datetime.now().hour
    return INFO_RESTAURANTE["horario_abertura"] <= hora_atual < INFO_RESTAURANTE["horario_fechamento"]


def todos_produtos():
    produtos_dict = carregar_produtos_bd()
    lista = []
    for prods in produtos_dict.values():
        lista.extend(prods)
    return lista


# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================

class GourmetService:

    def __init__(self, root):
        self.root = root
        self.root.title("Gourmet Service")
        self.root.geometry("1080x720")
        self.root.minsize(900, 620)

        self.usuario_atual = None
        self.nome_atual = None
        self.carrinho = {}
        self.imagens = []

        self.janela_chat = None
        self.chat_texto = None
        self.chat_entry = None

        criar_banco()
        self.aplicar_estilo()
        self.mostrar_login()

    def aplicar_estilo(self):
        cores = CORES[TEMA]
        self.root.configure(bg=cores["bg"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "TButton",
            background=cores["accent"],
            foreground="white",
            font=("Arial", 10, "bold"),
            padding=8
        )
        style.map("TButton", background=[("active", cores["accent2"])])

    def alternar_tema(self):
        global TEMA
        TEMA = "light" if TEMA == "dark" else "dark"
        self.aplicar_estilo()
        if self.usuario_atual:
            self.mostrar_menu()
        else:
            self.mostrar_login()

    def sair_da_conta(self):
        self.usuario_atual = None
        self.nome_atual = None
        self.carrinho.clear()
        if self.janela_chat:
            self.fechar_chat()
        self.mostrar_login()

    def limpar_tela(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.imagens.clear()

    # ========================================================
    # TELA DE LOGIN
    # ========================================================

    def mostrar_login(self):
        self.limpar_tela()
        cores = CORES[TEMA]

        frame = tk.Frame(self.root, bg=cores["bg"])
        frame.pack(expand=True)

        tk.Label(
            frame,
            text="🍔 GOURMET SERVICE",
            font=("Arial", 28, "bold"),
            bg=cores["bg"],
            fg=cores["accent2"]
        ).pack(pady=(20, 5))

        status_txt = "🟢 Aberto Agora" if restaurante_aberto() else "🔴 Fechado Agora"
        tk.Label(
            frame,
            text=f"Cardápio Dinâmico | Status: {status_txt}",
            font=("Arial", 11, "bold"),
            bg=cores["bg"],
            fg=cores["success"] if restaurante_aberto() else cores["danger"]
        ).pack(pady=(0, 20))

        card = tk.Frame(frame, bg=cores["card"], padx=35, pady=30)
        card.pack()

        tk.Label(card, text="Usuário", bg=cores["card"], fg=cores["text"], font=("Arial", 11, "bold")).pack(anchor="w")
        self.login_usuario = tk.Entry(card, width=35, bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat", font=("Arial", 11))
        self.login_usuario.pack(pady=(5, 15), ipady=7)

        tk.Label(card, text="Senha", bg=cores["card"], fg=cores["text"], font=("Arial", 11, "bold")).pack(anchor="w")
        self.login_senha = tk.Entry(card, width=35, show="*", bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat", font=("Arial", 11))
        self.login_senha.pack(pady=(5, 20), ipady=7)

        ttk.Button(card, text="ENTRAR", command=self.fazer_login).pack(fill="x", pady=5)
        ttk.Button(card, text="CRIAR NOVA CONTA", command=self.mostrar_cadastro).pack(fill="x", pady=5)

        tk.Button(
            card, text="☀️ / 🌙 Alterar tema", command=self.alternar_tema,
            bg=cores["card"], fg=cores["accent2"], relief="flat", font=("Arial", 10, "bold"), cursor="hand2"
        ).pack(pady=(15, 0))

        self.login_usuario.bind("<Return>", lambda e: self.fazer_login())
        self.login_senha.bind("<Return>", lambda e: self.fazer_login())

    def fazer_login(self):
        usuario = self.login_usuario.get().strip()
        senha = self.login_senha.get().strip()

        if not usuario or not senha:
            messagebox.showwarning("Atenção", "Preencha o usuário e a senha.")
            return

        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        cursor.execute("SELECT nome FROM usuarios WHERE usuario = ? AND senha = ?", (usuario, senha))
        resultado = cursor.fetchone()
        conexao.close()

        if resultado:
            self.usuario_atual = usuario
            self.nome_atual = resultado[0]
            self.carrinho.clear()
            self.mostrar_menu()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")

    # ========================================================
    # TELA DE CADASTRO
    # ========================================================

    def mostrar_cadastro(self):
        self.limpar_tela()
        cores = CORES[TEMA]

        frame = tk.Frame(self.root, bg=cores["bg"])
        frame.pack(expand=True)

        tk.Label(frame, text="👤 CRIAR CONTA", font=("Arial", 26, "bold"), bg=cores["bg"], fg=cores["accent2"]).pack(pady=(10, 25))

        card = tk.Frame(frame, bg=cores["card"], padx=35, pady=30)
        card.pack()

        campos = []
        for texto, mostrar in [("Nome completo", ""), ("Usuário", ""), ("Senha", "*"), ("Confirmar senha", "*")]:
            tk.Label(card, text=texto, bg=cores["card"], fg=cores["text"], font=("Arial", 11, "bold")).pack(anchor="w")
            ent = tk.Entry(card, width=35, show=mostrar, bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat", font=("Arial", 11))
            ent.pack(pady=(5, 12), ipady=6)
            campos.append(ent)

        self.cad_nome, self.cad_usuario, self.cad_senha, self.cad_confirmar = campos

        ttk.Button(card, text="CRIAR CONTA", command=self.criar_conta).pack(fill="x", pady=5)
        ttk.Button(card, text="VOLTAR PARA LOGIN", command=self.mostrar_login).pack(fill="x", pady=5)

    def criar_conta(self):
        nome = self.cad_nome.get().strip()
        usuario = self.cad_usuario.get().strip()
        senha = self.cad_senha.get()
        confirmar = self.cad_confirmar.get()

        if not nome or not usuario or not senha or not confirmar:
            messagebox.showwarning("Atenção", "Preencha todos os campos.")
            return

        if senha != confirmar:
            messagebox.showerror("Erro", "As senhas não coincidem.")
            return

        try:
            conexao = sqlite3.connect(DB_NAME)
            cursor = conexao.cursor()
            cursor.execute("INSERT INTO usuarios (usuario, nome, senha) VALUES (?, ?, ?)", (usuario, nome, senha))
            conexao.commit()
            conexao.close()
            messagebox.showinfo("Sucesso", "Conta criada com sucesso!")
            self.mostrar_login()
        except sqlite3.IntegrityError:
            messagebox.showerror("Erro", "Esse nome de usuário já existe.")

    # ========================================================
    # CARDÁPIO DINÂMICO
    # ========================================================

    def mostrar_menu(self):
        self.limpar_tela()
        cores = CORES[TEMA]

        header = tk.Frame(self.root, bg=cores["card"], height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🍔 Gourmet Service", font=("Arial", 20, "bold"), bg=cores["card"], fg=cores["accent2"]).pack(side="left", padx=20)
        tk.Label(header, text=f"Olá, {self.nome_atual}!", font=("Arial", 11), bg=cores["card"], fg=cores["sub"]).pack(side="left", padx=10)

        total_itens = sum(i["quantidade"] for i in self.carrinho.values())
        txt_carrinho = f"🛒 Carrinho ({total_itens})" if total_itens > 0 else "🛒 Carrinho"

        ttk.Button(header, text="🚪 Sair", command=self.sair_da_conta).pack(side="right", padx=8)
        ttk.Button(header, text="📜 Histórico", command=self.mostrar_historico).pack(side="right", padx=8)
        ttk.Button(header, text="🤖 Suporte IA", command=self.abrir_chat).pack(side="right", padx=8)
        ttk.Button(header, text=txt_carrinho, command=self.mostrar_carrinho).pack(side="right", padx=8)
        
        # Painel Administrativo de Exportação visível apenas para o Root Master
        if self.usuario_atual == "root":
            ttk.Button(header, text="⚙️ Exportar JSON", command=self.exportar_dados_json).pack(side="right", padx=8)

        ttk.Button(header, text="☀️/🌙", command=self.alternar_tema).pack(side="right", padx=8)

        container = tk.Frame(self.root, bg=cores["bg"])
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=cores["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        conteudo = tk.Frame(canvas, bg=cores["bg"])
        conteudo.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=conteudo, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        produtos_por_categoria = carregar_produtos_bd()

        for categoria, produtos in produtos_por_categoria.items():
            tk.Label(conteudo, text=categoria, font=("Arial", 19, "bold"), bg=cores["bg"], fg=cores["text"]).pack(anchor="w", padx=25, pady=(25, 12))
            grade = tk.Frame(conteudo, bg=cores["bg"])
            grade.pack(fill="x", padx=20)

            for col, prod in enumerate(produtos):
                self.criar_card_produto(grade, prod, col)

    def criar_card_produto(self, parent, produto, coluna):
        cores = CORES[TEMA]

        card = tk.Frame(parent, bg=cores["card"], width=280, height=340)
        card.grid(row=0, column=coluna, padx=8, pady=8, sticky="n")
        card.grid_propagate(False)

        img_label = tk.Label(card, text="🍽️", bg=cores["card"], fg=cores["text"], font=("Arial", 45))
        img_label.pack(pady=(12, 5))

        self.carregar_imagem(produto["imagem"], img_label)

        tk.Label(card, text=produto["nome"], font=("Arial", 14, "bold"), bg=cores["card"], fg=cores["text"]).pack()
        tk.Label(card, text=produto["descricao"], font=("Arial", 9), bg=cores["card"], fg=cores["sub"], wraplength=240).pack(pady=5)
        tk.Label(card, text=formatar_moeda(produto["preco"]), font=("Arial", 15, "bold"), bg=cores["card"], fg=cores["accent2"]).pack(pady=5)

        ttk.Button(card, text="➕ Adicionar", command=lambda p=produto: self.adicionar_carrinho(p)).pack(padx=25, pady=8, fill="x")

    def carregar_imagem(self, url, label):
        if not PIL_OK:
            return

        def baixar():
            try:
                resp = requests.get(url, timeout=6)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content))
                img.thumbnail((220, 120))
                foto = ImageTk.PhotoImage(img)

                def atualizar():
                    self.imagens.append(foto)
                    if label.winfo_exists():
                        label.configure(image=foto, text="")

                self.root.after(0, atualizar)
            except Exception:
                pass

        threading.Thread(target=baixar, daemon=True).start()

    # ========================================================
    # EXPORTAÇÃO JSON (RECURSO EXCLUSIVO ROOT MASTER)
    # ========================================================

    def exportar_dados_json(self):
        if self.usuario_atual != "root":
            messagebox.showerror("Acesso Negado", "Apenas o Root Master tem permissão para esta ação.")
            return

        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()

        # Obter todos os pedidos
        cursor.execute("SELECT id, cliente, usuario, data_hora, itens, total, cep, endereco, numero, forma_pagamento FROM pedidos")
        pedidos_db = cursor.fetchall()
        
        lista_pedidos = []
        for p in pedidos_db:
            lista_pedidos.append({
                "id": p[0],
                "cliente": p[1],
                "usuario": p[2],
                "data_hora": p[3],
                "itens": p[4],
                "total": p[5],
                "cep": p[6],
                "endereco": p[7],
                "numero": p[8],
                "forma_pagamento": p[9]
            })

        # Obter todas as conversas do Chat
        cursor.execute("SELECT id, usuario, autor, mensagem, data_hora FROM conversas")
        conversas_db = cursor.fetchall()

        lista_conversas = []
        for c in conversas_db:
            lista_conversas.append({
                "id": c[0],
                "usuario": c[1],
                "autor": c[2],
                "mensagem": c[3],
                "data_hora": c[4]
            })

        conexao.close()

        dados_exportados = {
            "restaurante": INFO_RESTAURANTE["nome"],
            "data_exportacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "pedidos": lista_pedidos,
            "conversas": lista_conversas
        }

        caminho_ficheiro = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Ficheiros JSON", "*.json")],
            title="Guardar Exportação de Dados"
        )

        if caminho_ficheiro:
            try:
                with open(caminho_ficheiro, "w", encoding="utf-8") as f:
                    json.dump(dados_exportados, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("Sucesso", "✅ Dados de conversas e pedidos exportados em JSON com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Ocorreu um erro ao exportar: {e}")

    # ========================================================
    # GERENCIAMENTO DO CARRINHO
    # ========================================================

    def adicionar_carrinho(self, produto):
        nome = produto["nome"]
        if nome not in self.carrinho:
            self.carrinho[nome] = {"produto": produto, "quantidade": 0}
        self.carrinho[nome]["quantidade"] += 1
        messagebox.showinfo("Carrinho", f"✅ {produto['nome']} adicionado ao carrinho!")
        self.mostrar_menu()

    def alterar_quantidade(self, nome, valor):
        if nome in self.carrinho:
            self.carrinho[nome]["quantidade"] += valor
            if self.carrinho[nome]["quantidade"] <= 0:
                del self.carrinho[nome]
            self.mostrar_carrinho()

    def remover_item(self, nome):
        if nome in self.carrinho:
            del self.carrinho[nome]
            self.mostrar_carrinho()

    def calcular_total(self):
        return sum(i["produto"]["preco"] * i["quantidade"] for i in self.carrinho.values())

    def mostrar_carrinho(self):
        self.limpar_tela()
        cores = CORES[TEMA]

        header = tk.Frame(self.root, bg=cores["card"], height=65)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🛒 MEU CARRINHO", font=("Arial", 20, "bold"), bg=cores["card"], fg=cores["text"]).pack(side="left", padx=20)
        ttk.Button(header, text="← Voltar ao cardápio", command=self.mostrar_menu).pack(side="right", padx=20)

        container = tk.Frame(self.root, bg=cores["bg"])
        container.pack(fill="both", expand=True, padx=30, pady=20)

        if not self.carrinho:
            tk.Label(container, text="Seu carrinho está vazio.", font=("Arial", 18), bg=cores["bg"], fg=cores["sub"]).pack(pady=80)
            ttk.Button(container, text="VER CARDÁPIO", command=self.mostrar_menu).pack()
            return

        for nome, item in list(self.carrinho.items()):
            prod = item["produto"]
            qtd = item["quantidade"]

            linha = tk.Frame(container, bg=cores["card"], padx=15, pady=12)
            linha.pack(fill="x", pady=5)

            tk.Label(linha, text=prod["nome"], font=("Arial", 13, "bold"), bg=cores["card"], fg=cores["text"], width=22, anchor="w").pack(side="left")
            tk.Label(linha, text=formatar_moeda(prod["preco"]), bg=cores["card"], fg=cores["accent2"], font=("Arial", 11, "bold")).pack(side="left", padx=15)

            ttk.Button(linha, text="−", command=lambda n=nome: self.alterar_quantidade(n, -1)).pack(side="left", padx=2)
            tk.Label(linha, text=str(qtd), width=4, bg=cores["card"], fg=cores["text"], font=("Arial", 11, "bold")).pack(side="left")
            ttk.Button(linha, text="+", command=lambda n=nome: self.alterar_quantidade(n, 1)).pack(side="left", padx=2)

            ttk.Button(linha, text="Remover", command=lambda n=nome: self.remover_item(n)).pack(side="right")

        rodape = tk.Frame(container, bg=cores["bg"])
        rodape.pack(fill="x", pady=25)

        tk.Label(rodape, text=f"TOTAL: {formatar_moeda(self.calcular_total())}", font=("Arial", 20, "bold"), bg=cores["bg"], fg=cores["text"]).pack(side="left")
        ttk.Button(rodape, text="FINALIZAR PEDIDO", command=self.finalizar_pedido).pack(side="right")

    # ========================================================
    # CHECKOUT
    # ========================================================

    def finalizar_pedido(self):
        if not self.carrinho:
            messagebox.showwarning("Carrinho", "Adicione produtos antes de finalizar.")
            return

        cores = CORES[TEMA]

        janela = tk.Toplevel(self.root)
        janela.title("Finalizar Pedido")
        janela.geometry("520x640")
        janela.configure(bg=cores["bg"])
        janela.transient(self.root)
        janela.grab_set()

        tk.Label(janela, text="📦 CHECKOUT", font=("Arial", 20, "bold"), bg=cores["bg"], fg=cores["accent2"]).pack(pady=15)

        form = tk.Frame(janela, bg=cores["card"], padx=25, pady=20)
        form.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        tk.Label(form, text="CEP", bg=cores["card"], fg=cores["text"], font=("Arial", 10, "bold")).pack(anchor="w")
        cep_entry = tk.Entry(form, bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat")
        cep_entry.pack(fill="x", pady=(3, 8), ipady=6)

        tk.Label(form, text="Endereço Completo", bg=cores["card"], fg=cores["text"], font=("Arial", 10, "bold")).pack(anchor="w")
        endereco_entry = tk.Entry(form, bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat")
        endereco_entry.pack(fill="x", pady=(3, 8), ipady=6)

        def buscar_cep():
            cep_limpo = re.sub(r"\D", "", cep_entry.get())
            if len(cep_limpo) != 8:
                messagebox.showwarning("CEP", "Digite um CEP válido com 8 dígitos.", parent=janela)
                return

            try:
                resp = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=5)
                dados = resp.json()
                if dados.get("erro"):
                    messagebox.showerror("CEP", "CEP não localizado.", parent=janela)
                    return

                rua_completa = f"{dados.get('logradouro', '')}, {dados.get('bairro', '')}, {dados.get('localidade', '')} - {dados.get('uf', '')}"
                endereco_entry.delete(0, tk.END)
                endereco_entry.insert(0, rua_completa)
            except Exception:
                messagebox.showerror("Erro", "Falha ao conectar com o serviço de CEP.", parent=janela)

        ttk.Button(form, text="🔎 Buscar Endereço", command=buscar_cep).pack(fill="x", pady=(0, 10))

        tk.Label(form, text="Número / Complemento", bg=cores["card"], fg=cores["text"], font=("Arial", 10, "bold")).pack(anchor="w")
        numero_entry = tk.Entry(form, bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat")
        numero_entry.pack(fill="x", pady=(3, 10), ipady=6)

        tk.Label(form, text="Forma de Pagamento", bg=cores["card"], fg=cores["text"], font=("Arial", 10, "bold")).pack(anchor="w")
        pagamento = ttk.Combobox(form, values=["PIX", "Cartão de Crédito", "Cartão de Débito", "Dinheiro"], state="readonly")
        pagamento.current(0)
        pagamento.pack(fill="x", pady=(3, 15))

        tk.Label(form, text=f"Total: {formatar_moeda(self.calcular_total())}", bg=cores["card"], fg=cores["accent2"], font=("Arial", 15, "bold")).pack(pady=5)

        def confirmar():
            cep = cep_entry.get().strip()
            endereco = endereco_entry.get().strip()
            numero = numero_entry.get().strip()
            forma = pagamento.get()

            if not cep or not endereco or not numero:
                messagebox.showwarning("Atenção", "Preencha o CEP, Endereço e Número antes de confirmar!", parent=janela)
                return

            resumo = [f"{item['quantidade']}x {item['produto']['nome']}" for item in self.carrinho.values()]
            itens_str = ", ".join(resumo)
            total = self.calcular_total()

            try:
                conexao = sqlite3.connect(DB_NAME)
                cursor = conexao.cursor()
                cursor.execute("""
                    INSERT INTO pedidos (cliente, usuario, data_hora, itens, total, cep, endereco, numero, forma_pagamento)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (self.nome_atual, self.usuario_atual, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), itens_str, total, cep, endereco, numero, forma))
                conexao.commit()
                conexao.close()

                self.carrinho.clear()
                janela.destroy()
                messagebox.showinfo("Sucesso", "✅ Pedido confirmado com sucesso!")
                self.mostrar_menu()
            except Exception as e:
                messagebox.showerror("Erro ao Salvar", f"Não foi possível gravar o pedido: {e}", parent=janela)

        ttk.Button(form, text="✅ CONFIRMAR PEDIDO", command=confirmar).pack(fill="x", pady=8)

    # ========================================================
    # HISTÓRICO DE PEDIDOS
    # ========================================================

    def mostrar_historico(self):
        self.limpar_tela()
        cores = CORES[TEMA]

        header = tk.Frame(self.root, bg=cores["card"], height=65)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="📜 MEUS PEDIDOS", font=("Arial", 18, "bold"), bg=cores["card"], fg=cores["text"]).pack(side="left", padx=20)
        ttk.Button(header, text="← Voltar", command=self.mostrar_menu).pack(side="right", padx=20)

        container = tk.Frame(self.root, bg=cores["bg"])
        container.pack(fill="both", expand=True, padx=30, pady=20)

        conexao = sqlite3.connect(DB_NAME)
        cursor = conexao.cursor()
        
        if self.usuario_atual == "root":
            cursor.execute("SELECT data_hora, itens, total, endereco, numero, forma_pagamento FROM pedidos ORDER BY id DESC")
        else:
            cursor.execute("SELECT data_hora, itens, total, endereco, numero, forma_pagamento FROM pedidos WHERE usuario = ? ORDER BY id DESC", (self.usuario_atual,))
            
        pedidos = cursor.fetchall()
        conexao.close()

        if not pedidos:
            tk.Label(container, text="Nenhum pedido encontrado.", font=("Arial", 16), bg=cores["bg"], fg=cores["sub"]).pack(pady=80)
            return

        canvas = tk.Canvas(container, bg=cores["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        conteudo = tk.Frame(canvas, bg=cores["bg"])

        conteudo.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=conteudo, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for p in pedidos:
            card = tk.Frame(conteudo, bg=cores["card"], padx=15, pady=12)
            card.pack(fill="x", pady=6, expand=True)

            tk.Label(card, text=f"📅 Data: {p[0]}", font=("Arial", 10, "bold"), bg=cores["card"], fg=cores["accent2"]).pack(anchor="w")
            tk.Label(card, text=f"🛍️ Itens: {p[1]}", font=("Arial", 11), bg=cores["card"], fg=cores["text"]).pack(anchor="w", pady=2)
            tk.Label(card, text=f"💳 Pagamento: {p[5]} | Total: {formatar_moeda(p[2])}", font=("Arial", 11, "bold"), bg=cores["card"], fg=cores["text"]).pack(anchor="w")

    # ========================================================
    # IA ASSISTENTE DINÂMICA (CHATBOX DIMINUÍDO E REGISTO)
    # ========================================================

    def abrir_chat(self):
        if self.janela_chat and self.janela_chat.winfo_exists():
            self.janela_chat.lift()
            return

        cores = CORES[TEMA]
        self.janela_chat = tk.Toplevel(self.root)
        self.janela_chat.title("🤖 Suporte IA")
        
        # DIMINUÍDO O TAMANHO DO CHATBOX
        self.janela_chat.geometry("380x480") 
        self.janela_chat.configure(bg=cores["bg"])
        self.janela_chat.protocol("WM_DELETE_WINDOW", self.fechar_chat)

        header = tk.Frame(self.janela_chat, bg=cores["accent"], height=45)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🤖 Assistente IA", font=("Arial", 12, "bold"), bg=cores["accent"], fg="white").pack(side="left", padx=10)

        self.chat_texto = tk.Text(self.janela_chat, bg=cores["card"], fg=cores["text"], font=("Arial", 9), wrap="word", state="disabled", padx=8, pady=8, relief="flat")
        self.chat_texto.pack(fill="both", expand=True, padx=8, pady=8)

        f_ent = tk.Frame(self.janela_chat, bg=cores["bg"])
        f_ent.pack(fill="x", padx=8, pady=(0, 8))

        self.chat_entry = tk.Entry(f_ent, bg=cores["entry"], fg=cores["text"], insertbackground=cores["text"], relief="flat", font=("Arial", 9))
        self.chat_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 5))

        ttk.Button(f_ent, text="ENVIAR", command=self.enviar_chat).pack(side="right")
        self.chat_entry.bind("<Return>", lambda e: self.enviar_chat())

        self.adicionar_chat("IA", f"Olá, {self.nome_atual}! Como posso te ajudar hoje?", salvar=False)

    def fechar_chat(self):
        if self.janela_chat:
            self.janela_chat.destroy()
        self.janela_chat = None

    def adicionar_chat(self, autor, msg, salvar=True):
        if self.chat_texto:
            self.chat_texto.configure(state="normal")
            self.chat_texto.insert(tk.END, f"{autor}: {msg}\n\n")
            self.chat_texto.configure(state="disabled")
            self.chat_texto.see(tk.END)

        if salvar:
            try:
                conexao = sqlite3.connect(DB_NAME)
                cursor = conexao.cursor()
                cursor.execute("""
                    INSERT INTO conversas (usuario, autor, mensagem, data_hora)
                    VALUES (?, ?, ?, ?)
                """, (self.usuario_atual, autor, msg, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
                conexao.commit()
                conexao.close()
            except Exception:
                pass

    def enviar_chat(self):
        if not self.chat_entry:
            return
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        self.chat_entry.delete(0, tk.END)
        self.adicionar_chat("Você", msg)
        self.root.after(300, lambda: self.processar_ia(msg))

    def processar_ia(self, mensagem):
        texto = normalizar_texto(mensagem)
        produtos = todos_produtos()

        if any(w in texto for w in ["hora", "horario", "aberto", "fechado"]):
            status = "🟢 ABERTO" if restaurante_aberto() else "🔴 FECHADO"
            resp = f"Status: {status}\nHorário: {INFO_RESTAURANTE['horario_abertura']}h às {INFO_RESTAURANTE['horario_fechamento']}h."
        elif "mais barato" in texto:
            barato = min(produtos, key=lambda x: x["preco"])
            resp = f"O item mais barato do cardápio é **{barato['nome']}** por {formatar_moeda(barato['preco'])}."
        elif any(w in texto for w in ["orcamento", "gostar", "posso gastar", "reais"]):
            numeros = re.findall(r"\d+", texto)
            if numeros:
                v = float(numeros[0])
                opcoes = [p for p in produtos if p["preco"] <= v]
                if opcoes:
                    res = [f"Com R$ {v:.2f}, você pode comprar:"]
                    for o in opcoes:
                        res.append(f"• {o['nome']} - {formatar_moeda(o['preco'])}")
                    resp = "\n".join(res)
                else:
                    resp = f"Com R$ {v:.2f} não temos opções disponíveis no momento."
            else:
                resp = "Informe um valor limite em reais para eu filtrar as opções!"
        else:
            resp = "Posso consultar horários, verificar itens por preço ou calcular o que você pode comprar com seu orçamento!"

        self.adicionar_chat("IA", resp)


# ============================================================
# EXECUÇÃO DA APLICAÇÃO
# ============================================================

if __name__ == "__main__":
    root = tk.Tk()
    app = GourmetService(root)
    root.mainloop()