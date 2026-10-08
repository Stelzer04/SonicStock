import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash


# ============================================================
# CONFIGURAÇÃO DO BANCO
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "bluestock"
}


# ============================================================
# DADOS DO USUÁRIO
# ============================================================

nome = "Administrador SonicStock"
email = "admin@sonicstock.com"
senha = "123456"
perfil = "ADMINISTRADOR"


# ============================================================
# CRIAÇÃO DO HASH DA SENHA
# ============================================================

senha_hash = generate_password_hash(senha)


# ============================================================
# CONEXÃO COM O BANCO
# ============================================================

try:

    conexao = mysql.connector.connect(**DB_CONFIG)

    if conexao.is_connected():

        cursor = conexao.cursor()

        comando = """
            INSERT INTO usuario
                (nome, email, senha, perfil)
            VALUES
                (%s, %s, %s, %s)
        """

        valores = (
            nome,
            email,
            senha_hash,
            perfil
        )

        cursor.execute(comando, valores)

        conexao.commit()

        print("Usuário criado com sucesso!")
        print(f"Nome: {nome}")
        print(f"E-mail: {email}")
        print(f"Perfil: {perfil}")

        cursor.close()
        conexao.close()


except Error as erro:

    print("Erro ao criar usuário:")
    print(erro)