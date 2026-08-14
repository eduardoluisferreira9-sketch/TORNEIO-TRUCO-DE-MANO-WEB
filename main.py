import os
import sys
import time
import random
import shutil
import json
import base64

from fastapi import FastAPI, Request, Form, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

--- CONFIGURAÇÃO DE SEGURANÇA E AMBIENTE ---

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "truco123")
DATABASE_URL = os.environ.get("DATABASE_URL")  # String de conexão do Postgres (Neon/Supabase)

BASE_DIR = os.path.dirname(os.path.abspath(file))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
TEMPLATES_PUBLICO_DIR = os.path.join(BASE_DIR, "sistema_publico", "templates")

app = FastAPI(title="Painel de Controle do Administrador - Truco Cego")
templates = Jinja2Templates(directory=[TEMPLATES_DIR, TEMPLATES_PUBLICO_DIR])
templates.env.globals.update(chr=chr)

--- FILTRO ESCAPEJS PARA COMPATIBILIDADE COM JINJA2 ---

def escapejs_filter(val):
if not val:
return ""
return json.dumps(str(val))[1:-1]

templates.env.filters["escapejs"] = escapejs_filter

UPLOAD_DIR = os.path.join(BASE_DIR, "static", "comprovantes")
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
except Exception:
pass

==============================================================================

🗄️ GERENCIAMENTO CONEXÃO INTELIGENTE (HÍBRIDO)

==============================================================================

def get_db():
if DATABASE_URL:
import psycopg2
from psycopg2.extras import DictCursor
conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
try:
yield conn
finally:
conn.close()
else:
import sqlite3
if os.path.exists("/data"):
db_file = "/data/torneio.db"
else:
db_file = os.path.join(BASE_DIR, "torneio.db")
conn = sqlite3.connect(db_file, check_same_thread=False)
conn.row_factory = sqlite3.Row
try:
yield conn
finally:
conn.close()

def execute_query(cursor, query_sqlite, query_postgres, params=()):
"""Executa a query correta dependendo do banco ativo"""
query = query_postgres if DATABASE_URL else query_sqlite
cursor.execute(query, params)
return cursor

def init_db():
"""Inicializa as tabelas com sintaxes compatíveis para ambos os bancos"""
if DATABASE_URL:
import psycopg2
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS torneios (
            id SERIAL PRIMARY KEY,
            nome_torneio VARCHAR(255) DEFAULT 'Torneio de Truco Cego',
            taxa_inscricao REAL DEFAULT 45.0,
            max_rodadas_classificatoria INTEGER DEFAULT 5,
            crono_tempo_restante_seg INTEGER DEFAULT 3000,
            crono_ativo INTEGER DEFAULT 0,
            crono_fim_ms BIGINT DEFAULT 0,
            fase_torneio VARCHAR(50) DEFAULT 'INSCRICAO'
        );
    ''')
    
    cursor.execute("ALTER TABLE torneios ADD COLUMN IF NOT EXISTS crono_ativo INTEGER DEFAULT 0;")
    cursor.execute("ALTER TABLE torneios ADD COLUMN IF NOT EXISTS crono_fim_ms BIGINT DEFAULT 0;")
    cursor.execute("ALTER TABLE torneios ADD COLUMN IF NOT EXISTS crono_tempo_restante_seg INTEGER DEFAULT 3000;")
    
    cursor.execute("SELECT COUNT(*) FROM torneios;")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO torneios (nome_torneio, taxa_inscricao, max_rodadas_classificatoria, crono_tempo_restante_seg, fase_torneio, crono_fim_ms) 
            VALUES ('Torneio de Truco Cego', 45.00, 5, 3000, 'INSCRICAO', 0);
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atletas (
            id SERIAL PRIMARY KEY,
            torneio_id INTEGER NOT NULL DEFAULT 1,
            nome VARCHAR(255) NOT NULL,
            entidade VARCHAR(255) NOT NULL DEFAULT 'AVULSO',
            whatsapp VARCHAR(50),
            status VARCHAR(50) DEFAULT 'PENDENTE'
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS confrontos (
            id SERIAL PRIMARY KEY,
            torneio_id INTEGER NOT NULL DEFAULT 1,
            rodada INTEGER NOT NULL,
            mesa INTEGER NOT NULL,
            atleta1_id INTEGER,
            atleta2_id INTEGER,
            atleta1_nome VARCHAR(255),
            atleta2_nome VARCHAR(255),
            tipo_placar VARCHAR(50) DEFAULT NULL,
            vencedor_id INTEGER DEFAULT NULL,
            sets1 INTEGER DEFAULT NULL,
            sets2 INTEGER DEFAULT NULL,
            tentos1 INTEGER DEFAULT NULL,
            tentos2 INTEGER DEFAULT NULL,
            flores1 INTEGER DEFAULT 0,
            flores2 INTEGER DEFAULT 0
        );
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_campeoes (
            id SERIAL PRIMARY KEY,
            torneio_id INTEGER UNIQUE,
            nome_torneio VARCHAR(255),
            campeao VARCHAR(255),
            vice VARCHAR(255),
            terceiro VARCHAR(255),
            quarto VARCHAR(255),
            rei_das_flores VARCHAR(255),
            qtd_flores INTEGER
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()
else:
    import sqlite3
    if os.path.exists("/data"):
        db_file = "/data/torneio.db"
    else:
        db_file = os.path.join(BASE_DIR, "torneio.db")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS torneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_torneio TEXT DEFAULT 'Torneio de Truco Cego',
            taxa_inscricao REAL DEFAULT 45.0,
            max_rodadas_classificatoria INTEGER DEFAULT 5,
            crono_tempo_restante_seg INTEGER DEFAULT 3000,
            crono_ativo INTEGER DEFAULT 0,
            crono_fim_ms INTEGER DEFAULT 0,
            fase_torneio TEXT DEFAULT 'INSCRICAO'
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM torneios")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO torneios (nome_torneio, taxa_inscricao, max_rodadas_classificatoria, crono_tempo_restante_seg, fase_torneio, crono_fim_ms) 
            VALUES ('Torneio de Truco Cego', 45.00, 5, 3000, 'INSCRICAO', 0)
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS atletas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER NOT NULL DEFAULT 1,
            nome TEXT NOT NULL,
            entidade TEXT NOT NULL DEFAULT 'AVULSO',
            whatsapp TEXT,
            status TEXT DEFAULT 'PENDENTE',
            FOREIGN KEY (torneio_id) REFERENCES torneios(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS confrontos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER NOT NULL DEFAULT 1,
            rodada INTEGER NOT NULL,
            mesa INTEGER NOT NULL,
            atleta1_id INTEGER,
            atleta2_id INTEGER,
            atleta1_nome TEXT,
            atleta2_nome TEXT,
            tipo_placar TEXT DEFAULT NULL,
            vencedor_id INTEGER DEFAULT NULL,
            sets1 INTEGER DEFAULT NULL,
            sets2 INTEGER DEFAULT NULL,
            tentos1 INTEGER DEFAULT NULL,
            tentos2 INTEGER DEFAULT NULL,
            flores1 INTEGER DEFAULT 0,
            flores2 INTEGER DEFAULT 0,
            FOREIGN KEY (torneio_id) REFERENCES torneios(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_campeoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            torneio_id INTEGER UNIQUE,
            nome_torneio TEXT,
            campeao TEXT,
            vice TEXT,
            terceiro TEXT,
            quarto TEXT,
            rei_das_flores TEXT,
            qtd_flores INTEGER,
            FOREIGN KEY (torneio_id) REFERENCES torneios(id)
        )
    ''')
    conn.commit()
    conn.close()

try:
init_db()
except Exception as e:
print(f"Erro na inicialização do Banco: {e}", file=sys.stderr)

--- FUNÇÕES AUXILIARES ---

def verificar_admin(request: Request):
token = request.cookies.get("admin_token")
if token != ADMIN_PASSWORD:
raise HTTPException(status_code=303, headers={"Location": "/admin-painel/login"})
return True

def obtener_torneio_ativo(cursor):
cursor.execute("SELECT * FROM torneios WHERE fase_torneio != 'CONCLUIDO' ORDER BY id DESC LIMIT 1")
torneio = cursor.fetchone()

if not torneio:
    cursor.execute("SELECT * FROM torneios ORDER BY id DESC LIMIT 1")
    torneio = cursor.fetchone()
    
if not torneio:
    return None

if isinstance(torneio, dict):
    return torneio

colunas = [col[0] for col in cursor.description]
return dict(zip(colunas, torneio))

def atualizar_e_obter_cronometro(db):
cursor = db.cursor()
config = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

if config and config["crono_ativo"] == 1:
    agora_ms = int(time.time() * 1000)
    fim_ms = int(config["crono_fim_ms"])
    
    if agora_ms >= fim_ms:
        cursor.execute(
            f'UPDATE torneios SET crono_tempo_restante_seg = 0, crono_ativo = 0 WHERE id = {p}', 
            (config["id"],)
        )
        db.commit()
        config["crono_tempo_restante_seg"] = 0
        config["crono_ativo"] = 0
    else:
        restante_seg = int((fim_ms - agora_ms) / 1000)
        config["crono_tempo_restante_seg"] = max(0, restante_seg)
        
return config

def obtener_ranking_fase_classificatoria(cursor, torneio_id: int):
p = "%s" if DATABASE_URL else "?"
cursor.execute(f"SELECT id, nome, status FROM atletas WHERE status IN ('APROVADO', 'DESISTENTE') AND torneio_id = {p} ORDER BY nome ASC", (torneio_id,))
todos_atletas = cursor.fetchall()
lista_classificacao = []

for atleta in todos_atletas:
    atleta_id = atleta["id"]
    
    cursor.execute(f"""
        SELECT COALESCE(SUM(sets1), 0) as s_pro, COALESCE(SUM(tentos1), 0) as t_pro, 
               COALESCE(SUM(tentos2), 0) as t_contra, COALESCE(SUM(flores1), 0) as fl, 
               SUM(CASE WHEN atleta2_id IS NULL THEN 1 ELSE 0 END) as byes 
        FROM confrontos 
        WHERE atleta1_id = {p} AND torneio_id = {p} AND rodada > 0 AND vencedor_id IS NOT NULL
    """, (atleta_id, torneio_id))
    p1 = cursor.fetchone()
    
    cursor.execute(f"""
        SELECT COALESCE(SUM(sets2), 0) as s_pro, COALESCE(SUM(tentos2), 0) as t_pro, 
               COALESCE(SUM(tentos1), 0) as t_contra, COALESCE(SUM(flores2), 0) as fl 
        FROM confrontos 
        WHERE atleta2_id = {p} AND torneio_id = {p} AND rodada > 0 AND vencedor_id IS NOT NULL
    """, (atleta_id, torneio_id))
    p2 = cursor.fetchone()
        
    cursor.execute(f"SELECT COUNT(*) FROM confrontos WHERE vencedor_id = {p} AND torneio_id = {p} AND rodada > 0", (atleta_id, torneio_id))
    vitorias = cursor.fetchone()[0]
    
    sets_ganhos = p1["s_pro"] + p2["s_pro"]
    tentos_pro = p1["t_pro"] + p2["t_pro"]
    tentos_contra = p1["t_contra"] + p2["t_contra"]
    flores = p1["fl"] + p2["fl"]
    
    lista_classificacao.append({
        "id": atleta_id, "nome": atleta["nome"], "status": atleta["status"], "vitorias": vitorias, "sets_ganhos": sets_ganhos,
        "saldo_tentos": tentos_pro - tentos_contra, "tentos_pro": tentos_pro, "flores": flores, "chapeu_jogados": p1["byes"]
    })
