FROM python:3.12-slim

# Dependências do sistema para Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libcairo2 libx11-6 \
    fonts-liberation libappindicator3-1 lsb-release xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala somente o Chromium (menor que instalar todos os browsers)
RUN playwright install chromium && playwright install-deps chromium

COPY . .

# Cria diretórios de saída com permissões corretas
RUN mkdir -p logs screenshots exports && chmod 777 logs screenshots exports

# Usuário sem privilégios de root
RUN useradd -m -u 1000 efisco
USER efisco

ENTRYPOINT ["python", "main.py"]
CMD []
