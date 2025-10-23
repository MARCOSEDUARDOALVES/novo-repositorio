const express = require('express');
const fs = require('fs');
const path = require('path');
const os = require('os');

const app = express();
const PORT = process.env.PORT || 4000;
const buildPath = path.join(__dirname, 'build');
const hasBuild = fs.existsSync(buildPath);

app.use(express.json());
if (hasBuild) {
  app.use(express.static(buildPath));
}

app.get('*', (_req, res) => {
  if (!hasBuild) {
    res.status(503).send(
      '<h1>Build ausente</h1><p>Execute "npm run build" antes de iniciar o servidor Express.</p>'
    );
    return;
  }

  res.sendFile(path.join(buildPath, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Servidor rodando em http://localhost:${PORT}`);

  if (!hasBuild) {
    console.warn('⚠️ Nenhum build React encontrado. Rode "npm run build" para gerar os arquivos estáticos.');
  }

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
