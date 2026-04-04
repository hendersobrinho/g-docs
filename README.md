<p align="center">
  <img src="assets/capa.png" alt="Capa do G-docs" width="100%">
</p>

# G-docs

Sistema desktop local para controle de recebimento de documentos empresariais.

Versao atual: `1.2.0`

O projeto foi pensado para substituir planilhas e controles manuais por um fluxo local, auditavel e simples de operar. O foco e manter o uso direto no escritorio: cadastro de empresas, documentos por tipo, controle mensal de recebimento, relatorio de pendencias e backup do banco sem depender de servidor.

## Visao geral

O G-docs permite:

- cadastrar e manter empresas
- cadastrar documentos por empresa e por tipo
- vincular meios de recebimento por documento
- controlar status por periodo
- aplicar regras de ocorrencia mensal, trimestral e anual em janeiro
- exportar pendencias em Excel
- manter logs administrativos
- gerar backup e restaurar o banco pela interface

## Principais recursos

- aplicacao desktop em Python, Tkinter e SQLite
- banco local separado da pasta instalada do programa
- autenticacao com perfis `admin` e `comum`
- login lembrado por perfil do computador, com expiracao de `60` dias e rotacao do token
- logs de alteracoes relevantes
- observacao por empresa com ate `255` caracteres
- status automatico `Nao cobrar` para meses fora da ocorrencia do tipo
- regra de encerramento que bloqueia meses posteriores
- importacao e exportacao em Excel
- build com `PyInstaller`
- instalador Windows com `Inno Setup`

## Requisitos

### Desenvolvimento e execucao local

- Python `3.10+`
- `tkinter` disponivel no ambiente Python
- dependencias do `requirements.txt`

### Dependencias Python

- `openpyxl`
- `Pillow`
- `PyInstaller`

### Dependencias opcionais por ambiente

- `python3-tk` em distribuicoes Linux que nao trazem `tkinter` por padrao
- `python3-gi` ou `xrandr` para melhorar deteccao de tela no Linux
- `cairosvg` para renderizar `icon.svg` diretamente ao gerar os icones
- `Inno Setup` para gerar o instalador Windows

## Instalacao do ambiente

### Linux / macOS

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Execucao local

### Linux / macOS

```bash
.venv/bin/python main.py
```

### Windows PowerShell

```powershell
.\.venv\Scripts\python.exe main.py
```

## Primeiro acesso

Em um banco novo, o sistema cria automaticamente um usuario inicial:

- usuario: `admin`
- senha: `admin`

Recomendacao importante:

- altere essa senha imediatamente apos o primeiro login

## Testes

### Suite principal

```bash
python -m unittest tests.test_services tests.test_storage tests.test_resources tests.test_display
```

### Apenas servicos

```bash
python -m unittest tests.test_services
```

## Empacotamento

Os builds devem ser gerados no proprio sistema operacional de destino.

### Linux

```bash
bash scripts/build_release.sh
```

Saidas esperadas:

- build PyInstaller: `dist/G-docs/`
- pacote versionado: `dist_release/G-docs-linux-<arquitetura>-v<versao>.tar.gz`

### macOS

```bash
bash scripts/build_release.sh
```

Saidas esperadas:

- build PyInstaller: `dist/G-docs/`
- pacote versionado: `dist_release/G-docs-macos-<arquitetura>-v<versao>.tar.gz`

### Windows

```powershell
scripts\build_release.bat
```

Saidas esperadas:

- build PyInstaller: `dist\G-docs\`
- pacote versionado: `dist_release\G-docs-win64-v<versao>.zip`
- se o `Inno Setup` estiver no `PATH`, o script tambem tenta gerar o instalador

### Pular testes no build

Por padrao, os scripts de release executam os testes antes do empacotamento.

#### Linux / macOS

```bash
RUN_TESTS=0 bash scripts/build_release.sh
```

#### Windows PowerShell

```powershell
$env:RUN_TESTS=0
scripts\build_release.bat
```

## Estrutura do projeto

```text
.
├── main.py
├── README.md
├── requirements.txt
├── documentos_empresa_app.spec
├── assets/
├── docs/
├── installer/
├── scripts/
├── tests/
└── documentos_empresa_app/
    ├── app_context.py
    ├── database/
    ├── models/
    ├── services/
    ├── ui/
    └── utils/
```

## Pastas principais

- `documentos_empresa_app/`: codigo-fonte da aplicacao
- `documentos_empresa_app/database/`: conexao, repositorios e schema SQLite
- `documentos_empresa_app/services/`: regras de negocio
- `documentos_empresa_app/ui/`: interface Tkinter
- `documentos_empresa_app/utils/`: constantes, seguranca, recursos e helpers
- `scripts/`: build e geracao de icones
- `installer/`: script do Inno Setup para Windows
- `tests/`: testes automatizados
- `docs/`: documentacao tecnica detalhada

## Arquivos de release importantes

- `documentos_empresa_app.spec`: receita do `PyInstaller`
- `scripts/build_release.sh`: build Linux/macOS com pacote `.tar.gz`
- `scripts/build_release.bat`: build Windows com `.zip` e tentativa opcional de instalador
- `installer/G-docs.iss`: instalador Windows
- `scripts/generate_icons.py`: gera `icon.png`, `icon.ico` e `icon.icns`

## Banco e seguranca

- o banco e SQLite local
- o caminho do banco e salvo no perfil do usuario do computador
- o login lembrado e local ao perfil do sistema operacional
- a credencial lembrada expira em `60` dias sem uso
- o token lembrado e renovado automaticamente a cada autenticacao bem-sucedida
- backups restaurados precisam conter a estrutura esperada do sistema

## Fluxo principal de uso

1. Fazer login.
2. Cadastrar empresas manualmente ou por importacao.
3. Cadastrar documentos por empresa.
4. Definir ou revisar tipos e meios de recebimento.
5. Gerar os periodos do ano.
6. Controlar os status na aba `Controle`.
7. Exportar pendencias ou consultar logs quando necessario.
8. Gerar backup periodicamente.

## Regras de negocio principais

- empresa e unica por `codigo_empresa`
- documento e unico por `(empresa, tipo_documento, nome_documento)`
- consultas e relatorios aceitam no maximo `12` meses por vez
- tipos podem ser `Mensal`, `Trimestral` ou `Anual em janeiro`
- meses fora da ocorrencia aparecem como `Nao cobrar`
- `Encerrado` bloqueia meses posteriores do documento

## Documentacao tecnica

Os documentos detalhados continuam na pasta [`docs/`](docs). Os mais importantes para manutencao e distribuicao sao:

- [Estrutura de pastas e arquivos](docs/02-estrutura-de-pastas-e-arquivos.md)
- [Banco de dados](docs/10-banco-de-dados.md)
- [Dependencias e bibliotecas](docs/13-dependencias-e-bibliotecas-usadas.md)
- [Icones e empacotamento](docs/18-icones-e-empacotamento-por-sistema-operacional.md)
- [Git e empacotamento](docs/19-observacoes-importantes-para-git-e-empacotamento.md)

## O que nao deve ir para o Git

- bancos locais
- artefatos de build (`build/`, `dist/`, `dist_release/`, `dist_installer/`)
- ambientes virtuais
- caches
- planilhas exportadas localmente

## Status desta revisao

- build Linux validado localmente
- scripts de release revisados para Linux/macOS e Windows
- `.gitignore` ampliado para artefatos de release e arquivos SQLite auxiliares
- README refeito para uso, manutencao e distribuicao
