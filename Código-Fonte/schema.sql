-- ============================================================
-- SonicStock / BlueStock — esquema MySQL usado pelo back-end
-- ATENÇÃO: confira com o seu modelo (.mwb). Apenas a tabela `usuario`
-- (id_usuario, nome, email, senha, perfil) era conhecida pelo código
-- original; as demais colunas foram deduzidas do front-end.
-- Se algum nome for diferente no seu banco, ajuste este arquivo OU as
-- consultas SQL em app.py (todas usam estes nomes).
-- ============================================================

CREATE DATABASE IF NOT EXISTS bluestock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE bluestock;

CREATE TABLE IF NOT EXISTS usuario (
    id_usuario  INT AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    senha       VARCHAR(255) NOT NULL,              -- hash (werkzeug)
    perfil      ENUM('ADMINISTRADOR','FUNCIONARIO') NOT NULL
);

CREATE TABLE IF NOT EXISTS categoria (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nome         VARCHAR(255) NOT NULL UNIQUE,
    descricao    VARCHAR(500) NULL
);

CREATE TABLE IF NOT EXISTS fornecedor (
    id_fornecedor INT AUTO_INCREMENT PRIMARY KEY,
    nome          VARCHAR(255) NOT NULL,
    cnpj          VARCHAR(18)  NULL UNIQUE,
    telefone      VARCHAR(20)  NULL,
    email         VARCHAR(255) NULL
);

CREATE TABLE IF NOT EXISTS produto (
    id_produto     INT AUTO_INCREMENT PRIMARY KEY,
    codigo         VARCHAR(50)  NOT NULL UNIQUE,
    nome           VARCHAR(255) NOT NULL,
    descricao      VARCHAR(1000) NULL,
    preco          DECIMAL(10,2) NOT NULL DEFAULT 0,
    quantidade     INT NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
    estoque_minimo INT NOT NULL DEFAULT 0,
    id_categoria   INT NOT NULL,
    id_fornecedor  INT NOT NULL,
    FOREIGN KEY (id_categoria)  REFERENCES categoria(id_categoria),
    FOREIGN KEY (id_fornecedor) REFERENCES fornecedor(id_fornecedor)
);

CREATE TABLE IF NOT EXISTS movimentacao_estoque (
    id_movimentacao INT AUTO_INCREMENT PRIMARY KEY,
    id_produto      INT NOT NULL,
    id_usuario      INT NULL,
    tipo            ENUM('ENTRADA','SAIDA') NOT NULL,
    quantidade      INT NOT NULL CHECK (quantidade > 0),
    data_hora       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observacao      VARCHAR(500) NULL,
    FOREIGN KEY (id_produto) REFERENCES produto(id_produto),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
);
