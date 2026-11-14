"""Self-check dos filtros. Rodar: python test_pipeline.py"""
import pandas as pd

from pipeline import clean_modis, clean_viirs, normalize


def frame(rows, cols):
    return pd.DataFrame(rows, columns=cols).astype({"acq_time": str, "version": str, "confidence": str})


C = ["latitude", "longitude", "acq_date", "acq_time", "satellite", "confidence", "version", "frp", "daynight", "type"]

# MODIS: type!=0 sai, frp<=0 sai, conf<30 vai pro arquivo à parte, NRT sem type fica
m = normalize(frame([
    [-3, -60, "2020-01-01", "130", "Aqua", "80", "6.03", 10, "D", 0],     # principal
    [-3, -60, "2020-01-01", "130", "Aqua", "80", "6.03", 10, "D", 2],     # type 2 -> sai
    [-3, -60, "2020-01-01", "130", "Aqua", "80", "6.03", 0, "D", 0],      # frp 0 -> sai
    [-3, -61, "2020-01-01", "130", "Aqua", "20", "6.03", 5, "N", 0],      # conf 20 -> low
    [-3, -61, "2020-01-01", "130", "Aqua", "20", "6.03", 5, "N", 0],      # duplicata -> sai
    [-3, -60, "2026-11-01", "130", "Terra", "50", "6.1NRT", 5, "N", None],  # NRT -> principal, provisório
], C), "modis")
log = {}
main, low = clean_modis(m, log)
assert len(main) == 2 and len(low) == 1, (main, low)
assert main.acq_time.tolist() == ["0130", "0130"]
assert main.provisional.tolist() == [False, True]
assert log == {"type!=0": 1, "frp<=0_ou_vazio": 1, "duplicatas_identicas": 1}, log

# VIIRS: l+N sai, l+D vai pro low, duplicata idêntica sai, h marca high_conf
v = normalize(frame([
    [-3, -60, "2020-01-01", "418", "N", "n", "2", 1.2, "N", 0],
    [-3, -60, "2020-01-01", "418", "N", "n", "2", 1.2, "N", 0],   # duplicata -> sai
    [-3, -61, "2020-01-01", "418", "N", "l", "2", 1.2, "N", 0],   # baixa à noite -> sai
    [-3, -62, "2020-01-01", "1600", "N", "l", "2", 1.2, "D", 0],  # baixa de dia -> low
    [-3, -63, "2020-01-01", "1600", "N", "h", "2", 30, "D", 0],   # alta -> principal, high_conf
    [-3, -64, "2020-01-01", "1600", "N", "n", "2", None, "D", 0],  # frp vazio -> sai
], C), "viirs")
log = {}
main, low = clean_viirs(v, log)
assert len(main) == 2 and len(low) == 1, (main, low)
assert main.high_conf.tolist() == [False, True]
assert log == {"type!=0": 0, "frp<=0_ou_vazio": 1, "conf_l_noite": 1, "duplicatas_identicas": 1}, log
# missing_data do FIRMS: colunas SP (data, satélite) e NRT (data, satélite), vazio quando não há
from datetime import date  # noqa: E402
from pipeline import parse_missing  # noqa: E402
html = ("<tr><td>2026-07-16</td><td>Suomi NPP (VIIRS)</td><td>2024-03-06</td><td>NOAA-21 (VIIRS)</td></tr>"
        "<tr><td>2001-06-18</td><td>Terra (MODIS)</td><td></td><td></td></tr>")
fim = {"Terra": date(2026, 8, 31), "Aqua": date(2026, 8, 31), "SNPP": date(2026, 7, 31),
       "N20": date(2026, 7, 31), "N21": date(2026, 7, 31)}
# a falha NRT do N21 em 2024 é antes do fim do SP (o SP tem o dado): não entra
assert parse_missing(html, fim) == {(date(2026, 7, 16), "SNPP"), (date(2001, 6, 18), "Terra")}
html_nrt = "<tr><td></td><td></td><td>2026-09-10</td><td>NOAA-20 (VIIRS)</td></tr>"
assert parse_missing(html_nrt, fim) == {(date(2026, 9, 10), "N20")}   # depois do fim do SP: vale
try:
    parse_missing("<tr><td>2020-01-01</td><td>Outro</td><td></td><td></td></tr>", fim)
    raise AssertionError("satélite desconhecido deveria falhar")
except ValueError:
    pass
# cadastro: cada célula numa região só; borda sem dono vai para a primeira região que encosta
from pipeline import assign_cells  # noqa: E402
a, b = assign_cells([{1, 2}, {3}], [{1, 2, 9, 7}, {3, 2, 9, 8}])
assert a == {1, 2, 9, 7} and b == {3, 8} and not (a & b)

# importador: mapeamento para a tabela focos
from pipeline import to_focos  # noqa: E402

mf = normalize(frame([
    [-3.5, -60.1, "2020-09-01", "130", "Aqua", "29", "6.03", 10, "D", 0],
    [-3.5, -60.1, "2020-09-01", "130", "Aqua", "29", "6.03", 10, "D", 0],     # mesma chave -> 1 linha
    [-3.6, -60.2, "2020-09-01", "1745", "Terra", "80", "6.1NRT", 5, "N", None],
], C), "modis").assign(scan=1.0, track=1.0)
f = to_focos(mf, "modis", "teste.csv", 6)
assert len(f) == 2
assert f.satelite.tolist() == ["Aqua", "Terra"] and f.sensor.unique().tolist() == ["MODIS"]
assert f.confianca.tolist() == ["baixa", "alta"]          # <30 baixa, >=80 alta
assert f.qualidade.tolist() == ["SP", "NRT"]
assert str(f.datahora_utc.iloc[1]) == "2020-09-01 17:45:00+00:00"
assert f.tipo.isna().tolist() == [False, True]
assert all(((h >> 52) & 15) == 6 for h in f.h3)           # bate com o CHECK do banco

vf = normalize(frame([[-3, -60, "2020-01-01", "418", "N", "n", "2", 1.2, "N", 0],
                      [-3, -61, "2020-01-01", "418", "N21", "h", "2", 1.2, "N", 0]], C), "viirs").assign(scan=0.4, track=0.4)
f = to_focos(vf, "viirs", "teste.csv", 6)
assert f.satelite.tolist() == ["SNPP", "N21"] and f.confianca.tolist() == ["nominal", "alta"]

from pipeline import kind_of  # noqa: E402
assert kind_of(pd.DataFrame({"satellite": ["Aqua", "Terra"]})) == "modis"
assert kind_of(pd.DataFrame({"satellite": ["SNPP"], "instrument": ["SNPP"]})) == "viirs"  # ZIP do Archive Download

try:
    to_focos(normalize(frame([[-3, -60, "2020-01-01", "418", "X9", "n", "2", 1.2, "N", 0]], C), "viirs").assign(scan=0.4, track=0.4), "viirs", "t", 6)
    raise AssertionError("satélite desconhecido deveria falhar")
except ValueError:
    pass
print("ok")
