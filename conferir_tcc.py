"""Compara os números que o pipeline produz com os números escritos no TCC.
Cada linha diz OK ou DIVERGE; uma divergência significa que o texto ou o código precisa ser corrigido."""
import json
import config as cfg

S = cfg.SAIDA
L = json.load(open(S / "wifi_limpeza.json", encoding="utf-8"))
M = json.load(open(S / "wifi_mapa.json", encoding="utf-8"))
R = json.load(open(S / "lora_resumo.json", encoding="utf-8"))
O = json.load(open(S / "sobreposicao.json", encoding="utf-8"))
top = {t["ssid"]: t for t in L["top3_redes"]}
faixa = {f["faixa"]: f for f in R["faixas"]}
FSPL = R["espaco_livre"]["ptx_22_dbm"]

# (descrição, valor no pipeline, valor escrito no TCC)
checagens = [
    ("Pontos da sessão", L["sessoes"][0]["pontos"], 854),
    ("Medições originais", L["medicoes_originais"], 46999),
    ("% removidas por acurácia > 30 m", L["removidas_por_acuracia_pct"], 7.0),
    ("% mantidas", L["mantidas_apos_acuracia_pct"], 93.0),
    ("SSIDs observados", L["ssids_observados"], 52),
    ("SSIDs previstos", L["ssids_previstos"], 57),
    ("Medições institucionais", L["medicoes_institucionais"], 20734),
    ("Pontos de acesso institucionais", L["pontos_de_acesso_institucionais"], 467),
    ("Fatec Bloco D (medições)", top["Fatec Bloco D"]["medicoes"], 2223),
    ("Fatec Bloco D (pontos de acesso)", top["Fatec Bloco D"]["pontos_de_acesso"], 27),
    ("Fatec Bloco A (medições)", top["Fatec Bloco A"]["medicoes"], 996),
    ("Colégio (medições)", top["Colegio Shunji Nishimura"]["medicoes"], 927),
    ("Cobertura da grade (%)", round(M["cobertura_da_grade_pct"]), 81),
    ("Erro de escala da imagem (%, < 2)", M["escala_erro_x_pct"] < 2 and M["escala_erro_y_pct"] < 2, True),
    ("Pontos de coleta válidos (GPS <= 30 m)", L["pontos_validos_apos_acuracia"], 779),
    ("Pontos sem rede institucional", L["pontos_sem_rede_institucional"], 27),
    ("% de pontos sem rede institucional", L["pontos_sem_rede_institucional_pct"], 3.5),
    ("Pontos no mapa (com rede institucional)", M["pontos_no_mapa"], 752),
    ("Mediana do sinal mais forte por ponto (dBm)", M["rssi_do_ponto_dbm"]["mediana"], -65.0),
    ("Área estimada abaixo de -80 dBm (%)", M["estimativa_abaixo_de_80_dbm_pct"], 2.5),
    ("Medições em 2,4 GHz", L["medicoes_por_banda"]["2,4 GHz"], 9702),
    ("Medições em 5 GHz", L["medicoes_por_banda"]["5 GHz"], 11032),
    ("2,4 GHz: pontos no mapa", M["somente_2_4ghz"]["pontos_no_mapa"], 724),
    ("2,4 GHz: mediana por ponto (dBm)", M["somente_2_4ghz"]["rssi_do_ponto_dbm"]["mediana"], -70.0),
    ("2,4 GHz: área estimada abaixo de -80 dBm (%)", M["somente_2_4ghz"]["estimativa_abaixo_de_80_dbm_pct"], 21.2),
    ("Registros LoRa", R["registros"], 33),
    ("Distância mediana (m)", R["distancia_m"]["mediana"], 193.7),
    ("Distância máxima (m)", R["distancia_m"]["max"], 386.3),
    ("RSSI mediano (dBm)", R["rssi_dbm"]["mediana"], -73.0),
    ("SNR mediano (dB)", R["snr_db"]["mediana"], 5.25),
    ("Spearman distância x RSSI", R["spearman_dist_rssi"]["rho"], -0.81),
    ("Spearman distância x SNR", R["spearman_dist_snr"]["rho"], -0.73),
    ("Spearman sem piso, RSSI", R["spearman_sem_piso_dist_rssi"]["rho"], -0.85),
    ("Spearman altitude x RSSI", R["spearman_altitude_rssi"]["rho"], 0.25),
    ("RSSI médio 0-100 m", faixa["0 a 100 m"]["rssi_medio_dbm"], -52.3),
    ("RSSI médio 300-400 m", faixa["300 a 400 m"]["rssi_medio_dbm"], -87.1),
    ("Expoente de perda aparente", R["ajuste_log_distancia"]["expoente_n"], 5.2),
    ("R² do ajuste", R["ajuste_log_distancia"]["r2"], 0.62),
    ("Teste 2,3 km: previsto pelo ajuste (dBm)", R["teste_longa_distancia"]["previsto_pelo_ajuste_dbm"], -127.4),
    ("Teste 2,3 km: medido menos previsto (dB)", R["teste_longa_distancia"]["medido_menos_previsto_pelo_ajuste_db"], 8.4),
    ("Teste 2,3 km: abaixo do espaço livre, 22 dBm (dB)", round(R["teste_longa_distancia"]["abaixo_do_espaco_livre_ptx_22_db"]), 48),
    ("Teste 2,3 km: expoente local", R["teste_longa_distancia"]["expoente_local_entre_maior_dist_dos_33_e_teste"], 4.8),
    ("Espaço livre a 100 m, 22 dBm", FSPL["rssi_a_100m"], -43.7),
    ("Diferença para o medido a 386 m, 22 dBm (dB)", round(FSPL["diferenca_para_medido_db"]), 27),
    ("Sobreposição: células fracas, todas as bandas", O["todas_as_bandas"]["celulas_fracas"], 148),
    ("Sobreposição: células fracas, 2,4 GHz", O["somente_2_4ghz"]["celulas_fracas"], 1247),
    ("Sobreposição: maior distância de célula mapeada (m)", O["todas_as_bandas"]["distancia_max_celula_mapeada_m"], 365),
    ("Sobreposição: fracas dentro de 386 m (%, 2,4 GHz)", O["somente_2_4ghz"]["celulas_fracas_dentro_de_alcance_max_pct"], 100.0),
    ("Sobreposição: fracas até 200 m (%, 2,4 GHz)", O["somente_2_4ghz"]["celulas_fracas_ate_200m_pct"], 90.9),
    ("Sobreposição: distância mediana das fracas (m, 2,4 GHz)", O["somente_2_4ghz"]["celulas_fracas_dist_mediana_m"], 120),
]
ruins = 0
for nome, obtido, tcc in checagens:
    ok = obtido == tcc
    ruins += not ok
    print(f"{'OK     ' if ok else 'DIVERGE'}  {nome}: pipeline = {obtido} | TCC = {tcc}")
print(f"\n{len(checagens) - ruins} de {len(checagens)} conferem.")
