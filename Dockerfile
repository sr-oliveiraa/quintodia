# Use a imagem oficial do Python como base
FROM python:3.9-slim

# Defina o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copie o arquivo requirements.txt para o diretório de trabalho
COPY requirements.txt .

# Instale as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação para o diretório de trabalho
COPY . .

# Exponha a porta em que a aplicação Flask será executada
EXPOSE 5000

# Defina a variável de ambiente para desativar o buffer de saída
ENV PYTHONUNBUFFERED=1

# Comando para iniciar a aplicação Flask
CMD ["python", "app.py"]
