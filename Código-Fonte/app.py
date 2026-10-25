"""
SonicStock / BlueStock — back-end Flask + MySQL.

Estrutura:
  * Páginas HTML (render_template)  -> /, /dashboard, /produtos, ...
  * API JSON (usada pelo front-end) -> /api/...
  * Rotas já existentes mantidas      -> /login, /logout, POST /usuarios, /teste-banco

Todas as respostas JSON seguem o padrão: {"sucesso": true/false, "mensagem": "...", ...}
"""

import os
from datetime import date, datetime
from decimal import Decimal
from functools import wraps

import mysql.connector
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Chave usada pelo Flask para proteger a sessão.
# Em produção, defina a variável de ambiente SONICSTOCK_SECRET_KEY.
app.secret_key = os.environ.get("SONICSTOCK_SECRET_KEY", "chave-temporaria-sonicstock")


# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "root"),
    "database": os.environ.get("DB_NAME", "bluestock"),
}

PERFIS_VALIDOS = ("ADMINISTRADOR", "FUNCIONARIO")


class ErroApi(Exception):
    """Erro de negócio que vira resposta JSON com o status HTTP indicado."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def conectar_banco():
    try:
        conexao = mysql.connector.connect(**DB_CONFIG)
        if conexao.is_connected():
            return conexao
    except Error as erro:
        print(f"Erro ao conectar ao MySQL: {erro}")
    return None


def abrir_conexao():
    conexao = conectar_banco()
    if conexao is None:
        raise ErroApi("Não foi possível conectar ao banco de dados.", 500)
    return conexao


def limpar(valor):
    """Converte tipos do MySQL (Decimal, datetime) em tipos aceitos pelo JSON."""
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: limpar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [limpar(v) for v in valor]
    return valor


def consultar(sql, params=(), um=False):
    """Executa um SELECT e devolve lista de dicionários (ou um único dicionário)."""
    conexao = abrir_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(sql, params)
        linhas = cursor.fetchone() if um else cursor.fetchall()
        cursor.close()
        return limpar(linhas)
    finally:
        conexao.close()


def executar(sql, params=()):
    """Executa INSERT/UPDATE/DELETE com commit. Devolve (lastrowid, linhas_afetadas)."""
    conexao = abrir_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(sql, params)
        conexao.commit()
        resultado = (cursor.lastrowid, cursor.rowcount)
        cursor.close()
        return resultado
    except Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def resposta(mensagem="", status=200, **extra):
    corpo = {"sucesso": status < 400, "mensagem": mensagem}
    corpo.update(extra)
    return jsonify(corpo), status


# ------------------------------------------------------------
# Tratamento global de erros (sempre responde JSON nas APIs)
# ------------------------------------------------------------

@app.errorhandler(ErroApi)
def tratar_erro_api(erro):
    return resposta(erro.mensagem, erro.status)


@app.errorhandler(Error)
def tratar_erro_mysql(erro):
    codigo = getattr(erro, "errno", None)
    if codigo == 1062:
        return resposta("Já existe um registro com esses dados (valor duplicado).", 409)
    if codigo == 1451:
        return resposta("Este registro está em uso por outros dados e não pode ser excluído.", 409)
    if codigo == 1452:
        return resposta("Categoria, fornecedor ou produto informado não existe.", 400)
    print(f"Erro MySQL: {erro}")
    return resposta("Erro ao acessar o banco de dados.", 500)


# ============================================================
# AUTENTICAÇÃO / AUTORIZAÇÃO
# ============================================================

def usuario_logado():
    return bool(session.get("id_usuario"))


def usuario_e_admin():
    return session.get("perfil") == "ADMINISTRADOR"


def pagina_protegida(admin=False):
    """Páginas HTML: sem login -> volta para a tela de login."""

    def decorador(funcao):
        @wraps(funcao)
        def interno(*args, **kwargs):
            if not usuario_logado():
                return redirect(url_for("pagina_login"))
            if admin and not usuario_e_admin():
                return "Acesso permitido somente para administradores.", 403
            return funcao(*args, **kwargs)

        return interno

    return decorador


def api_protegida(admin=False):
    """Rotas JSON: sem login -> 401; sem permissão -> 403."""

    def decorador(funcao):
        @wraps(funcao)
        def interno(*args, **kwargs):
            if not usuario_logado():
                return resposta("Sessão expirada. Faça login novamente.", 401)
            if admin and not usuario_e_admin():
                return resposta("Acesso permitido somente para administradores.", 403)
            return funcao(*args, **kwargs)

        return interno

    return decorador


# ============================================================
# PÁGINAS (HTML)
# ============================================================

@app.route("/")
def pagina_login():
    if usuario_logado():
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
@pagina_protegida()
def dashboard():
    return render_template("dashboard.html")


@app.route("/fornecedores")
@pagina_protegida()
def fornecedores():
    return render_template("fornecedores.html")


@app.route("/produtos")
@pagina_protegida()
def produtos():
    return render_template("produtos.html")


@app.route("/categorias")
@pagina_protegida()
def categorias():
    return render_template("categorias.html")


@app.route("/produtos/adicionar")
@pagina_protegida()
def adicionar_produto():
    return render_template("adicionar_produto.html", produto_id=None)


@app.route("/produtos/<int:id_produto>/editar")
@pagina_protegida()
def editar_produto(id_produto):
    return render_template("adicionar_produto.html", produto_id=id_produto)


@app.route("/usuarios", methods=["GET"])
@pagina_protegida(admin=True)
def pagina_usuarios():
    return render_template("usuarios.html")


@app.route("/estoque/entrada", methods=["GET"])
@pagina_protegida()
def entrada_estoque():
    return render_template("entrada_estoque.html")


@app.route("/estoque/saida", methods=["GET"])
@pagina_protegida()
def saida_estoque():
    return render_template("saida_estoque.html")


@app.route("/movimentacoes", methods=["GET"])
@pagina_protegida()
def historico_movimentacoes():
    return render_template("historico_movimentacoes.html")


# ============================================================
# TESTE DA CONEXÃO COM O BANCO
# ============================================================

@app.route("/teste-banco", methods=["GET"])
def teste_banco():
    linha = consultar("SELECT DATABASE() AS banco", um=True)
    return resposta("Conexão com o MySQL realizada com sucesso.", banco=linha["banco"])


# ============================================================
# LOGIN / LOGOUT - RF002
# ============================================================

@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True)
    if not dados:
        return resposta("Nenhum dado foi enviado.", 400)

    email = (dados.get("email") or "").strip()
    senha = dados.get("senha")
    if not email or not senha:
        return resposta("E-mail e senha são obrigatórios.", 400)

    usuario = consultar(
        "SELECT id_usuario, nome, email, senha, perfil FROM usuario WHERE email = %s",
        (email,),
        um=True,
    )

    # Mesma mensagem para e-mail inexistente e senha errada (não revela qual falhou)
    if usuario is None or not check_password_hash(usuario["senha"], senha):
        return resposta("E-mail ou senha incorretos.", 401)

    session.clear()
    session["id_usuario"] = usuario["id_usuario"]
    session["nome"] = usuario["nome"]
    session["perfil"] = usuario["perfil"]

    return resposta(
        "Login realizado com sucesso.",
        usuario={
            "id_usuario": usuario["id_usuario"],
            "nome": usuario["nome"],
            "email": usuario["email"],
            "perfil": usuario["perfil"],
        },
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return resposta("Logout realizado com sucesso.")


@app.route("/api/me", methods=["GET"])
@api_protegida()
def api_me():
    return resposta(
        usuario={
            "id_usuario": session["id_usuario"],
            "nome": session["nome"],
            "perfil": session["perfil"],
        }
    )


# ============================================================
# FUNÇÕES AUXILIARES DE VALIDAÇÃO
# ============================================================

def corpo_json():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ErroApi("Nenhum dado foi enviado.", 400)
    return dados


def texto(dados, campo, obrigatorio=False, maximo=255, rotulo=None):
    valor = dados.get(campo)
    valor = valor.strip() if isinstance(valor, str) else valor
    rotulo = rotulo or campo
    if valor in (None, ""):
        if obrigatorio:
            raise ErroApi(f"O campo {rotulo} é obrigatório.", 400)
        return None
    if not isinstance(valor, str):
        raise ErroApi(f"O campo {rotulo} é inválido.", 400)
    if len(valor) > maximo:
        raise ErroApi(f"O campo {rotulo} deve ter no máximo {maximo} caracteres.", 400)
    return valor


def inteiro(dados, campo, minimo=0, obrigatorio=True, rotulo=None):
    valor = dados.get(campo)
    rotulo = rotulo or campo
    if valor in (None, ""):
        if obrigatorio:
            raise ErroApi(f"O campo {rotulo} é obrigatório.", 400)
        return None
    # bool é subclasse de int em Python; floats com parte decimal também são recusados
    if isinstance(valor, bool) or (isinstance(valor, float) and not valor.is_integer()):
        raise ErroApi(f"O campo {rotulo} deve ser um número inteiro.", 400)
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ErroApi(f"O campo {rotulo} deve ser um número inteiro.", 400)
    if numero < minimo:
        raise ErroApi(f"O campo {rotulo} deve ser maior ou igual a {minimo}.", 400)
    return numero


def decimal_positivo(dados, campo, rotulo=None):
    valor = dados.get(campo)
    rotulo = rotulo or campo
    if valor in (None, "") or isinstance(valor, bool):
        raise ErroApi(f"O campo {rotulo} é obrigatório.", 400)
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except Exception:
        raise ErroApi(f"O campo {rotulo} é inválido.", 400)
    if not numero.is_finite() or numero < 0:
        raise ErroApi(f"O campo {rotulo} deve ser maior ou igual a zero.", 400)
    return numero.quantize(Decimal("0.01"))


def garantir_existe(linhas_afetadas_ou_registro, mensagem):
    if not linhas_afetadas_ou_registro:
        raise ErroApi(mensagem, 404)


# ============================================================
# API - CATEGORIAS
# ============================================================

SQL_CATEGORIAS = """
    SELECT c.id_categoria, c.nome, c.descricao,
           COUNT(p.id_produto) AS total_produtos
    FROM categoria c
    LEFT JOIN produto p ON p.id_categoria = c.id_categoria
