"""Testes da aba Eventos (sem internet). Execute: python -m unittest discover tests"""
import json
import unittest
from datetime import date, datetime, timezone

from app import eventos

CFG = eventos.load_config()
HOJE = date(2026, 11, 17)


def html_com(*blobs, next_data=None):
    parts = [f'<script type="application/ld+json">{json.dumps(b)}</script>' for b in blobs]
    if next_data is not None:
        parts.append(f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>')
    return "<html><head>" + "".join(parts) + "</head><body></body></html>"


class TestExtracao(unittest.TestCase):
    def test_jsonld_eventbrite(self):
        html = html_com({"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": 1, "item": {
            "@type": "Event", "name": "Workshop de IA Generativa para o Varejo", "startDate": "2026-12-03T19:00:00-03:00",
            "endDate": "2026-12-03T22:00:00-03:00", "url": "https://www.eventbrite.com.br/e/workshop-ia-123",
            "location": {"@type": "Place", "name": "Cubo Itaú", "address": {"addressLocality": "São Paulo",
                         "addressRegion": "SP", "addressCountry": "BR"}},
            "organizer": {"name": "Comunidade X"}}}]})
        evs = eventos.extract_events(eventos.page_blobs(html), "https://www.eventbrite.com.br/d/brazil/ia/")
        self.assertEqual(len(evs), 1)
        e = evs[0]
        self.assertEqual((e["city"], e["state"], e["country"], e["organizer"]), ("São Paulo", "SP", "BR", "Comunidade X"))
        self.assertEqual(e["start_dt"], datetime(2026, 12, 3, 22, 0, tzinfo=timezone.utc))
        fin = eventos.finalize(e, {"id": "x", "country": "BR", "require_topic": True}, CFG, HOJE)
        self.assertEqual(fin["format"], "presencial")
        self.assertIn("ia", fin["themes"])
        self.assertIn("varejo", fin["themes"])

    def test_next_data_luma(self):
        nd = {"props": {"pageProps": {"initialData": {"events": [{
            "event": {"name": "Security in the Age of AI", "start_at": "2026-11-25T22:00:00.000Z", "url": "z6xrxlg6",
                      "location_type": "offline", "geo_address_info": {"city": "São Paulo", "country": "Brazil"}},
            "calendar": {"name": "AI House Brasil"}, "hosts": [{"name": "Fulana"}]}]}}}}
        evs = eventos.extract_events(eventos.page_blobs(html_com(next_data=nd)), "https://luma.com/sao-paulo")
        self.assertEqual(evs[0]["url"], "https://luma.com/z6xrxlg6")
        self.assertEqual(evs[0]["organizer"], "AI House Brasil")
        fin = eventos.finalize(evs[0], {"id": "l", "country": "BR", "require_topic": True}, CFG, HOJE)
        self.assertEqual((fin["format"], fin["country"]), ("presencial", "BR"))
        self.assertEqual(set(fin["themes"]) & {"ia", "seguranca"}, {"ia", "seguranca"})

    def test_apollo_meetup_online(self):
        nd = {"props": {"pageProps": {"__APOLLO_STATE__": {
            "Group:1": {"name": "Python São Paulo"},
            "Event:9": {"title": "Meetup Python online: FastAPI na prática", "dateTime": "2026-12-01T19:00:00-03:00",
                        "eventUrl": "https://www.meetup.com/python-sp/events/9/", "eventType": "ONLINE",
                        "group": {"__ref": "Group:1"}}}}}}
        evs = eventos.extract_events(eventos.page_blobs(html_com(next_data=nd)), "https://www.meetup.com/find/")
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["mode"], evs[0]["organizer"]), ("online", "Python São Paulo"))

    def test_presencial_no_exterior_sai_e_online_fica(self):
        base = {"title": "PyCon Software", "url": "https://x.org", "start_dt": datetime(2026, 12, 5, tzinfo=timezone.utc),
                "all_day": True, "end_dt": None, "end_all_day": True, "city": "Berlin", "country": "Germany", "mode": "presencial"}
        self.assertIsNone(eventos.finalize(dict(base), {"id": "c"}, CFG, HOJE))
        on = eventos.finalize(dict(base, mode="online", city=None), {"id": "c"}, CFG, HOJE)
        self.assertEqual(on["format"], "online")

    def test_passado_e_fora_de_tema_saem(self):
        base = {"title": "Workshop de Python", "url": "https://x.org", "start_dt": datetime(2026, 11, 10, tzinfo=timezone.utc),
                "all_day": True, "end_dt": None, "end_all_day": True, "mode": "online"}
        self.assertIsNone(eventos.finalize(dict(base), {"id": "c"}, CFG, HOJE))
        festa = dict(base, title="Festa de fim de ano", start_dt=datetime(2026, 12, 10, tzinfo=timezone.utc))
        self.assertIsNone(eventos.finalize(festa, {"id": "c", "require_topic": True}, CFG, HOJE))

    def test_titulo_online_e_curso_longo(self):
        base = {"title": "IA aplicada aos empreendedores - Online", "url": "https://x.org", "city": "Belo Horizonte",
                "start_dt": datetime(2026, 11, 23, 22, tzinfo=timezone.utc), "all_day": False, "end_dt": None,
                "end_all_day": False, "mode": None}
        self.assertEqual(eventos.finalize(dict(base), {"id": "s", "country": "BR"}, CFG, HOJE)["format"], "online")
        curso = dict(base, start_dt=datetime(2026, 10, 1, tzinfo=timezone.utc), end_dt=datetime(2027, 2, 1, tzinfo=timezone.utc))
        self.assertIsNone(eventos.finalize(curso, {"id": "s", "country": "BR"}, CFG, HOJE))

    def test_data_meia_noite_utc_vira_dia(self):
        dt, so_dia = eventos._date("2026-11-28T00:00:00.000Z")
        self.assertTrue(so_dia)
        self.assertEqual(eventos._iso(dt, so_dia), "2026-11-28")

    def test_rsc_nextjs(self):
        chunk = '1:{"items":[{"name":"Workshop de Python","start_date":"2026-12-01 19:00:00","url":"https://www.sympla.com.br/evento/x/1","location":{"city":"Recife","state":"PE"}}]}\n'
        html = f'<script>self.__next_f.push([1,{json.dumps(chunk)}])</script>'
        evs = eventos.extract_events(eventos.page_blobs(html), "https://www.sympla.com.br/eventos/tecnologia")
        self.assertEqual((evs[0]["city"], evs[0]["state"]), ("Recife", "PE"))

    def test_devevents_descricao(self):
        i = eventos.parse_devevents_desc("Clean Architecture Masterclass is happening on December 10, 2026, Online.")
        self.assertEqual((i["mode"], i["start_dt"].day), ("online", 10))
        i = eventos.parse_devevents_desc("Summit is happening on April 13-15, 2027 in Las Cruces, United States, North America.")
        self.assertEqual((i["mode"], i["city"], i["country"], i["end_dt"].day), ("presencial", "Las Cruces", "United States", 15))

    def test_ical(self):
        ics = ("BEGIN:VCALENDAR\r\nX-WR-CALNAME:AI Dev SP\r\nBEGIN:VEVENT\r\nSUMMARY:Agentes de IA com LangGraph\r\n"
               "DTSTART;TZID=America/Sao_Paulo:20261208T190000\r\nDTEND;TZID=America/Sao_Paulo:20261208T210000\r\n"
               "LOCATION:Rua X\\, 100\\, São Paulo\\, SP\r\nURL:https://www.meetup.com/aidev-saopaulo/events/1/\r\n"
               "END:VEVENT\r\nEND:VCALENDAR\r\n")

        class R:  # resposta falsa
            text = ics
            status_code = 200
        orig = eventos._get
        eventos._get = lambda url: R()
        try:
            evs = eventos.fetch_ical({"url": "https://x"})
        finally:
            eventos._get = orig
        self.assertEqual(evs[0]["start_dt"], datetime(2026, 12, 8, 22, 0, tzinfo=timezone.utc))
        self.assertEqual((evs[0]["mode"], evs[0]["city"], evs[0]["state"], evs[0]["organizer"]),
                         ("presencial", "São Paulo", "SP", "AI Dev SP"))

    def test_temas_palavra_exata(self):
        self.assertEqual(eventos.themes_for({"title": "Ele ia ao mercado"}, CFG), [])
        self.assertIn("ia", eventos.themes_for({"title": "IA no agronegócio"}, CFG))
        self.assertIn("agro", eventos.themes_for({"title": "IA no agronegócio"}, CFG))


