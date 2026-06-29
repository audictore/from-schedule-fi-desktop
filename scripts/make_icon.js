#!/usr/bin/env node
// Genera assets/icon.ico y assets/icon.png desde el logo "Schedule FI YELLOW.svg".
// El logo amarillo va centrado sobre un cuadrado oscuro de marca (#221F20) para que
// se vea bien en cualquier fondo de Windows. Requiere sharp + png-to-ico (devDeps).
// Lo corre el pipeline de build después de `npm ci`.  Uso: node scripts/make_icon.js
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const pngToIco = require('png-to-ico');

const ROOT = path.join(__dirname, '..');
const SVG = path.join(ROOT, 'app', 'assets', 'Schedule FI YELLOW.svg');
const OUT_ICO = path.join(ROOT, 'assets', 'icon.ico');
const OUT_PNG = path.join(ROOT, 'assets', 'icon.png');
const BG = { r: 0x22, g: 0x1f, b: 0x20, alpha: 1 }; // #221F20

// Renderiza el SVG (a alta densidad para que quede nítido) centrado en un
// cuadrado oscuro del tamaño pedido, y devuelve el PNG como buffer.
async function lienzo(size) {
  const logo = await sharp(SVG, { density: 512 })
    .resize(Math.round(size * 0.66), Math.round(size * 0.66), {
      fit: 'contain',
      background: { r: 0, g: 0, b: 0, alpha: 0 }
    })
    .png()
    .toBuffer();
  return sharp({ create: { width: size, height: size, channels: 4, background: BG } })
    .composite([{ input: logo, gravity: 'center' }])
    .png()
    .toBuffer();
}

(async () => {
  fs.mkdirSync(path.join(ROOT, 'assets'), { recursive: true });
  const sizes = [256, 128, 64, 48, 32, 16];
  const pngs = await Promise.all(sizes.map(lienzo));
  fs.writeFileSync(OUT_ICO, await pngToIco(pngs));
  fs.writeFileSync(OUT_PNG, await lienzo(512));
  console.log('Ícono generado desde', path.basename(SVG), '→ assets/icon.ico, assets/icon.png');
})().catch((e) => { console.error('Error generando el ícono:', e); process.exit(1); });
