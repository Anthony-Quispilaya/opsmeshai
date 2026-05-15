#!/usr/bin/env node
import net from 'net';

async function findAvailablePort(startPort = 3000, maxAttempts = 100) {
  for (let i = 0; i < maxAttempts; i++) {
    const port = startPort + i;
    const isAvailable = await isPortAvailable(port);
    if (isAvailable) {
      return port;
    }
  }
  throw new Error(`No available ports found starting from ${startPort}`);
}

function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close();
      resolve(true);
    });
    server.listen(port, '127.0.0.1');
  });
}

async function main() {
  try {
    const frontendPort = await findAvailablePort(3000);
    const backendPort = await findAvailablePort(8000);
    
    console.log(JSON.stringify({
      frontend: frontendPort,
      backend: backendPort,
      app_url: `http://localhost:${frontendPort}`,
      api_url: `http://localhost:${backendPort}`
    }));
  } catch (err) {
    console.error('Error finding available ports:', err.message);
    process.exit(1);
  }
}

main();