lista_classificacao.sort(key=lambda x: (-x["vitorias"], -x["sets_ganhos"], -x["saldo_tentos"], -x["tentos_pro"], -x["flores"], x["id"]))
return lista_classificacao

--- ROTAS DE INSCRIÇÃO E LOGIN ---

@app.get("/inscrever", response_class=HTMLResponse)
@app.get("/admin-painel/inscrever", response_class=HTMLResponse)
def tela_inscricao_atleta(request: Request, db=Depends(get_db)):
cursor = db.cursor()
cfg_db = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

entidades = []
if cfg_db:
    cursor.execute(f"SELECT DISTINCT entidade FROM atletas WHERE status = 'APROVADO' AND torneio_id = {p} ORDER BY entidade ASC", (cfg_db["id"],))
    entities_rows = cursor.fetchall()
    entidades = [row["entidade"] for row in entities_rows]

taxa_val = cfg_db["taxa_inscricao"] if cfg_db else 0.0
taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')

return templates.TemplateResponse(
    request=request, name="inscricao_atleta.html", 
    context={"config_taxa": taxa_formatada, "entidades": entidades, "config": cfg_db}
)

@app.post("/inscrever")
@app.post("/admin-painel/inscrever")
async def processar_inscricao_atleta(
nome: str = Form(...), entidade: str = Form(...), whatsapp: str = Form(...),
comprovante: UploadFile = File(...), db=Depends(get_db)
):
if not comprovante.filename:
raise HTTPException(status_code=400, detail="O envio do comprovante é obrigatório.")

# 🌟 SEGURANÇA CONTRA LIMPEZA DO RENDER: Garante que a pasta existe
PASTA_SALVAR = "static/comprovantes"
if not os.path.exists(PASTA_SALVAR):
    os.makedirs(PASTA_SALVAR, exist_ok=True)
    
# Extrai a extensão da imagem enviada (.jpg, .png, etc)
extensao = os.path.splitext(comprovante.filename)[1]

# Limpa o whatsapp para virar um nome de arquivo seguro (sem parênteses ou traços)
whats_limpo = "".join(c for c in whatsapp if c.isdigit())
nome_arquivo_salvo = f"pix_{whats_limpo}{extensao}"
caminho_completo = os.path.join(PASTA_SALVAR, nome_arquivo_salvo)

# 🌟 SALVA O ARQUIVO FÍSICO NA PASTA DO SERVIDOR
conteudo_arquivo = await comprovante.read()
with open(caminho_completo, "wb") as f:
    f.write(conteudo_arquivo)
    
# Guarda no banco apenas o link relativo da foto
url_comprovante = f"/static/comprovantes/{nome_arquivo_salvo}"

cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
entidade_limpa = entidade.strip().upper() if entidade.strip() else "AVULSO"
p = "%s" if DATABASE_URL else "?"

# Grava no Supabase
cursor.execute(f'''
    INSERT INTO atletas (torneio_id, nome, entidade, whatsapp, comprovante_url, status) 
    VALUES ({p}, {p}, {p}, {p}, {p}, 'PENDENTE')
''', (cfg["id"], nome.strip().upper(), entidade_limpa, whatsapp.strip(), url_comprovante))
db.commit()

# Redireciona de volta para a inscrição mostrando a mensagem verde de sucesso
return RedirectResponse(url="/inscrever?sucesso=true", status_code=303)

@app.get("/login", response_class=HTMLResponse)
@app.get("/admin-painel/login", response_class=HTMLResponse)
def tela_login(request: Request, erro: str = None):
erro_html = '<div class="erro">⚠️ Chave incorreta. Tente novamente.</div>' if erro else ""

html_content = """

<!DOCTYPE html>

<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" href="/static/favicon.ico" type="image/x-icon">
<title>Acesso Restrito • Torneio de Truco Cego</title>
<style>
*{box-sizing:border-box}
html,body{margin:0;width:100%;min-height:100%;font-family:"Segoe UI",Arial,sans-serif}
body{
 min-height:100vh;display:flex;align-items:center;justify-content:center;
 position:relative;overflow:hidden;color:#f5f1e8;
 background:
 radial-gradient(circle at 50% 28%,rgba(212,175,55,.13),transparent 27%),
 radial-gradient(circle at 50% 100%,rgba(18,80,42,.30),transparent 50%),
 linear-gradient(145deg,#020a05 0%,#06150c 48%,#031008 100%);
}
body:before{
 content:"";position:fixed;inset:0;pointer-events:none;opacity:.24;
 background:
 repeating-linear-gradient(90deg,transparent 0 110px,rgba(255,255,255,.018) 111px,transparent 113px),
 repeating-linear-gradient(0deg,transparent 0 84px,rgba(212,175,55,.012) 85px,transparent 87px);
}
body:after{
 content:"";position:fixed;inset:0;pointer-events:none;
 background:linear-gradient(90deg,rgba(0,0,0,.38),transparent 22%,transparent 78%,rgba(0,0,0,.38));
}
.login-wrap{position:relative;z-index:2;width:min(460px,calc(100vw - 32px))}
.brand{text-align:center;margin-bottom:18px}
.brand-mark{
 width:68px;height:68px;margin:0 auto 11px;display:flex;align-items:center;justify-content:center;
 border-radius:50%;border:1px solid rgba(212,175,55,.72);
 background:radial-gradient(circle at 35% 28%,#1d4a27,#0b1f12 68%);
 box-shadow:0 10px 28px rgba(0,0,0,.48),inset 0 0 0 5px rgba(212,175,55,.07);
 font-size:31px
}
.brand h1{margin:0;color:#f1cf54;font-family:Georgia,"Times New Roman",serif;font-size:1.48rem}
.brand p{margin:5px 0 0;color:#a8b5ac;font-size:.80rem;letter-spacing:.35px}
.box{
 position:relative;padding:30px;
 border:1px solid #295238;border-radius:14px;
 background:linear-gradient(145deg,rgba(16,43,25,.985),rgba(5,19,10,.99));
 box-shadow:0 26px 65px rgba(0,0,0,.58),inset 0 1px 0 rgba(255,255,255,.045);
}
.box:before{
 content:"";position:absolute;top:0;left:25px;right:25px;height:2px;
 background:linear-gradient(90deg,transparent,#d4af37,transparent)
}
.box h2{margin:0;color:#f7f3eb;font-size:1.46rem;text-align:center}
.subtitle{margin:7px 0 23px;color:#a8b5ac;font-size:.84rem;text-align:center}
.erro{
 margin:0 0 16px;padding:11px 13px;border:1px solid rgba(224,74,63,.48);
 border-radius:8px;background:rgba(128,30,24,.18);color:#ffb9b2;text-align:center;font-size:.82rem;font-weight:700
}
label{display:block;margin:0 0 7px;color:#d9e2dc;font-size:.78rem;font-weight:800}
.input-wrap{position:relative}
.input-icon{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#d4af37;font-size:17px}
input{
 width:100%;height:52px;margin:0 0 16px;padding:0 14px 0 44px;
 border:1px solid #3a5d45;border-radius:8px;outline:none;background:#06150c;color:#fff;font-size:.96rem
}
input::placeholder{color:#718278}
input:focus{border-color:#d4af37;box-shadow:0 0 0 3px rgba(212,175,55,.10)}
button{
 width:100%;height:52px;border:1px solid #f1cf54;border-radius:8px;
 background:linear-gradient(180deg,#e7c74d,#d4af37);color:#10150f;font-size:.92rem;font-weight:900;cursor:pointer;
 box-shadow:0 6px 16px rgba(0,0,0,.28)
}
button:hover{filter:brightness(1.06);transform:translateY(-1px)}
.secure{margin:17px 0 0;color:#718177;font-size:.70rem;text-align:center}
@media(max-width:520px){.login-wrap{width:calc(100vw - 24px)}.box{padding:25px 20px}.brand h1{font-size:1.28rem}}
</style>
</head>
<body>
<main class="login-wrap">
<header class="brand">
<div class="brand-mark">🏆</div>
<h1>Torneio de Truco Cego</h1>
<p>Painel de Administração</p>
</header>
<section class="box">
<h2>🔐 Acesso do Administrador</h2>
<p class="subtitle">Entre com a chave para acessar o painel do torneio.</p>
__ERRO__
<form action="/admin-painel/login" method="POST">
<label for="chave">Chave de acesso</label>
<div class="input-wrap"><span class="input-icon">🔑</span>
<input id="chave" type="password" name="chave" placeholder="Digite sua chave de acesso" required autofocus autocomplete="current-password">
</div>
<button type="submit">ENTRAR NO SISTEMA&nbsp;&nbsp;→</button>
</form>
<p class="secure">🔒 Área administrativa restrita</p>
</section>
</main>
</body>
</html>
""".replace("__ERRO__", erro_html)
    return HTMLResponse(content=html_content)

@app.post("/login")
@app.post("/admin-painel/login")
def processar_login(chave: str = Form(...)):
if chave == ADMIN_PASSWORD:
response = RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)
response.set_cookie(key="admin_token", value=chave, httponly=True)
return response
return RedirectResponse(url="/admin-painel/login?erro=1", status_code=303)

@app.get("/logout")
@app.get("/admin-painel/logout")
def processar_logout():
response = RedirectResponse(url="/admin-painel/login", status_code=303)
response.delete_cookie("admin_token")
return response

@app.get("/api/cronometro")
@app.get("/admin-painel/api/cronometro")
def api_cronometro(db=Depends(get_db)):
cfg = atualizar_e_obter_cronometro(db)
tempo_restante = int(cfg["crono_tempo_restante_seg"]) if cfg else 0
ativo = int(cfg["crono_ativo"]) if cfg else 0
return JSONResponse({"tempo_restante": tempo_restante, "ativo": ativo})

