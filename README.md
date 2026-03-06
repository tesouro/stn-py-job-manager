# STN Job Manager

Gerenciador de jobs para execução de cargas SIORG em background.

Este projeto fornece um módulo Python para gerenciar a execução assíncrona de jobs, incluindo modelos de dados, armazenamento em memória e execução de scripts em background.

## Instalação

### Pré-requisitos

- Python >= 3.9

### Instalação diretamente do GitHub

```bash
pip install git+https://github.com/tesouro/stn-py-job-manager.git
```

### Instalação a partir do código fonte

1. Clone o repositório:
   ```bash
   git clone https://github.com/tesouro/stn-py-job-manager.git
   cd stn-py-job-manager
   ```

2. Instale as dependências:
   ```bash
   pip install -e .
   ```

## Uso

```python
from stn_job_manager import JobManager

# Exemplo de uso básico
manager = JobManager()
# Adicione código para criar e executar jobs
```

Para mais detalhes, consulte a documentação do módulo.

## Dependências

- pydantic >= 2.0.0

## Contribuição

Contribuições são bem-vindas! Por favor, abra uma issue ou envie um pull request no [repositório GitHub](https://github.com/tesouro/stn-py-job-manager).

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.