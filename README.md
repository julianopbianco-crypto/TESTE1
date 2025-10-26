# PowRAR

PowRAR é um compactador moderno inspirado em ferramentas como WinRAR, mas
projetado para entregar compressão agressiva e velocidade elevada em um
aplicativo com interface gráfica amigável.

## Recursos principais

- **Compactação poderosa**: utiliza o formato `.pwr`, baseado em `tar` + `LZMA`
  (XZ) com nível configurável de 0 a 9.
- **Interface moderna**: aplicação GUI escrita com `tkinter` e `ttk`, focada em
  usuários Windows.
- **Monitoramento em tempo real**: barra de progresso, status detalhado e
  possibilidade de cancelar operações longas.
- **Extração segura**: valida caminhos antes de extrair para evitar ataques de
  path traversal.

## Como executar

1. Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```

2. Instale o pacote em modo desenvolvimento:

   ```bash
   pip install -e .[dev]
   ```

3. Execute a interface gráfica:

   ```bash
   python -m powrar
   ```

## Uso básico

1. Adicione arquivos ou pastas com os botões "Adicionar arquivos" ou
   "Adicionar pasta".
2. Escolha o destino do arquivo `.pwr` e ajuste o nível de compactação.
3. Clique em **Compactar** para gerar o arquivo.
4. Use **Extrair** para abrir um arquivo `.pwr` existente e selecionar a pasta de
   destino.

## Testes automatizados

Execute a suíte de testes com:

```bash
pytest
```
