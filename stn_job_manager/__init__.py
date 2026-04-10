"""
Gerenciador de jobs para execução de cargas SIORG em background.

Este módulo encapsula toda a lógica de gerenciamento de jobs assíncronos,
incluindo modelos, armazenamento em memória e execução de scripts.
"""

import contextlib
import io
import subprocess
import sys
import uuid
import datetime
import threading
from collections.abc import Callable
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class StatusCarga(str, Enum):
    """Status possíveis de uma carga."""
    PENDENTE = "pendente"
    EXECUTANDO = "executando"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class CargaInfo(BaseModel):
    """Informações sobre um job de carga."""
    job_id: str
    tipo: str
    status: StatusCarga
    inicio: datetime.datetime
    fim: Optional[datetime.datetime] = None
    saida: Optional[str] = None


# ---------------------------------------------------------------------------
# Gerenciador de Jobs
# ---------------------------------------------------------------------------

class JobManager:
    """Gerencia a execução e o estado dos jobs de carga."""
    
    def __init__(
        self,
        timeout: int = 1800,
        redis_url: Optional[str] = None,
        redis_prefix: str = "stn_job_manager",
    ):
        """
        Inicializa o gerenciador de jobs.
        
        Args:
            timeout: Timeout em segundos para execução de cada script (padrão: 30 min)
            redis_url: URL do Redis para persistir jobs de forma compartilhada.
                       Se None, usa armazenamento em memória local (padrão).
            redis_prefix: Prefixo das chaves no Redis
        """
        self._jobs: dict[str, CargaInfo] = {}
        self._timeout = timeout
        self._redis: Optional[Any] = None
        self._redis_prefix = redis_prefix

        if redis_url:
            try:
                import redis
            except ImportError as exc:
                raise ImportError(
                    "Pacote redis não instalado. Instale com: pip install 'stn-job-manager[redis]'"
                ) from exc
            self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def _job_key(self, job_id: str) -> str:
        return f"{self._redis_prefix}:job:{job_id}"

    def _salvar_job(self, job: CargaInfo) -> None:
        if self._redis:
            self._redis.set(self._job_key(job.job_id), job.model_dump_json())
            return
        self._jobs[job.job_id] = job

    def _obter_job(self, job_id: str) -> Optional[CargaInfo]:
        if self._redis:
            raw = self._redis.get(self._job_key(job_id))
            if raw is None:
                return None
            return CargaInfo.model_validate_json(raw)
        return self._jobs.get(job_id)

    def _listar_todos_jobs(self) -> list[CargaInfo]:
        if self._redis:
            jobs: list[CargaInfo] = []
            for key in self._redis.scan_iter(match=f"{self._redis_prefix}:job:*"):
                raw = self._redis.get(key)
                if raw is None:
                    continue
                jobs.append(CargaInfo.model_validate_json(raw))
            return jobs
        return list(self._jobs.values())
    
    def _rodar_script(self, script: str, job_id: str) -> None:
        """Executa um script Python como subprocess e atualiza o job."""
        job = self._obter_job(job_id)
        if job is None:
            return
        job.status = StatusCarga.EXECUTANDO
        self._salvar_job(job)

        try:
            resultado = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            job.saida = resultado.stdout + resultado.stderr
            job.status = (
                StatusCarga.CONCLUIDO if resultado.returncode == 0 else StatusCarga.ERRO
            )
        except subprocess.TimeoutExpired:
            job.saida = f"ERRO: Timeout de {self._timeout // 60} minutos excedido."
            job.status = StatusCarga.ERRO
        except Exception as exc:
            job.saida = f"ERRO inesperado: {exc}"
            job.status = StatusCarga.ERRO
        finally:
            job.fim = datetime.datetime.now()
            self._salvar_job(job)
    
    def _rodar_funcao(self, fn: Callable[[], None], job_id: str) -> None:
        """Executa uma função Python em thread e captura stdout/stderr."""
        job = self._obter_job(job_id)
        if job is None:
            return
        job.status = StatusCarga.EXECUTANDO
        self._salvar_job(job)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                fn()
            job.saida = buf.getvalue()
            job.status = StatusCarga.CONCLUIDO
        except Exception as exc:
            job.saida = buf.getvalue() + f"\nERRO inesperado: {exc}"
            job.status = StatusCarga.ERRO
        finally:
            job.fim = datetime.datetime.now()
            self._salvar_job(job)

    def iniciar_job(self, tipo: str, script: Union[str, Callable[[], None]]) -> CargaInfo:
        """
        Cria um job e dispara a execução em uma thread.

        Args:
            tipo: Tipo da carga (ex: "funcoes", "unidades")
            script: Caminho para um script Python (.py) ou uma função callable
                    sem argumentos a ser executada em background.

        Returns:
            Informações do job criado
        """
        job_id = str(uuid.uuid4())
        job = CargaInfo(
            job_id=job_id,
            tipo=tipo,
            status=StatusCarga.PENDENTE,
            inicio=datetime.datetime.now(),
        )
        self._salvar_job(job)

        if callable(script):
            target, args = self._rodar_funcao, (script, job_id)
        else:
            target, args = self._rodar_script, (script, job_id)

        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

        return job

    def iniciar_carga(self, tipo: str, script: Union[str, Callable[[], None]]) -> CargaInfo:
        """Alias de iniciar_job mantido para retrocompatibilidade."""
        return self.iniciar_job(tipo=tipo, script=script)
    
    def consultar_job(self, job_id: str) -> Optional[CargaInfo]:
        """
        Consulta o status de um job pelo ID.
        
        Args:
            job_id: ID do job a ser consultado
            
        Returns:
            Informações do job ou None se não encontrado
        """
        return self._obter_job(job_id)
    
    def listar_jobs(self) -> list[CargaInfo]:
        """
        Lista todos os jobs já disparados.
        
        Returns:
            Lista de jobs ordenados do mais recente para o mais antigo
        """
        return sorted(self._listar_todos_jobs(), key=lambda j: j.inicio, reverse=True)


# ---------------------------------------------------------------------------
# Instância global
# ---------------------------------------------------------------------------

# Instância única do gerenciador de jobs para uso na API
job_manager = JobManager()