@app.post("/admin/cronometro/controle")
@app.post("/admin-painel/admin/cronometro/controle")
def controle_cronometro(
acao: str = Form(...),
tempo_minutos: int = Form(None),  # <--- CAPTURA O VALOR QUE O SEU BOTÃO ENVIA
db=Depends(get_db),
auth: bool = Depends(verificar_admin)
):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

if cfg["fase_torneio"] == "INSCRICAO":
    return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=torneio_nao_iniciado", status_code=303)

agora_ms = int(time.time() * 1000)

if acao == "iniciar" and cfg["crono_ativo"] == 0 and int(cfg["crono_tempo_restante_seg"]) > 0:
    fim_ms = agora_ms + (int(cfg["crono_tempo_restante_seg"]) * 1000)
    cursor.execute(f"UPDATE torneios SET crono_ativo = 1, crono_fim_ms = {p} WHERE id = {p}", (fim_ms, cfg["id"]))
    
elif acao == "pausar" and cfg["crono_ativo"] == 1:
    fim_ms = int(cfg["crono_fim_ms"])
    restante_seg = max(0, int((fim_ms - agora_ms) / 1000))
    cursor.execute(f"UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = {p}, crono_fim_ms = 0 WHERE id = {p}", (restante_seg, cfg["id"]))
    
elif acao == "reiniciar":
    # CORREÇÃO CRÍTICA: Se o novo botão mandou os minutos, calcula o novo tempo em segundos.
    # Caso contrário, mantém o tempo que já estava registrado no banco.
    if tempo_minutos is not None:
        novo_tempo_seg = int(tempo_minutos) * 60
    else:
        novo_tempo_seg = int(cfg.get("crono_tempo_restante_seg", 1800))
        
    # Grava os novos segundos na memória física do banco de dados, limpa o contador de milissegundos e para o cronômetro
    cursor.execute(
        f"UPDATE torneios SET crono_ativo = 0, crono_tempo_restante_seg = {p}, crono_fim_ms = 0 WHERE id = {p}", 
        (novo_tempo_seg, cfg["id"])
    )
    
db.commit()
return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.get("/admin/inscricoes")
@app.get("/admin-painel/admin/inscricoes")
def aba_inscricoes(request: Request, db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cfg = atualizar_e_obter_cronometro(db)
cursor = db.cursor()
p = "%s" if DATABASE_URL else "?"

cursor.execute(f"SELECT * FROM atletas WHERE status = 'PENDENTE' AND torneio_id = {p} ORDER BY id DESC", (cfg["id"],))
pendentes = cursor.fetchall()
cursor.execute(f"SELECT * FROM atletas WHERE status = 'APROVADO' AND torneio_id = {p} ORDER BY nome ASC", (cfg["id"],))
oficiais = cursor.fetchall()
cursor.execute(f"SELECT * FROM atletas WHERE status = 'DESISTENTE' AND torneio_id = {p} ORDER BY nome ASC", (cfg["id"],))
desistentes = cursor.fetchall()
total_arrecadado = len(oficiais) * cfg['taxa_inscricao']

return templates.TemplateResponse(
    request=request, name="admin_inscricoes.html", 
    context={"config": cfg, "pendentes": pendentes, "oficiais": oficiais, "desistentes": desistentes, "total_arrecadado": str(total_arrecadado), "aba_ativa": "inscricoes"}
)

@app.post("/admin/salvar-configuracoes")
@app.post("/admin-painel/admin/salvar-configuracoes")
def salvar_configuracoes(nome_torneio: str = Form(...), max_rodadas: int = Form(...), tempo_minutos: int = Form(...), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"
if cfg["fase_torneio"] != "INSCRICAO":
return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=torneio_ja_iniciado", status_code=303)
total_seg = tempo_minutos * 60

# ⚙️ CORREÇÃO DEFINITIVA: Inserida a coluna taxa_inscricao recebendo o seu novo valor padrão
cursor.execute(f"UPDATE torneios SET nome_torneio = {p}, max_rodadas_classificatoria = {p}, crono_tempo_restante_seg = {p}, crono_fim_ms = 0, crono_ativo = 0, taxa_inscricao = 45.00 WHERE id = {p}", 
               (nome_torneio.strip(), max_rodadas, total_seg, cfg["id"]))
db.commit()
return RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)

@app.post("/admin/iniciar-torneio")
@app.post("/admin-painel/admin/iniciar-torneio")
def iniciar_torneio_e_gerar_r1(db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"
if cfg["fase_torneio"] != "INSCRICAO":
return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

cursor.execute(f"SELECT COUNT(*) FROM atletas WHERE status = 'APROVADO' AND torneio_id = {p}", (cfg["id"],))
if cursor.fetchone()[0] < 2:
    return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=jogadores_insuficientes", status_code=303)

tempo_salvo = int(cfg.get("crono_tempo_restante_seg", 3000))
cursor.execute(f"UPDATE torneios SET fase_torneio = 'CLASSIFICATORIA', crono_tempo_restante_seg = {p}, crono_fim_ms = 0, crono_ativo = 0 WHERE id = {p}", 
               (tempo_salvo, cfg["id"],))
db.commit()
return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.get("/admin/jogos")
@app.get("/admin-painel/admin/jogos")
def aba_jogos(request: Request, db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cfg = atualizar_e_obter_cronometro(db)
p = "%s" if DATABASE_URL else "?"

if cfg["fase_torneio"] == "INSCRICAO":
    return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

cursor = db.cursor()
cursor.execute(f"SELECT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY id DESC LIMIT 1", (cfg["id"],))
row_r = cursor.fetchone()

if row_r:
    if isinstance(row_r, dict):
        rodada_atual = row_r["rodada"]
    else:
        rodada_atual = row_r[0]
else:
    rodada_atual = 1

cursor.execute(f"SELECT * FROM confrontos WHERE rodada = {p} AND torneio_id = {p} ORDER BY mesa ASC", (rodada_atual, cfg["id"]))

confrontos_cru = cursor.fetchall()
confrontos = []
for row in confrontos_cru:
    if isinstance(row, dict):
        confrontos.append(row)
    else:
        confrontos.append(dict(row))

cursor.execute(f"SELECT COUNT(*) as total FROM confrontos WHERE rodada = {p} AND torneio_id = {p} AND vencedor_id IS NULL", (rodada_atual, cfg["id"]))
res_concluida = cursor.fetchone()
qtd_pendentes = res_concluida["total"] if isinstance(res_concluida, dict) else res_concluida[0]
rodada_concluida = (qtd_pendentes == 0) if confrontos else False

# Histórico de adversários para o ajuste manual.
# A rodada atual fica fora porque estamos apenas reorganizando os jogos dela.
cursor.execute(
    f"""
    SELECT atleta1_id, atleta2_id
    FROM confrontos
    WHERE torneio_id = {p}
      AND rodada > 0
      AND rodada != {p}
      AND atleta2_id IS NOT NULL
    """,
    (cfg["id"], rodada_atual)
)
historico_ajuste = [
    [int(r["atleta1_id"]), int(r["atleta2_id"])]
    for r in cursor.fetchall()
    if r["atleta1_id"] is not None and r["atleta2_id"] is not None
]

mins = cfg["crono_tempo_restante_seg"] // 60
segs = cfg["crono_tempo_restante_seg"] % 60
tempo_formatado = f"{mins:02d}:{segs:02d}"

return templates.TemplateResponse(
    request=request, 
    name="admin_jogos.html", 
    context={
        "config": cfg, 
        "torneio": cfg, 
        "rodada": rodada_atual, 
        "fase_atual_rodada": rodada_atual, 
        "confrontos": confrontos,
        "rodada_concluida": rodada_concluida,
        "historico_ajuste": historico_ajuste,
        "tempo_formatado": tempo_formatado, 
        "aba_ativa": "jogos"
    }
)

@app.post("/admin/gerar-rodada")
@app.post("/admin-painel/admin/gerar-rodada")
def gerar_rodada_admin(
tempo_minutos: int = Form(None),
refazer: bool = Form(False),
db=Depends(get_db),
auth: bool = Depends(verificar_admin)
):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

# ==========================================================
# 1. VALIDAÇÕES BÁSICAS
# ==========================================================

if cfg["fase_torneio"] == "INSCRICAO":
    return RedirectResponse(
        url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio",
        status_code=303
    )

cursor.execute(
    f"""
    SELECT COALESCE(MAX(rodada), 0)
    FROM confrontos
    WHERE rodada > 0
      AND torneio_id = {p}
    """,
    (cfg["id"],)
)

rodada_atual = cursor.fetchone()[0]
proxima_rodada = rodada_atual + 1

# ==========================================================
# 2. MODO REFAZER RODADA
#
# Refazer NÃO cria uma nova rodada.
# Ele substitui a rodada classificatória atual.
# ==========================================================

if refazer:

    # Só podemos refazer uma rodada classificatória existente.
    if rodada_atual <= 0:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=refazer_indisponivel",
            status_code=303
        )

    # ------------------------------------------------------
    # VERIFICAR SE ALGUM JOGO REAL JÁ POSSUI RESULTADO
    #
    # A folga automática possui vencedor_id preenchido,
    # portanto ela NÃO conta como partida disputada.
    # ------------------------------------------------------
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM confrontos
        WHERE rodada = {p}
          AND torneio_id = {p}
          AND atleta2_id IS NOT NULL
          AND vencedor_id IS NOT NULL
        """,
        (rodada_atual, cfg["id"])
    )

    partidas_com_resultado = cursor.fetchone()[0]

    if partidas_com_resultado > 0:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=rodada_ja_iniciada",
            status_code=303
        )

    # A nova rodada terá o MESMO número da rodada atual.
    proxima_rodada = rodada_atual

else:

    # ======================================================
    # 2. NÃO PERMITIR NOVA RODADA ENQUANTO A ATUAL
    #    NÃO TERMINAR
    # ======================================================

    if rodada_atual > 0:
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM confrontos
            WHERE rodada = {p}
              AND torneio_id = {p}
              AND vencedor_id IS NULL
            """,
            (rodada_atual, cfg["id"])
        )

        if cursor.fetchone()[0] > 0:
            return RedirectResponse(
                url="/admin-painel/admin/jogos?erro=jogos_pendentes",
                status_code=303
            )

# ==========================================================
# 3. VERIFICAR LIMITE DE RODADAS
# ==========================================================

if proxima_rodada > cfg["max_rodadas_classificatoria"]:
    return RedirectResponse(
        url="/admin-painel/admin/classificacao?aviso=fim_da_classificatoria",
        status_code=303
    )

# ==========================================================
# 4. CARREGAR ATLETAS APROVADOS
# ==========================================================

cursor.execute(
    f"""
    SELECT id, nome, entidade
    FROM atletas
    WHERE status = 'APROVADO'
      AND torneio_id = {p}
    """,
    (cfg["id"],)
)

atletas_lista = [dict(row) for row in cursor.fetchall()]

if len(atletas_lista) < 2:
    return RedirectResponse(
        url="/admin-painel/admin/inscricoes?erro=jogadores_insuficientes",
        status_code=303
    )

==========================================================

# 5. HISTÓRICO DE ADVERSÁRIOS
#
# Quando estamos refazendo a rodada atual, a própria rodada
# atual NÃO pode participar do histórico.
# ==========================================================

if refazer:

    cursor.execute(
        f"""
        SELECT atleta1_id, atleta2_id
        FROM confrontos
        WHERE atleta2_id IS NOT NULL
          AND rodada > 0
          AND rodada != {p}
          AND torneio_id = {p}
        """,
        (rodada_atual, cfg["id"])
    )

else:

    cursor.execute(
        f"""
        SELECT atleta1_id, atleta2_id
        FROM confrontos
        WHERE atleta2_id IS NOT NULL
          AND rodada > 0
          AND torneio_id = {p}
        """,
        (cfg["id"],)
    )

historico = {
    tuple(sorted((r["atleta1_id"], r["atleta2_id"])))
    for r in cursor.fetchall()
}

# ==========================================================
# 6. HISTÓRICO DE CHAPÉUS
# ==========================================================

if refazer:

    cursor.execute(
        f"""
        SELECT atleta1_id
        FROM confrontos
        WHERE atleta2_id IS NULL
          AND rodada > 0
          AND rodada != {p}
          AND torneio_id = {p}
        """,
        (rodada_atual, cfg["id"])
    )

else:

    cursor.execute(
        f"""
        SELECT atleta1_id
        FROM confrontos
        WHERE atleta2_id IS NULL
          AND rodada > 0
          AND torneio_id = {p}
        """,
        (cfg["id"],)
    )

atletas_que_ja_tiveram_chapeu = {
    r["atleta1_id"]
    for r in cursor.fetchall()
    if r["atleta1_id"] is not None
}

# ==========================================================
# 7. PREPARAR MAPA DOS ATLETAS
# ==========================================================

atletas_por_id = {
    atleta["id"]: atleta
    for atleta in atletas_lista
}

# ==========================================================
# 8. FUNÇÃO DE VALIDAÇÃO DE PAR
# ==========================================================

def par_valido(a, b):
    if a["id"] == b["id"]:
        return False

    # Nunca repetir adversário
    chave = tuple(sorted((a["id"], b["id"])))

    if chave in historico:
        return False

    return True

# ==========================================================
# 9. GERAÇÃO DE UMA SOLUÇÃO
#
# Aqui NÃO usamos ID, nome ou posição para decidir.
#
# A lista é embaralhada antes de cada tentativa.
#
# A entidade entra apenas como critério de qualidade:
# preferimos entidades diferentes na mesma mesa.
# ==========================================================

def gerar_solucao(atletas_disponiveis):
    restantes = atletas_disponiveis.copy()
    random.shuffle(restantes)

    pares = []

    while restantes:
        # Escolhe aleatoriamente um atleta entre os restantes.
        a1 = restantes.pop(
            random.randrange(len(restantes))
        )

        candidatos = [
            atleta
            for atleta in restantes
            if par_valido(a1, atleta)
        ]

        if not candidatos:
            return None

        # ==================================================
        # Prioridade:
        #
        # 1. adversário nunca enfrentado
        # 2. entidade diferente
        # 3. escolha aleatória
        #
        # Não usamos ID/nome como critério.
        # ==================================================

        candidatos_entidade_diferente = [
            atleta
            for atleta in candidatos
            if str(atleta.get("entidade", "")).strip().upper()
            != str(a1.get("entidade", "")).strip().upper()
        ]

        if candidatos_entidade_diferente:
            candidatos = candidatos_entidade_diferente

        random.shuffle(candidatos)

        # ==================================================
        # Para evitar escolhas ruins no início da montagem,
        # damos preferência ao candidato que deixa mais
        # possibilidades para os demais.
        #
        # Empates continuam sendo resolvidos aleatoriamente.
        # ==================================================

        melhor_candidatos = []
        melhor_grau = None

        for candidato in candidatos:

            grau = sum(
                1
                for outro in restantes
                if outro["id"] != candidato["id"]
                and par_valido(candidato, outro)
            )

            if melhor_grau is None or grau > melhor_grau:
                melhor_grau = grau
                melhor_candidatos = [candidato]

            elif grau == melhor_grau:
                melhor_candidatos.append(candidato)

        parceiro = random.choice(melhor_candidatos)

        restantes.remove(parceiro)

        pares.append((a1, parceiro))

    return pares

# ==========================================================
# 10. ESCOLHA DO CHAPÉU
#
# Se número de atletas for ímpar:
#
# - só pode receber chapéu quem ainda não recebeu;
# - tentamos diferentes candidatos;
# - para cada candidato tentamos montar a rodada inteira.
#
# Isso é importante porque o atleta escolhido para o chapéu
# pode influenciar a possibilidade de formar os demais pares.
# ==========================================================

candidatos_chapeu = []

if len(atletas_lista) % 2 == 1:

    candidatos_chapeu = [
        atleta
        for atleta in atletas_lista
        if atleta["id"] not in atletas_que_ja_tiveram_chapeu
    ]

    if not candidatos_chapeu:
        # Não existe mais ninguém elegível para receber chapéu.
        #
        # NÃO vamos quebrar a regra para gerar a rodada.
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=chapeus_esgotados",
            status_code=303
        )

    random.shuffle(candidatos_chapeu)

