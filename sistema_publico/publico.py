import os
import sqlite3
import time
import shutil
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# 📁 NOVOS CAMINHOS AJUSTADOS: Aponta para a pasta templates DENTRO de sistema_publico
CORRENTE_DIR = os.path.dirname(os.path.abspath(__file__)) # Pasta 'sistema_publico'
BASE_DIR = os.path.dirname(CORRENTE_DIR)                  # Raiz do projeto (onde está o .db)

DB_FILE = os.path.join(BASE_DIR, "torneio.db")
TEMPLATES_DIR = os.path.join(CORRENTE_DIR, "templates")    # templates interna
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "comprovantes")

app = FastAPI(title="App de Acompanhamento Público - Truco Cego")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Habilita CORS (Essencial para quando virar Aplicativo Mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    # check_same_thread=False adicionado para evitar erros de concorrência
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def obter_ranking_publico(cursor):
    cursor.execute("SELECT id, nome FROM atletas WHERE status = 'APROVADO'")
    todos_atletas = cursor.fetchall()
    lista_classificacao = []
    
    for atleta in todos_atletas:
        atleta_id = atleta["id"]
        
        # 🛡️ BLINDAGEM DE COLUNAS: Tenta ler em Português, se falhar tenta em Inglês
        try:
            cursor.execute("SELECT COALESCE(SUM(sets1), 0) as s_pro, COALESCE(SUM(tentos1), 0) as t_pro, COALESCE(SUM(tentos2), 0) as t_contra, COALESCE(SUM(flores1), 0) as fl FROM confrontos WHERE atleta1_id = ? AND rodada > 0 AND vencedor_id IS NOT NULL", (atleta_id,))
            p1 = cursor.fetchone()
            cursor.execute("SELECT COALESCE(SUM(sets2), 0) as s_pro, COALESCE(SUM(tentos2), 0) as t_pro, COALESCE(SUM(tentos1), 0) as t_contra, COALESCE(SUM(flores2), 0) as fl FROM confrontos WHERE atleta2_id = ? AND rodada > 0 AND vencedor_id IS NOT NULL", (atleta_id,))
            p2 = cursor.fetchone()
        except sqlite3.OperationalError:
            cursor.execute("SELECT COALESCE(SUM(sets1), 0) as s_pro, COALESCE(SUM(tentos1), 0) as t_pro, COALESCE(SUM(tentos2), 0) as t_contra, COALESCE(SUM(flores1), 0) as fl FROM confrontos WHERE athlete1_id = ? AND rodada > 0 AND vencedor_id IS NOT NULL", (atleta_id,))
            p1 = cursor.fetchone()
            cursor.execute("SELECT COALESCE(SUM(sets2), 0) as s_pro, COALESCE(SUM(tentos2), 0) as t_pro, COALESCE(SUM(tentos1), 0) as t_contra, COALESCE(SUM(flores2), 0) as fl FROM confrontos WHERE athlete2_id = ? AND rodada > 0 AND vencedor_id IS NOT NULL", (atleta_id,))
            p2 = cursor.fetchone()
            
        cursor.execute("SELECT COUNT(*) FROM confrontos WHERE vencedor_id = ? AND rodada > 0", (atleta_id,))
        vitorias = cursor.fetchone()[0]
        
        tentos_pro = p1["t_pro"] + p2["t_pro"]
        tentos_contra = p1["t_contra"] + p2["t_contra"]
        lista_classificacao.append({
            "nome": atleta["nome"], "vitorias": vitorias, "saldo_tentos": tentos_pro - tentos_contra
        })
        
    lista_classificacao.sort(key=lambda x: (-x["vitorias"], -x["saldo_tentos"]))
    return lista_classificacao

@app.get("/", response_class=HTMLResponse)
def rota_telao(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM config LIMIT 1")
    cfg = dict(cursor.fetchone())
    return templates.TemplateResponse(request=request, name="publico_telao.html", context={"config": cfg})

# 🚀 ROTA PÚBLICA: EXIBIR PÁGINA DE INSCRIÇÃO
@app.get("/inscrever", response_class=HTMLResponse)
def tela_inscricao_atleta(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT nome_torneio, taxa_inscricao FROM config LIMIT 1")
    cfg_db = cursor.fetchone()
    
    # Busca entidades distintas cadastradas para alimentar o formulário
    cursor.execute("SELECT DISTINCT entidade FROM atletas WHERE status = 'APROVADO' ORDER BY entidade ASC")
    entidades = [row["entidade"] for row in cursor.fetchall()]
    
    taxa_val = cfg_db["taxa_inscricao"] if cfg_db else 0.0
    taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')

    return templates.TemplateResponse(
        request=request, 
        name="inscricao_atleta.html", 
        context={
            "config_taxa": taxa_formatada, 
            "entidades": entidades
        }
    )

# 📥 ROTA PÚBLICA CORRIGIDA: Processa a inscrição com segurança no SQLite
@app.post("/inscrever")
def processar_inscricao_atleta(
    nome: str = Form(...),
    entidade: str = Form(...),
    whatsapp: str = Form(...),
    comprovante: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db)
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
    cursor.execute('''
        INSERT INTO atletas (nome, entidade, whatsapp, status) 
        VALUES (?, ?, ?, 'PENDENTE')
    ''', (nome.strip(), entidade.strip().upper(), whatsapp.strip()))
    db.commit()
    
    return RedirectResponse(url="/inscrever?sucesso=true", status_code=303)

@app.get("/api/publico/dados")
def api_dados_publicos(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM config LIMIT 1")
    cfg = dict(cursor.fetchone())
    
    # 1. Atualiza o cronômetro na memória e sincroniza no Banco de Dados
    if cfg["crono_ativo"] == 1:
        agora = time.time()
        decorrido = int(agora - cfg["crono_ultimo_clique"])
        if decorrido > 0:
            novo_tempo = max(0, cfg["crono_tempo_restante_seg"] - decorrido)
            cfg["crono_tempo_restante_seg"] = novo_tempo
            cfg["crono_ultimo_clique"] = agora
            
            # SALVA NO BANCO para a próxima requisição pegar o tempo certo decrescente
            cursor.execute(
                "UPDATE config SET crono_tempo_restante_seg = ?, crono_ultimo_clique = ?", 
                (novo_tempo, agora)
            )
            db.commit()
            
    # 2. Formata o tempo para "MM:SS"
    mins = cfg["crono_tempo_restante_seg"] // 60
    segs = cfg["crono_tempo_restante_seg"] % 60
    tempo_formatado = f"{mins:02d}:{segs:02d}"

    # 3. Se o tempo zerou e o cronômetro ainda está ativo, muda o texto para o telão disparar o alerta
    if cfg["crono_tempo_restante_seg"] <= 0 and cfg["crono_ativo"] == 1:
        tempo_formatado = "AGORA TUDO É FALTA!"

    # --- (Mantém o restante do seu código original intacto) ---
    cursor.execute("SELECT rodada FROM confrontos ORDER BY id DESC LIMIT 1")
    row_r = cursor.fetchone()
    rodada_atual = row_r["rodada"] if row_r else 0
    
    confrontos = []
    nome_fase = "Inscrições Abertas"
    
    if rodada_atual != 0:
        cursor.execute("SELECT * FROM confrontos WHERE rodada = ? ORDER BY mesa ASC", (rodada_atual,))
        confrontos = [dict(row) for row in cursor.fetchall()]
        if rodada_atual > 0: nome_fase = f"Fase de Grupos - {rodada_atual}ª Rodada"
        elif rodada_atual == -1: nome_fase = "Oitavas de Final"
        elif rodada_atual == -2: nome_fase = "Quartas de Final"
        elif rodada_atual == -3: nome_fase = "Semifinal"
        elif rodada_atual == -4: nome_fase = "Grande Final"

    ranking = []
    if cfg["fase_torneio"] != "INSCRICAO":
        ranking = obter_ranking_publico(cursor)[:5]

    return JSONResponse({
        "fase_torneio": cfg["fase_torneio"], 
        "nome_fase": nome_fase, 
        "tempo": tempo_formatado,
        "crono_ativo": cfg["crono_ativo"], 
        "confrontos": confrontos, 
        "ranking": ranking
    })