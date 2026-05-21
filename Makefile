.PHONY: setup run build clean help

# Variáveis
VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

help:
	@echo "Comandos disponíveis:"
	@echo "  make setup   - Cria o ambiente virtual e instala as dependências"
	@echo "  make run     - Executa a aplicação"
	@echo "  make build   - Gera o executável standalone usando PyInstaller"
	@echo "  make clean   - Remove arquivos temporários e o ambiente virtual"

setup: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	@echo "Criando ambiente virtual com acesso a pacotes do sistema (necessário para GTK)..."
	rm -rf $(VENV)
	python3 -m venv --system-site-packages $(VENV) || (echo "ERRO: Falha ao criar venv. Verifique se o pacote 'python3-venv' está instalado." && exit 1)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

run: setup
	$(PYTHON) app.py

build: setup
	$(PYTHON) -m PyInstaller --onefile --windowed --add-data "templates:templates" --add-data "static:static" app.py

clean:
	rm -rf $(VENV)
	rm -rf build dist
	rm -f *.spec
	find . -type d -name "__pycache__" -exec rm -rf {} +
