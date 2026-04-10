# STN Job Manager

Gerenciador de jobs para execução de cargas SIORG em background.

Este projeto fornece um módulo Python para gerenciar a execução assíncrona de jobs, incluindo modelos de dados, armazenamento em memória e execução de scripts Python em background via threads.

## Instalação

### Pré-requisitos

- Python >= 3.9

### Instalação diretamente do GitHub

```bash
pip install git+https://github.com/tesouro/stn-py-job-manager.git
```

### Instalação a partir do código fonte

```bash
git clone https://github.com/tesouro/stn-py-job-manager.git
cd stn-py-job-manager
pip install -e .
```

---

## Uso básico

```python
from stn_job_manager import JobManager

manager = JobManager(timeout=1800)  # timeout em segundos (padrão: 30 min)

# Inicia um job que executa o script scripts/carga_funcoes.py em background
job = manager.iniciar_carga(tipo="funcoes", script="scripts/carga_funcoes.py")
print(job.job_id)    # UUID gerado automaticamente
print(job.status)    # "pendente" → "executando" → "concluido" | "erro"

# Consulta o status de um job pelo ID
job = manager.consultar_job(job.job_id)
print(job.status)
print(job.saida)     # stdout + stderr do script

# Lista todos os jobs (mais recentes primeiro)
todos = manager.listar_jobs()
for j in todos:
    print(j.job_id, j.tipo, j.status)
```

### Instância global

O módulo já exporta uma instância pronta para uso direto em aplicações:

```python
from stn_job_manager import job_manager

job = job_manager.iniciar_carga(tipo="unidades", script="scripts/carga_unidades.py")
```

---

## Integração com Flask

### Instalação das dependências adicionais

```bash
pip install flask
```

### Exemplo completo de API REST


---

## Integração com FastAPI

### Instalação das dependências adicionais

```bash
pip install fastapi uvicorn
```

### Exemplo completo de API REST com FastAPI

```python
# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from stn_job_manager import job_manager, CargaInfo

app = FastAPI(title="STN Job Manager")

SCRIPTS: dict[str, str] = {
    "funcoes": "scripts/carga_funcoes.py",
    "unidades": "scripts/carga_unidades.py",
    "pessoas": "scripts/carga_pessoas.py",
}


class JobIniciado(BaseModel):
    job_id: str
    status: str


@app.post("/cargas/{tipo}", response_model=JobIniciado, status_code=202)
def iniciar_carga(tipo: str):
    """Inicia uma carga em background e retorna o job_id."""
    script = SCRIPTS.get(tipo)
    if script is None:
        raise HTTPException(status_code=400, detail=f"Tipo de carga desconhecido: {tipo}")

    job = job_manager.iniciar_carga(tipo=tipo, script=script)
    return JobIniciado(job_id=job.job_id, status=job.status)


@app.get("/cargas/{job_id}", response_model=CargaInfo)
def consultar_carga(job_id: str):
    """Retorna o status e a saída de um job específico."""
    job = job_manager.consultar_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


@app.get("/cargas", response_model=list[CargaInfo])
def listar_cargas():
    """Lista todos os jobs registrados, do mais recente ao mais antigo."""
    return job_manager.listar_jobs()
```

### Executando o servidor

```bash
uvicorn app:app --reload
```

### Testando os endpoints

```bash
# Inicia uma carga do tipo "funcoes"
curl -X POST http://localhost:8000/cargas/funcoes

# Consulta o status de um job (substitua <job_id> pelo valor retornado acima)
curl http://localhost:8000/cargas/<job_id>

# Lista todos os jobs
curl http://localhost:8000/cargas
```

> O FastAPI gera automaticamente a documentação interativa em `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/redoc`.

## Integração com Flask

