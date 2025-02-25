# Use a imagem oficial do Node.js como base
FROM node:14

# Defina o diretório de trabalho dentro do contêiner
WORKDIR /usr/src/app



# Instale as dependências da aplicação
RUN npm install

# Copie o restante do código da aplicação para o diretório de trabalho
COPY . .

# Copie o arquivo .env para o diretório de trabalho
COPY .env ./

# Exponha a porta que a aplicação irá rodar
EXPOSE 3000

# Defina o comando para iniciar a aplicação
CMD ["npm", "start"]
