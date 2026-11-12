"""Testes do processamento (sem internet). Execute: python -m unittest discover tests"""
import unittest
from datetime import datetime, timezone

from app.collectors import rss
from app.processing import classify, dedup, erp, legal, summarize
from app.processing.normalize import canonical_url, fts_query, norm_title, parse_any_date, parse_pt_date


class TestNormalize(unittest.TestCase):
    def test_canonical_remove_rastreamento(self):
        self.assertEqual(canonical_url("https://www.Site.com/a/?utm_source=x&id=2#top"), "https://site.com/a?id=2")

    def test_datas(self):
        dt, p = parse_pt_date("Publicado em 30/10/2026")
        self.assertEqual((dt.day, dt.month, p), (30, 10, "date"))
        dt, p = parse_pt_date("CONVÊNIO ICMS Nº 150, DE 10 DE OUTUBRO DE 2026")
        self.assertEqual((dt.day, dt.month, dt.year), (10, 10, 2026))
        dt, p = parse_any_date("Mon, 09 Nov 2026 13:00:00 GMT")
        self.assertEqual((dt.hour, p), (13, "datetime"))
        dt, _ = parse_any_date("2026-11-09T10:00:00-03:00")
        self.assertEqual(dt.hour, 13)

    def test_busca(self):
        q_and, q_or = fts_query("Nova Nota Técnica da NF-e")
        self.assertIn('"nf e"', q_and)
        self.assertNotIn("nova", q_and)
        self.assertIn('"c#"', fts_query("Atualização do C#")[0])


class TestClassificacao(unittest.TestCase):
    def test_categorias(self):
        cats = [c[0] for c in classify.classify("Receita publica Nota Técnica da NF-e sobre IBS e CBS", "", None, "rss")]
        self.assertIn("fiscal", cats)
        self.assertIn("reforma", cats)
        cats = [c[0] for c in classify.classify("Anthropic lança novo modelo Claude", "", None, "rss")]
        self.assertEqual(cats[0], "ia")

    def test_oficial(self):
        self.assertTrue(classify.is_official("gov.br", False))
        self.assertTrue(classify.is_official("www12.senado.leg.br", False))
        self.assertFalse(classify.is_official("g1.globo.com", False))


class TestLegal(unittest.TestCase):
    def test_proposta_nunca_vigente(self):
        r = legal.analyze("Câmara aprova projeto de lei que altera o ICMS", "", official=True)
        self.assertEqual(r["legal_stage"], "projeto_de_lei")
        r = legal.analyze("Nova regra do ICMS já está em vigor, diz jornal", "", official=False)
        self.assertNotEqual(r["legal_stage"], "norma_em_vigor")

    def test_consulta_publica(self):
        r = legal.analyze("Receita Federal abre consulta pública sobre instrução normativa", "", official=True)
        self.assertEqual(r["legal_stage"], "consulta_publica")

    def test_publicada(self):
        r = legal.analyze("Publicada Nota Técnica 2025.002 v1.10", "", official=True)
        self.assertEqual(r["legal_stage"], "norma_publicada")
        self.assertIn("Nota Técnica 2025.002 v1.10", r["legal_refs"])


class TestDuplicidade(unittest.TestCase):
    def test_duplicada_e_atualizacao(self):
        recent = [{"id": 1, "title_norm": norm_title("Publicada Nota Técnica 2025.002 v1.10 da NF-e"), "group_id": 1}]
        d = dedup.decide(norm_title("Publicada a Nota Técnica 2025.002 v1.10 da NF-e"), recent)
        self.assertTrue(d["is_duplicate"])
        d = dedup.decide(norm_title("Publicada Nota Técnica 2025.002 v1.20 da NF-e"), recent)
        self.assertTrue(d["is_update"])
        d = dedup.decide(norm_title("OpenAI anuncia novo modelo de raciocínio"), recent)
        self.assertIsNone(d["match"])


class TestResumo(unittest.TestCase):
    def test_extrativo_usa_frases_da_fonte(self):
        text = ("A Receita Federal publicou nesta segunda-feira a Instrução Normativa que altera a EFD-Reinf. "
                "A mudança passa a valer em 1º de janeiro de 2027 para todas as empresas. "
                "Segundo o órgão, o leiaute será divulgado no portal do SPED nas próximas semanas.")
        s, pts = summarize.extractive("Receita altera EFD-Reinf", text)
        for frase in s.split(". "):
            self.assertIn(frase.strip(". "), text)
        self.assertTrue(summarize.find_terms("EFD-Reinf e SPED"))
        self.assertTrue(summarize.impacts("nova nota técnica altera leiaute da NF-e", ["fiscal"]))


class TestErp(unittest.TestCase):
    def test_marca_mudancas_que_exigem_ajuste_no_erp(self):
        for title, body in [
            ("Publicada a NT 2025.002 v1.30 da NF-e", ""),
            ("Ajuste SINIEF 49/25", ""),
            ("CT-e: SEFAZ publica novo leiaute do evento de comprovante de entrega", ""),
            ("EFD-Reinf: nova versão do leiaute entra em produção", ""),
            ("Empresas precisam adequar o ERP para IBS e CBS na nota fiscal", ""),
            ("Reforma tributária: o que muda para o varejo", "Empresas devem ajustar o ERP para destacar IBS e CBS na NF-e."),
        ]:
            self.assertTrue(erp.analyze(title, body)["erp_impact"], title)
        self.assertIn("NF-e", erp.analyze("Publicada a NT 2025.002 v1.30 da NF-e")["erp_docs"])

    def test_nao_marca_noticias_sem_mudanca_tecnica(self):
        for title, body in [
            ("Receita Federal divulga arrecadação de outubro", "Os sistemas da Receita registraram nova alta."),
            ("Nota Fiscal Paulista sorteia prêmios", ""),
            ("Senado aprova PLP 108 da reforma tributária", "IBS, CBS e Comitê Gestor."),
            ("Microsoft lança nova versão do Windows", "software"),
        ]:
            self.assertFalse(erp.analyze(title, body)["erp_impact"], title)


class TestAcbr(unittest.TestCase):
    def test_titulo_do_commit(self):
        t = rss.commit_title("12/11/2026 -- ACBrNFe.Classes -- [*] ACBR-10195 - Alterado o tipo da propriedade "
                             "vUnComLiq para Double. Por: Fulano de Tal\n View Changes")
        self.assertEqual(t, "ACBrNFe.Classes: ACBR-10195 - Alterado o tipo da propriedade vUnComLiq para Double")
        self.assertEqual(rss.commit_title("11/11/2026 [+] Pacote de instalação do NFeABI. Por: Fulano"),
                         "Novo: Pacote de instalação do NFeABI")

    def test_categoria(self):
        cats = classify.classify("ACBrLib: nova versão com suporte à NFS-e nacional", "", None, "rss",
                                 require_title=True)
        self.assertIn("acbr", [c[0] for c in cats])


if __name__ == "__main__":
    unittest.main()
