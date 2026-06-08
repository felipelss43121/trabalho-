-- =============================================================================
-- Migração 001 – Esquema inicial do banco analítico e-Fisco
-- Banco: efisco_analitico
-- Compatível com PostgreSQL 14+
-- =============================================================================

-- Cria banco caso não exista (executar manualmente como superusuário, se necessário)
-- CREATE DATABASE efisco_analitico ENCODING 'UTF8';

-- Cria usuário com privilégios mínimos necessários
-- CREATE USER efisco_user WITH PASSWORD 'sua_senha';
-- GRANT CONNECT ON DATABASE efisco_analitico TO efisco_user;
-- GRANT USAGE ON SCHEMA public TO efisco_user;

-- =============================================================================
-- Tabela: fato_empenho
-- =============================================================================
CREATE TABLE IF NOT EXISTS fato_empenho (
    id                   SERIAL        PRIMARY KEY,
    data_coleta          DATE          NOT NULL,
    unidade_gestora      VARCHAR(20)   NOT NULL,
    acao                 VARCHAR(20)   NOT NULL,
    subacao              VARCHAR(20)   NOT NULL,
    data_empenho         DATE,
    credor               VARCHAR(500),
    valor_empenhado_item NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_empenhado      NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_liquidado      NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_pago           NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_at           TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMP     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_empenho_chave_negocio
        UNIQUE (data_coleta, unidade_gestora, acao, subacao, data_empenho, credor)
);

COMMENT ON TABLE  fato_empenho IS 'Despesa Empenhada por Unidade Gestora – e-Fisco PE';
COMMENT ON COLUMN fato_empenho.data_coleta          IS 'Data em que a coleta foi executada';
COMMENT ON COLUMN fato_empenho.unidade_gestora       IS 'Código da Unidade Gestora';
COMMENT ON COLUMN fato_empenho.acao                  IS 'Código da Ação orçamentária';
COMMENT ON COLUMN fato_empenho.subacao               IS 'Código da Subação orçamentária';
COMMENT ON COLUMN fato_empenho.valor_empenhado_item  IS 'Valor empenhado no item de gasto';
COMMENT ON COLUMN fato_empenho.valor_empenhado       IS 'Valor empenhado acumulado atual';
COMMENT ON COLUMN fato_empenho.valor_liquidado       IS 'Valor liquidado acumulado atual';
COMMENT ON COLUMN fato_empenho.valor_pago            IS 'Valor pago acumulado atual';

-- Índices para filtros comuns no Power BI
CREATE INDEX IF NOT EXISTS idx_empenho_data_coleta   ON fato_empenho (data_coleta);
CREATE INDEX IF NOT EXISTS idx_empenho_ug_acao       ON fato_empenho (unidade_gestora, acao, subacao);

-- Trigger para manter updated_at atualizado automaticamente
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS tg_empenho_updated_at ON fato_empenho;
CREATE TRIGGER tg_empenho_updated_at
    BEFORE UPDATE ON fato_empenho
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================================
-- Tabela: fato_ficha_financeira
-- =============================================================================
CREATE TABLE IF NOT EXISTS fato_ficha_financeira (
    id                    SERIAL        PRIMARY KEY,
    data_coleta           DATE          NOT NULL,
    ficha_id              VARCHAR(50)   NOT NULL,
    exercicio             VARCHAR(10)   NOT NULL,
    unidade_gestora       VARCHAR(200),
    gestao                VARCHAR(200),
    grupo_despesa         VARCHAR(200),
    fonte_recurso         VARCHAR(200),
    natureza_despesa      VARCHAR(200),
    dea                   VARCHAR(200),
    detalhamento_despesa  VARCHAR(500),
    destinacao_recurso    VARCHAR(200),
    situacao              VARCHAR(100),
    dotacao_inicial       NUMERIC(18,2) NOT NULL DEFAULT 0,
    dotacao_atual         NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_empenhado       NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_liquidado       NUMERIC(18,2) NOT NULL DEFAULT 0,
    valor_pago            NUMERIC(18,2) NOT NULL DEFAULT 0,
    saldo                 NUMERIC(18,2) NOT NULL DEFAULT 0,
    created_at            TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMP     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_ficha_chave_negocio
        UNIQUE (data_coleta, ficha_id, exercicio)
);

COMMENT ON TABLE fato_ficha_financeira IS 'Ficha Financeira Detalhada – e-Fisco PE';

CREATE INDEX IF NOT EXISTS idx_ficha_data_coleta ON fato_ficha_financeira (data_coleta);
CREATE INDEX IF NOT EXISTS idx_ficha_ug_exercicio ON fato_ficha_financeira (unidade_gestora, exercicio);

DROP TRIGGER IF EXISTS tg_ficha_updated_at ON fato_ficha_financeira;
CREATE TRIGGER tg_ficha_updated_at
    BEFORE UPDATE ON fato_ficha_financeira
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();

-- =============================================================================
-- View consolidada para Power BI
-- =============================================================================
CREATE OR REPLACE VIEW vw_execucao_orcamentaria AS
SELECT
    e.unidade_gestora,
    e.acao,
    e.subacao,
    e.data_coleta,
    SUM(e.valor_empenhado)      AS total_empenhado,
    SUM(e.valor_liquidado)      AS total_liquidado,
    SUM(e.valor_pago)           AS total_pago,
    SUM(e.valor_empenhado)
        - SUM(e.valor_pago)     AS saldo,
    CASE
        WHEN SUM(e.valor_empenhado) = 0 THEN 0
        ELSE ROUND(
            (SUM(e.valor_pago) / SUM(e.valor_empenhado)) * 100, 2
        )
    END                         AS pct_execucao
FROM fato_empenho e
GROUP BY e.unidade_gestora, e.acao, e.subacao, e.data_coleta;

COMMENT ON VIEW vw_execucao_orcamentaria
    IS 'Visão consolidada de execução orçamentária para consumo pelo Power BI';

-- Privilégios mínimos de leitura para o usuário da aplicação
GRANT SELECT, INSERT, UPDATE ON fato_empenho        TO efisco_user;
GRANT SELECT, INSERT, UPDATE ON fato_ficha_financeira TO efisco_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO efisco_user;
GRANT SELECT ON vw_execucao_orcamentaria             TO efisco_user;