"""


@app.route("/api/categorias", methods=["GET"])
@api_protegida()
def api_listar_categorias():
    linhas = consultar(SQL_CATEGORIAS + " GROUP BY c.id_categoria, c.nome, c.descricao ORDER BY c.nome")
    return resposta(categorias=linhas)


@app.route("/api/categorias", methods=["POST"])
@api_protegida()
def api_criar_categoria():
    dados = corpo_json()
    nome = texto(dados, "nome", obrigatorio=True, rotulo="nome")
    descricao = texto(dados, "descricao", maximo=500, rotulo="descrição")
    novo_id, _ = executar("INSERT INTO categoria (nome, descricao) VALUES (%s, %s)", (nome, descricao))
    return resposta(
        "Categoria criada com sucesso.", 201,
        categoria={"id_categoria": novo_id, "nome": nome, "descricao": descricao},
    )


@app.route("/api/categorias/<int:id_categoria>", methods=["PUT"])
@api_protegida()
def api_atualizar_categoria(id_categoria):
    dados = corpo_json()
    nome = texto(dados, "nome", obrigatorio=True, rotulo="nome")
    descricao = texto(dados, "descricao", maximo=500, rotulo="descrição")
    existe = consultar("SELECT id_categoria FROM categoria WHERE id_categoria = %s", (id_categoria,), um=True)
    garantir_existe(existe, "Categoria não encontrada.")
    executar(
        "UPDATE categoria SET nome = %s, descricao = %s WHERE id_categoria = %s",
        (nome, descricao, id_categoria),
    )
    return resposta("Categoria atualizada com sucesso.")


@app.route("/api/categorias/<int:id_categoria>", methods=["DELETE"])
@api_protegida()
def api_excluir_categoria(id_categoria):
    _, afetadas = executar("DELETE FROM categoria WHERE id_categoria = %s", (id_categoria,))
    garantir_existe(afetadas, "Categoria não encontrada.")
    return resposta("Categoria excluída com sucesso.")


# ============================================================
# API - FORNECEDORES
# ============================================================

SQL_FORNECEDORES = """
    SELECT f.id_fornecedor, f.nome, f.cnpj, f.telefone, f.email,
           COUNT(p.id_produto) AS total_produtos
    FROM fornecedor f
    LEFT JOIN produto p ON p.id_fornecedor = f.id_fornecedor
