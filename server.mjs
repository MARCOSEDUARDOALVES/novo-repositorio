import express from 'express';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Servir arquivos estáticos da pasta atual
app.use(express.static(path.join(__dirname)));

// Rota principal que serve o index.html
app.get('*', (_req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Iniciar o servidor
app.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);

  const networks = os.networkInterfaces();
  const links = Object.values(networks)
    .flatMap((iface = []) => iface)
    .filter((address) => Boolean(address) && !address.internal && address.family === 'IPv4')
    .map((address) => `http://${address.address}:${PORT}`);

  if (links.length > 0) {
    console.log('Acesse pelo navegador em qualquer um dos endereços abaixo na mesma rede:');
    links.forEach((link) => console.log(`  • ${link}`));
  }

  console.log('Pressione Ctrl+C para encerrar o servidor');
});
