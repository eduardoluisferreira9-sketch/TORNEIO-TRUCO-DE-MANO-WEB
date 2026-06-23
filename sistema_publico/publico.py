import os
import time
import shutil
import logging
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📁 CAMINHOS AJUSTADOS
CORRENTE_DIR = os.path.dirname(os.path.abspath(__file__)) # Pasta 'sistema_publico'
BASE_DIR = os.path.dirname(CORRENTE_DIR)                  # Raiz do projeto

TEMPLATES_DIR = os.path.join(CORRENTE_DIR, "templates")    # templates interna
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "comprovantes")

app = FastAPI(title="App de Acompanhamento Público - Truco Cego")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Habilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONEXÃO INTELIGENTE DE BANCO DE DADOS ---
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import DictCursor
    def get_db():
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
        try:
            yield conn
        finally:
            conn.close()
else:
    import sqlite3
    def get_db():
        db_file = "/data/torneio.db" if os.path.exists("/data") else os.path.join(BASE_DIR, "torneio.db")
        conn = sqlite3.connect(db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

# --- FUNÇÃO TRADUTORA DE LINHAS ---
def row_to_dict(row):
    if row is None:
        return None
    if hasattr(row, "items"):  # Postgres
        return dict(row.items())
    return dict(row)           # SQLite

def obtener_torneio_ativo(cursor):
    cursor.execute("SELECT * FROM torneios WHERE fase_torneio != 'CONCLUIDO' ORDER BY id DESC LIMIT 1")
    torneio = cursor.fetchone()
    if not torneio:
        cursor.execute("SELECT * FROM torneios ORDER BY id DESC LIMIT 1")
        torneio = cursor.fetchone()
    return row_to_dict(torneio)

# --- RANKING PÚBLICO SEGURO ---
def obter_ranking_publico(cursor):
    p = "%s" if DATABASE_URL else "?"
    cursor.execute(f"SELECT id, nome FROM atletas WHERE status = 'APROVADO'")
    todos_atletas = cursor.fetchall()
    lista_classificacao = []
    
    for row in todos_atletas:
        atleta = row_to_dict(row)
        atleta_id = atleta["id"]
        
        cursor.execute(f"""
            SELECT COALESCE(SUM(sets1), 0) as s_pro, COALESCE(SUM(tentos1), 0) as t_pro, COALESCE(SUM(tentos2), 0) as t_contra 
            FROM confrontos WHERE atleta1_id = {p} AND rodada > 0 AND vencedor_id IS NOT NULL
        """, (atleta_id,))
        p1 = row_to_dict(cursor.fetchone())
        
        cursor.execute(f"""
            SELECT COALESCE(SUM(sets2), 0) as s_pro, COALESCE(SUM(tentos2), 0) as t_pro, COALESCE(SUM(tentos1), 0) as t_contra 
            FROM confrontos WHERE atleta2_id = {p} AND rodada > 0 AND vencedor_id IS NOT NULL
        """, (atleta_id,))
        p2 = row_to_dict(cursor.fetchone())
        
        cursor.execute(f"SELECT COUNT(*) FROM confrontos WHERE vencedor_id = {p} AND rodada > 0", (atleta_id,))
        vitorias = cursor.fetchone()[0]
        
        tentos_pro = p1["t_pro"] + p2["t_pro"]
        tentos_contra = p1["t_contra"] + p2["t_contra"]
        lista_classificacao.append({
            "nome": atleta["nome"], "vitorias": vitorias, "saldo_tentos": tentos_pro - tentos_contra
        })
        
    lista_classificacao.sort(key=lambda x: (-x["vitorias"], -x["saldo_tentos"]))
    return lista_classificacao

@app.get("/", response_class=HTMLResponse)
def rota_telao(request: Request, db=Depends(get_db)):
    cursor = db.cursor()
    cfg = obtener_torneio_ativo(cursor)
    return templates.TemplateResponse(request=request, name="publico_telao.html", context={"config": cfg})

@app.get("/inscrever", response_class=HTMLResponse)
def tela_inscricao_atleta(request: Request, db=Depends(get_db)):
    cursor = db.cursor()
    cfg = obtener_torneio_ativo(cursor)
    
    cursor.execute("SELECT DISTINCT entidade FROM atletas WHERE status = 'APROVADO' ORDER BY entidade ASC")
    entidades = [row[0] for row in cursor.fetchall()]
    
    taxa_val = cfg["taxa_inscricao"] if cfg and "taxa_inscricao" in cfg else 0.0
    taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')

    return templates.TemplateResponse(
        request=request, 
        name="inscricao_atleta.html", 
        context={
            "config_taxa": taxa_formatada, 
            "entidades": entidades,
            "torneio": cfg
        }
    )

@app.post("/inscrever")
def processar_inscricao_atleta(
    nome: str = Form(...),
    entidade: str = Form(...),
    whatsapp: str = Form(...),
    comprovante: UploadFile = File(...),
    db=Depends(get_db)
):
    if not comprovante.filename:
        raise HTTPException(status_code=400, detail="O envio do comprovante é obrigatório.")
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    extensao = os.path.splitext(comprovante.filename)[1]
    nome_seguro = "".join(c for c in nome if c.isalnum() or c in (' ', '_')).rstrip()
    nome_arquivo = f"comprovante_{nome_seguro}_{int(time.time())}{extensao}"
    caminho_final = os.path.join(UPLOAD_DIR, nome_arquivo)
    
    with open(caminho_final, "wb") as buffer:
        shutil.copyfileobj(comprovante.file, buffer)
        
    cursor = db.cursor()
    cfg = obtener_torneio_ativo(cursor)
    torneio_id = cfg["id"] if cfg else 1
    
    p = "%s" if DATABASE_URL else "?"
    cursor.execute(f'''
        INSERT INTO atletas (torneio_id, nome, entidade, whatsapp, status) 
        VALUES ({p}, {p}, {p}, {p}, 'PENDENTE')
    ''', (torneio_id, nome.strip(), entidade.strip().upper(), whatsapp.strip()))
    db.commit()
    
    return RedirectResponse(url="/inscrever?sucesso=true", status_code=303)

@app.get("/api/publico/dados")
def api_dados_publicos(db=Depends(get_db)):
    cursor = db.cursor()
    cfg = obtener_torneio_ativo(cursor)
    p = "%s" if DATABASE_URL else "?"
    
    if not cfg:
        return JSONResponse({"fase_torneio": "INSCRICAO", "nome_fase": "Nenhum Torneio Ativo", "tempo": "00:00", "crono_ativo": 0, "confrontos": [], "ranking": []})

    # Cálculo dinâmico do cronômetro usando a marca de tempo final em milissegundos
    tempo_restante = int(cfg.get("crono_tempo_restante_seg", 3000))
    if cfg.get("crono_ativo") == 1 and cfg.get("crono_fim_ms", 0) > 0:
        agora_ms = int(time.time() * 1000)
        restante_ms = cfg["crono_fim_ms"] - agora_ms
        tempo_restante = max(0, int(restante_ms / 1000))
        
        # Atualiza banco de dados para sincronismo sutil
        cursor.execute(f"UPDATE torneios SET crono_tempo_restante_seg = {p} WHERE id = {p}", (tempo_restante, cfg["id"]))
        db.commit()

    mins = tempo_restante // 60
    segs = tempo_restante % 60
    tempo_formatado = f"{mins:02d}:{segs:02d}"

    if tempo_restante <= 0 and cfg.get("crono_ativo") == 1:
        tempo_formatado = "AGORA TUDO É FALTA!"

    cursor.execute(f"SELECT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY id DESC LIMIT 1", (cfg["id"],))
    row_r = cursor.fetchone()
    rodada_atual = row_r[0] if row_r else 0
    
    confrontos = []
    nome_fase = "Inscrições Abertas"
    
    if rodada_atual != 0:
        cursor.execute(f"SELECT * FROM confrontos WHERE rodada = {p} AND torneio_id = {p} ORDER BY mesa ASC", (rodada_atual, cfg["id"]))
        confrontos = [row_to_dict(row) for row in cursor.fetchall()]
        if rodada_atual > 0: nome_fase = f"Fase de Grupos - {rodada_atual}ª Rodada"
        elif rodada_atual == -1: nome_fase = "Oitavas de Final"
        elif rodada_atual == -2: nome_fase = "Quartas de Final"
        elif rodada_atual == -3: nome_fase = "Semifinal"
        elif rodada_atual == -4: nome_fase = "Grande Final"

    ranking = []
    if cfg["fase_torneio"] != "INSCRICAO":
        ranking = obter_ranking_publico(cursor)[:5]

    # 🔍 LINHA PROVISÓRIA DE DIAGNÓSTICO: Mostra no console do servidor as chaves do banco!
    logger.info(f"--- COLUNAS DO BANCO DE DADOS: {list(cfg.keys())} ---")

    return JSONResponse({
        "fase_torneio": cfg["fase_torneio"], 
        "nome_fase": nome_fase, 
        "tempo": tempo_formatado,
        "crono_ativo": cfg.get("crono_ativo", 0), 
        "confrontos": confrontos, 
        "ranking": ranking,
        # Tenta mapear variantes comuns do banco
        "tempo_rodada": cfg.get("duracao_rodada") or cfg.get("tempo_rodada") or cfg.get("config_tempo") or cfg.get("duracao") or 30,
        "max_rodadas": cfg.get("max_rodadas_classificatoria") or cfg.get("total_rodadas") or cfg.get("qtd_rodadas") or cfg.get("rodadas") or 5
    })
