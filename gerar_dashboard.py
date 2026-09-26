#!/usr/bin/env python3
"""
RFS — Gerador de Dashboard
Lê registro.csv e pesagens.csv e gera dashboard.html.

Uso: python3 gerar_dashboard.py
"""

import json
import csv
from datetime import datetime, date
from pathlib import Path


# ── Config ────────────────────────────────────────────────────────────────────

REGISTRO_PATH = Path("registro.csv")
PESAGENS_PATH = Path("pesagens.csv")
TEMPLATE_PATH = Path("dashboard_template.html")
OUTPUT_PATH   = Path("docs/index.html")

METAS = {
    "proteina_min": 160,  "proteina_max": 9999,
    "carbo_min":    150,  "carbo_max":    250,
    "gordura_min":   60,  "gordura_max":   75,
    "kcal_min":    1850,  "kcal_max":    1950,
    "sono_min":     7.0,  "sono_max":     8.5,
    "peso_meta":  105.0,  "peso_final":  85.0,
}


# ── Leitura ───────────────────────────────────────────────────────────────────

def safe_float(v, default=0.0):
    try:
        return float(str(v).replace(",", ".")) if v else default
    except Exception:
        return default


def parse_dt(s: str) -> datetime:
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y")
    except Exception:
        return datetime.min


def ler_registro() -> list[dict]:
    if not REGISTRO_PATH.exists():
        return []
    with open(REGISTRO_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dados = []
    for r in rows:
        if not r.get("data", "").strip():
            continue
        dados.append({
            "data":       r["data"].strip(),
            "proteina":   safe_float(r.get("proteina")),
            "carbo":      safe_float(r.get("carbo")),
            "gordura":    safe_float(r.get("gordura")),
            "kcal_ing":   safe_float(r.get("kcal_ing")),
            "kcal_gasto": safe_float(r.get("kcal_gasto")),
            "sono":       safe_float(r.get("sono")),
            "atividade1": r.get("atividade1", "").strip(),
            "atividade2": r.get("atividade2", "").strip(),
            "obs":        r.get("obs", "").strip(),
        })
    return sorted(dados, key=lambda r: parse_dt(r["data"]))


def ler_pesagens() -> list[dict]:
    if not PESAGENS_PATH.exists():
        return []
    with open(PESAGENS_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dados = []
    for r in rows:
        if not r.get("data", "").strip():
            continue
        peso = safe_float(r.get("peso"), default=0.0)
        if peso:
            dados.append({
                "data": r["data"].strip(),
                "peso": peso,
                "obs":  r.get("obs", "").strip(),
            })
    return sorted(dados, key=lambda p: parse_dt(p["data"]))


# ── Processamento ─────────────────────────────────────────────────────────────

def media(lista: list, campo: str) -> float:
    vals = [r[campo] for r in lista if r.get(campo, 0) > 0]
    return round(sum(vals) / len(vals), 1) if vals else 0


def processar(registro: list, pesagens: list) -> dict:
    ultima_pesagem = pesagens[-1] if pesagens else None
    peso_atual     = ultima_pesagem["peso"] if ultima_pesagem else None
    peso_inicial   = pesagens[0]["peso"]    if pesagens else None
    perda_total    = round(peso_inicial - peso_atual, 1) if peso_inicial and peso_atual else 0

    ultimas4  = pesagens[-4:] if len(pesagens) >= 4 else pesagens
    media4sem = round(sum(p["peso"] for p in ultimas4) / len(ultimas4), 2) if ultimas4 else None

    cd   = [r for r in registro if r["kcal_ing"] > 0]
    ult30 = cd[-30:]

    freq_ativ: dict[str, int] = {}
    for r in registro:
        for a in [r["atividade1"], r["atividade2"]]:
            if a:
                freq_ativ[a] = freq_ativ.get(a, 0) + 1

    return {
        "gerado_em":        datetime.now().strftime("%d/%m/%Y %H:%M"),
        "registro":         registro,
        "pesagens":         pesagens,
        "exames":           [],
        "metas":            METAS,
        "ultima_pesagem":   ultima_pesagem,
        "peso_atual":       peso_atual,
        "media_4sem":       media4sem,
        "peso_inicial":     peso_inicial,
        "perda_total":      perda_total,
        "media_proteina":   media(ult30, "proteina"),
        "media_carbo":      media(ult30, "carbo"),
        "media_gordura":    media(ult30, "gordura"),
        "media_kcal_ing":   media(ult30, "kcal_ing"),
        "media_kcal_gasto": media(ult30, "kcal_gasto"),
        "media_sono":       media(registro[-30:], "sono"),
        "freq_ativ":        freq_ativ,
        "total_dias":       len(registro),
        "total_pesagens":   len(pesagens),
    }


# ── Geração ───────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*50}")
    print(f"RFS Dashboard Generator — {date.today()}")
    print(f"{'='*50}\n")

    print("📥 Lendo CSVs...")
    registro = ler_registro()
    pesagens = ler_pesagens()
    print(f"   → {len(registro)} dias | {len(pesagens)} pesagens")

    print("⚙️  Processando...")
    dados = processar(registro, pesagens)

    print("🎨 Gerando HTML...")
    template   = TEMPLATE_PATH.read_text(encoding="utf-8")
    dados_json = json.dumps(dados, ensure_ascii=False, default=str)
    html       = template.replace("__DADOS_RFS__", dados_json)
    OUTPUT_PATH.write_text(html, encoding="utf-8")

    print(f"✅ {OUTPUT_PATH.resolve()}")
    print("\n🎉 Concluído! Abra o dashboard.html no navegador.")


if __name__ == "__main__":
    main()
