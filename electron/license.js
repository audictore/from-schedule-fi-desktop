const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { app } = require('electron');
const institutional = require('./institutional');

const API = 'https://www.fromindustries.com/api/license';
const LICENSE_FILE = () => path.join(app.getPath('userData'), 'license.json');
const MACHINE_FILE = () => path.join(app.getPath('userData'), '.machine-id');
const GRACE_DAYS = 30;

function getMachineId() {
  const f = MACHINE_FILE();
  if (fs.existsSync(f)) return fs.readFileSync(f, 'utf8').trim();
  const id = crypto.randomUUID();
  fs.writeFileSync(f, id, 'utf8');
  return id;
}

function readLicense() {
  const f = LICENSE_FILE();
  if (!fs.existsSync(f)) return null;
  try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; }
}

function saveLicense(data) {
  fs.writeFileSync(LICENSE_FILE(), JSON.stringify(data), 'utf8');
}

function removeLicense() {
  const f = LICENSE_FILE();
  if (fs.existsSync(f)) fs.unlinkSync(f);
}

async function getStatus() {
  const lic = readLicense();
  if (!lic) return { active: false };

  const instConfig = institutional.getConfig();
  const isInstitutional = !!instConfig?.apiToken;

  const daysSince = (Date.now() - (lic.lastValidated || 0)) / (1000 * 60 * 60 * 24);
  if (daysSince <= GRACE_DAYS) return { active: true, key: lic.key, email: lic.email, trial: false, institutional: isInstitutional };

  try {
    const r = await fetch(`${API}/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: lic.key, machineId: lic.machineId })
    });
    const data = await r.json();
    if (data.valid) {
      lic.lastValidated = Date.now();
      saveLicense(lic);
      return { active: true, key: lic.key, email: lic.email, trial: false };
    }
    removeLicense();
    return { active: false, error: 'Licencia revocada o expirada' };
  } catch {
    if (daysSince <= GRACE_DAYS * 2) return { active: true, key: lic.key, email: lic.email, trial: false };
    return { active: false, error: 'Sin conexión para validar' };
  }
}

async function activate(key) {
  const machineId = getMachineId();
  try {
    const r = await fetch(`${API}/activate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: key.trim().toUpperCase(), machineId })
    });
    const data = await r.json();
    if (data.valid) {
      saveLicense({ key: key.trim().toUpperCase(), machineId, email: data.email, lastValidated: Date.now() });
      if (data.institutional) {
        institutional.setConfig({ apiToken: data.apiToken, institutionName: data.institutionName });
      }
      return { active: true, email: data.email, institutional: !!data.institutional };
    }
    return { active: false, error: data.error || 'Clave inválida' };
  } catch (e) {
    return { active: false, error: 'Sin conexión a internet' };
  }
}

function deactivate() {
  removeLicense();
  return { active: false };
}

module.exports = { getStatus, activate, deactivate };
