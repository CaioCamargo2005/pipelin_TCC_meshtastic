"""Passo 3 — Enlace LoRa/Meshtastic: estatística descritiva, hipótese H1 e comparação com o espaço livre.

Entrada : dados/registros_lora.csv (33 registros das campanhas de 30/09 e 05/10/2026, relatório da turma)
Saída   : saida/lora_resumo.json, saida/lora_faixas.csv, saida/lora_rssi_snr.png

Cada linha é uma mensagem recebida em salto único: distância ao ponto fixo (calculada das coordenadas),
RSSI, SNR e altitude do remetente (GPS do celular).
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import config as cfg

cfg.SAIDA.mkdir(exist_ok=True)
d = pd.read_csv(cfg.REGISTROS_LORA)
r = {"registros": len(d)}


def resumo(s):
    return {"min": float(s.min()), "mediana": float(s.median()), "max": float(s.max())}


r["distancia_m"] = resumo(d.dist_m)
r["rssi_dbm"] = resumo(d.rssi_dbm)
r["snr_db"] = resumo(d.snr_db)
r["rssi_na_maior_distancia"] = float(d.loc[d.dist_m.idxmax(), "rssi_dbm"])
r["snr_na_maior_distancia"] = float(d.loc[d.dist_m.idxmax(), "snr_db"])


# H1 (parte da distância): correlação de Spearman — não supõe relação linear nem normalidade.
def sp(x, y):
    rho, p = spearmanr(x, y)
    return {"rho": round(float(rho), 2), "p": float(p), "n": int(len(x))}


r["spearman_dist_rssi"] = sp(d.dist_m, d.rssi_dbm)
r["spearman_dist_snr"] = sp(d.dist_m, d.snr_db)
sem = d[d.rssi_dbm > cfg.LIMIAR_OUTLIER_DBM]          # sem os registros no piso do rádio (-100 dBm)
r["registros_no_piso"] = int((d.rssi_dbm <= cfg.LIMIAR_OUTLIER_DBM).sum())
r["spearman_sem_piso_dist_rssi"] = sp(sem.dist_m, sem.rssi_dbm)
r["spearman_sem_piso_dist_snr"] = sp(sem.dist_m, sem.snr_db)
r["spearman_altitude_rssi"] = sp(d.alt_m, d.rssi_dbm)
r["altitude_m"] = {"min": float(d.alt_m.min()), "max": float(d.alt_m.max())}

# Faixas de distância.
fx = []
for lo, hi in zip(cfg.FAIXAS_DIST_M[:-1], cfg.FAIXAS_DIST_M[1:]):
    s = d[(d.dist_m >= lo) & (d.dist_m < hi)]
    fx.append({"faixa": f"{lo} a {hi} m", "registros": len(s),
               "rssi_medio_dbm": round(s.rssi_dbm.mean(), 1), "snr_medio_db": round(s.snr_db.mean(), 2)})
pd.DataFrame(fx).to_csv(cfg.SAIDA / "lora_faixas.csv", index=False)
r["faixas"] = fx

# Ajuste por mínimos quadrados: RSSI = a + b * log10(d)  ->  expoente de perda aparente n = -b/10.
lg = np.log10(d.dist_m.values)
b, a = np.polyfit(lg, d.rssi_dbm.values, 1)
r2 = float(np.corrcoef(lg, d.rssi_dbm.values)[0, 1] ** 2)
r["ajuste_log_distancia"] = {"expoente_n": round(float(-b / 10), 1), "r2": round(r2, 2)}


# Espaço livre (FSPL): RSSI = Ptx + Gtx + Grx - (20 log10(d_km) + 20 log10(f_MHz) + 32,44)
def fspl_rssi(dist_m, ptx):
    perda = 20 * np.log10(dist_m / 1000) + 20 * np.log10(cfg.FREQ_MHZ) + 32.44
    return ptx + 2 * cfg.GANHO_ANTENA_DBI - perda


dmax = float(d.dist_m.max())
r["espaco_livre"] = {"freq_mhz": cfg.FREQ_MHZ, "ganho_antena_dbi": cfg.GANHO_ANTENA_DBI}
for ptx in cfg.POTENCIA_TX_DBM:
    r["espaco_livre"][f"ptx_{int(ptx)}_dbm"] = {
        "rssi_a_100m": round(float(fspl_rssi(100, ptx)), 1),
        "rssi_na_maior_distancia": round(float(fspl_rssi(dmax, ptx)), 1),
        "diferenca_para_medido_db": round(float(fspl_rssi(dmax, ptx) - r["rssi_na_maior_distancia"]), 1)}

# Figura: RSSI e SNR contra a distância.
fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
xx = np.linspace(d.dist_m.min(), d.dist_m.max(), 100)
ax[0].scatter(d.dist_m, d.rssi_dbm, c="#1f6f8b", s=28)
ax[0].plot(xx, a + b * np.log10(xx), "--", c="gray", label=f"ajuste log-distância (n ≈ {-b / 10:.1f})")
ax[0].set_ylabel("RSSI (dBm)"); ax[0].legend(fontsize=8)
ax[1].scatter(d.dist_m, d.snr_db, c="#c0392b", s=28)
ax[1].axhline(0, c="gray", lw=0.8)
ax[1].set_ylabel("SNR (dB)")
for x in ax:
    x.set_xlabel("Distância ao ponto fixo (m)"); x.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(cfg.SAIDA / "lora_rssi_snr.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------------------------
# Teste isolado de longa distância (~2,3 km). NÃO entra nas estatísticas acima: é de outro dia, com
# outro nó, a uma distância 6x maior que a dos 33 registros. É comparado ao que o ajuste e o espaço
# livre prevêem (extrapolação: o ajuste só foi feito até 386 m).
# ---------------------------------------------------------------------------------------------
t = pd.read_csv(cfg.TESTE_LONGA).iloc[0]
dl = float(t.distancia_m)
prev_ajuste = float(a + b * np.log10(dl))
lt = {"distancia_m": dl, "rssi_dbm": float(t.rssi_dbm), "snr_db": float(t.snr_db),
      "saltos_informados": int(t.saltos_informados),
      "previsto_pelo_ajuste_dbm": round(prev_ajuste, 1),
      "medido_menos_previsto_pelo_ajuste_db": round(float(t.rssi_dbm) - prev_ajuste, 1),
      "razao_para_maior_distancia_dos_33": round(dl / dmax, 1),
      "expoente_local_entre_maior_dist_dos_33_e_teste": round(
          float((r["rssi_na_maior_distancia"] - t.rssi_dbm) / (10 * np.log10(dl / dmax))), 1)}
for ptx in cfg.POTENCIA_TX_DBM:
    lt[f"espaco_livre_ptx_{int(ptx)}_dbm"] = round(float(fspl_rssi(dl, ptx)), 1)
    lt[f"abaixo_do_espaco_livre_ptx_{int(ptx)}_db"] = round(float(fspl_rssi(dl, ptx) - t.rssi_dbm), 1)
r["teste_longa_distancia"] = lt

fig, ax = plt.subplots(figsize=(8, 4.6))
xx = np.logspace(np.log10(50), np.log10(2600), 200)
ax.scatter(d.dist_m, d.rssi_dbm, c="#1f6f8b", s=26, label="33 registros (58 a 386 m)", zorder=3)
ax.plot(xx, a + b * np.log10(xx), "--", c="gray", label="ajuste dos 33 registros (extrapolado)")
ax.plot(xx, fspl_rssi(xx, cfg.POTENCIA_TX_DBM[0]), ":", c="#c0392b", label=f"espaço livre ({int(cfg.POTENCIA_TX_DBM[0])} dBm)")
ax.scatter([dl], [t.rssi_dbm], marker="*", s=170, c="#e67e22", zorder=4, label="teste de 09/10 (≈2,3 km)")
ax.set_xscale("log"); ax.set_xlabel("Distância (m, escala logarítmica)"); ax.set_ylabel("RSSI (dBm)")
ax.grid(alpha=0.3, which="both"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(cfg.SAIDA / "lora_longa_distancia.png", dpi=150); plt.close(fig)

(cfg.SAIDA / "lora_resumo.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(r, ensure_ascii=False, indent=2))
