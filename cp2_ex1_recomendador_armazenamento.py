"""
exercicio 1 - assistente de decisao de armazenamento

recebe o perfil de um conjunto de dados e devolve qual banco usar,
qual lado do cap priorizar e qual risco owasp a escolha errada cria
"""


def recomendar(perfil):
    schema_fixo = perfil["schema_fixo"]
    precisa_acid = perfil["precisa_acid"]
    escala_horizontal = perfil["escala_horizontal"]
    tolera_atraso = perfil["tolera_atraso_de_consistencia"]
    dado_sensivel = perfil["dado_sensivel"]

   
    banco = "MySQL" if precisa_acid else "MongoDB"

    # se o sistema aguenta ficar um pouco desatualizado da pra trocar
    # consistencia por disponibilidade
    cap = "AP" if tolera_atraso else "CP"

    
    if precisa_acid:
        motivo_cap = "perder uma transacao pela metade e pior que a escrita demorar mais"
    elif escala_horizontal and tolera_atraso:
        motivo_cap = "recusar escrita por causa de particionamento e pior que aceitar com atraso pequeno"
    else:
        motivo_cap = "aceitar dado inconsistente aqui custa mais caro que recusar escrita na hora da particao"

    # risco owasp que a escolha errada abriria, e o erro que seria inaceitavel
    if dado_sensivel and precisa_acid:
        risco_owasp = "A07"
        erro_inaceitavel = "autenticar alguem com uma credencial que ja devia estar revogada"
    elif dado_sensivel and not tolera_atraso:
        risco_owasp = "A08"
        erro_inaceitavel = "um registro que diverge entre replicas nao serve como prova de nada"
    elif dado_sensivel:
      
        risco_owasp = "A04"
        erro_inaceitavel = "dado sensivel espalhado em varias replicas so pra ganhar disponibilidade aumenta a chance de vazamento"
    elif precisa_acid:
        risco_owasp = "A08"
        erro_inaceitavel = "uma transacao que confirma pela metade corrompe o dado que devia ser fonte da verdade"
    else:
        risco_owasp = "A09"
        erro_inaceitavel = "desligar o log pra nao perder performance e o mesmo que nao ter log quando o incidente acontecer"

    justificativa = f"{motivo_cap}; por isso {erro_inaceitavel}"

    return {
        "banco": banco,
        "cap": cap,
        "justificativa": justificativa,
        "risco_owasp": risco_owasp,
    }


if __name__ == "__main__":
    perfis = {
        "credenciais_do_SOC": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
        "telemetria_de_sensores": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": False},
        "trilha_de_auditoria": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
        "carrinho_de_licencas": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": False},
        "cache_de_sessoes": {"schema_fixo": True, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": True},
    }

    for nome, perfil in perfis.items():
        r = recomendar(perfil)
        print(f"{nome:24s} -> {r['banco']:7s} | {r['cap']} | \"{r['justificativa']}\" | {r['risco_owasp']}")