else:
    # Número par: ninguém recebe chapéu.
    candidatos_chapeu = [None]

# ==========================================================
# 11. PROCURAR A MELHOR COMBINAÇÃO VÁLIDA
#
# Não aceitamos simplesmente a primeira solução encontrada.
#
# Fazemos várias tentativas e escolhemos entre as melhores.
#
# REGRAS ABSOLUTAS:
# - adversário repetido continua proibido;
# - atleta não pode aparecer duas vezes;
# - chapéu não pode ser repetido.
#
# CRITÉRIO DE QUALIDADE:
# - preferir confrontos entre entidades diferentes;
# - manter aleatoriedade entre soluções equivalentes.
# ==========================================================

parceiros_finais = None
atleta_folga = None

melhores_solucoes = []
melhor_pontuacao = None

MAX_TENTATIVAS = 5000

for tentativa in range(MAX_TENTATIVAS):

    # ------------------------------------------------------
    # ESCOLHER POSSÍVEL CHAPÉU
    # ------------------------------------------------------

    if len(atletas_lista) % 2 == 1:

        atleta_folga_tentativa = random.choice(candidatos_chapeu)

        atletas_para_pareamento = [
            atleta
            for atleta in atletas_lista
            if atleta["id"] != atleta_folga_tentativa["id"]
        ]

    else:

        atleta_folga_tentativa = None
        atletas_para_pareamento = atletas_lista.copy()

    # ------------------------------------------------------
    # EMBARALHAR
    # ------------------------------------------------------

    random.shuffle(atletas_para_pareamento)

    # ------------------------------------------------------
    # TENTAR GERAR UMA SOLUÇÃO COMPLETA
    # ------------------------------------------------------

    solucao = gerar_solucao(atletas_para_pareamento)

    if solucao is None:
        continue

    # ------------------------------------------------------
    # AVALIAR A SOLUÇÃO
    #
    # Quanto MENOR a pontuação, melhor.
    # ------------------------------------------------------

    confrontos_mesma_entidade = 0

    for a1, a2 in solucao:

        if a1["entidade"] == a2["entidade"]:
            confrontos_mesma_entidade += 1

    # ------------------------------------------------------
    # SEGUNDO CRITÉRIO:
    #
    # Entre soluções com a mesma quantidade de confrontos
    # da mesma entidade, verificamos se algum desses pares
    # já aconteceu anteriormente.
    #
    # Isso NÃO invalida a solução, porque a regra absoluta
    # de adversário repetido já foi tratada por par_valido().
    #
    # Aqui é apenas um critério de desempate.
    # ------------------------------------------------------

    peso_historico_entidade = 0

    for a1, a2 in solucao:

        if a1["entidade"] != a2["entidade"]:
            continue

        chave = tuple(sorted((a1["id"], a2["id"])))

        if chave in historico:
            peso_historico_entidade += 1

    # ------------------------------------------------------
    # PONTUAÇÃO
    #
    # A prioridade principal é NÃO colocar atletas da mesma
    # entidade frente a frente.
    #
    # O random.random() garante que não fique sempre
    # escolhendo exatamente a mesma configuração.
    # ------------------------------------------------------

    pontuacao = (
        confrontos_mesma_entidade * 1000
        + peso_historico_entidade * 100
        + random.random()
    )

    # ------------------------------------------------------
    # PRIMEIRA SOLUÇÃO
    # ------------------------------------------------------

    if melhor_pontuacao is None:

        melhor_pontuacao = pontuacao

        melhores_solucoes = [{
            "solucao": solucao,
            "folga": atleta_folga_tentativa
        }]

    # ------------------------------------------------------
    # SOLUÇÃO MELHOR
    # ------------------------------------------------------

    elif pontuacao < melhor_pontuacao:

        melhor_pontuacao = pontuacao

        melhores_solucoes = [{
            "solucao": solucao,
            "folga": atleta_folga_tentativa
        }]

    # ------------------------------------------------------
    # SOLUÇÃO EQUIVALENTE
    #
    # Mantemos também para preservar aleatoriedade.
    # ------------------------------------------------------

    elif pontuacao == melhor_pontuacao:

        melhores_solucoes.append({
            "solucao": solucao,
            "folga": atleta_folga_tentativa
        })

# ==========================================================
# 12. ESCOLHER A MELHOR SOLUÇÃO ENCONTRADA
# ==========================================================

if not melhores_solucoes:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=nao_foi_possivel_formar_rodada",
        status_code=303
    )

# Escolhe aleatoriamente entre as melhores soluções equivalentes.
# Isso mantém o sorteio imprevisível.
solucao_escolhida = random.choice(melhores_solucoes)

parceiros_finais = solucao_escolhida["solucao"]
atleta_folga = solucao_escolhida["folga"]

# ==========================================================
# 13. VALIDAÇÃO FINAL DE SEGURANÇA
#
# Antes de gravar qualquer coisa no banco, conferimos:
#
# - nenhum adversário repetido;
# - nenhum atleta duplicado;
# - chapéu permitido;
# - todas as pessoas utilizadas.
# ==========================================================

atletas_usados = set()
pares_validacao = set()

