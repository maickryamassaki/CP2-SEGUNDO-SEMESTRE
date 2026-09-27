"""
roteiro de teste do exercicio 9. precisa do cp2_ex9_api_rate_limit_anomalia.py
rodando em outro terminal antes de executar este script
"""

import time

import requests

BASE = "http://localhost:5005"


def bater(ip, rota="/api/incidentes"):
    return requests.get(f"{BASE}{rota}", headers={"X-Forwarded-For": ip})


def main():
    ip_normal = "192.168.1.10"
    ips_normais_extra = ["192.168.1.11", "192.168.1.12", "192.168.1.13"]
    ip_hostil = "185.220.101.1"

    # ip normal: poucas requisicoes 
    for _ in range(5):
        r = bater(ip_normal)
        time.sleep(0.5)
    print(f"ip normal ({ip_normal}) terminou com status {r.status_code}")

    # ips normais extras: mesmo padrao, so pra dar ao IsolationForest mais
    # de um ponto de referencia "normal" (com so 2 grupos no total a
    # contaminacao de 0.2 fica instavel e pode nao marcar ninguem)
    for ip in ips_normais_extra:
        for _ in range(5):
            r = bater(ip)
            time.sleep(0.5)
        print(f"ip normal ({ip}) terminou com status {r.status_code}")

    # ip hostil: rajada rapida, boa parte em rota que nao existe
    for i in range(60):
        rota = "/api/rota-que-nao-existe" if i % 3 != 0 else "/api/incidentes"
        r = bater(ip_hostil, rota)
    print(f"ip hostil ({ip_hostil}) terminou rajada com status {r.status_code}")

    # dispara a analise
    resultado = requests.post(f"{BASE}/api/analisar")
    print("bloqueados apos analise:", resultado.json())

    # proxima requisicao do ip hostil deve tomar 429
    r = bater(ip_hostil)
    print(f"\nProxima requisicao de {ip_hostil} -> {r.status_code}")
    if r.status_code == 429:
        print(f"Retry-After: {r.headers.get('Retry-After')}")


if __name__ == "__main__":
    main()