```python
# app.py
from flask import Flask, jsonify, request
from stn_job_manager import job_manager

app = Flask(__name__)


@app.post("/cargas/<tipo>")
def iniciar_carga(tipo: str):
    """Inicia uma carga em background e retorna o job_id."""
    scripts = {
        "funcoes": "scripts/carga_funcoes.py",
        "unidades": "scripts/carga_unidades.py",
        "pessoas": "scripts/carga_pessoas.py",
    }

    script = scripts.get(tipo)
    if script is None:
        return jsonify({"erro": f"Tipo de carga desconhecido: {tipo}"}), 400

    job = job_manager.iniciar_carga(tipo=tipo, script=script)
    return jsonify({"job_id": job.job_id, "status": job.status}), 202


@app.get("/cargas/<job_id>")
def consultar_carga(job_id: str):
    """Retorna o status e a saída de um job específico."""
    job = job_manager.consultar_job(job_id)
    if job is None:
        return jsonify({"erro": "Job não encontrado"}), 404

    return jsonify({
        "job_id": job.job_id,
        "tipo": job.tipo,
        "status": job.status,
        "inicio": job.inicio.isoformat(),
        "fim": job.fim.isoformat() if job.fim else None,
        "saida": job.saida,
    })


@app.get("/cargas")
def listar_cargas():
    """Lista todos os jobs registrados, do mais recente ao mais antigo."""
    jobs = job_manager.listar_jobs()
    return jsonify([
        {
            "job_id": j.job_id,
            "tipo": j.tipo,
            "status": j.status,
            "inicio": j.inicio.isoformat(),
            "fim": j.fim.isoformat() if j.fim else None,
        }
        for j in jobs
    ])


if __name__ == "__main__":
    app.run(debug=True)
```

### Testando os endpoints

```bash
# Inicia uma carga do tipo "funcoes"
curl -X POST http://localhost:5000/cargas/funcoes

# Consulta o status de um job (substitua <job_id> pelo valor retornado acima)
curl http://localhost:5000/cargas/<job_id>

# Lista todos os jobs
curl http://localhost:5000/cargas
```

### Exemplo de resposta

`POST /cargas/funcoes` → `202 Accepted`
```json
{
  "job_id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
  "status": "pendente"
}
```

`GET /cargas/e3b0c442-98fc-1c14-9afb-f4c8996fb924`
```json
{
  "job_id": "e3b0c442-98fc-1c14-9afb-f4c8996fb924",
  "tipo": "funcoes",
  "status": "concluido",
  "inicio": "2026-04-10T14:00:00.000000",
  "fim": "2026-04-10T14:01:23.456789",
  "saida": "Carga concluída com sucesso.\n"
}
```

---

## Referência da API

### `JobManager(timeout=1800)`

| Método | Descrição |
|---|---|
| `iniciar_carga(tipo, script)` | Cria um job e executa o script em background. Retorna `CargaInfo`. |
| `consultar_job(job_id)` | Retorna o `CargaInfo` do job ou `None` se não encontrado. |
| `listar_jobs()` | Retorna todos os jobs ordenados do mais recente para o mais antigo. |

### `CargaInfo`

| Campo | Tipo | Descrição |
|---|---|---|
| `job_id` | `str` | UUID único do job |
| `tipo` | `str` | Tipo da carga (ex: `"funcoes"`) |
| `status` | `StatusCarga` | Status atual do job |
| `inicio` | `datetime` | Data/hora de criação |
| `fim` | `datetime \| None` | Data/hora de conclusão |
| `saida` | `str \| None` | Saída combinada (stdout + stderr) do script |

### `StatusCarga` (enum)

| Valor | Descrição |
|---|---|
| `pendente` | Job criado, aguardando execução |
| `executando` | Script em execução |
| `concluido` | Script finalizado com código 0 |
| `erro` | Script falhou ou timeout excedido |

---

## Dependências

- [pydantic](https://docs.pydantic.dev/) >= 2.0.0

## Contribuição

Contribuições são bem-vindas! Por favor, abra uma issue ou envie um pull request no [repositório GitHub](https://github.com/tesouro/stn-py-job-manager).

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.