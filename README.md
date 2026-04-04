<p align="center">
  <img src="assets/capa.png" alt="Capa do G-docs" width="100%">
</p>

# G-docs

Sistema desktop local para controle de recebimento de documentos empresariais.

Versao atual: `1.2.0`

O G-docs foi desenhado para substituir planilhas e controles manuais por um fluxo local, rastreavel e simples de operar. O foco do projeto continua sendo clareza operacional: cadastrar empresas, organizar documentos, controlar recebimentos por periodo e manter historico auditavel sem depender de servidor.

## Objetivo

Centralizar o acompanhamento de documentos por empresa, documento e periodo, permitindo saber com clareza:

- quais documentos precisam ser cobrados
- por qual meio cada documento costuma ser recebido
- quais itens estao pendentes, recebidos ou encerrados
- quais tipos seguem regra mensal, trimestral ou anual em janeiro
- quem realizou alteracoes relevantes no sistema

## Principais caracteristicas

- aplicacao desktop local em Python, Tkinter e SQLite
- banco separado da pasta instalada do programa
- autenticacao com perfis `admin` e `comum`
- logs administrativos de alteracoes relevantes
- observacao livre por empresa com ate 255 caracteres
- meios de recebimento vinculados a cada documento
- tipos com ocorrencia configuravel:
  - `Mensal`
  - `Trimestral`
  - `Anual em janeiro`
- status automatico `Nao cobrar` para meses fora da ocorrencia do tipo
- regra de encerramento que bloqueia meses posteriores
- importacao Excel com layouts atualizados e compatibilidade legada
- relatorio de pendencias em Excel
- backup e restauracao do banco pela interface
- vinculo opcional de pasta local por empresa

## Novidades da versao `1.2.0`

- observacao por empresa validada em servico, banco e interface
- meios de recebimento migrados de empresa para documento
- importacao completa atualizada para receber meio de recebimento por documento
- tipos com ocorrencia especial para documentos trimestrais e anuais
- grade de controle mostrando `Nao cobrar` automaticamente quando o tipo nao deve ser cobrado naquele mes
- painel de tipos atualizado para configurar a ocorrencia sem poluir a interface

## Fluxo principal de uso

1. Fazer login.
2. Cadastrar empresas manualmente ou importar por Excel.
3. Cadastrar documentos por empresa, definindo tipo e meios de recebimento.
4. Ajustar a ocorrencia do tipo quando necessario.
5. Gerar os periodos anuais de controle.
6. Consultar a empresa na aba `Controle`.
7. Atualizar os status permitidos para cada mes.
8. Exportar pendencias, consultar logs ou gerar backup quando necessario.

## Regras importantes

- empresa e unica por `codigo_empresa`
- documento e unico por `(empresa, tipo, nome_documento)`
- observacao de empresa aceita no maximo 255 caracteres
- meios de recebimento pertencem ao documento, nao mais a empresa
- tipo `Trimestral` libera apenas `01`, `04`, `07` e `10`
- tipo `Anual em janeiro` libera apenas `01`
- meses fora da ocorrencia aparecem como `Nao cobrar` e nao recebem edicao manual
- `Encerrado` continua removendo a exibicao/editabilidade dos meses posteriores
- consultas e relatorios aceitam no maximo 12 meses por vez

## Layouts de importacao

### Empresas

- `codigo_empresa`
- `nome_empresa`
- `email_contato`
- `nome_contato`
- `observacao`

Compatibilidade mantida com o layout legado de 2 colunas.

### Documentos

- `meios_recebimento`
- `nome_documento`
- `nome_tipo`

Compatibilidade mantida com o layout legado de 2 colunas (`nome_documento`, `nome_tipo`).

### Cadastro completo

- `codigo_empresa`
- `nome_empresa`
- `email_contato`
- `nome_contato`
- `meios_recebimento`
- `nome_documento`
- `nome_tipo`
- `observacao`

## Execucao local

Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe main.py
```

Para executar a suite principal de servicos:

```powershell
.\.venv\Scripts\python.exe -W default -m unittest tests.test_services
```

## Tecnologias utilizadas

- Python
- Tkinter
- SQLite
- openpyxl
- PyInstaller

## Estrutura da documentacao

Este `README` cobre a visao atual do produto. A documentacao tecnica detalhada continua na pasta [`docs/`](docs).

### Documentacao tecnica

- [1. Visao Geral Do Sistema](docs/01-visao-geral-do-sistema.md)
- [2. Estrutura De Pastas E Arquivos](docs/02-estrutura-de-pastas-e-arquivos.md)
- [3. Arquitetura Geral Do Projeto](docs/03-arquitetura-geral-do-projeto.md)
- [4. Hierarquia Das Classes](docs/04-hierarquia-das-classes.md)
- [5. Documentacao Completa Das Classes](docs/05-documentacao-completa-das-classes.md)
- [6. Documentacao Completa Das Funcoes E Metodos](docs/06-documentacao-completa-das-funcoes-e-metodos.md)
- [7. Relacionamento Entre Classes](docs/07-relacionamento-entre-classes.md)
- [8. Mapa De Chamadas Entre Classes E Modulos](docs/08-mapa-de-chamadas-entre-classes-e-modulos.md)
- [9. Fluxos Importantes Do Sistema](docs/09-fluxos-importantes-do-sistema.md)
- [10. Banco De Dados](docs/10-banco-de-dados.md)
- [11. Regras De Negocio](docs/11-regras-de-negocio.md)
- [12. Interface Do Sistema](docs/12-interface-do-sistema.md)
- [13. Dependencias E Bibliotecas Usadas](docs/13-dependencias-e-bibliotecas-usadas.md)
- [14. UML Textual / Diagrama Descritivo](docs/14-uml-textual-diagrama-descritivo.md)
- [15. Ordem Ideal Para Estudar O Projeto](docs/15-ordem-ideal-para-estudar-o-projeto.md)
- [16. Pontos De Melhoria E Refatoracao](docs/16-pontos-de-melhoria-e-refatoracao.md)
- [17. Resumo Final](docs/17-resumo-final.md)
- [18. Icones E Empacotamento Por Sistema Operacional](docs/18-icones-e-empacotamento-por-sistema-operacional.md)
- [19. Observacoes Importantes Para Git E Empacotamento](docs/19-observacoes-importantes-para-git-e-empacotamento.md)
- [20. Encerramento](docs/20-encerramento.md)
