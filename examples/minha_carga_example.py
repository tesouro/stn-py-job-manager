import time
from stn_job_manager import JobManager


def minha_carga():
    print("Minha carga começou")
    for i in range(3):
        print(f"Passo {i+1}")
        time.sleep(1)
    print("Minha carga terminou")


def main():
    manager = JobManager()

    # Inicia um job usando uma função callable
    job1 = manager.iniciar_job(tipo="custom", script=minha_carga)
    print("Job callable iniciado:", job1.job_id)

    # Inicia um job usando um script externo
    job2 = manager.iniciar_job(tipo="funcoes", script="scripts/carga_funcoes.py")
    print("Job script iniciado:", job2.job_id)

    # Poll simples até concluir
    while True:
        j1 = manager.consultar_job(job1.job_id)
        j2 = manager.consultar_job(job2.job_id)
        status1 = j1.status if j1 else "desconhecido"
        status2 = j2.status if j2 else "desconhecido"
        print(f"Status -> job1: {status1}, job2: {status2}")
        if (j1 and j1.fim) and (j2 and j2.fim):
            break
        time.sleep(0.5)

    print("\n--- Resultado final ---")
    print("Job1 saída:\n", j1.saida)
    print("Job2 saída:\n", j2.saida)


if __name__ == "__main__":
    main()
