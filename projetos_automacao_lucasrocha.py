import io
import json
import os
import sqlite3
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import requests

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# ===================== BANCO DE DADOS =====================


def inicializar_banco():
    conn = sqlite3.connect("restaurante.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            usuario TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            itens TEXT NOT NULL,
            total REAL NOT NULL,
            cep TEXT NOT NULL,
            endereco TEXT NOT NULL,
            numero TEXT NOT NULL,
            forma_pagamento TEXT NOT NULL
        )
    """
    )

    conn.commit()
    conn.close()


def salvar_usuario_bd(usuario, nome, senha):
    conn = sqlite3.connect("restaurante.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (usuario, nome, senha) VALUES (?, ?, ?)",
            (usuario, nome, senha),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def buscar_usuario_bd(usuario):
    conn = sqlite3.connect("restaurante.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT usuario, nome, senha FROM usuarios WHERE usuario = ?",
        (usuario,),
    )
    res = cursor.fetchone()
    conn.close()
    return res


def salvar_pedido_bd(pedido):
    conn = sqlite3.connect("restaurante.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO pedidos (cliente, data_hora, itens, total, cep, endereco, numero, forma_pagamento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            pedido["cliente"],
            pedido["data_hora"],
            json.dumps(pedido["itens"], ensure_ascii=False),
            pedido["total"],
            pedido["cep"],
            pedido["endereco"],
            pedido["numero"],
            pedido["forma_pagamento"],
        ),
    )
    conn.commit()
    pedido_id = cursor.lastrowid
    conn.close()
    return pedido_id


# ===================== DADOS DO CARDÁPIO =====================

CARDAPIO_PADRAO = [
    {
        "categoria": "🍔 HAMBÚRGUERES",
        "itens": [
            {
                "nome": "Poderoso Chefão",
                "preco": 34.90,
                "desc": "Blend 180g, gorgonzola e bacon.",
            },
            {
                "nome": "Clássico Smash",
                "preco": 22.00,
                "desc": "2x smash 80g e cheddar.",
            },
            {
                "nome": "Duplo Bacon",
                "preco": 38.50,
                "desc": "2x blends 180g e triplo bacon.",
            },
            {
                "nome": "Chicken Crispy",
                "preco": 25.90,
                "desc": "Frango crocante e coleslaw.",
            },
        ],
    },
    {
        "categoria": "🍕 PIZZAS",
        "itens": [
            {
                "nome": "Calabresa",
                "preco": 45.00,
                "desc": "Calabresa fatiada e cebola.",
            },
            {
                "nome": "Marguerita",
                "preco": 42.00,
                "desc": "Muçarela e manjericão fresco.",
            },
            {
                "nome": "Quatro Queijos",
                "preco": 50.00,
                "desc": "Muçarela, provolone, gorgonzola e parmesão.",
            },
        ],
    },
    {
        "categoria": "🥤 BEBIDAS",
        "itens": [
            {
                "nome": "Soda Artesanal",
                "preco": 12.00,
                "desc": "Frutas vermelhas 500ml.",
            },
            {
                "nome": "Milkshake",
                "preco": 18.00,
                "desc": "Chocolate ou Morango 400ml.",
            },
            {
                "nome": "Refrigerante",
                "preco": 6.50,
                "desc": "Lata 350ml.",
            },
        ],
    },
]

# ===================== SISTEMA PRINCIPAL =====================


class SistemaGourmetApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Gourmet Service - Sistema de Pedidos")
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.geometry("1100x700")

        self.usuario_atual = None
        self.carrinho = {}  # {nome_item: {"preco": X, "qtd": Y}}

        self.container = tk.Frame(self.root, bg="#121212")
        self.container.pack(fill="both", expand=True)

        self.mostrar_tela_login()

    # ===================== TELA DE LOGIN =====================

    def mostrar_tela_login(self):
        for w in self.container.winfo_children():
            w.destroy()

        card = tk.Frame(
            self.container, bg="#1E1E1E", padx=40, pady=30, bd=1, relief="solid"
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="🔥 GOURMET SERVICE 🔥",
            font=("Segoe UI", 18, "bold"),
            bg="#1E1E1E",
            fg="#693DE2",
        ).pack(pady=(0, 15))

        tk.Label(
            card,
            text="Usuário",
            font=("Segoe UI", 10, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w")
        self.ent_user = tk.Entry(
            card,
            font=("Segoe UI", 11),
            width=28,
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        self.ent_user.pack(pady=(2, 10))

        tk.Label(
            card,
            text="Senha",
            font=("Segoe UI", 10, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w")
        self.ent_pass = tk.Entry(
            card,
            font=("Segoe UI", 11),
            width=28,
            show="*",
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        self.ent_pass.pack(pady=(2, 15))

        tk.Button(
            card,
            text="ENTRAR",
            command=self.fazer_login,
            bg="#693DE2",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")
        tk.Button(
            card,
            text="Criar nova conta",
            command=self.mostrar_tela_cadastro,
            bg="#1E1E1E",
            fg="#8B39E7",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
        ).pack(pady=5)

    def fazer_login(self):
        usr = self.ent_user.get().strip()
        pwd = self.ent_pass.get().strip()

        res = buscar_usuario_bd(usr)
        if res and res[2] == pwd:
            self.usuario_atual = {"usuario": res[0], "nome": res[1]}
            self.mostrar_tela_cardapio()
        else:
            messagebox.showerror("Erro", "Usuário ou senha incorretos.")

    def mostrar_tela_cadastro(self):
        for w in self.container.winfo_children():
            w.destroy()

        card = tk.Frame(
            self.container, bg="#1E1E1E", padx=40, pady=30, bd=1, relief="solid"
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="📝 CRIAR CONTA",
            font=("Segoe UI", 16, "bold"),
            bg="#1E1E1E",
            fg="#693DE2",
        ).pack(pady=(0, 15))

        tk.Label(
            card,
            text="Nome Completo",
            font=("Segoe UI", 10, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w")
        ent_nome = tk.Entry(
            card,
            font=("Segoe UI", 11),
            width=28,
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        ent_nome.pack(pady=(2, 10))

        tk.Label(
            card,
            text="Usuário",
            font=("Segoe UI", 10, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w")
        ent_user = tk.Entry(
            card,
            font=("Segoe UI", 11),
            width=28,
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        ent_user.pack(pady=(2, 10))

        tk.Label(
            card,
            text="Senha",
            font=("Segoe UI", 10, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w")
        ent_pass = tk.Entry(
            card,
            font=("Segoe UI", 11),
            width=28,
            show="*",
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        ent_pass.pack(pady=(2, 15))

        def cadastrar():
            if salvar_usuario_bd(
                ent_user.get().strip(),
                ent_nome.get().strip(),
                ent_pass.get().strip(),
            ):
                messagebox.showinfo("Sucesso", "Conta criada com sucesso!")
                self.mostrar_tela_login()
            else:
                messagebox.showerror("Erro", "Nome de usuário já existe.")

        tk.Button(
            card,
            text="CADASTRAR",
            command=cadastrar,
            bg="#693DE2",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")
        tk.Button(
            card,
            text="Voltar ao Login",
            command=self.mostrar_tela_login,
            bg="#1E1E1E",
            fg="#8B39E7",
            font=("Segoe UI", 9),
            relief="flat",
        ).pack(pady=5)

    # ===================== TELA DO CARDÁPIO & CARRINHO =====================

    def mostrar_tela_cardapio(self):
        for w in self.container.winfo_children():
            w.destroy()

        # Header
        header = tk.Frame(self.container, bg="#693DE2", height=60)
        header.pack(fill="x")
        tk.Label(
            header,
            text="🔥 GOURMET SERVICE",
            font=("Segoe UI", 16, "bold"),
            bg="#693DE2",
            fg="white",
        ).pack(side="left", padx=20)
        tk.Label(
            header,
            text=f"👤 {self.usuario_atual['nome']}",
            font=("Segoe UI", 10),
            bg="#693DE2",
            fg="white",
        ).pack(side="right", padx=20)

        # Corpo
        corpo = tk.Frame(self.container, bg="#121212")
        corpo.pack(fill="both", expand=True, padx=10, pady=10)

        # Lado Esquerdo: Cardápio
        painel_cardapio = tk.Frame(corpo, bg="#121212")
        painel_cardapio.pack(side="left", fill="both", expand=True)

        notebook = ttk.Notebook(painel_cardapio)
        notebook.pack(fill="both", expand=True)

        for bloco in CARDAPIO_PADRAO:
            aba = tk.Frame(notebook, bg="#121212")
            notebook.add(aba, text=bloco["categoria"])

            for item in bloco["itens"]:
                card = tk.Frame(aba, bg="#1E1E1E", padx=10, pady=8, bd=1)
                card.pack(fill="x", pady=4, padx=5)

                info = tk.Frame(card, bg="#1E1E1E")
                info.pack(side="left", fill="x", expand=True)

                tk.Label(
                    info,
                    text=f"{item['nome']} - R$ {item['preco']:.2f}",
                    font=("Segoe UI", 11, "bold"),
                    bg="#1E1E1E",
                    fg="#8B39E7",
                ).pack(anchor="w")
                tk.Label(
                    info,
                    text=item["desc"],
                    font=("Segoe UI", 9),
                    bg="#1E1E1E",
                    fg="#CCCCCC",
                ).pack(anchor="w")

                # Botão de 1 CLIQUE para Adicionar
                tk.Button(
                    card,
                    text="➕ Adicionar",
                    command=lambda i=item: self.adicionar_ao_carrinho(i),
                    bg="#693DE2",
                    fg="white",
                    font=("Segoe UI", 9, "bold"),
                    relief="flat",
                    cursor="hand2",
                ).pack(side="right", padx=5)

        # Lado Direito: Carrinho
        painel_carrinho = tk.Frame(
            corpo, bg="#1E1E1E", width=350, bd=1, relief="solid"
        )
        painel_carrinho.pack(side="right", fill="both", padx=(10, 0))
        painel_carrinho.pack_propagate(False)

        tk.Label(
            painel_carrinho,
            text="🛒 SEU CARRINHO",
            font=("Segoe UI", 12, "bold"),
            bg="#1E1E1E",
            fg="#693DE2",
        ).pack(pady=10)

        # Lista do Carrinho
        self.frame_lista_cart = tk.Frame(painel_carrinho, bg="#1E1E1E")
        self.frame_lista_cart.pack(fill="both", expand=True, padx=10)

        # Footer do Carrinho
        footer_cart = tk.Frame(painel_carrinho, bg="#1E1E1E")
        footer_cart.pack(fill="x", padx=10, pady=10)

        self.lbl_total = tk.Label(
            footer_cart,
            text="TOTAL: R$ 0.00",
            font=("Segoe UI", 14, "bold"),
            bg="#1E1E1E",
            fg="white",
        )
        self.lbl_total.pack(pady=5)

        tk.Button(
            footer_cart,
            text="CHECKOUT / FINALIZAR ➔",
            command=self.abrir_modal_checkout,
            bg="#693DE2",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
        ).pack(fill="x")

        self.atualizar_interface_carrinho()

    # ===================== LÓGICA DO CARRINHO (1 CLIQUE) =====================

    def adicionar_ao_carrinho(self, item):
        nome = item["nome"]
        preco = item["preco"]

        if nome in self.carrinho:
            self.carrinho[nome]["qtd"] += 1
        else:
            self.carrinho[nome] = {"preco": preco, "qtd": 1}

        self.atualizar_interface_carrinho()

    def remover_uma_qtd(self, nome):
        if nome in self.carrinho:
            self.carrinho[nome]["qtd"] -= 1
            if self.carrinho[nome]["qtd"] <= 0:
                del self.carrinho[nome]
        self.atualizar_interface_carrinho()

    def remover_item_completo(self, nome):
        if nome in self.carrinho:
            del self.carrinho[nome]
        self.atualizar_interface_carrinho()

    def atualizar_interface_carrinho(self):
        for w in self.frame_lista_cart.winfo_children():
            w.destroy()

        total = 0.0

        if not self.carrinho:
            tk.Label(
                self.frame_lista_cart,
                text="Carrinho vazio",
                bg="#1E1E1E",
                fg="#888888",
            ).pack(pady=20)
        else:
            for nome, dados in self.carrinho.items():
                subtotal = dados["preco"] * dados["qtd"]
                total += subtotal

                row = tk.Frame(self.frame_lista_cart, bg="#2A2A2A", pady=3)
                row.pack(fill="x", pady=2)

                tk.Label(
                    row,
                    text=f"{dados['qtd']}x {nome[:12]}..",
                    font=("Segoe UI", 9, "bold"),
                    bg="#2A2A2A",
                    fg="white",
                    width=12,
                    anchor="w",
                ).pack(side="left", padx=5)

                tk.Label(
                    row,
                    text=f"R${subtotal:.2f}",
                    font=("Segoe UI", 9),
                    bg="#2A2A2A",
                    fg="#8B39E7",
                ).pack(side="left")

                # Botões interativos de ajuste (+, -, x)
                tk.Button(
                    row,
                    text="❌",
                    command=lambda n=nome: self.remover_item_completo(n),
                    bg="#2A2A2A",
                    fg="#FF5555",
                    relief="flat",
                ).pack(side="right", padx=2)
                tk.Button(
                    row,
                    text="-",
                    command=lambda n=nome: self.remover_uma_qtd(n),
                    bg="#444",
                    fg="white",
                    relief="flat",
                    width=2,
                ).pack(side="right", padx=1)
                tk.Button(
                    row,
                    text="+",
                    command=lambda n={
                        "nome": nome,
                        "preco": dados["preco"],
                    }: self.adicionar_ao_carrinho(n),
                    bg="#693DE2",
                    fg="white",
                    relief="flat",
                    width=2,
                ).pack(side="right", padx=1)

        self.lbl_total.config(text=f"TOTAL: R$ {total:.2f}")

    # ===================== FLUXO DE CHECKOUT & VIA CEP =====================

    def abrir_modal_checkout(self):
        if not self.carrinho:
            messagebox.showwarning(
                "Carrinho Vazio", "Adicione produtos antes de finalizar!"
            )
            return

        modal = tk.Toplevel(self.root)
        modal.title("Finalizar Pedido - Endereço & Pagamento")
        modal.geometry("400x520")
        modal.configure(bg="#1E1E1E")
        modal.transient(self.root)
        modal.grab_set()

        tk.Label(
            modal,
            text="📍 ENDEREÇO DE ENTREGA",
            font=("Segoe UI", 12, "bold"),
            bg="#1E1E1E",
            fg="#693DE2",
        ).pack(pady=(15, 5))

        # Etapa CEP
        tk.Label(
            modal,
            text="Digite o CEP:",
            font=("Segoe UI", 9, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w", padx=20)
        frame_cep = tk.Frame(modal, bg="#1E1E1E")
        frame_cep.pack(fill="x", padx=20, pady=2)

        ent_cep = tk.Entry(
            frame_cep,
            font=("Segoe UI", 10),
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        ent_cep.pack(side="left", fill="x", expand=True)

        lbl_rua = tk.Label(
            modal,
            text="Rua: (Buscar CEP primeiro)",
            font=("Segoe UI", 9),
            bg="#1E1E1E",
            fg="#AAAAAA",
            wraplength=350,
            justify="left",
        )

        dados_endereco = {"valido": False, "logradouro": "", "cidade": ""}

        def consultar_cep():
            cep = "".join(filter(str.isdigit, ent_cep.get()))
            if len(cep) != 8:
                messagebox.showerror(
                    "CEP Errado",
                    "CEP inválido! Digite 8 números.",
                    parent=modal,
                )
                return

            try:
                res = requests.get(
                    f"https://viacep.com.br/ws/{cep}/json/", timeout=5
                ).json()
                if "erro" in res:
                    messagebox.showerror(
                        "CEP Errado",
                        "CEP não encontrado na base de dados!",
                        parent=modal,
                    )
                else:
                    dados_endereco["valido"] = True
                    dados_endereco["logradouro"] = (
                        f"{res.get('logradouro')}, {res.get('bairro')}"
                    )
                    dados_endereco["cidade"] = (
                        f"{res.get('localidade')}/{res.get('uf')}"
                    )
                    lbl_rua.config(
                        text=f"Rua: {dados_endereco['logradouro']} ({dados_endereco['cidade']})",
                        fg="#00FF88",
                    )
            except Exception:
                messagebox.showerror(
                    "Erro", "Erro ao conectar com servidor de CEP."
                )

        tk.Button(
            frame_cep,
            text="Buscar CEP",
            command=consultar_cep,
            bg="#693DE2",
            fg="white",
            font=("Segoe UI", 8, "bold"),
            relief="flat",
        ).pack(side="right", padx=(5, 0))

        lbl_rua.pack(anchor="w", padx=20, pady=5)

        # Número da Rua
        tk.Label(
            modal,
            text="Número da residência e Complemento:",
            font=("Segoe UI", 9, "bold"),
            bg="#1E1E1E",
            fg="white",
        ).pack(anchor="w", padx=20)
        ent_num = tk.Entry(
            modal,
            font=("Segoe UI", 10),
            bg="#2A2A2A",
            fg="white",
            insertbackground="white",
        )
        ent_num.pack(fill="x", padx=20, pady=2)

        # SEÇÃO DE PAGAMENTO (Aparece somente nesta etapa)
        tk.Label(
            modal,
            text="💳 FORMA DE PAGAMENTO",
            font=("Segoe UI", 12, "bold"),
            bg="#1E1E1E",
            fg="#693DE2",
        ).pack(pady=(15, 5))

        combo_pag = ttk.Combobox(
            modal,
            values=[
                "PIX",
                "Cartão de Crédito",
                "Cartão de Débito",
                "Dinheiro",
            ],
            state="readonly",
            font=("Segoe UI", 10),
        )
        combo_pag.set("PIX")
        combo_pag.pack(fill="x", padx=20, pady=5)

        # Botão Final
        def concluir_tudo():
            if not dados_endereco["valido"]:
                messagebox.showerror(
                    "Erro",
                    "Por favor, consulte e valide um CEP correto primeiro.",
                    parent=modal,
                )
                return

            num = ent_num.get().strip()
            if not num:
                messagebox.showwarning(
                    "Aviso",
                    "Digite o número da rua/residência.",
                    parent=modal,
                )
                return

            total_calculado = sum(
                v["preco"] * v["qtd"] for v in self.carrinho.values()
            )

            # Estruturar Pedido
            itens_lista = [
                {
                    "item": k,
                    "quantidade": v["qtd"],
                    "subtotal": v["preco"] * v["qtd"],
                }
                for k, v in self.carrinho.items()
            ]

            pedido = {
                "cliente": self.usuario_atual["nome"],
                "data_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "itens": itens_lista,
                "total": total_calculado,
                "cep": ent_cep.get().strip(),
                "endereco": dados_endereco["logradouro"],
                "numero": num,
                "forma_pagamento": combo_pag.get(),
            }

            pedido_id = salvar_pedido_bd(pedido)
            pedido["id"] = pedido_id

            modal.destroy()
            self.enviar_para_whatsapp_ia(pedido)
            self.carrinho.clear()
            self.atualizar_interface_carrinho()

        tk.Button(
            modal,
            text="CONFIRMAR E ENVIAR PEDIDO 🚀",
            command=concluir_tudo,
            bg="#00AA55",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
        ).pack(fill="x", padx=20, pady=20)

    # ===================== ENVIO PARA WHATSAPP IA =====================

    def enviar_para_whatsapp_ia(self, pedido):
        itens_txt = "\n".join(
            [f"• {i['quantidade']}x {i['item']} (R${i['subtotal']:.2f})" for i in pedido["itens"]]
        )

        mensagem = (
            f"🤖 *NOVO PEDIDO RECEBIDO #{pedido['id']}*\n\n"
            f"👤 *Cliente:* {pedido['cliente']}\n"
            f"📅 *Data:* {pedido['data_hora']}\n\n"
            f"🛒 *ITENS DO PEDIDO:*\n{itens_txt}\n\n"
            f"💰 *TOTAL:* R$ {pedido['total']:.2f}\n"
            f"💳 *Pagamento:* {pedido['forma_pagamento']}\n\n"
            f"📍 *ENDEREÇO DE ENTREGA:*\n"
            f"Rua: {pedido['endereco']}, Nº {pedido['numero']}\n"
            f"CEP: {pedido['cep']}"
        )

        # Número simulado do WhatsApp da IA (coloque o número com DDD)
        numero_whatsapp_ia = "5511999999999"

        # Abre o WhatsApp Web com o texto pronto
        texto_codificado = urllib.parse.quote(mensagem)
        link_api = f"https://api.whatsapp.com/send?phone={numero_whatsapp_ia}&text={texto_codificado}"

        webbrowser.open(link_api)

        messagebox.showinfo(
            "Pedido Salvo",
            f"Pedido N° {pedido['id']} registrado no Banco de Dados!\n\nRedirecionando para a conversa do WhatsApp...",
        )


# ===================== EXECUÇÃO DO PROGRAMA =====================

if __name__ == "__main__":
    inicializar_banco()
    root = tk.Tk()
    app = SistemaGourmetApp(root)
    root.mainloop()