"""


def dados_fornecedor(dados):
    return (
        texto(dados, "nome", obrigatorio=True, rotulo="nome"),
        texto(dados, "cnpj", maximo=18, rotulo="CNPJ"),
        texto(dados, "telefone", maximo=20, rotulo="telefone"),
        texto(dados, "email", maximo=255, rotulo="e-mail"),
    )


@app.route("/api/fornecedores", methods=["GET"])
@api_protegida()
def api_listar_fornecedores():
    linhas = consultar(
        SQL_FORNECEDORES + " GROUP BY f.id_fornecedor, f.nome, f.cnpj, f.telefone, f.email ORDER BY f.nome"
    )
    return resposta(fornecedores=linhas)


@app.route("/api/fornecedores", methods=["POST"])
@api_protegida()
def api_criar_fornecedor():
    nome, cnpj, telefone, email = dados_fornecedor(corpo_json())
    novo_id, _ = executar(
        "INSERT INTO fornecedor (nome, cnpj, telefone, email) VALUES (%s, %s, %s, %s)",
        (nome, cnpj, telefone, email),
    )
    return resposta(
        "Fornecedor criado com sucesso.", 201,
        fornecedor={"id_fornecedor": novo_id, "nome": nome, "cnpj": cnpj, "telefone": telefone, "email": email},
    )


@app.route("/api/fornecedores/<int:id_fornecedor>", methods=["PUT"])
@api_protegida()
def api_atualizar_fornecedor(id_fornecedor):
    nome, cnpj, telefone, email = dados_fornecedor(corpo_json())
    existe = consultar("SELECT id_fornecedor FROM fornecedor WHERE id_fornecedor = %s", (id_fornecedor,), um=True)
    garantir_existe(existe, "Fornecedor não encontrado.")
    executar(
        "UPDATE fornecedor SET nome = %s, cnpj = %s, telefone = %s, email = %s WHERE id_fornecedor = %s",
        (nome, cnpj, telefone, email, id_fornecedor),
    )
    return resposta("Fornecedor atualizado com sucesso.")


@app.route("/api/fornecedores/<int:id_fornecedor>", methods=["DELETE"])
@api_protegida()
def api_excluir_fornecedor(id_fornecedor):
    _, afetadas = executar("DELETE FROM fornecedor WHERE id_fornecedor = %s", (id_fornecedor,))
    garantir_existe(afetadas, "Fornecedor não encontrado.")
    return resposta("Fornecedor excluído com sucesso.")


# ============================================================
# API - PRODUTOS
# ============================================================

SQL_PRODUTOS = """
    SELECT p.id_produto, p.codigo, p.nome, p.descricao, p.preco,
           p.quantidade, p.estoque_minimo,
           p.id_categoria, c.nome AS categoria,
           p.id_fornecedor, f.nome AS fornecedor,
           CASE WHEN p.quantidade <= p.estoque_minimo THEN 'low' ELSE 'ok' END AS status_estoque
    FROM produto p
    LEFT JOIN categoria c ON c.id_categoria = p.id_categoria
    LEFT JOIN fornecedor f ON f.id_fornecedor = p.id_fornecedor