class TestGratisECertificado(unittest.TestCase):
    def test_luma_ticket_info_e_offers(self):
        nd = {"props": {"pageProps": {"initialData": {"data": {"events": [
            {"event": {"name": "Workshop de IA", "start_at": "2026-11-25T22:00:00.000Z", "url": "aaa", "location_type": "online"},
             "ticket_info": {"price": None, "is_free": True}},
            {"event": {"name": "Conferência de Dados", "start_at": "2026-11-26T22:00:00.000Z", "url": "bbb", "location_type": "online"},
             "ticket_info": {"price": {"cents": 15000}, "is_free": False}}]}}}}}
        evs = eventos.extract_events(eventos.page_blobs(html_com(next_data=nd)), "https://luma.com/sao-paulo")
        self.assertEqual([e["free"] for e in evs], [True, False])
        ld = {"@type": "Event", "name": "Meetup Python", "startDate": "2026-12-03T19:00:00-03:00", "url": "https://x.org/e",
              "offers": [{"@type": "Offer", "price": 0, "priceCurrency": "BRL"}]}
        self.assertTrue(eventos.extract_events(eventos.page_blobs(html_com(ld)), "https://x.org")[0]["free"])
        ld["offers"] = {"@type": "AggregateOffer", "lowPrice": "0", "highPrice": "R$ 120,00"}
        self.assertFalse(eventos.extract_events(eventos.page_blobs(html_com(ld)), "https://x.org")[0]["free"])

    def test_meetup_sem_taxa_e_gratis(self):
        nd = {"props": {"pageProps": {"__APOLLO_STATE__": {
            "Event:9": {"__typename": "Event", "title": "Meetup de Python", "dateTime": "2026-12-01T19:00:00-03:00",
                        "eventUrl": "https://www.meetup.com/python-sp/events/9/", "eventType": "ONLINE", "feeSettings": None},
            "Event:10": {"__typename": "Event", "title": "Workshop de Python", "dateTime": "2026-12-02T19:00:00-03:00",
                         "eventUrl": "https://www.meetup.com/python-sp/events/10/", "eventType": "ONLINE",
                         "feeSettings": {"amount": 30, "currency": "BRL"}}}}}}
        evs = eventos.extract_events(eventos.page_blobs(html_com(next_data=nd)), "https://www.meetup.com/find/")
        self.assertEqual({e["url"][-3:]: e["free"] for e in evs}, {"/9/": True, "10/": False})

    def test_texto(self):
        self.assertEqual(eventos.text_flags("Workshop gratuito de IA", "Ao final, os participantes receberão certificado de participação."), (True, True))
        self.assertEqual(eventos.text_flags("Emissão de certificado digital A1 para empresas"), (None, False))
        self.assertEqual(eventos.text_flags("Ingressos a partir de R$ 50"), (False, False))
        self.assertEqual(eventos.text_flags("Free admission. Certificate of attendance provided."), (True, True))

    def test_finalize_marca_fonte_gratuita_e_certificado(self):
        base = {"title": "Curso de Python com certificado", "url": "https://www.sympla.com.br/evento/x/1", "mode": "online",
                "start_dt": datetime(2026, 12, 5, 22, tzinfo=timezone.utc), "all_day": False, "end_dt": None, "end_all_day": False}
        fin = eventos.finalize(dict(base), {"id": "sympla-gratis", "country": "BR", "mark_free": True}, CFG, HOJE)
        self.assertEqual((fin["free"], fin["certificate"]), (True, True))
        fin = eventos.finalize(dict(base, title="Curso de Python"), {"id": "s", "country": "BR"}, CFG, HOJE)
        self.assertEqual((fin["free"], fin["certificate"]), (None, None))

    def test_pagina_do_evento(self):
        html = ('<html><body><nav>Grátis</nav><h1>Curso de IA</h1><div>Ao final do curso, os participantes receberão '
                'um certificado de conclusão.</div><script>var x = "certificado";</script></body></html>')

        class R:
            text = html
            url = "https://www.sympla.com.br/evento/curso/1"
            status_code = 200
        orig = eventos._get
        eventos._get = lambda url: R()
        try:
            d = eventos.read_details("https://www.sympla.com.br/evento/curso/1")
        finally:
            eventos._get = orig
        self.assertEqual((d["free"], d["certificate"]), (None, True))
        self.assertFalse(eventos.text_flags(eventos.page_text("<nav>certificado</nav><p>Meetup</p>"))[1])


if __name__ == "__main__":
    unittest.main()
