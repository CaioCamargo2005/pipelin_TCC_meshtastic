"""Executa o pipeline completo, na ordem: 01 -> 02 -> 03 -> 04 -> conferência com o TCC."""
import subprocess
import sys

for passo in ["01_wifi_limpeza.py", "02_wifi_mapa.py", "03_lora_analise.py", "04_sobreposicao.py", "conferir_tcc.py"]:
    print(f"\n===== {passo} =====", flush=True)
    r = subprocess.run([sys.executable, passo], stdout=subprocess.DEVNULL if passo != "conferir_tcc.py" else None)
    if r.returncode != 0:
        sys.exit(f"Falhou em {passo}")
print("\nPipeline concluído. Resultados em saida/.")
