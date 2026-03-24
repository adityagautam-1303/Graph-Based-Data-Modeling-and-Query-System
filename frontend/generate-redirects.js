import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// This script generates the _redirects file for Netlify using an environment variable.
// Set BACKEND_URL in your Netlify dashboard (e.g., https://your-backend.onrender.com)

const backendUrl = process.env.BACKEND_URL;

if (!backendUrl) {
  console.error('ERROR: BACKEND_URL environment variable is not set.');
  process.exit(1);
}

const redirectsContent = `# Netlify Redirects - Generated at build time
/api/*  ${backendUrl.replace(/\/$/, '')}/api/:splat  200
`;

const outputPath = path.join(__dirname, 'public', '_redirects');

try {
  fs.writeFileSync(outputPath, redirectsContent);
  console.log(`Successfully generated _redirects at ${outputPath}`);
} catch (err) {
  console.error('Error writing _redirects file:', err);
  process.exit(1);
}
