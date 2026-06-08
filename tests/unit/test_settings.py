"""
Testes unitários para config/settings.py — parsing de ACOES_SUBACOES
e DETALHAMENTOS_GERENCIAIS.
"""
from unittest.mock import patch

import pytest

from config.settings import ColetaConfig


class TestColetaConfigAcoesSubacoes:
    def test_parse_multiplos_pares(self):
        with patch.dict(
            "os.environ",
            {"ACOES_SUBACOES": "1313:2115,4685:1958,4685:1959,4685:1960,3929:0000"},
        ):
            cfg = ColetaConfig()
            pares = cfg.acoes_subacoes
            assert len(pares) == 5
            assert ("1313", "2115") in pares
            assert ("4685", "1958") in pares
            assert ("4685", "1959") in pares
            assert ("4685", "1960") in pares
            assert ("3929", "0000") in pares

    def test_parse_par_unico(self):
        with patch.dict("os.environ", {"ACOES_SUBACOES": "1234:001"}):
            cfg = ColetaConfig()
            assert cfg.acoes_subacoes == [("1234", "001")]

    def test_vazio_retorna_lista_vazia(self):
        with patch.dict("os.environ", {"ACOES_SUBACOES": ""}):
            cfg = ColetaConfig()
            assert cfg.acoes_subacoes == []

    def test_ignora_formato_invalido(self):
        with patch.dict("os.environ", {"ACOES_SUBACOES": "1234:001,invalido,5678:002"}):
            cfg = ColetaConfig()
            # "invalido" não tem ":" então é descartado
            assert len(cfg.acoes_subacoes) == 2
            assert ("1234", "001") in cfg.acoes_subacoes
            assert ("5678", "002") in cfg.acoes_subacoes

    def test_strip_espacos(self):
        with patch.dict("os.environ", {"ACOES_SUBACOES": " 1313 : 2115 , 4685 : 1958 "}):
            cfg = ColetaConfig()
            assert ("1313", "2115") in cfg.acoes_subacoes
            assert ("4685", "1958") in cfg.acoes_subacoes


class TestColetaConfigDetalhamentos:
    def test_todos_detectado(self):
        with patch.dict("os.environ", {"DETALHAMENTOS_GERENCIAIS": "TODOS"}):
            cfg = ColetaConfig()
            assert cfg.coletar_todos_detalhamentos is True

    def test_todos_case_insensitive(self):
        with patch.dict("os.environ", {"DETALHAMENTOS_GERENCIAIS": "todos"}):
            cfg = ColetaConfig()
            assert cfg.coletar_todos_detalhamentos is True

    def test_lista_especifica(self):
        raw = "subsidios,credito de vale transporte,Prog. Parcerias Público Privadas"
        with patch.dict("os.environ", {"DETALHAMENTOS_GERENCIAIS": raw}):
            cfg = ColetaConfig()
            assert cfg.coletar_todos_detalhamentos is False
            assert "subsidios" in cfg.detalhamentos_gerenciais
            assert "credito de vale transporte" in cfg.detalhamentos_gerenciais
            assert "Prog. Parcerias Público Privadas" in cfg.detalhamentos_gerenciais
            assert len(cfg.detalhamentos_gerenciais) == 3

    def test_todos_junto_com_especificos(self):
        raw = "subsidios,TODOS"
        with patch.dict("os.environ", {"DETALHAMENTOS_GERENCIAIS": raw}):
            cfg = ColetaConfig()
            assert cfg.coletar_todos_detalhamentos is True
