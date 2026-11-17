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


if __name__ == "__main__":
    unittest.main()
