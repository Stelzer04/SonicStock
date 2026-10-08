from flask import Flask, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

# Chave usada pelo Flask para proteger a sessão.
# Para o projeto acadêmico, podemos manter assim inicialmente.
app.secret_key = "chave-temporaria-sonicstock"


# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "bluestock"
}


# ============================================================
# CONEXÃO COM O BANCO
# ============================================================

def conectar_banco():
    try:
        conexao = mysql.connector.connect(**DB_CONFIG)

        if conexao.is_connected():
            return conexao

    except Error as erro:
        print(f"Erro ao conectar ao MySQL: {erro}")

    return None

def usuario_e_admin():
    return session.get("perfil") == "ADMINISTRADOR"

# ============================================================
# ROTA INICIAL
# ============================================================

@app.route("/")
def inicio():
    return jsonify({
        "mensagem": "API SonicStock funcionando!"
    })


# ============================================================
# TESTE DA CONEXÃO COM O BANCO
# ============================================================

@app.route("/teste-banco", methods=["GET"])
def teste_banco():

    conexao = conectar_banco()

    if conexao is None:
        return jsonify({
            "sucesso": False,
            "mensagem": "Não foi possível conectar ao banco de dados."
        }), 500

    try:
        cursor = conexao.cursor()

        cursor.execute("SELECT DATABASE()")

        banco = cursor.fetchone()[0]

        cursor.close()
        conexao.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Conexão com o MySQL realizada com sucesso.",
            "banco": banco
        })

    except Error as erro:

        if conexao.is_connected():
            conexao.close()

        return jsonify({
            "sucesso": False,
            "mensagem": "Erro ao consultar o banco.",
            "erro": str(erro)
        }), 500


# ============================================================
# LOGIN - RF002
# ============================================================

@app.route("/login", methods=["POST"])
def login():

    dados = request.get_json()

    if not dados:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado foi enviado."
        }), 400

    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return jsonify({
            "sucesso": False,
            "mensagem": "E-mail e senha são obrigatórios."
        }), 400

    conexao = conectar_banco()

    if conexao is None:
        return jsonify({
            "sucesso": False,
            "mensagem": "Não foi possível conectar ao banco de dados."
        }), 500

    try:

        cursor = conexao.cursor(dictionary=True)

        comando = """
            SELECT
                id_usuario,
                nome,
                email,
                senha,
                perfil
            FROM usuario
            WHERE email = %s
        """

        cursor.execute(comando, (email,))

        usuario = cursor.fetchone()

        cursor.close()
        conexao.close()

        # Usuário não encontrado
        if usuario is None:
            return jsonify({
                "sucesso": False,
                "mensagem": "E-mail ou senha incorretos."
            }), 401

        # Verifica a senha criptografada
        senha_correta = check_password_hash(
            usuario["senha"],
            senha
        )

        if not senha_correta:
            return jsonify({
                "sucesso": False,
                "mensagem": "E-mail ou senha incorretos."
            }), 401

        # Cria a sessão
        session["id_usuario"] = usuario["id_usuario"]
        session["nome"] = usuario["nome"]
        session["perfil"] = usuario["perfil"]

        return jsonify({
            "sucesso": True,
            "mensagem": "Login realizado com sucesso.",
            "usuario": {
                "id_usuario": usuario["id_usuario"],
                "nome": usuario["nome"],
                "email": usuario["email"],
                "perfil": usuario["perfil"]
            }
        }), 200

    except Error as erro:

        if conexao.is_connected():
            conexao.close()

        return jsonify({
            "sucesso": False,
            "mensagem": "Erro ao realizar login.",
            "erro": str(erro)
        }), 500


@app.route("/usuarios", methods=["POST"])
def criar_usuario():

    # 1. Verificar se o usuário está logado como administrador
    if not usuario_e_admin():
        return jsonify({
            "sucesso": False,
            "mensagem": "Acesso permitido somente para administradores."
        }), 403

    # 2. Receber os dados enviados
    dados = request.get_json()

    if not dados:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nenhum dado foi enviado."
        }), 400

    # 3. Separar os dados
    nome = dados.get("nome")
    email = dados.get("email")
    senha = dados.get("senha")
    perfil = dados.get("perfil")

    # 4. Verificar campos obrigatórios
    if not nome or not email or not senha or not perfil:
        return jsonify({
            "sucesso": False,
            "mensagem": "Nome, e-mail, senha e perfil são obrigatórios."
        }), 400

    # 5. Verificar se o perfil é válido
    if perfil not in ["ADMINISTRADOR", "FUNCIONARIO"]:
        return jsonify({
            "sucesso": False,
            "mensagem": "Perfil inválido."
        }), 400

    # 6. Conectar ao banco
    conexao = conectar_banco()

    if conexao is None:
        return jsonify({
            "sucesso": False,
            "mensagem": "Não foi possível conectar ao banco de dados."
        }), 500

    try:

        # 7. Criar o hash da senha
        senha_hash = generate_password_hash(senha)

        # 8. Criar cursor
        cursor = conexao.cursor()

        # 9. Comando SQL
        comando = """
            INSERT INTO usuario
                (nome, email, senha, perfil)
            VALUES
                (%s, %s, %s, %s)
        """

        valores = (nome, email, senha_hash, perfil)

        # 10. Executar INSERT
        cursor.execute(comando, valores)

        # 11. Confirmar alteração no banco
        conexao.commit()

        # 12. Recuperar ID criado
        id_usuario = cursor.lastrowid

        cursor.close()
        conexao.close()

        # 13. Responder ao Postman/frontend
        return jsonify({
            "sucesso": True,
            "mensagem": "Usuário criado com sucesso.",
            "usuario": {
                "id_usuario": id_usuario,
                "nome": nome,
                "email": email,
                "perfil": perfil
            }
        }), 201

    except Error as erro:

        if conexao.is_connected():
            conexao.rollback()
            conexao.close()

        return jsonify({
            "sucesso": False,
            "mensagem": "Erro ao criar usuário.",
            "erro": str(erro)
        }), 500


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "sucesso": True,
        "mensagem": "Logout realizado com sucesso."
    })


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    app.run(debug=True)