for a1, a2 in parceiros_finais:

    if a1["id"] in atletas_usados or a2["id"] in atletas_usados:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=erro_interno_sorteio",
            status_code=303
        )

    atletas_usados.add(a1["id"])
    atletas_usados.add(a2["id"])

    chave = tuple(sorted((a1["id"], a2["id"])))

    if chave in historico:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=adversario_repetido_bloqueado",
            status_code=303
        )

    if chave in pares_validacao:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=par_duplicado_bloqueado",
            status_code=303
        )

    pares_validacao.add(chave)

# ==========================================================
# 14. VALIDAR CHAPÉU
# ==========================================================

if atleta_folga:

    if atleta_folga["id"] in atletas_usados:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=atleta_chapeu_duplicado",
            status_code=303
        )

    if atleta_folga["id"] in atletas_que_ja_tiveram_chapeu:
        return RedirectResponse(
            url="/admin-painel/admin/jogos?erro=chapeu_repetido_bloqueado",
            status_code=303
        )

    atletas_usados.add(atleta_folga["id"])

# ==========================================================
# 15. CONFERIR SE TODOS OS ATLETAS FORAM UTILIZADOS
# ==========================================================

ids_atletas = {atleta["id"] for atleta in atletas_lista}

if atletas_usados != ids_atletas:

    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=atletas_nao_distribuidos",
        status_code=303
    )

# ==========================================================
# 16. EMBARALHAR A ORDEM DAS MESAS
#
# Mesmo depois de encontrar os pares, não queremos que
# a ordem dos pares denuncie qualquer critério.
# ==========================================================

random.shuffle(parceiros_finais)

# ==========================================================
# 16.5. SE FOR REFAZER, REMOVER A RODADA ANTIGA
#
# Só chegamos aqui depois de encontrar uma nova solução
# válida. Assim, nunca apagamos a rodada sem ter uma
# nova combinação pronta.
# ==========================================================

if refazer:

    cursor.execute(
        f"""
        DELETE FROM confrontos
        WHERE rodada = {p}
          AND torneio_id = {p}
        """,
        (rodada_atual, cfg["id"])
    )

# ==========================================================
# 17. GRAVAR AS MESAS
# ==========================================================

mesa = 1

for a1, a2 in parceiros_finais:

    cursor.execute(
        f"""
        INSERT INTO confrontos (
            torneio_id,
            rodada,
            mesa,
            atleta1_id,
            atleta2_id,
            atleta1_nome,
            atleta2_nome
        )
        VALUES (
            {p},
            {p},
            {p},
            {p},
            {p},
            {p},
            {p}
        )
        """,
        (
            cfg["id"],
            proxima_rodada,
            mesa,
            a1["id"],
            a2["id"],
            a1["nome"],
            a2["nome"]
        )
    )

    mesa += 1

# ==========================================================
# 18. GRAVAR CHAPÉU
# ==========================================================

if atleta_folga:

    cursor.execute(
        f"""
        INSERT INTO confrontos (
            torneio_id,
            rodada,
            mesa,
            atleta1_id,
            atleta2_id,
            atleta1_nome,
            atleta2_nome,
            tipo_placar,
            sets1,
            sets2,
            tentos1,
            tentos2,
            vencedor_id
        )
        VALUES (
            {p},
            {p},
            {p},
            {p},
            NULL,
            {p},
            'FOLGA - GANHOU PONTOS',
            '2x0',
            3,
            0,
            72,
            0,
            {p}
        )
        """,
        (
            cfg["id"],
            proxima_rodada,
            mesa,
            atleta_folga["id"],
            atleta_folga["nome"],
            atleta_folga["id"]
        )
    )

# ==========================================================
# 19. CRONÔMETRO
# ==========================================================

novo_tempo_seg = (
    tempo_minutos * 60
    if tempo_minutos
    else int(cfg.get("crono_tempo_restante_seg", 1800))
)

cursor.execute(
    f"""
    UPDATE torneios
    SET
        crono_ativo = 0,
        crono_fim_ms = 0,
        crono_tempo_restante_seg = {p}
    WHERE id = {p}
    """,
    (novo_tempo_seg, cfg["id"])
)

# ==========================================================
# 20. CONFIRMAR TRANSAÇÃO
# ==========================================================

db.commit()

return RedirectResponse(
    url="/admin-painel/admin/jogos",
    status_code=303
)

@app.post("/admin/disparar-matamata")
@app.post("/admin-painel/admin/disparar-matamata")
def disparar_matamata(corte: int = Form(...), tempo_minutos: int = Form(None), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

cursor.execute(f"SELECT COALESCE(MAX(rodada), 0) FROM confrontos WHERE rodada > 0 AND torneio_id = {p}", (cfg["id"],))
r_atual = cursor.fetchone()[0]
if r_atual > 0:
    cursor.execute(f"SELECT COUNT(*) FROM confrontos WHERE rodada = {p} AND torneio_id = {p} AND vencedor_id IS NULL", (r_atual, cfg["id"]))
    if cursor.fetchone()[0] > 0:
        return RedirectResponse(url="/admin-painel/admin/classificacao?erro=conclua_rodada_atual", status_code=303)

ranking = obtener_ranking_fase_classificatoria(cursor, cfg["id"])
if len(ranking) < corte:
    return RedirectResponse(url="/admin-painel/admin/classificacao?erro=atletas_insuficientes_para_corte", status_code=303)

# Desistentes permanecem na classificação, mas não ocupam vaga na próxima fase.
classificados = [atleta for atleta in ranking if atleta.get("status") != "DESISTENTE"][:corte]
if len(classificados) < corte:
    return RedirectResponse(url="/admin-painel/admin/classificacao?erro=atletas_insuficientes_para_corte", status_code=303)
cursor.execute(f"UPDATE torneios SET fase_torneio = 'MATA_MATA' WHERE id = {p}", (cfg["id"],))

if corte == 16: fase_id = -1
elif corte == 8: fase_id = -2
elif corte == 4: fase_id = -3
else: fase_id = -2

confrontos_fase = []
if corte == 8:
    confrontos_fase = [
        (classificados[0], classificados[7]), (classificados[3], classificados[4]),
        (classificados[1], classificados[6]), (classificados[2], classificados[5])
    ]
elif corte == 16:
    confrontos_fase = [
        (classificados[0], classificados[15]), (classificados[7], classificados[8]),
        (classificados[3], classificados[12]), (classificados[4], classificados[11]),
        (classificados[1], classificados[14]), (classificados[6], classificados[9]),
        (classificados[2], classificados[13]), (classificados[5], classificados[10])
    ]
elif corte == 4:
    confrontos_fase = [
        (classificados[0], classificados[3]), (classificados[1], classificados[2])
    ]

for idx, (a1, a2) in enumerate(confrontos_fase, start=1):
    cursor.execute(f'''
        INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})
    ''', (cfg["id"], fase_id, idx, a1["id"], a2["id"], a1["nome"], a2["nome"]))
    
novo_tempo_seg = (tempo_minutos * 60) if tempo_minutos else int(cfg.get("crono_tempo_restante_seg", 1800))
cursor.execute(f"UPDATE torneios SET crono_ativo = 0, crono_fim_ms = 0, crono_tempo_restante_seg = {p} WHERE id = {p}", (novo_tempo_seg, cfg["id"],))
db.commit()
return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.post("/admin/avancar-matamata")
@app.post("/admin-painel/admin/avancar-matamata")
def avancar_matamata(tempo_minutos: int = Form(None), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"
cursor.execute(f"SELECT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY id DESC LIMIT 1", (cfg["id"],))
row_f = cursor.fetchone()
if not row_f:
return RedirectResponse(url="/admin-painel/admin/jogos?erro=nenhum_jogo", status_code=303)

fase_atual = row_f["rodada"]

cursor.execute(f"SELECT COUNT(*) FROM confrontos WHERE rodada = {p} AND torneio_id = {p} AND vencedor_id IS NULL", (fase_atual, cfg["id"]))
if cursor.fetchone()[0] > 0:
    return RedirectResponse(url="/admin-painel/admin/jogos?erro=jogos_eliminatorios_pendentes", status_code=303)
    
cursor.execute(f"SELECT * FROM confrontos WHERE rodada = {p} AND torneio_id = {p} ORDER BY mesa ASC", (fase_atual, cfg["id"]))
jogos_concluidos = cursor.fetchall()

if fase_atual == -4:
    return RedirectResponse(url="/admin-painel/admin/podio", status_code=303)

proxima_fase = fase_atual - 1

if fase_atual in [-1, -2]:
    nova_mesa = 1
    for i in range(0, len(jogos_concluidos), 2):
        j1 = jogos_concluidos[i]
        j2 = jogos_concluidos[i+1] if (i+1) < len(jogos_concluidos) else j1 
        
        v1_id = j1["vencedor_id"]
        v1_nome = j1["atleta1_nome"] if v1_id == j1["atleta1_id"] else j1["atleta2_nome"]
        v2_id = j2["vencedor_id"]
        v2_nome = j2["atleta1_nome"] if v2_id == j2["atleta1_id"] else j2["atleta2_nome"]
        
        cursor.execute(f'INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})',
                       (cfg["id"], proxima_fase, nova_mesa, v1_id, v2_id, v1_nome, v2_nome))
        nova_mesa += 1
        
elif fase_atual == -3:
    if len(jogos_concluidos) < 2:
        return RedirectResponse(url="/admin-painel/admin/jogos?erro=semifinais_insuficientes", status_code=303)
        
    j1 = jogos_concluidos[0]
    j2 = jogos_concluidos[1]
    
    v1_id = j1["vencedor_id"]
    v2_id = j2["vencedor_id"]
    
    v1_nome = j1["atleta1_nome"] if v1_id == j1["atleta1_id"] else j1["atleta2_nome"]
    v2_nome = j2["atleta1_nome"] if v2_id == j2["atleta1_id"] else j2["atleta2_nome"]
    p1_id = j1["atleta2_id"] if v1_id == j1["atleta1_id"] else j1["atleta1_id"]
    p1_nome = j1["atleta2_nome"] if v1_id == j1["atleta1_id"] else j1["atleta1_nome"]
    p2_id = j2["atleta2_id"] if v2_id == j2["atleta1_id"] else j2["atleta1_id"]
    p2_nome = j2["atleta2_nome"] if v2_id == j2["atleta1_id"] else j2["atleta1_nome"]

    cursor.execute(f'INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES ({p}, -4, 1, {p}, {p}, {p}, {p})', (cfg["id"], v1_id, v2_id, v1_nome, v2_nome))
    cursor.execute(f'INSERT INTO confrontos (torneio_id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome) VALUES ({p}, -4, 2, {p}, {p}, {p}, {p})', (cfg["id"], p1_id, p2_id, p1_nome, p2_nome))
    
novo_tempo_seg = (tempo_minutos * 60) if tempo_minutos else int(cfg.get("crono_tempo_restante_seg", 1800))
cursor.execute(f"UPDATE torneios SET crono_ativo = 0, crono_fim_ms = 0, crono_tempo_restante_seg = {p} WHERE id = {p}", (novo_tempo_seg, cfg["id"],))
db.commit()
return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

def aplicar_salvamento_placar(cursor, confronto_id, vencedor_id, tipo_placar, tentos1, tentos2, flores1, flores2):
p = "%s" if DATABASE_URL else "?"
cursor.execute(f"SELECT atleta1_id, atleta2_id FROM confrontos WHERE id = {p}", (confronto_id,))
conf = cursor.fetchone()
id1, id2 = conf["atleta1_id"], conf["atleta2_id"]

if tipo_placar == "2x0":
    if vencedor_id == id1:
        if tentos1 != 72 or tentos2 > 46:
            raise HTTPException(status_code=400, detail="Para 2x0, o vencedor deve ter exatamente 72 tentos e o perdedor no máximo 46.")
    elif vencedor_id == id2:
        if tentos2 != 72 or tentos1 > 46:
            raise HTTPException(status_code=400, detail="Para 2x0, o vencedor deve ter exatamente 72 tentos e o perdedor no máximo 46.")
elif tipo_placar == "2x1":
    if vencedor_id == id1:
        if tentos1 < 48 or tentos2 < 24:
            raise HTTPException(status_code=400, detail="Para 2x1, o vencedor precisa de no mínimo 48 tentos e o perdedor no mínimo 24.")
    elif vencedor_id == id2:
        if tentos2 < 48 or tentos1 < 24:
            raise HTTPException(status_code=400, detail="Para 2x1, o vencedor precisa de no mínimo 48 tentos e o perdedor no mínimo 24.")

s1 = (3 if tipo_placar == "2x0" else 2) if vencedor_id == id1 else (0 if tipo_placar == "2x0" else 1)
s2 = (3 if tipo_placar == "2x0" else 2) if vencedor_id == id2 else (0 if tipo_placar == "2x0" else 1)
t1 = 72 if (tipo_placar == "2x0" and vencedor_id == id1) else tentos1
t2 = 72 if (tipo_placar == "2x0" and vencedor_id == id2) else tentos2

cursor.execute(f'UPDATE confrontos SET tipo_placar = {p}, vencedor_id = {p}, sets1 = {p}, sets2 = {p}, tentos1 = {p}, tentos2 = {p}, flores1 = {p}, flores2 = {p} WHERE id = {p}',
               (tipo_placar, vencedor_id, s1, s2, t1, t2, flores1, flores2, confronto_id))

@app.post("/admin/salvar-placar")
@app.post("/admin-painel/admin/salvar-placar")
def salvar_placar(confronto_id: int = Form(...), vencedor_id: int = Form(...), tipo_placar: str = Form(...), tentos1: int = Form(...), tentos2: int = Form(...), flores1: int = Form(0), flores2: int = Form(0), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
try:
aplicar_salvamento_placar(cursor, confronto_id, vencedor_id, tipo_placar, tentos1, tentos2, flores1, flores2)
except HTTPException as e:
return JSONResponse(status_code=e.status_code, content={"erro": e.detail})
db.commit()
return RedirectResponse(url="/admin-painel/admin/jogos", status_code=303)

@app.post("/admin/ajustar-confronto")
@app.post("/admin-painel/admin/ajustar-confronto")
def ajustar_confronto_admin(
confronto_id_origem: int = Form(...),
jogador_origem_id: int = Form(...),
confronto_id_destino: int = Form(...),
jogador_destino_id: int = Form(...),
db=Depends(get_db),
auth: bool = Depends(verificar_admin)
):
"""
Troca dois atletas entre duas mesas da rodada atual.

Segurança:
- somente a rodada atualmente exibida pode ser alterada;
- nenhuma das duas partidas pode ter resultado lançado;
- folga automática não pode ser usada nesta troca;
- cada atleta continua aparecendo uma única vez na rodada;
- se a troca criar adversário repetido, a troca é bloqueada
  definitivamente, sem possibilidade de exceção.
"""
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

if not cfg:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=torneio_nao_encontrado",
        status_code=303
    )

cursor.execute(
    f"SELECT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY id DESC LIMIT 1",
    (cfg["id"],)
)
ultima = cursor.fetchone()
if not ultima:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=nenhum_jogo",
        status_code=303
    )

rodada_atual = ultima["rodada"]

if rodada_atual <= 0:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=ajuste_apenas_classificatoria",
        status_code=303
    )

