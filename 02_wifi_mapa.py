"""Passo 2 — Levantamento Wi-Fi: grade, interpolação, cobertura e mapas de calor.

Entrada : saida/wifi_medicoes_institucionais.csv (passo 1) e base/earth_campus.png
Saída   : saida/wifi_mapa_calor.png            (mapa de calor, sem imagem de fundo)
          saida/wifi_mapa_calor_satelite.png   (mapa de calor sobre a imagem de satélite)
          saida/wifi_grade.npz                 (grade interpolada, para sobrepor outras camadas)
          saida/wifi_mapa_calor_2_4ghz*.png/.npz  (o mesmo, só com a banda de 2,4 GHz)
          saida/wifi_mapa.json                 (números do passo)

O mapa é gerado duas vezes: com todas as medições institucionais e só com a banda de 2,4 GHz
(as placas ESP32 usadas como gateway só operam nessa banda).

Método (Seção 3.4.1 do TCC):
  1. valor do ponto  = sinal institucional MAIS FORTE medido naquele ponto (RSSI máximo);
  2. valor da célula = MEDIANA dos valores dos pontos dentro da célula (grade de CELULA_M metros);
  3. interpolação linear entre células medidas (dentro do envoltório convexo dos pontos);
  4. fora dele, preenchimento pelo vizinho mais próximo até PREENCHIMENTO_M metros;
  5. o que sobra fica sem estimativa (transparente), para não mostrar cobertura onde ninguém mediu.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import config as cfg


d_todas = pd.read_csv(cfg.SAIDA / "wifi_medicoes_institucionais.csv")
sem = pd.read_csv(cfg.SAIDA / "wifi_pontos_sem_rede_institucional.csv")
base = Image.open(cfg.IMAGEM_BASE).convert("RGB")
cinza = np.array(base.convert("L")).astype(int)
e = cfg.EXTENSAO_BASE
cmap = plt.get_cmap("RdYlGn").copy()
cmap.set_bad(alpha=0)


def gerar(d, sufixo, rotulo):
    """Passos 1 a 5 do método, para o conjunto de medições d. Devolve o dicionário de números."""
    # 1. Valor do ponto: RSSI máximo entre as redes institucionais.
    pt = d.groupby("pointId").agg(lat=("lat", "first"), lon=("lon", "first"), rssi=("rssi_dbm", "max")).reset_index()

    # Coordenadas métricas locais (projeção equiretangular, suficiente para ~500 m).
    lat0, lon0 = pt.lat.mean(), pt.lon.mean()
    KX = 111320.0 * np.cos(np.radians(lat0))
    KY = 110574.0
    pt["x"] = (pt.lon - lon0) * KX
    pt["y"] = (pt.lat - lat0) * KY

    # 2. Grade e mediana por célula.
    c = cfg.CELULA_M
    pt["cx"] = np.floor(pt.x / c).astype(int)
    pt["cy"] = np.floor(pt.y / c).astype(int)
    cel = pt.groupby(["cx", "cy"]).rssi.median().reset_index()
    cel["x"] = (cel.cx + 0.5) * c
    cel["y"] = (cel.cy + 0.5) * c

    xs = np.arange(pt.x.min(), pt.x.max() + c, c)
    ys = np.arange(pt.y.min(), pt.y.max() + c, c)
    GX, GY = np.meshgrid(xs, ys)
    alvo = np.c_[GX.ravel(), GY.ravel()]
    orig = cel[["x", "y"]].values

    # 3. Interpolação linear (só dentro do envoltório convexo das células medidas).
    z = griddata(orig, cel.rssi.values, alvo, method="linear")
    dentro = ~np.isnan(z)

    # 4. Preenchimento pelo vizinho mais próximo, até PREENCHIMENTO_M.
    dist, idx = cKDTree(orig).query(alvo)
    fora = ~dentro & (dist <= cfg.PREENCHIMENTO_M)
    z[fora] = cel.rssi.values[idx[fora]]
    Z = z.reshape(GX.shape)

    # 5. O que sobra fica sem estimativa (NaN).
    est = ~np.isnan(Z)
    r = {
        "pontos_no_mapa": int(len(pt)),
        "medicoes_usadas": int(len(d)),
        "celulas_medidas": int(len(cel)),
        "celulas_na_grade": int(Z.size),
        "celulas_com_estimativa": int(est.sum()),
        "cobertura_da_grade_pct": round(100 * est.mean(), 1),
        "rssi_do_ponto_dbm": {"min": float(pt.rssi.min()), "mediana": float(pt.rssi.median()), "max": float(pt.rssi.max())},
    }
    for lim in (-70, -80):
        r[f"estimativa_abaixo_de_{abs(lim)}_dbm_pct"] = round(100 * float((Z[est] < lim).mean()), 1)

    lon_g = lon0 + xs / KX
    lat_g = lat0 + ys / KY
    np.savez(cfg.SAIDA / f"wifi_grade{sufixo}.npz", rssi=Z, lon=lon_g, lat=lat_g, celula_m=c)

    ext = [lon_g[0] - c / 2 / KX, lon_g[-1] + c / 2 / KX, lat_g[0] - c / 2 / KY, lat_g[-1] + c / 2 / KY]
    aspecto = 1 / np.cos(np.radians(lat0))      # 1° de longitude é menor que 1° de latitude

    def desenhar(ax, titulo):
        im = ax.imshow(np.ma.masked_invalid(Z), origin="lower", extent=ext, cmap=cmap, vmin=-90, vmax=-40,
                       alpha=0.75, interpolation="bilinear", zorder=3)
        ax.scatter(pt.lon, pt.lat, s=3, c="k", alpha=0.4, zorder=4, label=f"{len(pt)} pontos de medição")
        ax.scatter(sem.lon, sem.lat, s=22, marker="x", c="#8b0000", lw=1.2, zorder=5,
                   label=f"{len(sem)} pontos sem rede institucional")
        ax.set_aspect(aspecto)
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude"); ax.set_title(titulo, fontsize=11)
        ax.legend(loc="upper right", fontsize=8)
        return im

    fig, ax = plt.subplots(figsize=(9, 8))
    im = desenhar(ax, f"Cobertura Wi-Fi institucional ({rotulo}) — sinal mais forte por ponto")
    fig.colorbar(im, ax=ax, label="RSSI (dBm)", shrink=0.8)
    fig.savefig(cfg.SAIDA / f"wifi_mapa_calor{sufixo}.png", dpi=150, bbox_inches="tight"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.imshow(base, extent=[e["lon_min"], e["lon_max"], e["lat_min"], e["lat_max"]], zorder=1)
    im = desenhar(ax, f"Cobertura Wi-Fi institucional ({rotulo}) sobre imagem de satélite (Google Earth)")
    ax.set_xlim(e["lon_min"], e["lon_max"]); ax.set_ylim(e["lat_min"], e["lat_max"])
    fig.colorbar(im, ax=ax, label="RSSI (dBm)", shrink=0.8)
    fig.savefig(cfg.SAIDA / f"wifi_mapa_calor_satelite{sufixo}.png", dpi=150, bbox_inches="tight"); plt.close(fig)
    return r, lat0


r, lat0 = gerar(d_todas, "", "todas as bandas")
r24, _ = gerar(d_todas[d_todas.banda == "2,4 GHz"], "_2_4ghz", "somente 2,4 GHz")
r["somente_2_4ghz"] = r24
r["celula_m"] = cfg.CELULA_M
r["preenchimento_m"] = cfg.PREENCHIMENTO_M

# Validação de escala da imagem de satélite: barra de 200 m da captura x extensão usada.
larg_m = (e["lon_max"] - e["lon_min"]) * 111320.0 * np.cos(np.radians(lat0))
alt_m = (e["lat_max"] - e["lat_min"]) * 110574.0
px_por_m_ext_x = base.width / larg_m
px_por_m_ext_y = base.height / alt_m
melhor = 0
for y in range(base.height - 15, base.height):             # barra de escala fica no rodapé
    xs_b = np.where(cinza[y, 700:1250] > 200)[0]
    melhor = max(melhor, int(xs_b.max() - xs_b.min() + 1)) if len(xs_b) > 50 else melhor
px_por_m_barra = melhor / cfg.ESCALA_BARRA_M
r["escala_barra_px"] = melhor
r["escala_erro_x_pct"] = round(100 * abs(px_por_m_ext_x - px_por_m_barra) / px_por_m_barra, 1)
r["escala_erro_y_pct"] = round(100 * abs(px_por_m_ext_y - px_por_m_barra) / px_por_m_barra, 1)

(cfg.SAIDA / "wifi_mapa.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(r, ensure_ascii=False, indent=2))
