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
print("ok")
