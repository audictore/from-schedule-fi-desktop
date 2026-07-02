const fs = require('fs');
const path = require('path');
const { app } = require('electron');

const API = 'https://www.fromindustries.com/api/institutional';
const CONFIG_FILE = () => path.join(app.getPath('userData'), 'institutional.json');

function readConfig() {
  const f = CONFIG_FILE();
  if (!fs.existsSync(f)) return null;
  try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; }
}

function saveConfig(data) {
  const existing = readConfig() || {};
  fs.writeFileSync(CONFIG_FILE(), JSON.stringify({ ...existing, ...data }), 'utf8');
}

function getConfig() {
  return readConfig();
}

function setConfig({ campus, apiToken, institutionName }) {
  const update = {};
  if (campus) update.campus = campus;
  if (apiToken) update.apiToken = apiToken;
  if (institutionName) update.institutionName = institutionName;
  saveConfig(update);
  return readConfig();
}

async function publish(horario, periodo) {
  const config = readConfig();
  if (!config?.apiToken) return { ok: false, error: 'No hay token institucional configurado' };
  if (!config.campus) return { ok: false, error: 'Falta configurar el campus' };

  try {
    const r = await fetch(`${API}/publish`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.apiToken}`
      },
      body: JSON.stringify({
        campus: config.campus,
        periodo,
        publishedBy: config.institutionName || null,
        horario: horario.horario,
        metadata: {
          colocadas: horario.colocadas,
          total: horario.total,
          optimo: horario.optimo,
          huecos: horario.huecos
        }
      })
    });
    const data = await r.json();
    if (r.ok) return { ok: true, ...data };
    return { ok: false, error: data.error || 'Error al publicar' };
  } catch (e) {
    return { ok: false, error: 'Sin conexión a internet' };
  }
}

module.exports = { getConfig, setConfig, publish };