if confronto_id_origem == confronto_id_destino:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=mesma_mesa",
        status_code=303
    )

cursor.execute(
    f"""
    SELECT id, rodada, mesa, atleta1_id, atleta2_id, atleta1_nome, atleta2_nome,
           vencedor_id
    FROM confrontos
    WHERE id IN ({p}, {p})
      AND torneio_id = {p}
    ORDER BY id
    """,
    (confronto_id_origem, confronto_id_destino, cfg["id"])
)
encontrados = cursor.fetchall()

if len(encontrados) != 2:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=confronto_nao_encontrado",
        status_code=303
    )

confs = {int(r["id"]): r for r in encontrados}
origem = confs.get(confronto_id_origem)
destino = confs.get(confronto_id_destino)

if not origem or not destino:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=confronto_nao_encontrado",
        status_code=303
    )

if origem["rodada"] != rodada_atual or destino["rodada"] != rodada_atual:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=rodada_invalida",
        status_code=303
    )

# Não mexer em partidas já lançadas nem na folga automática.
if origem["vencedor_id"] is not None or destino["vencedor_id"] is not None:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=ajuste_jogo_ja_lancado",
        status_code=303
    )

if origem["atleta2_id"] is None or destino["atleta2_id"] is None:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=ajuste_folga_nao_permitida",
        status_code=303
    )

jogadores_origem = {int(origem["atleta1_id"]), int(origem["atleta2_id"])}
jogadores_destino = {int(destino["atleta1_id"]), int(destino["atleta2_id"])}

if jogador_origem_id not in jogadores_origem or jogador_destino_id not in jogadores_destino:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=atleta_invalido",
        status_code=303
    )

if jogador_origem_id == jogador_destino_id:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=mesmo_atleta",
        status_code=303
    )

# Descobre quem permanece em cada mesa após a troca.
restante_origem = (
    origem["atleta2_id"]
    if int(origem["atleta1_id"]) == jogador_origem_id
    else origem["atleta1_id"]
)
restante_destino = (
    destino["atleta2_id"]
    if int(destino["atleta1_id"]) == jogador_destino_id
    else destino["atleta1_id"]
)

novos_pares = [
    tuple(sorted((int(restante_origem), int(jogador_destino_id)))),
    tuple(sorted((int(restante_destino), int(jogador_origem_id))))
]

# Histórico anterior à rodada atual.
cursor.execute(
    f"""
    SELECT atleta1_id, atleta2_id
    FROM confrontos
    WHERE torneio_id = {p}
      AND rodada > 0
      AND rodada != {p}
      AND atleta2_id IS NOT NULL
    """,
    (cfg["id"], rodada_atual)
)
historico = {
    tuple(sorted((int(r["atleta1_id"]), int(r["atleta2_id"]))))
    for r in cursor.fetchall()
    if r["atleta1_id"] is not None and r["atleta2_id"] is not None
}

repetidos = [par for par in novos_pares if par in historico]

# Regra absoluta:
# confronto já realizado NUNCA pode ser recriado por ajuste manual.
# A validação é feita no backend para impedir qualquer contorno
# da interface administrativa.
if repetidos:
    return RedirectResponse(
        url="/admin-painel/admin/jogos?erro=ajuste_repeticao",
        status_code=303
    )

# Faz a troca somente dos atletas. Resultado, placar e demais dados
# permanecem intocados porque a partida ainda não começou.
if int(origem["atleta1_id"]) == jogador_origem_id:
    origem_novo1_id = jogador_destino_id
    origem_novo1_nome = destino["atleta1_nome"] if int(destino["atleta1_id"]) == jogador_destino_id else destino["atleta2_nome"]
else:
    origem_novo1_id = origem["atleta1_id"]
    origem_novo1_nome = origem["atleta1_nome"]

if int(origem["atleta2_id"]) == jogador_origem_id:
    origem_novo2_id = jogador_destino_id
    origem_novo2_nome = destino["atleta1_nome"] if int(destino["atleta1_id"]) == jogador_destino_id else destino["atleta2_nome"]
else:
    origem_novo2_id = origem["atleta2_id"]
    origem_novo2_nome = origem["atleta2_nome"]

if int(destino["atleta1_id"]) == jogador_destino_id:
    destino_novo1_id = jogador_origem_id
    destino_novo1_nome = origem["atleta1_nome"] if int(origem["atleta1_id"]) == jogador_origem_id else origem["atleta2_nome"]
else:
    destino_novo1_id = destino["atleta1_id"]
    destino_novo1_nome = destino["atleta1_nome"]

if int(destino["atleta2_id"]) == jogador_destino_id:
    destino_novo2_id = jogador_origem_id
    destino_novo2_nome = origem["atleta1_nome"] if int(origem["atleta1_id"]) == jogador_origem_id else origem["atleta2_nome"]
else:
    destino_novo2_id = destino["atleta2_id"]
    destino_novo2_nome = destino["atleta2_nome"]

try:
    cursor.execute(
        f"""
        UPDATE confrontos
        SET atleta1_id = {p}, atleta1_nome = {p},
            atleta2_id = {p}, atleta2_nome = {p}
        WHERE id = {p} AND torneio_id = {p}
        """,
        (
            origem_novo1_id, origem_novo1_nome,
            origem_novo2_id, origem_novo2_nome,
            origem["id"], cfg["id"]
        )
    )

    cursor.execute(
        f"""
        UPDATE confrontos
        SET atleta1_id = {p}, atleta1_nome = {p},
            atleta2_id = {p}, atleta2_nome = {p}
        WHERE id = {p} AND torneio_id = {p}
        """,
        (
            destino_novo1_id, destino_novo1_nome,
            destino_novo2_id, destino_novo2_nome,
            destino["id"], cfg["id"]
        )
    )

    db.commit()
except Exception:
    db.rollback()
    raise

return RedirectResponse(
    url="/admin-painel/admin/jogos?sucesso=ajuste_realizado",
    status_code=303
)