"""


@app.route("/api/produtos", methods=["GET"])
@api_protegida()
def api_listar_produtos():
    linhas = consultar(SQL_PRODUTOS + " ORDER BY p.nome")
    return resposta(produtos=linhas)


@app.route("/api/produtos/<int:id_produto>", methods=["GET"])
@api_protegida()
def api_obter_produto(id_produto):
    produto = consultar(SQL_PRODUTOS + " WHERE p.id_produto = %s", (id_produto,), um=True)
    garantir_existe(produto, "Produto não encontrado.")
    return resposta(produto=produto)


def dados_produto(dados):
    return {
        "codigo": texto(dados, "codigo", obrigatorio=True, maximo=50, rotulo="código"),
        "nome": texto(dados, "nome", obrigatorio=True, rotulo="nome"),
        "descricao": texto(dados, "descricao", maximo=1000, rotulo="descrição"),
        "preco": decimal_positivo(dados, "preco", rotulo="preço"),
        "estoque_minimo": inteiro(dados, "estoque_minimo", rotulo="estoque mínimo"),
        "id_categoria": inteiro(dados, "id_categoria", minimo=1, rotulo="categoria"),
        "id_fornecedor": inteiro(dados, "id_fornecedor", minimo=1, rotulo="fornecedor"),
    }


@app.route("/api/produtos", methods=["POST"])
@api_protegida()
def api_criar_produto():
    dados = corpo_json()
    p = dados_produto(dados)
    quantidade = inteiro(dados, "quantidade", rotulo="quantidade inicial")

    # Produto + movimentação de estoque inicial são gravados juntos (uma transação).
    conexao = abrir_conexao()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO produto
                (codigo, nome, descricao, preco, quantidade, estoque_minimo, id_categoria, id_fornecedor)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (p["codigo"], p["nome"], p["descricao"], p["preco"], quantidade,
             p["estoque_minimo"], p["id_categoria"], p["id_fornecedor"]),
        )
        novo_id = cursor.lastrowid
        if quantidade > 0:
            cursor.execute(
                """
                INSERT INTO movimentacao_estoque (id_produto, id_usuario, tipo, quantidade, observacao)
                VALUES (%s, %s, 'ENTRADA', %s, 'Estoque inicial')
                """,
                (novo_id, session["id_usuario"], quantidade),
            )
        conexao.commit()
        cursor.close()
    except Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()

    return resposta("Produto cadastrado com sucesso.", 201, id_produto=novo_id)


@app.route("/api/produtos/<int:id_produto>", methods=["PUT"])
@api_protegida()
def api_atualizar_produto(id_produto):
    # A quantidade NÃO é alterada aqui: o saldo só muda por entrada/saída de estoque.
    p = dados_produto(corpo_json())
    existe = consultar("SELECT id_produto FROM produto WHERE id_produto = %s", (id_produto,), um=True)
    garantir_existe(existe, "Produto não encontrado.")
    executar(
        """
        UPDATE produto
        SET codigo = %s, nome = %s, descricao = %s, preco = %s, estoque_minimo = %s,
            id_categoria = %s, id_fornecedor = %s
        WHERE id_produto = %s
        """,
        (p["codigo"], p["nome"], p["descricao"], p["preco"], p["estoque_minimo"],
         p["id_categoria"], p["id_fornecedor"], id_produto),
    )
    return resposta("Produto atualizado com sucesso.")


@app.route("/api/produtos/<int:id_produto>", methods=["DELETE"])
@api_protegida()
def api_excluir_produto(id_produto):
    _, afetadas = executar("DELETE FROM produto WHERE id_produto = %s", (id_produto,))
    garantir_existe(afetadas, "Produto não encontrado.")
    return resposta("Produto excluído com sucesso.")


# ============================================================
# API - MOVIMENTAÇÕES DE ESTOQUE (entrada / saída / histórico)
# ============================================================

def registrar_movimentacao(tipo):
    dados = corpo_json()
    id_produto = inteiro(dados, "id_produto", minimo=1, rotulo="produto")
    quantidade = inteiro(dados, "quantidade", minimo=1, rotulo="quantidade")
    observacao = texto(dados, "observacao", maximo=500, rotulo="observação")

    # Saldo + histórico são confirmados juntos (transação). O SELECT ... FOR UPDATE
    # trava a linha do produto para duas saídas simultâneas não gerarem saldo negativo.
    conexao = abrir_conexao()
    try:
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT quantidade FROM produto WHERE id_produto = %s FOR UPDATE", (id_produto,)
        )
        produto = cursor.fetchone()
        if produto is None:
            raise ErroApi("Produto não encontrado.", 404)

        atual = produto["quantidade"]
        if tipo == "SAIDA" and quantidade > atual:
            raise ErroApi(
                f"Quantidade insuficiente em estoque. Disponível: {atual}.", 400
            )
        novo_saldo = atual + quantidade if tipo == "ENTRADA" else atual - quantidade

        cursor.execute(
            "UPDATE produto SET quantidade = %s WHERE id_produto = %s", (novo_saldo, id_produto)
        )
        cursor.execute(
            """
            INSERT INTO movimentacao_estoque (id_produto, id_usuario, tipo, quantidade, observacao)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id_produto, session["id_usuario"], tipo, quantidade, observacao),
        )
        conexao.commit()
        cursor.close()
    except (ErroApi, Error):
        conexao.rollback()
        raise
    finally:
        conexao.close()

    rotulo = "Entrada" if tipo == "ENTRADA" else "Saída"
    return resposta(f"{rotulo} registrada com sucesso.", 201, saldo_atual=novo_saldo)


