"""Parâmetros do pipeline. Toda decisão de tratamento citada no TCC está aqui."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DADOS = RAIZ / "dados"
SAIDA = RAIZ / "saida"
BASE = RAIZ / "base"

# ---------- Levantamento Wi-Fi ----------
DB_WIFI = DADOS / "wifi_mapper.db"
SESSAO = "Sessão fatec"          # a sessão "Sessão 731" (2 pontos, sem encerramento) fica de fora
ACURACIA_MAX_M = 30.0            # medições com acurácia de GPS acima disso são descartadas
LISTA_SSIDS = DADOS / "ssids_institucionais.csv"   # lista definida pelo autor
CELULA_M = 5.0                   # lado da célula da grade, em metros
PREENCHIMENTO_M = 15.0           # raio máximo de preenchimento pelo vizinho mais próximo
FAIXAS_LIMITE_MHZ = 3000         # < 3000 MHz = banda de 2,4 GHz; >= 3000 = 5 GHz

# Imagem de satélite (captura do Google Earth) e sua extensão geográfica.
# A ESCALA da extensão é conferida pela barra de 200 m da própria captura (script 02). A POSIÇÃO foi
# ajustada comparando as trilhas de medição com as vias e os caminhos visíveis na imagem: a posição
# anterior deslocava os pontos cerca de 108 m para leste e 39 m para norte em relação aos prédios.
# Erro estimado da posição: cerca de 5 m (mediana), pequeno frente à célula de 5 m da grade.
IMAGEM_BASE = BASE / "earth_campus.png"
EXTENSAO_BASE = dict(lon_min=-50.202986, lon_max=-50.187556, lat_min=-22.113525, lat_max=-22.107015)
ESCALA_BARRA_M = 200.0

# ---------- Enlace LoRa/Meshtastic ----------
REGISTROS_LORA = DADOS / "registros_lora.csv"
TESTE_LONGA = DADOS / "teste_longa_distancia.csv"   # teste isolado a ~2,3 km (09/10/2026), fora dos 33 registros
FREQ_MHZ = 915.0                 # conforme o relatório da turma (LONG_FAST)
POTENCIA_TX_DBM = (22.0, 28.0)   # faixa informada no relatório da turma
GANHO_ANTENA_DBI = 3.0           # antenas omnidirecionais de 3 dBi nos dois rádios
FAIXAS_DIST_M = [0, 100, 200, 300, 400]
LIMIAR_OUTLIER_DBM = -100        # registros no piso do rádio, analisados também sem eles

# ---------- Sobreposição Wi-Fi x LoRa (passo 4) ----------
# Ponto fixo do enlace LoRa (Laboratório Maker, Fatec Pompeia). As coordenadas dos pontos MÓVEIS da campanha
# LoRa não foram preservadas; por isso a sobreposição usa a distância ao ponto fixo, não o sinal medido.
PONTO_FIXO = dict(lat=-22.110526, lon=-50.195753)
LIMIAR_FRACO_DBM = -80.0         # abaixo disso o sinal institucional é considerado fraco
