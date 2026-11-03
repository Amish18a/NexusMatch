FROM node:20-alpine
WORKDIR /web
COPY Phase3/frontend/package.json ./package.json
RUN npm install
COPY Phase3/frontend ./
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