@app.route("/api/movimentacoes/entrada", methods=["POST"])
@api_protegida()
def api_entrada_estoque():
    return registrar_movimentacao("ENTRADA")


@app.route("/api/movimentacoes/saida", methods=["POST"])
@api_protegida()
def api_saida_estoque():
    return registrar_movimentacao("SAIDA")


@app.route("/api/movimentacoes", methods=["GET"])
@api_protegida()
def api_listar_movimentacoes():
    linhas = consultar(
        """
        SELECT m.id_movimentacao, m.tipo, m.quantidade, m.data_hora, m.observacao,
               p.id_produto, p.codigo, p.nome AS produto,
               u.nome AS responsavel
        FROM movimentacao_estoque m
        JOIN produto p ON p.id_produto = m.id_produto
        LEFT JOIN usuario u ON u.id_usuario = m.id_usuario
        ORDER BY m.data_hora DESC, m.id_movimentacao DESC
        LIMIT 500
        """
    )
    return resposta(movimentacoes=linhas)


# ============================================================
# API - DASHBOARD
# ============================================================

@app.route("/api/dashboard", methods=["GET"])
@api_protegida()
def api_dashboard():
    resumo = consultar(
        """
        SELECT
            (SELECT COUNT(*) FROM produto)    AS total_produtos,
            (SELECT COUNT(*) FROM fornecedor) AS total_fornecedores,
            (SELECT COUNT(*) FROM produto WHERE quantidade <= estoque_minimo) AS estoque_baixo,
            (SELECT COUNT(*) FROM movimentacao_estoque
              WHERE DATE(data_hora) = CURDATE()) AS movimentacoes_hoje
        """,
        um=True,
    )
    baixos = consultar(
        SQL_PRODUTOS
        + " WHERE p.quantidade <= p.estoque_minimo ORDER BY p.quantidade ASC, p.nome LIMIT 10"
    )
    return resposta(resumo=resumo, estoque_baixo=baixos)


