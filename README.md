# Pipeline de dados do TCC — cobertura Wi-Fi e enlace LoRa/Meshtastic (Fatec Pompeia)

Esta pasta contém o código que gera **todos os números e figuras** dos Capítulos 3 e 4 do TCC. Não é um sistema
rodando sozinho: é uma sequência de quatro scripts em Python que você executa em ordem, e cada um lê os arquivos
que o anterior deixou em `saida/`.

## Como rodar

Precisa de Python 3.10 ou mais novo.

```
pip install -r requirements.txt
python run_all.py
```

O `run_all.py` executa os passos abaixo, na ordem, e termina imprimindo a conferência com o TCC. Leva alguns
segundos. Se preferir, rode um passo de cada vez (`python 01_wifi_limpeza.py`, depois `02_...`, `03_...` e `04_...`).
Tudo que for gerado aparece em `saida/`; pode apagar essa pasta e rodar de novo, o resultado é o mesmo.

## O que cada passo faz

| Passo | Lê | Faz | Gera (em `saida/`) |
|---|---|---|---|
| `01_wifi_limpeza.py` | `dados/wifi_mapper.db`, `dados/ssids_institucionais.csv` | Lê o banco do aplicativo; fica só com a "Sessão fatec"; descarta medições cujo ponto tem acurácia de GPS acima de 30 m; fica só com as redes da lista institucional; marca a banda (2,4 ou 5 GHz) pela frequência; separa os pontos onde nenhuma rede institucional foi vista | `wifi_medicoes_institucionais.csv`, `wifi_por_rede.csv`, `wifi_pontos_sem_rede_institucional.csv`, `wifi_limpeza.json` |
| `02_wifi_mapa.py` | saída do passo 1, `base/earth_campus.png` | Para cada ponto, pega o sinal institucional mais forte; agrupa em células de 5 m pela mediana; interpola linearmente entre células; preenche com o vizinho mais próximo até 15 m; o resto fica sem valor; calcula a cobertura e desenha os mapas (todas as bandas e só 2,4 GHz, com e sem imagem de satélite); confere a escala da imagem de satélite pela barra de 200 m | `wifi_mapa_calor*.png`, `wifi_mapa_calor_satelite*.png`, `wifi_grade*.npz`, `wifi_mapa.json` |
| `03_lora_analise.py` | `dados/registros_lora.csv` | Estatística descritiva dos 33 registros; correlação de Spearman entre distância e RSSI/SNR (com e sem os registros de −100 dBm) e entre altitude e RSSI; médias por faixa de distância; ajuste RSSI × log10(distância); comparação com a perda em espaço livre | `lora_resumo.json`, `lora_faixas.csv`, `lora_rssi_snr.png` |
| `04_sobreposicao.py` | `saida/wifi_grade*.npz`, `saida/lora_resumo.json` | Sobreposição descritiva (H2): distância de cada célula do mapa Wi-Fi ao ponto fixo LoRa, comparada com o alcance medido (mediana e máximo dos 33 registros). Não usa sinal LoRa medido nas células, porque as coordenadas dos pontos móveis não foram preservadas | `sobreposicao.json`, `sobreposicao_wifi_lora.png` |
| `conferir_tcc.py` | os `.json` acima | Compara cada número do pipeline com o escrito no TCC e imprime `OK` ou `DIVERGE` | (só imprime) |

## Onde mudar uma decisão de tratamento

Tudo está em `config.py`: limite de acurácia (30 m), tamanho da célula (5 m), raio de preenchimento (15 m),
sessão usada, frequência e potência para a comparação com o espaço livre. Mude o valor, rode `python run_all.py`
e veja o efeito nos mapas e nos números. O `conferir_tcc.py` vai apontar o que deixou de bater com o texto.

## De onde vêm os dados

- `dados/wifi_mapper.db`: banco SQLite exportado pelo aplicativo de coleta Wi-Fi feito por um colega da turma.
  Tabelas usadas: `sessions`, `points` (posição e acurácia do GPS) e `measurements` (SSID, BSSID, RSSI, frequência).
- `dados/ssids_institucionais.csv`: lista de redes institucionais definida pelo autor (57 previstas, 52 observadas).
- `dados/registros_lora.csv`: os 33 registros válidos das campanhas de 30/09 e 05/10/2026, copiados do relatório
  da turma ("Testes dos primeiros dispositivos"). Foram digitados a partir do relatório, não gerados por código.
- `base/earth_campus.png`: captura de tela do Google Earth usada como fundo.

## O que este pipeline não faz (limites)

- **A coleta é manual.** O Wi-Fi vem de um aplicativo de celular; o LoRa, de mensagens enviadas à mão e
  anotadas em planilha. Não há ingestão automática, e o código não lê os rádios.
- **A extensão geográfica da imagem de satélite** (`EXTENSAO_BASE` em `config.py`) é um valor fixo. O passo 2
  confere a escala por uma barra de 200 m (diferença de 0,5%), mas não descobre a posição sozinho. A posição
  foi ajustada comparando as trilhas de medição com as vias e os caminhos visíveis na imagem (erro estimado de
  cerca de 5 m). Se trocar a imagem, é preciso informar a nova extensão e conferir o alinhamento.
- **A hipótese H2** (previsão por modelo de elevação) e **H3** (sobreposição do alcance LoRa ao mapa Wi-Fi)
  **não estão implementadas**. O passo 2 já salva a grade em `wifi_grade.npz` (RSSI, longitude, latitude)
  exatamente para essa sobreposição futura.
- **A parte de saltos da H1** não pode ser testada: todos os 33 registros são de salto único.
- **A potência de transmissão** (22 a 28 dBm) e a **frequência** (915 MHz) vêm do relatório da turma e ainda
  precisam ser confirmadas contra a configuração real dos rádios (a região Meshtastic do Brasil é BR_902).
- Pontos sem nenhuma rede institucional **não entram no mapa de calor** (não têm RSSI para interpolar). Eles são
  contados à parte e desenhados como cruzes.

## Resultados de referência (rodada de 09/10/2026)

Wi-Fi: 854 pontos e 46.999 medições; 7% removidas por acurácia > 30 m; 20.734 medições institucionais em 52 redes
e 467 pontos de acesso; 752 pontos no mapa, cobrindo 81% do retângulo dos pontos; 27 pontos (3,5%) sem rede
institucional, todos na borda leste. LoRa: 33 registros, 58,2 a 386,3 m; Spearman distância × RSSI = −0,81 e
distância × SNR = −0,73; expoente de perda aparente ≈ 5,2.
