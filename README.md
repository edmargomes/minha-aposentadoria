# Controle de Investimentos para Aposentadoria

Aplicação desktop nativa para acompanhamento de investimentos com foco em atingir R$ 100.000 em 5 anos.

## Funcionalidades
- Dashboard com métricas em tempo real.
- Gráfico de evolução com projeção ideal vs patrimônio real.
- Gerenciamento de investimentos (CRUD completo).
- Histórico de valores por investimento.
- Interface desktop nativa (PyWebView).

## Como Executar

O projeto utiliza um `Makefile` para automatizar as tarefas de configuração e execução.

### Pré-requisitos
- Python 3.8+
- Bibliotecas do sistema (Linux/Ubuntu/Debian):
  ```bash
  sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 libgirepository1.0-dev libcairo2-dev pkg-config python3-dev
  ```

### Comandos Principais

1. **Configurar o ambiente (Venv + Dependências):**
   ```bash
   make setup
   ```

2. **Executar a aplicação:**
   ```bash
   make run
   ```

3. **Gerar executável standalone:**
   ```bash
   make build
   ```

4. **Limpar arquivos temporários:**
   ```bash
   make clean
   ```
