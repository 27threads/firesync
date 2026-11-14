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
print("ok")
