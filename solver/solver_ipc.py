#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CP-SAT solver — From Schedule FI Desktop (IPC stdin/stdout).
Modelo de una sola fase (igual que cp_horarios.py): completitud SUAVE (máx horas en
el objetivo), cero huecos de grupo DURO, escalón de días PA DURO, huecos PA ≤3 DURO.
Objetivo lexicográfico por pesos: 1º máx horas, 2º patrón didáctico, 3º huecos docente,
4º días parejos, 4b días flacos docente, 5º márgenes de jornada.
Emite líneas JSON: {"type":"progress",...} durante el solve y {"type":"result",...} al final."""
import json, sys, time, unicodedata, re, threading, os, pathlib
from collections import defaultdict
from ortools.sat.python import cp_model

DURMAX = 4

def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').upper()
def es_ing17(mat): u = norm(mat); return 'INGLES' in u and not re.search(r'INGLES\s*[89]', u)
def es_tut(mat): return 'TUTORIA' in norm(mat)
def max_ses(mat): return 3 if es_ing17(mat) else (2 if es_tut(mat) else 1)

def emit(tp, **kw):
    sys.stdout.write(json.dumps({'type': tp, **kw}, ensure_ascii=False) + '\n')
    sys.stdout.flush()

def progress_ticker(secs, stop):
    t0 = time.time()
    while not stop.wait(5):
        emit('progress', msg=f'Optimizando {time.time()-t0:.0f}/{secs}s…')

def resolver(D):
    ventanas, docentes, cargas = D['ventanas'], D['docentes'], D['cargas']
    DIAS = range(6)
    HREQ = sum(c['horas'] for c in cargas)
    max_time = int(D.get('maxTime') or 300)
    t0 = time.time()

    # Captura de entrada para depuración (no afecta al solve).
    try:
        dbg = pathlib.Path(os.path.dirname(os.path.abspath(__file__))) / 'last_input.json'
        dbg.write_text(json.dumps(D, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass
    sys.stderr.write(f'[solver] cargas={len(cargas)} docentes={len(docentes)} HREQ={HREQ} ventanas={ventanas}\n')
    sys.stderr.flush()

    emit('progress', msg=f'Construyendo modelo: {HREQ}h, {len(cargas)} cargas…')

    m = cp_model.CpModel()
    x = {}
    for i, c in enumerate(cargas):
        lo, hi = ventanas[c['turno']]; disp = docentes[c['docente']]['disponibilidad']
        for d in DIAS:
            dd = set(disp.get(str(d), []))
            for h in range(lo, hi):
                if h in dd: x[(i, d, h)] = m.NewBoolVar(f'x_{i}_{d}_{h}')

    # Horas colocadas por carga (≤ requeridas) y durMax horas/día.
    colocadas = []
    for i, c in enumerate(cargas):
        s = [x[(i, d, h)] for d in DIAS for h in range(*ventanas[c['turno']]) if (i, d, h) in x]
        m.Add(sum(s) <= c['horas']); colocadas.append(sum(s))
        for d in DIAS:
            sd = [x[(i, d, h)] for h in range(*ventanas[c['turno']]) if (i, d, h) in x]
            if sd: m.Add(sum(sd) <= DURMAX)

    porDoc, porGru = defaultdict(list), defaultdict(list)
    for i, c in enumerate(cargas):
        porDoc[c['docente']].append(i); porGru[c['grupo']].append(i)
    # No-solape docente y grupo.
    for idxs in list(porDoc.values()) + list(porGru.values()):
        for d in DIAS:
            for h in range(7, 21):
                t = [x[(i, d, h)] for i in idxs if (i, d, h) in x]
                if len(t) > 1: m.AddAtMostOne(t)

    # N sesiones/día (comienzos de bloque ≤ max_ses) + exceso (3.ª hora contigua).
    sesion_terms, exceso_terms = [], []
    for i, c in enumerate(cargas):
        lim = max_ses(c['materia']); lo, hi = ventanas[c['turno']]
        normal = not es_tut(c['materia'])
        for d in DIAS:
            inicios = []
            for h in range(lo, hi):
                if (i, d, h) not in x: continue
                ini = m.NewBoolVar(f'ini_{i}_{d}_{h}'); prev = x.get((i, d, h - 1))
                if prev is None: m.Add(ini == x[(i, d, h)])
                else: m.Add(ini <= x[(i, d, h)]); m.Add(ini <= 1 - prev); m.Add(ini >= x[(i, d, h)] - prev)
                inicios.append(ini)
            if inicios: m.Add(sum(inicios) <= lim)
            if normal:
                sesion_terms.extend(inicios)
                for h in range(lo + 2, hi):
                    if (i, d, h) in x and (i, d, h - 1) in x and (i, d, h - 2) in x:
                        e = m.NewBoolVar(f'exc_{i}_{d}_{h}')
                        m.Add(e >= x[(i, d, h)] + x[(i, d, h - 1)] + x[(i, d, h - 2)] - 2)
                        exceso_terms.append(e)
    # Bloques ≤ 2h DURO (materias normales).
    for e in exceso_terms: m.Add(e == 0)

    # Inglés simultáneo (2°/5°).
    sync = defaultdict(list)
    for i, c in enumerate(cargas):
        if c.get('sync'): sync[c['sync']].append(i)
    for idxs in sync.values():
        if len(idxs) < 2: continue
        for d in DIAS:
            for h in range(7, 21):
                vs = [x[(i, d, h)] for i in idxs if (i, d, h) in x]
                if len(vs) == len(idxs):
                    for k in range(1, len(vs)): m.Add(vs[0] == vs[k])
                else:
                    for v in vs: m.Add(v == 0)

    # Días por perfil (DURO, solo PA tipo=2). Si maxDias es menor que el mínimo físico
    # para las horas del docente, se corrige al alza (evita INFEASIBLE por dato imposible).
    # Escalón de días PA: PREFERENCIA fuerte (no DURA). Se respeta el maxDias del docente
    # siempre que sea posible, pero el solver puede excederlo (penalizado) si es la única
    # forma de colocar todas las horas sin huecos — equivale a conceder "+1 día" automático
    # solo donde hace falta. Prioridad: completitud ≫ escalón días ≫ calidad fina.
    maxdias_over_terms = []
    for doc, idxs in porDoc.items():
        md = docentes[doc].get('maxDias')
        if docentes[doc]['tipo'] != 2 or md is None: continue
        horas_doc = sum(cargas[i]['horas'] for i in idxs)
        slots_por_dia = {}
        for i in idxs:
            for d in DIAS:
                for h in range(7, 21):
                    if (i, d, h) in x:
                        slots_por_dia.setdefault(d, set()).add(h)
        dias_orden = sorted(slots_por_dia, key=lambda d: -len(slots_por_dia[d]))
        needed, acc = 0, 0
        for d in dias_orden:
            acc += len(slots_por_dia[d]); needed += 1
            if acc >= horas_doc: break
        if md < needed:
            sys.stderr.write(f'[solver] maxDias {doc}: {md} → {needed} (necesita {horas_doc}h)\n'); sys.stderr.flush()
            md = needed
        dias_doc = []
        for d in DIAS:
            slots = [x[(i, d, h)] for i in idxs for h in range(7, 21) if (i, d, h) in x]
            if not slots: continue
            y = m.NewBoolVar(f'act_{doc}_{d}')
            for v in slots: m.Add(y >= v)
            m.Add(y <= sum(slots)); dias_doc.append(y)
        if dias_doc:
            over = m.NewIntVar(0, 6, f'over_{doc}')
            m.Add(sum(dias_doc) <= md + over)
            maxdias_over_terms.append(over)

    # Huecos de grupo por (grupo, día): span(última−primera) − ocupadas.
    hueco_terms = []
    for g, idxs in porGru.items():
        turno = cargas[idxs[0]]['turno']; lo, hi = ventanas[turno]
        for d in DIAS:
            slots = {h: [x[(i, d, h)] for i in idxs if (i, d, h) in x] for h in range(lo, hi)}
            ocup = {h: m.NewBoolVar(f'oc_{g}_{d}_{h}') for h in range(lo, hi) if slots[h]}
            for h, ov in ocup.items(): m.Add(ov == sum(slots[h]))
            if len(ocup) < 2: continue
            prim = m.NewIntVar(lo, hi, f'pri_{g}_{d}'); ult = m.NewIntVar(lo, hi, f'ult_{g}_{d}')
            tiene = m.NewBoolVar(f'tie_{g}_{d}')
            m.Add(sum(ocup.values()) >= 1).OnlyEnforceIf(tiene)
            m.Add(sum(ocup.values()) == 0).OnlyEnforceIf(tiene.Not())
            for h, ov in ocup.items():
                m.Add(prim <= h).OnlyEnforceIf(ov); m.Add(ult >= h + 1).OnlyEnforceIf(ov)
            span = m.NewIntVar(0, hi - lo, f'span_{g}_{d}')
            m.Add(span == ult - prim).OnlyEnforceIf(tiene); m.Add(span == 0).OnlyEnforceIf(tiene.Not())
            hk = m.NewIntVar(0, hi - lo, f'hk_{g}_{d}')
            m.Add(hk == span - sum(ocup.values())); hueco_terms.append(hk)
    # Cero huecos de grupo (DURO) se añade en la Fase 2 (warm start).

    # Docente por (doc, día): huecos y días flacos (compartiendo horas/día y "abierto").
    MIN_HORAS_DOC = 3
    hueco_doc_terms, corto_doc_terms = [], []
    hueco_por_doc = defaultdict(list)
    for doc, idxs in porDoc.items():
        for d in DIAS:
            slots = {h: [x[(i, d, h)] for i in idxs if (i, d, h) in x] for h in range(7, 21)}
            ocup = {h: m.NewBoolVar(f'od_{doc}_{d}_{h}') for h in range(7, 21) if slots[h]}
            for h, ov in ocup.items(): m.Add(ov == sum(slots[h]))
            if not ocup: continue
            horas_dd = m.NewIntVar(0, 14, f'hdd_{doc}_{d}'); m.Add(horas_dd == sum(ocup.values()))
            tiene = m.NewBoolVar(f'dti_{doc}_{d}')
            m.Add(horas_dd >= 1).OnlyEnforceIf(tiene); m.Add(horas_dd == 0).OnlyEnforceIf(tiene.Not())
            corto_d = m.NewIntVar(0, MIN_HORAS_DOC, f'crd_{doc}_{d}')
            m.Add(corto_d >= MIN_HORAS_DOC - horas_dd - MIN_HORAS_DOC * (1 - tiene))
            corto_doc_terms.append(corto_d)
            if len(ocup) < 2: continue
            prim = m.NewIntVar(7, 21, f'dpr_{doc}_{d}'); ult = m.NewIntVar(7, 21, f'dul_{doc}_{d}')
            for h, ov in ocup.items():
                m.Add(prim <= h).OnlyEnforceIf(ov); m.Add(ult >= h + 1).OnlyEnforceIf(ov)
            span = m.NewIntVar(0, 14, f'dsp_{doc}_{d}')
            m.Add(span == ult - prim).OnlyEnforceIf(tiene); m.Add(span == 0).OnlyEnforceIf(tiene.Not())
            hk = m.NewIntVar(0, 14, f'dhk_{doc}_{d}')
            m.Add(hk == span - horas_dd); hueco_doc_terms.append(hk)
            hueco_por_doc[doc].append(hk)
    # Huecos semanales PA ≤ 3: DURO (tipo=2).
    for doc, hks in hueco_por_doc.items():
        if docentes[doc]['tipo'] != 2 or not hks: continue
        m.Add(sum(hks) <= 3)

    # Variables por (grupo, día) para días parejos y márgenes.
    abierto_gd, horas_gd = {}, {}
    for g, idxs in porGru.items():
        turno = cargas[idxs[0]]['turno']; lo, hi = ventanas[turno]
        for d in DIAS:
            slots = [x[(i, d, h)] for i in idxs for h in range(lo, hi) if (i, d, h) in x]
            if not slots: continue
            hgd = m.NewIntVar(0, hi - lo, f'hgd_{g}_{d}'); m.Add(hgd == sum(slots))
            abr = m.NewBoolVar(f'abr_{g}_{d}')
            m.Add(hgd >= 1).OnlyEnforceIf(abr); m.Add(hgd == 0).OnlyEnforceIf(abr.Not())
            horas_gd[(g, d)] = hgd; abierto_gd[(g, d)] = abr

    desnivel_terms = []
    for g, idxs in porGru.items():
        turno = cargas[idxs[0]]['turno']; lo, hi = ventanas[turno]
        dias_g = [d for d in DIAS if (g, d) in abierto_gd]
        if len(dias_g) < 2: continue
        max_g = m.NewIntVar(0, hi - lo, f'maxg_{g}'); min_g = m.NewIntVar(0, hi - lo, f'ming_{g}')
        for d in dias_g:
            m.Add(max_g >= horas_gd[(g, d)])
            m.Add(min_g <= horas_gd[(g, d)]).OnlyEnforceIf(abierto_gd[(g, d)])
        spread = m.NewIntVar(0, hi - lo, f'spr_{g}'); m.Add(spread == max_g - min_g)
        desnivel_terms.append(spread)

    margen_terms = []
    for g, idxs in porGru.items():
        turno = cargas[idxs[0]]['turno']; h_critico = 7 if turno == 'matutino' else 20
        for d in DIAS:
            if (g, d) not in abierto_gd: continue
            slot = [x[(i, d, h_critico)] for i in idxs if (i, d, h_critico) in x]
            if not slot: continue
            ocup = m.NewBoolVar(f'mc_{g}_{d}'); m.Add(ocup == sum(slot))
            pen = m.NewBoolVar(f'mrg_{g}_{d}'); m.Add(pen >= abierto_gd[(g, d)] - ocup)
            margen_terms.append(pen)

    patron = 2 * sum(sesion_terms) + 3 * sum(exceso_terms)
    nvars = len(x)
    sys.stderr.write(f'[solver] modelo listo: {nvars} vars x, max_time={max_time}s\n'); sys.stderr.flush()

    # Cero huecos de grupo: DURO. Completitud SUAVE (peso enorme) ⇒ el modelo siempre es
    # factible (huecos=0 con menos horas) y el solver empuja hacia las 354 h.
    # Orden de prioridad por pesos: completitud (1e6) ≫ escalón días PA (5e4) ≫ calidad fina.
    for hk in hueco_terms: m.Add(hk == 0)
    W_DESN = int(os.environ.get('W_DESN', '6000'))   # peso días equilibrados (ajustable)
    m.Maximize(1000000 * sum(colocadas) - 50000 * sum(maxdias_over_terms)
               - W_DESN * sum(desnivel_terms) - 1000 * patron
               - 100 * sum(hueco_doc_terms)
               - 200 * sum(corto_doc_terms) - sum(margen_terms))

    # Usa todos los núcleos de la máquina (más workers = búsqueda más fuerte).
    # En una laptop de 8 hilos = 8; en un Ryzen 5 5600 (12 hilos) = 12; tope 24.
    n_workers = max(4, min(os.cpu_count() or 8, 24))
    sys.stderr.write(f'[solver] num_search_workers={n_workers} (cpu_count={os.cpu_count()})\n'); sys.stderr.flush()
    emit('progress', msg=f'Resolviendo ({max_time}s máx, {n_workers} núcleos)…')
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time
    solver.parameters.num_search_workers = n_workers
    solver.parameters.random_seed = 42
    stop = threading.Event()
    tk = threading.Thread(target=progress_ticker, args=(max_time, stop), daemon=True)
    tk.start()
    st = solver.Solve(m)
    stop.set()
    dt = time.time() - t0

    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        sys.stderr.write(f'[solver] FALLÓ: {solver.StatusName(st)} dt={dt:.1f}s\n'); sys.stderr.flush()
        emit('result', data={'ok': False, 'colocadas': 0, 'total': HREQ, 'horario': [],
             'status': solver.StatusName(st), 'segundos': round(dt, 1),
             'error': f'Sin solución ({solver.StatusName(st)})'})
        return

    col = sum(solver.Value(v) for v in x.values())
    horario = [{'grupo': cargas[i]['grupo'], 'materia': cargas[i]['materia'],
                 'docente': cargas[i]['docente'], 'dia': d, 'hora': h}
                for (i, d, h), v in x.items() if solver.Value(v)]
    huecos = sum(solver.Value(t) for t in hueco_terms)
    desn = sum(solver.Value(t) for t in desnivel_terms)
    hd = sum(solver.Value(t) for t in hueco_doc_terms)
    dias_extra = sum(solver.Value(t) for t in maxdias_over_terms)
    sys.stderr.write(f'[solver] OK status={solver.StatusName(st)} col={col}/{HREQ} huecos={huecos} dias_extra_PA={dias_extra} dt={dt:.1f}s\n'); sys.stderr.flush()

    emit('result', data={
        'ok': True, 'colocadas': col, 'total': HREQ, 'horario': horario,
        'optimo': st == cp_model.OPTIMAL,
        'patron': solver.Value(patron),
        'huecos': huecos,
        'huecos_doc': hd,
        'desnivel': desn,
        'dias_extra': dias_extra,
        'status': solver.StatusName(st), 'segundos': round(dt, 1)
    })


if __name__ == '__main__':
    D = json.loads(sys.stdin.read())
    resolver(D)
