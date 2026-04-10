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
from typing import Optional, Union

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
    
    def __init__(self, timeout: int = 1800):
        """
        Inicializa o gerenciador de jobs.
        
        Args:
            timeout: Timeout em segundos para execução de cada script (padrão: 30 min)
        """
        self._jobs: dict[str, CargaInfo] = {}
        self._timeout = timeout
    
    def _rodar_script(self, script: str, job_id: str) -> None:
        """Executa um script Python como subprocess e atualiza o job."""
        job = self._jobs[job_id]
        job.status = StatusCarga.EXECUTANDO

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
    
    def _rodar_funcao(self, fn: Callable[[], None], job_id: str) -> None:
        """Executa uma função Python em thread e captura stdout/stderr."""
        job = self._jobs[job_id]
        job.status = StatusCarga.EXECUTANDO
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
        self._jobs[job_id] = job

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
        return self._jobs.get(job_id)
    
    def listar_jobs(self) -> list[CargaInfo]:
        """
        Lista todos os jobs já disparados.
        
        Returns:
            Lista de jobs ordenados do mais recente para o mais antigo
        """
        return sorted(self._jobs.values(), key=lambda j: j.inicio, reverse=True)


# ---------------------------------------------------------------------------
# Instância global
# ---------------------------------------------------------------------------

# Instância única do gerenciador de jobs para uso na API
job_manager = JobManager()
