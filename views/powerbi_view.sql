-- =============================================================================
-- Views para consumo direto pelo Power BI via conector PostgreSQL
-- =============================================================================

-- View principal de execução orçamentária
CREATE OR REPLACE VIEW vw_execucao_orcamentaria AS
SELECT
    e.unidade_gestora,
    e.acao,
    e.subacao,
    e.data_coleta,
    SUM(e.valor_empenhado)               AS total_empenhado,
    SUM(e.valor_liquidado)               AS total_liquidado,
    SUM(e.valor_pago)                    AS total_pago,
    SUM(e.valor_empenhado)
        - SUM(e.valor_pago)              AS saldo,
    CASE
        WHEN SUM(e.valor_empenhado) = 0 THEN 0
        ELSE ROUND(
            (SUM(e.valor_pago) / SUM(e.valor_empenhado)) * 100, 2
        )
    END                                  AS pct_execucao
FROM fato_empenho e
GROUP BY
    e.unidade_gestora,
    e.acao,
    e.subacao,
    e.data_coleta;


-- View de série temporal: evolução diária dos valores
CREATE OR REPLACE VIEW vw_serie_temporal AS
SELECT
    data_coleta,
    unidade_gestora,
    acao,
    subacao,
    SUM(valor_empenhado) AS empenhado,
    SUM(valor_liquidado) AS liquidado,
    SUM(valor_pago)      AS pago
FROM fato_empenho
GROUP BY
    data_coleta,
    unidade_gestora,
    acao,
    subacao
ORDER BY data_coleta;


-- View de credores com maior volume empenhado
CREATE OR REPLACE VIEW vw_top_credores AS
SELECT
    credor,
    unidade_gestora,
    acao,
    SUM(valor_empenhado) AS total_empenhado,
    SUM(valor_pago)      AS total_pago,
    COUNT(*)             AS qtd_empenhos
FROM fato_empenho
WHERE credor IS NOT NULL
GROUP BY credor, unidade_gestora, acao
ORDER BY total_empenhado DESC;


-- View de fichas financeiras consolidadas por natureza de despesa
CREATE OR REPLACE VIEW vw_fichas_por_natureza AS
SELECT
    exercicio,
    natureza_despesa,
    grupo_despesa,
    fonte_recurso,
    SUM(dotacao_inicial) AS dotacao_inicial,
    SUM(dotacao_atual)   AS dotacao_atual,
    SUM(valor_empenhado) AS empenhado,
    SUM(valor_liquidado) AS liquidado,
    SUM(valor_pago)      AS pago,
    SUM(saldo)           AS saldo
FROM fato_ficha_financeira
GROUP BY
    exercicio,
    natureza_despesa,
    grupo_despesa,
    fonte_recurso;