@app.get("/admin/classificacao")
@app.get("/admin-painel/admin/classificacao")
def aba_classificacao_e_auditoria(request: Request, rodada_filtro: int = None, db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cfg = atualizar_e_obter_cronometro(db)
p = "%s" if DATABASE_URL else "?"

if cfg["fase_torneio"] == "INSCRICAO":
    return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

cursor = db.cursor()
lista_classificacao = obtener_ranking_fase_classificatoria(cursor, cfg["id"])

cursor.execute(f"SELECT DISTINCT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY rodada DESC", (cfg["id"],))
todas_rodadas = [r["rodada"] for r in cursor.fetchall()]

rodada_selecionada = rodada_filtro if rodada_filtro is not None else (todas_rodadas[0] if todas_rodadas else 1)
cursor.execute(f"SELECT * FROM confrontos WHERE rodada = {p} AND torneio_id = {p} ORDER BY mesa ASC", (rodada_selecionada, cfg["id"]))
confrontos_auditoria = cursor.fetchall()

return templates.TemplateResponse(
    request=request, name="admin_classificacao.html",
    context={"config": cfg, "classificacao": lista_classificacao, "todas_rodadas": todas_rodadas, "rodada_selecionada": rodada_selecionada, "confrontos_auditoria": confrontos_auditoria, "aba_ativa": "classificacao"}
)

@app.post("/admin/auditoria/corrigir")
@app.post("/admin-painel/admin/auditoria/corrigir")
def corrigir_placar_auditoria(confronto_id: int = Form(...), vencedor_id: int = Form(...), tipo_placar: str = Form(...), tentos1: int = Form(...), tentos2: int = Form(...), flores1: int = Form(0), flores2: int = Form(0), rodada_retorno: int = Form(...), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
try:
aplicar_salvamento_placar(cursor, confronto_id, vencedor_id, tipo_placar, tentos1, tentos2, flores1, flores2)
except HTTPException as e:
return JSONResponse(status_code=e.status_code, content={"erro": e.detail})
db.commit()
return RedirectResponse(url=f"/admin-painel/admin/classificacao?rodada_filtro={rodada_retorno}", status_code=303)

@app.get("/admin/podio")
@app.get("/admin-painel/admin/podio")
def exibir_podio(request: Request, db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cfg = atualizar_e_obter_cronometro(db)
p = "%s" if DATABASE_URL else "?"

if cfg["fase_torneio"] == "INSCRICAO":
    return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=inicie_o_torneio", status_code=303)

cursor = db.cursor()
cursor.execute(f"SELECT COUNT(*) FROM confrontos WHERE rodada = -4 AND torneio_id = {p} AND vencedor_id IS NULL", (cfg["id"],))
if cursor.fetchone()[0] > 0:
    return RedirectResponse(url="/admin-painel/admin/jogos?erro=finais_nao_concluidas", status_code=303)
    
cursor.execute(f"SELECT * FROM confrontos WHERE rodada = -4 AND mesa = 1 AND torneio_id = {p}", (cfg["id"],))
jogo_final = cursor.fetchone()
cursor.execute(f"SELECT * FROM confrontos WHERE rodada = -4 AND mesa = 2 AND torneio_id = {p}", (cfg["id"],))
jogo_terceiro = cursor.fetchone()

if not jogo_final or not jogo_terceiro:
    return RedirectResponse(url="/admin-painel/admin/jogos?erro=finais_nao_geradas", status_code=303)

campeao = jogo_final["atleta1_nome"] if jogo_final["vencedor_id"] == jogo_final["atleta1_id"] else jogo_final["atleta2_nome"]
vice = jogo_final["atleta2_nome"] if jogo_final["vencedor_id"] == jogo_final["atleta1_id"] else jogo_final["atleta1_nome"]

third_place = jogo_terceiro["atleta1_nome"] if jogo_terceiro["vencedor_id"] == jogo_terceiro["atleta1_id"] else jogo_terceiro["atleta2_nome"]
fourth_place = jogo_terceiro["atleta2_nome"] if jogo_terceiro["vencedor_id"] == jogo_terceiro["atleta1_id"] else jogo_terceiro["atleta1_nome"]

cursor.execute(f"SELECT id, nome FROM atletas WHERE status = 'APROVADO' AND torneio_id = {p}", (cfg["id"],))
atletas = cursor.fetchall()

rei_nome = "Nenhum"
max_flores = 0
for atl in atletas:
    a_id = atl["id"]
    cursor.execute(f"SELECT COALESCE(SUM(flores1), 0) FROM confrontos WHERE atleta1_id = {p} AND torneio_id = {p}", (a_id, cfg["id"]))
    f1 = cursor.fetchone()[0]
    cursor.execute(f"SELECT COALESCE(SUM(flores2), 0) FROM confrontos WHERE atleta2_id = {p} AND torneio_id = {p}", (a_id, cfg["id"]))
    f2 = cursor.fetchone()[0]
        
    total_f = f1 + f2
    if total_f > max_flores:
        max_flores = total_f
        rei_nome = atl["nome"]

return templates.TemplateResponse(
    request=request, name="admin_podio.html",
    context={"config": cfg, "campeao": campeao, "vice": vice, "terceiro": third_place, "quarto": fourth_place, "rei_nome": rei_nome, "max_flores": max_flores, "aba_ativa": "podio"}
)

@app.post("/admin/encerrar-e-salvar")
@app.post("/admin-painel/admin/encerrar-e-salvar")
def encerrar_e_salvar(campeao: str = Form(...), vice: str = Form(...), terceiro: str = Form(...), quarto: str = Form(...), rei: str = Form(...), flores: int = Form(...), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

cursor.execute(f'INSERT INTO historico_campeoes (torneio_id, nome_torneio, campeao, vice, terceiro, quarto, rei_das_flores, qtd_flores) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})',
               (cfg["id"], cfg["nome_torneio"], campeao, vice, terceiro, quarto, rei, flores))

cursor.execute(f"UPDATE torneios SET fase_torneio = 'CONCLUIDO', crono_ativo = 0 WHERE id = {p}", (cfg["id"],))

novo_nome_sugerido = f"Torneio de Truco Cego - Edição {cfg['id'] + 1}"

# Define o tempo padrão para o próximo torneio (recupera o atual ou seta 3000 segundos por padrão)
tempo_restante_novo = cfg.get("crono_tempo_restante_seg", 3000) if cfg else 3000

cursor.execute(f'''
    INSERT INTO torneios (nome_torneio, taxa_inscricao, max_rodadas_classificatoria, crono_tempo_restante_seg, fase_torneio, crono_fim_ms) 
    VALUES ({p}, 45.00, {p}, {p}, 'INSCRICAO', 0)
    ''', (novo_nome_sugerido, cfg["max_rodadas_classificatoria"], tempo_restante_novo))

db.commit()
return RedirectResponse(url="/admin-painel/admin/historico?sucesso=torneio_imortalizado", status_code=303)

@app.get("/admin/historico")
@app.get("/admin-painel/admin/historico")
def exibir_historico(request: Request, db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cfg = atualizar_e_obter_cronometro(db)
cursor = db.cursor()
cursor.execute("SELECT * FROM historico_campeoes ORDER BY id DESC")
galeria = cursor.fetchall()
return templates.TemplateResponse(request=request, name="admin_historico.html", context={"config": cfg, "galeria": galeria, "aba_ativa": "historico"})

@app.post("/admin/historico/excluir/{historico_id}")
@app.post("/admin-painel/admin/historico/excluir/{historico_id}")
def excluir_historico(
historico_id: int,
db=Depends(get_db),
auth: bool = Depends(verificar_admin)
):
cursor = db.cursor()
p = "%s" if DATABASE_URL else "?"

try:
    # ==========================================================
    # LOCALIZAR O REGISTRO DA GALERIA
    # ==========================================================

    cursor.execute(
        f"""
        SELECT torneio_id
        FROM historico_campeoes
        WHERE id = {p}
        """,
        (historico_id,)
    )

    historico = cursor.fetchone()

    if not historico:
        return RedirectResponse(
            url="/admin-painel/admin/historico?erro=historico_nao_encontrado",
            status_code=303
        )

    torneio_id = historico["torneio_id"]

    # ==========================================================
    # EXCLUIR O REGISTRO DA GALERIA
    # ==========================================================

    cursor.execute(
        f"""
        DELETE FROM historico_campeoes
        WHERE id = {p}
        """,
        (historico_id,)
    )

    # ==========================================================
    # EXCLUIR OS DADOS DO TORNEIO ARQUIVADO
    # ==========================================================

    if torneio_id is not None:

        cursor.execute(
            f"""
            DELETE FROM confrontos
            WHERE torneio_id = {p}
            """,
            (torneio_id,)
        )

        cursor.execute(
            f"""
            DELETE FROM atletas
            WHERE torneio_id = {p}
            """,
            (torneio_id,)
        )

        cursor.execute(
            f"""
            DELETE FROM torneios
            WHERE id = {p}
            """,
            (torneio_id,)
        )

    db.commit()

except Exception:
    db.rollback()
    raise

return RedirectResponse(
    url="/admin-painel/admin/historico?sucesso=historico_excluido",
    status_code=303
) 

@app.post("/admin/reset-mantendo-atletas")
@app.post("/admin-painel/admin/reset-mantendo-atletas")
def reset_mantendo_atletas(
db=Depends(get_db),
auth: bool = Depends(verificar_admin)
):
"""
Reinicia somente o andamento do torneio atual, preservando os atletas.
É diferente do reset-total-testes, que apaga os atletas.
"""
cursor = db.cursor()
p = "%s" if DATABASE_URL else "?"

try:
    cfg = obtener_torneio_ativo(cursor)

    if not cfg:
        return RedirectResponse(
            url="/admin-painel/admin/inscricoes?erro=torneio_nao_encontrado",
            status_code=303
        )

    # Apaga somente os confrontos do torneio atual.
    cursor.execute(
        f"DELETE FROM confrontos WHERE torneio_id = {p}",
        (cfg["id"],)
    )

    # Todos os atletas cadastrados neste torneio voltam a participar.
    # Isso inclui quem havia sido marcado como DESISTENTE.
    cursor.execute(
        f"""
        UPDATE atletas
        SET status = 'APROVADO'
        WHERE torneio_id = {p}
        """,
        (cfg["id"],)
    )

    # O mesmo torneio é devolvido ao estado de inscrição.
    # Assim preservamos nome, atletas e demais dados cadastrais.
    cursor.execute(
        f"""
        UPDATE torneios
        SET fase_torneio = 'INSCRICAO',
            crono_ativo = 0,
            crono_fim_ms = 0,
            crono_tempo_restante_seg = 3000
        WHERE id = {p}
        """,
        (cfg["id"],)
    )

    db.commit()

except Exception:
    db.rollback()
    raise

return RedirectResponse(
    url="/admin-painel/admin/inscricoes?sucesso=torneio_reiniciado_mantendo_atletas",
    status_code=303
)

@app.post("/admin/reset-total-testes")
@app.post("/admin-painel/admin/reset-total-testes")
def reset_total_testes(
db=Depends(get_db),
auth: bool = Depends(verificar_admin)
):
cursor = db.cursor()
p = "%s" if DATABASE_URL else "?"

try:

    # ==========================================================
    # LIMPEZA DOS DADOS OPERACIONAIS
    # ==========================================================
    #
    # IMPORTANTE:
    # NÃO apagamos a tabela historico_campeoes.
    #
    # A Galeria de Campeões é permanente.
    #
    cursor.execute("DELETE FROM confrontos;")
    cursor.execute("DELETE FROM atletas;")

    # ==========================================================
    # PRESERVAR TORNEIOS QUE JÁ ESTÃO NA GALERIA
    # ==========================================================
    #
    # Torneios que possuem registro em historico_campeoes
    # permanecem preservados.
    #
    cursor.execute("""
        DELETE FROM torneios
        WHERE id NOT IN (
            SELECT torneio_id
            FROM historico_campeoes
            WHERE torneio_id IS NOT NULL
        );
    """)

    # ==========================================================
    # CRIAR NOVO TORNEIO
    # ==========================================================

    cursor.execute(
        f"""
        INSERT INTO torneios (
            nome_torneio,
            taxa_inscricao,
            max_rodadas_classificatoria,
            crono_tempo_restante_seg,
            fase_torneio,
            crono_ativo,
            crono_fim_ms
        )
        VALUES (
            {p},
            {p},
            {p},
            {p},
            {p},
            {p},
            {p}
        )
        """,
        (
            "Torneio de Truco Cego",
            45.00,
            5,
            3000,
            "INSCRICAO",
            0,
            0
        )
    )

    # ==========================================================
    # CONFIRMAR
    # ==========================================================

    db.commit()

except Exception:
    db.rollback()
    raise

return RedirectResponse(
    url="/admin-painel/admin/inscricoes?sucesso=banco_zerado",
    status_code=303
)

@app.post("/admin/cadastrar-direto")
@app.post("/admin-painel/admin/cadastrar-direto")
def cadastrar_direto_admin(nome: str = Form(...), entity: str = Form(None), entidade: str = Form("INDIVIDUAL"), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
fabric_nome = entity if entity else entidade
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
entidade_limpa = fabric_nome.strip().upper() if fabric_nome else "AVULSO"
p = "%s" if DATABASE_URL else "?"

cursor.execute(f"INSERT INTO atletas (torneio_id, nome, entidade, status) VALUES ({p}, {p}, {p}, 'APROVADO')", (cfg["id"], nome.strip().upper(), entidade_limpa))
db.commit()
return RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)

@app.post("/admin/acao-atleta")
@app.post("/admin-painel/admin/acao-atleta")
def acao_atleta_admin(id_atleta: int = Form(...), acao: str = Form(...), db=Depends(get_db), auth: bool = Depends(verificar_admin)):
cursor = db.cursor()
p = "%s" if DATABASE_URL else "?"
cfg = obtener_torneio_ativo(cursor)

if acao == "aprovar":
    cursor.execute(f"UPDATE atletas SET status = 'APROVADO' WHERE id = {p}", (id_atleta,))
elif acao == "desistir":
    if cfg["fase_torneio"] == "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=torneio_nao_iniciado", status_code=303)
    cursor.execute(f"UPDATE atletas SET status = 'DESISTENTE' WHERE id = {p}", (id_atleta,))
elif acao == "reativar":
    if cfg["fase_torneio"] != "CLASSIFICATORIA":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=reativacao_indisponivel", status_code=303)
    cursor.execute(f"UPDATE atletas SET status = 'APROVADO' WHERE id = {p}", (id_atleta,))
elif acao == "excluir":
    if cfg["fase_torneio"] != "INSCRICAO":
        return RedirectResponse(url="/admin-painel/admin/inscricoes?erro=exclusao_bloqueada_torneio_iniciado", status_code=303)
    cursor.execute(f"DELETE FROM atletas WHERE id = {p}", (id_atleta,))
db.commit()
return RedirectResponse(url="/admin-painel/admin/inscricoes", status_code=303)

@app.get("/telao", response_class=HTMLResponse)
def pagina_telao_publico(request: Request, db=Depends(get_db)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"
rodada_atual = 1
if cfg:
cursor.execute(f"SELECT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY id DESC LIMIT 1", (cfg["id"],))
row_r = cursor.fetchone()
rodada_atual = row_r["rodada"] if row_r else 1
return templates.TemplateResponse(request=request, name="telao.html", context={"config": cfg, "rodada": rodada_atual})

@app.get("/api/publico/dados")
@app.get("/admin-painel/api/publico/dados")
def api_dados_publicos_telao(db=Depends(get_db)):
cursor = db.cursor()
cfg = atualizar_e_obter_cronometro(db)
p = "%s" if DATABASE_URL else "?"

cursor.execute(f"SELECT rodada FROM confrontos WHERE torneio_id = {p} ORDER BY id DESC LIMIT 1", (cfg["id"],))
row_r = cursor.fetchone()
rodada_atual = row_r["rodada"] if row_r else 1

cursor.execute(f"SELECT * FROM confrontos WHERE rodada = {p} AND torneio_id = {p} ORDER BY mesa ASC", (rodada_atual, cfg["id"]))
confrontos = [dict(row) for row in cursor.fetchall()]

ranking = obtener_ranking_fase_classificatoria(cursor, cfg["id"])

mins = cfg["crono_tempo_restante_seg"] // 60
segs = cfg["crono_tempo_restante_seg"] % 60
tempo_formatado = f"{mins:02d}:{segs:02d}"
if cfg["crono_ativo"] == 0 and cfg["crono_tempo_restante_seg"] == 0 and cfg["fase_torneio"] != "INSCRICAO":
    tempo_formatado = "AGORA TUDO É FALTA!"
    
cursor.execute(f"SELECT * FROM historico_campeoes WHERE torneio_id = {p}", (cfg["id"],))
hist = cursor.fetchone()
podio_dados = None

if hist:
    podio_dados = {
        "primeiro": str(hist["campeao"]),
        "segundo": str(hist["vice"]),
        "terceiro": str(hist["terceiro"]),
        "quarto": str(hist["quarto"]),
        "rei": str(hist["rei_das_flores"]),
        "rei_nome": str(hist["rei_das_flores"]),
        "rei_flores": str(hist["rei_das_flores"]),
        "flores": int(hist["qtd_flores"]),
        "max_flores": int(hist["qtd_flores"])
    }
else:
    cursor.execute(f"SELECT id, nome FROM atletas WHERE status = 'APROVADO' AND torneio_id = {p}", (cfg["id"],))
    atletas = cursor.fetchall()
    
    rei_nome = "---"
    max_flores = 0
    for atl in atletas:
        a_id = atl["id"]
        cursor.execute(f"SELECT COALESCE(SUM(flores1), 0) FROM confrontos WHERE atleta1_id = {p} AND torneio_id = {p}", (a_id, cfg["id"]))
        f1 = cursor.fetchone()[0]
        cursor.execute(f"SELECT COALESCE(SUM(flores2), 0) FROM confrontos WHERE atleta2_id = {p} AND torneio_id = {p}", (a_id, cfg["id"]))
        f2 = cursor.fetchone()[0]
        
        total_f = f1 + f2
        if total_f > max_flores:
            max_flores = total_f
            rei_nome = str(atl["nome"]).strip()
    
    podio_dados = {
        "primeiro": "---",
        "segundo": "---",
        "terceiro": "---",
        "quarto": "---",
        "rei": rei_nome,
        "rei_nome": rei_nome,
        "rei_flores": rei_nome,
        "flores": int(max_flores),
        "max_flores": int(max_flores)
    }

nome_fase = f"{rodada_atual}ª Rodada"
if rodada_atual == -1: nome_fase = "Oitavas de Final"
elif rodada_atual == -2: nome_fase = "Quartas de Final"
elif rodada_atual == -3: nome_fase = "Semifinal"
elif rodada_atual == -4: nome_fase = "Grande Final"

dados_retorno = {
    "fase_torneio": cfg["fase_torneio"],
    "nome_fase": nome_fase,
    "tempo": tempo_formatado,
    "crono_ativo": cfg["crono_ativo"],
    "rodada": rodada_atual,
    "confrontos": confrontos,
    "ranking": ranking,
    "podio": podio_dados
}

return JSONResponse(content=dados_retorno)

@app.get("/inscricao", response_class=HTMLResponse)
@app.get("/admin-painel/inscricao", response_class=HTMLResponse)
def pagina_inscricao_externa(request: Request, db=Depends(get_db)):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)

taxa_val = cfg["taxa_inscricao"] if cfg else 0.0
taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')

return templates.TemplateResponse(
    request=request, 
    name="inscricao_atleta.html", 
    context={
        "config": cfg, 
        "config_taxa": taxa_formatada
    }
)

@app.post("/inscricao/salvar")
@app.post("/admin-painel/inscricao/salvar")
async def salvar_inscricao_externa(
nome: str = Form(...),
ctg: str = Form(None),
entidade: str = Form(None),
whatsapp: str = Form(""),
comprovante: UploadFile = File(None),
db=Depends(get_db)
):
cursor = db.cursor()
cfg = obtener_torneio_ativo(cursor)
p = "%s" if DATABASE_URL else "?"

ent_final = entidade if entidade else ctg
entidade_limpa = ent_final.strip().upper() if (ent_final and ent_final.strip()) else "AVULSO"
nome_atleta_limpo = nome.strip().upper()

comprovante_url = None
if comprovante and comprovante.filename:
    pasta_destino = os.path.join("static", "comprovantes")
    if not os.path.exists(pasta_destino):
        os.makedirs(pasta_destino, exist_ok=True)
        
    _, extensao = os.path.splitext(comprovante.filename)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nome_arquivo_seguro = f"{timestamp}_{nome_atleta_limpo.replace(' ', '_')}{extensao}"
    caminho_completo = os.path.join(pasta_destino, nome_arquivo_seguro)
    
    with open(caminho_completo, "wb") as f:
        f.write(await comprovante.read())
        
    comprovante_url = f"/static/comprovantes/{nome_arquivo_seguro}"

cursor.execute(f'''
    INSERT INTO atletas (torneio_id, nome, entidade, status, whatsapp, comprovante_url) 
    VALUES ({p}, {p}, {p}, 'PENDENTE', {p}, {p})
''', (cfg["id"], nome_atleta_limpo, entidade_limpa, whatsapp.strip(), comprovante_url))
db.commit()

return RedirectResponse(url="/admin-painel/inscricao?sucesso=true", status_code=303)

@app.exception_handler(404)
async def redirecionar_links_antigos(request: Request, exc: Exception):
url_path = request.url.path
if url_path.startswith("/admin") or url_path == "/login" or url_path == "/logout":
return RedirectResponse(url=f"/admin-painel{url_path}", status_code=303)
return HTMLResponse(content="Página não encontrada no Panel", status_code=404)
