# Controle de Investimentos para Aposentadoria

Aplicação desktop nativa para acompanhamento de investimentos com foco em atingir suas metas financeiras com inteligência.

![Interface do Software](primeira-tela-software.png)

## 🚀 Guia Rápido para Iniciantes

Se você é novo no aplicativo, aqui está como ele funciona de forma simples:

### 1. Configure sua Meta
Clique no ícone de **engrenagem** no topo. Defina quanto você quer ter no futuro, quanto já tem hoje e em quantos meses quer chegar lá. O sistema calculará automaticamente quanto você precisa poupar por mês.

### 2. Cadastre seus Ativos (Onde está o dinheiro)
Use o botão **"+ Novo Ativo"** para listar suas contas (Ex: Poupança, Tesouro Direto, CDB). 
- O **Saldo Atual** é o que mostra quão perto você está do seu objetivo final. 
- Você não precisa atualizar isso todo dia! Pode atualizar uma vez por mês ou a cada três meses.

### 3. Registre seus Aportes (Seu compromisso mensal)
Sempre que você investir dinheiro novo, clique em **"+ Registrar Aporte"**. 
- Isso serve para o sistema saber que você cumpriu sua parte no mês.
- A barra de progresso no topo ficará verde quando você atingir sua meta de economia mensal.

### 4. Entenda o Gráfico
- **Linha Azul**: O caminho ideal para bater sua meta.
- **Linha Amarela (Pontilhada)**: Onde seu dinheiro *deveria* estar se você fizer os aportes e a rentabilidade for a esperada.
- **Linha Verde**: Onde seu dinheiro *realmente* está (baseado nas suas atualizações de Ativos).

---

## 🛠️ Como Executar (Para Desenvolvedores)
...

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