# ============================================================
# USUÁRIOS (somente administrador) - RF001
# ============================================================

def dados_usuario(dados, senha_obrigatoria):
    nome = texto(dados, "nome", obrigatorio=True, rotulo="nome")
    email = texto(dados, "email", obrigatorio=True, rotulo="e-mail")
    perfil = dados.get("perfil")
    senha = dados.get("senha")
    if not perfil:
        raise ErroApi("O campo perfil é obrigatório.", 400)
    if perfil not in PERFIS_VALIDOS:
        raise ErroApi("Perfil inválido.", 400)
    if senha_obrigatoria and not senha:
        raise ErroApi("Nome, e-mail, senha e perfil são obrigatórios.", 400)
    if senha and (not isinstance(senha, str) or len(senha) < 6):
        raise ErroApi("A senha deve ter pelo menos 6 caracteres.", 400)
    return nome, email, senha, perfil


@app.route("/api/usuarios", methods=["GET"])
@api_protegida(admin=True)
def api_listar_usuarios():
    linhas = consultar("SELECT id_usuario, nome, email, perfil FROM usuario ORDER BY nome")
    return resposta(usuarios=linhas)


# POST /usuarios é a rota original (testada no Postman); /api/usuarios é o alias usado pelo front-end.
@app.route("/usuarios", methods=["POST"])
@app.route("/api/usuarios", methods=["POST"])
@api_protegida(admin=True)
def criar_usuario():
    nome, email, senha, perfil = dados_usuario(corpo_json(), senha_obrigatoria=True)
    novo_id, _ = executar(
        "INSERT INTO usuario (nome, email, senha, perfil) VALUES (%s, %s, %s, %s)",
        (nome, email, generate_password_hash(senha), perfil),
    )
    return resposta(
        "Usuário criado com sucesso.", 201,
        usuario={"id_usuario": novo_id, "nome": nome, "email": email, "perfil": perfil},
    )


