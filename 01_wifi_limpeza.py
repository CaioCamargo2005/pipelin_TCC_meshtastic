"""Passo 1 — Levantamento Wi-Fi: leitura do banco, limpeza e filtro de redes.

Entrada : dados/wifi_mapper.db (SQLite do aplicativo de coleta) e dados/ssids_institucionais.csv
Saída   : saida/wifi_medicoes_institucionais.csv  (medições já filtradas)
          saida/wifi_pontos_sem_rede_institucional.csv (pontos sem nenhuma rede institucional)
          saida/wifi_por_rede.csv                  (medições e pontos de acesso por SSID)
          saida/wifi_limpeza.json                  (todos os números do passo)
"""
import json
import sqlite3
import pandas as pd
import config as cfg

cfg.SAIDA.mkdir(exist_ok=True)

# 1. Leitura: cada medição é ligada ao ponto de coleta, de onde vem a acurácia do GPS.
con = sqlite3.connect(f"file:{cfg.DB_WIFI}?mode=ro", uri=True)
sessoes = pd.read_sql("select id, name, finishedAt from sessions", con)
med = pd.read_sql(
    """select m.id, m.sessionId, m.pointId, m.ssid, m.bssid, m.dbm as rssi_dbm,
              m.frequencyMhz as freq_mhz, m.latitude as lat, m.longitude as lon,
              p.accuracyMeters as acuracia_m
       from measurements m join points p on p.id = m.pointId""", con)
pontos = pd.read_sql("select sessionId, count(*) n from points group by sessionId", con)
con.close()

r = {"sessoes": []}
for _, s in sessoes.iterrows():
    r["sessoes"].append({"nome": s["name"],
                         "pontos": int(pontos.loc[pontos.sessionId == s["id"], "n"].iloc[0]),
                         "medicoes": int((med.sessionId == s["id"]).sum()),
                         "encerrada": s["finishedAt"] is not None and pd.notna(s["finishedAt"])})

# 2. Sessão de análise (a outra é incompleta e fica fora).
sid = int(sessoes.loc[sessoes.name == cfg.SESSAO, "id"].iloc[0])
med = med[med.sessionId == sid].copy()
r["sessao_usada"] = cfg.SESSAO
r["medicoes_originais"] = len(med)
r["pontos_com_medicao"] = int(med.pointId.nunique())
r["ssids_distintos"] = int(med.ssid.nunique())

# 3. Outliers de geolocalização: acurácia de GPS acima do limite.
ok = med.acuracia_m <= cfg.ACURACIA_MAX_M
r["acuracia_limite_m"] = cfg.ACURACIA_MAX_M
r["removidas_por_acuracia"] = int((~ok).sum())
r["removidas_por_acuracia_pct"] = round(100 * (~ok).mean(), 1)
r["mantidas_apos_acuracia"] = int(ok.sum())
r["mantidas_apos_acuracia_pct"] = round(100 * ok.mean(), 1)
med = med[ok]

# 4. Redes de interesse: lista institucional definida pelo autor.
lista = pd.read_csv(cfg.LISTA_SSIDS)
r["ssids_previstos"] = len(lista)
inst = med[med.ssid.isin(lista.ssid)].copy()
r["ssids_observados"] = int(inst.ssid.nunique())
r["ssids_nao_observados"] = sorted(set(lista.ssid) - set(inst.ssid))
r["medicoes_institucionais"] = len(inst)
r["pontos_de_acesso_institucionais"] = int(inst.bssid.nunique())
r["pontos_com_rede_institucional"] = int(inst.pointId.nunique())


# 4b. Pontos de coleta (já com GPS aceitável) onde NENHUMA rede institucional foi vista:
#     é onde a cobertura institucional é inexistente, e o mapa de calor não os mostra (sem valor de RSSI).
todos_pts = med.groupby("pointId").agg(lat=("lat", "first"), lon=("lon", "first"),
                                      redes_vistas=("ssid", "nunique"),
                                      sinal_mais_forte_qualquer_rede_dbm=("rssi_dbm", "max"))
sem_inst = todos_pts[~todos_pts.index.isin(inst.pointId)].reset_index()
sem_inst.to_csv(cfg.SAIDA / "wifi_pontos_sem_rede_institucional.csv", index=False)
r["pontos_validos_apos_acuracia"] = int(len(todos_pts))
r["pontos_sem_rede_institucional"] = int(len(sem_inst))
r["pontos_sem_rede_institucional_pct"] = round(100 * len(sem_inst) / len(todos_pts), 1)

# 5. Banda (2,4 ou 5 GHz), a partir da frequência gravada pelo aplicativo.
inst["banda"] = (inst.freq_mhz >= cfg.FAIXAS_LIMITE_MHZ).map({False: "2,4 GHz", True: "5 GHz"})
r["medicoes_por_banda"] = inst.banda.value_counts().to_dict()

por_rede = (inst.groupby("ssid").agg(medicoes=("id", "size"), pontos_de_acesso=("bssid", "nunique"))
            .sort_values("medicoes", ascending=False).reset_index())
por_rede.to_csv(cfg.SAIDA / "wifi_por_rede.csv", index=False)
r["top3_redes"] = por_rede.head(3).to_dict("records")

inst.to_csv(cfg.SAIDA / "wifi_medicoes_institucionais.csv", index=False)
(cfg.SAIDA / "wifi_limpeza.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(r, ensure_ascii=False, indent=2))
