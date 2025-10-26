# Hypercompressor

Hypercompressor é um projeto em estágio inicial para construir um compactador de arquivos de última geração, inspirado em ferramentas como WinRAR, mas com foco em modularidade, paralelismo e extensibilidade para algoritmos modernos.

## Objetivos do projeto

- **Alto poder de compactação**: arquitetura preparada para receber múltiplos codecs e técnicas híbridas.
- **Performance**: processamento em fluxo e paralelismo por blocos.
- **Extensibilidade**: interface clara para adicionar novos algoritmos e estratégias de otimização.

## Estrutura do repositório

```
.
├── pyproject.toml          # Configuração do pacote e dependências
├── src/
│   └── hypercompressor/
│       ├── __init__.py
│       ├── cli.py          # Interface de linha de comando
│       ├── core.py         # Núcleo de compressão com pipeline modular
│       └── strategies.py   # Estratégias e codecs disponíveis
└── tests/
    └── test_roundtrip.py   # Testes de compressão/descompressão
```

## Como usar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
hypercompress compress arquivo.txt arquivo.hcz
hypercompress decompress arquivo.hcz arquivo_recuperado.txt
```

## Próximos passos

1. Implementar novos codecs de alta performance (ex: Zstandard, Brotli, LZ4).
2. Adicionar heurísticas para escolha dinâmica do melhor codec.
3. Desenvolver interface gráfica e APIs para integração em outros sistemas.
4. Criar benchmarks automatizados comparando com packers tradicionais.

Contribuições são bem-vindas! Abra issues com ideias e relatórios de bugs.
