"""Passo 4 — Sobreposição descritiva Wi-Fi x LoRa (H2 do TCC).

Pergunta: o alcance LoRa medido a partir do ponto fixo abrange as áreas de sinal institucional fraco do mapa Wi-Fi?

Entrada : saida/wifi_grade.npz, saida/wifi_grade_2_4ghz.npz (passo 2), saida/lora_resumo.json (passo 3)
Saída   : saida/sobreposicao_wifi_lora.png  (satélite + células fracas + círculos de alcance)
          saida/sobreposicao.json           (números)

ATENÇÃO — o que isto NÃO é: a distância ao ponto fixo não é cobertura LoRa medida. Os pontos de medição LoRa
não tiveram as coordenadas preservadas, então não se sabe se o sinal foi recebido nas células fracas (borda
leste). O resultado diz apenas que essas células estão dentro da distância em que houve recepção.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import config as cfg

e = cfg.EXTENSAO_BASE
p = cfg.PONTO_FIXO
R_MAX = json.load(open(cfg.SAIDA / "lora_resumo.json", encoding="utf-8"))["distancia_m"]["max"]
R_MED = json.load(open(cfg.SAIDA / "lora_resumo.json", encoding="utf-8"))["distancia_m"]["mediana"]
KX = 111320.0 * np.cos(np.radians(p["lat"]))
KY = 110574.0


def analisar(arq, rotulo):
    z = np.load(cfg.SAIDA / arq)
    lon, lat, rssi = z["lon"], z["lat"], z["rssi"]
    LON, LAT = np.meshgrid(lon, lat)
    dist = np.hypot((LON - p["lon"]) * KX, (LAT - p["lat"]) * KY)
    mapeada = ~np.isnan(rssi)
    fraca = mapeada & (rssi < cfg.LIMIAR_FRACO_DBM)
    dm, df = dist[mapeada], dist[fraca]
    r = {
        "celulas_mapeadas": int(mapeada.sum()),
        "distancia_max_celula_mapeada_m": round(float(dm.max())),
        "celulas_fracas": int(fraca.sum()),
        "celulas_fracas_dentro_de_alcance_max_pct": round(100 * float((df <= R_MAX).mean()), 1),
        "celulas_fracas_dist_min_m": round(float(df.min())),
        "celulas_fracas_dist_mediana_m": round(float(np.median(df))),
        "celulas_fracas_dist_max_m": round(float(df.max())),
        "celulas_fracas_ate_200m_pct": round(100 * float((df <= 200).mean()), 1),
        "celulas_mapeadas_dentro_de_alcance_max_pct": round(100 * float((dm <= R_MAX).mean()), 1),
    }
    return r, (LON, LAT, rssi, fraca), rotulo


res = {"limiar_fraco_dbm": cfg.LIMIAR_FRACO_DBM, "alcance_max_m": R_MAX, "distancia_mediana_lora_m": R_MED}
res["todas_as_bandas"], g_todas, _ = analisar("wifi_grade.npz", "todas as bandas")
res["somente_2_4ghz"], g24, _ = analisar("wifi_grade_2_4ghz.npz", "somente 2,4 GHz")

base = Image.open(cfg.IMAGEM_BASE).convert("RGB")
LON, LAT, rssi24, fraca24 = g24
_, _, rssi_t, fraca_t = g_todas
fig, ax = plt.subplots(figsize=(10, 6.6))
ax.imshow(base, extent=[e["lon_min"], e["lon_max"], e["lat_min"], e["lat_max"]], zorder=1)
ok = ~np.isnan(rssi24) & ~fraca24
ax.scatter(LON[ok], LAT[ok], s=3, c="#2e7d32", alpha=0.25, zorder=2, label="Mapeada, sinal ≥ −80 dBm (2,4 GHz)")
ax.scatter(LON[fraca24], LAT[fraca24], s=6, c="#ff9f1c", alpha=0.9, zorder=3,
           label=f"Sinal < −80 dBm em 2,4 GHz ({res['somente_2_4ghz']['celulas_fracas']} células)")
ax.scatter(LON[fraca_t], LAT[fraca_t], s=6, c="#c1121f", alpha=0.95, zorder=4,
           label=f"Sinal < −80 dBm, todas as bandas ({res['todas_as_bandas']['celulas_fracas']} células)")
th = np.linspace(0, 2 * np.pi, 361)
for raio, est, rot in [(R_MED, ":", f"mediana das distâncias LoRa ({R_MED:.0f} m)"),
                       (R_MAX, "-", f"maior distância com recepção ({R_MAX:.0f} m)")]:
    ax.plot(p["lon"] + raio * np.cos(th) / KX, p["lat"] + raio * np.sin(th) / KY, ls=est, c="#ffffff", lw=3.5, zorder=5)
    ax.plot(p["lon"] + raio * np.cos(th) / KX, p["lat"] + raio * np.sin(th) / KY, ls=est, c="#A64B12", lw=2, zorder=6, label=rot)
ax.scatter([p["lon"]], [p["lat"]], marker="*", s=260, c="#A64B12", edgecolors="w", zorder=7, label="Ponto fixo LoRa (Lab. Maker)")
ax.set_xlim(e["lon_min"], e["lon_max"]); ax.set_ylim(e["lat_min"], e["lat_max"])
ax.set_aspect(1 / np.cos(np.radians(p["lat"])))
ax.ticklabel_format(useOffset=False, style="plain"); ax.tick_params(labelsize=8)
ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), fontsize=8, framealpha=0.9, ncol=2)
fig.tight_layout()
fig.savefig(cfg.SAIDA / "sobreposicao_wifi_lora.png", dpi=150, bbox_inches="tight"); plt.close(fig)

(cfg.SAIDA / "sobreposicao.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=2))