@app.route("/api/usuarios/<int:id_usuario>", methods=["PUT"])
@api_protegida(admin=True)
def api_atualizar_usuario(id_usuario):
    nome, email, senha, perfil = dados_usuario(corpo_json(), senha_obrigatoria=False)
    existe = consultar("SELECT id_usuario FROM usuario WHERE id_usuario = %s", (id_usuario,), um=True)
    garantir_existe(existe, "Usuário não encontrado.")
    if id_usuario == session["id_usuario"] and perfil != "ADMINISTRADOR":
        raise ErroApi("Você não pode remover o seu próprio perfil de administrador.", 400)

    if senha:
        executar(
            "UPDATE usuario SET nome = %s, email = %s, perfil = %s, senha = %s WHERE id_usuario = %s",
            (nome, email, perfil, generate_password_hash(senha), id_usuario),
        )
    else:
        executar(
            "UPDATE usuario SET nome = %s, email = %s, perfil = %s WHERE id_usuario = %s",
            (nome, email, perfil, id_usuario),
        )
    if id_usuario == session["id_usuario"]:
        session["nome"], session["perfil"] = nome, perfil
    return resposta("Usuário atualizado com sucesso.")


@app.route("/api/usuarios/<int:id_usuario>", methods=["DELETE"])
@api_protegida(admin=True)
def api_excluir_usuario(id_usuario):
    if id_usuario == session["id_usuario"]:
        raise ErroApi("Você não pode excluir o seu próprio usuário.", 400)
    _, afetadas = executar("DELETE FROM usuario WHERE id_usuario = %s", (id_usuario,))
    garantir_existe(afetadas, "Usuário não encontrado.")
    return resposta("Usuário excluído com sucesso.")


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)
