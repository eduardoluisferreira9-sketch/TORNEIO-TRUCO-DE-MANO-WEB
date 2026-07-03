import os
import sqlite3
import time
import shutil
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# 📁 CAMINHOS AJUSTADOS: Aponta para a pasta templates DENTRO de sistema_publico
CORRENTE_DIR = os.path.dirname(os.path.abspath(__file__)) # Pasta 'sistema_publico'
BASE_DIR = os.path.dirname(CORRENTE_DIR)                  # Raiz do projeto (onde está o .db)

DB_FILE = os.path.join(BASE_DIR, "torneio.db")
TEMPLATES_DIR = os.path.join(CORRENTE_DIR, "templates")    # templates interna
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "comprovantes")

app = FastAPI(title="App de Acompanhamento Público - Truco Cego")@app.post("/inscrever")@app.post("/inscrever")
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

def obter_rei_das_flores_atual(cursor):
    """Calcula quem é o líder atual do Rei das Flores somando rodadas classificatórias e eliminatórias"""
    cursor.execute("SELECT id, nome FROM atletas WHERE status = 'APROVADO'")
    atletas = cursor.fetchall()
    
    lider_nome = "Nenhum"
    max_flores = 0
    
    for atleta in atletas:
        atleta_id = atleta["id"]
        try:
            cursor.execute("SELECT COALESCE(SUM(flores1), 0) FROM confrontos WHERE atleta1_id = ?", (atleta_id,))
            f1 = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(flores2), 0) FROM confrontos WHERE atleta2_id = ?", (atleta_id,))
            f2 = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            cursor.execute("SELECT COALESCE(SUM(flores1), 0) FROM confrontos WHERE athlete1_id = ?", (atleta_id,))
            f1 = cursor.fetchone()[0]
            cursor.execute("SELECT COALESCE(SUM(flores2), 0) FROM confrontos WHERE athlete2_id = ?", (atleta_id,))
            f2 = cursor.fetchone()[0]
            
        total_flores = f1 + f2
        if total_flores > max_flores:
            max_flores = total_flores
            lider_nome = atleta["nome"]
            
    return {"nome": lider_nome, "flores": max_flores}

@app.get("/", response_class=HTMLResponse)
def rota_telao(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM config LIMIT 1")
    cfg = dict(cursor.fetchone())
    return templates.TemplateResponse(request=request, name="publico_telao.html", context={"config": cfg})

@app.get("/inscrever", response_class=HTMLResponse)
def tela_inscricao_atleta(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT id, nome_torneio, taxa_inscricao FROM config LIMIT 1")
    cfg_db = cursor.fetchone()
    
    entidades = []
    if cfg_db:
        # Corrige o filtro para usar entidade (e não entity) vinculado ao torneio id ativo
        cursor.execute("SELECT DISTINCT entidade FROM atletas WHERE status = 'APROVADO' AND torneio_id = ? ORDER BY entidade ASC", (cfg_db["id"],))
        entidades = [row["entidade"] for row in cursor.fetchall()]
    
    taxa_val = cfg_db["taxa_inscricao"] if cfg_db else 0.0
    taxa_formatada = f"{taxa_val:.2f}".replace('.', ',')

    return templates.TemplateResponse(
        request=request, 
        name="inscricao_atleta.html", 
        context={
            "config_taxa": taxa_formatada, 
            "entidades": entidades,
            "config": cfg_db
        }
    )

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
    extensao = os.path.splitext(comprovante.filename)[1].lower() # .lower() evita problemas com .PNG/.JPG maiúsculos
    nome_seguro = "".join(c for c in nome if c.isalnum() or c in (' ', '_')).rstrip()
    nome_arquivo = f"comprovante_{nome_seguro}_{int(time.time())}{extensao}"
    caminho_final = os.path.join(UPLOAD_DIR, nome_arquivo)
    
    with open(caminho_final, "wb") as buffer:
        shutil.copyfileobj(comprovante.file, buffer)
        
    cursor = db.cursor()
    cursor.execute("SELECT id FROM config LIMIT 1")
    cfg = cursor.fetchone()
    torneio_id = cfg["id"] if cfg else 1
    
    entidade_limpa = entidade.strip().upper() if entidade.strip() else "AVULSO"
    
    # URL relativa que aponta para a pasta static configurada no seu sistema
    url_comprovante = f"/static/comprovantes/{nome_arquivo}"
    
    # 🌟 CORREÇÃO: Adicionada a coluna comprovante_url no INSERT para salvar o caminho no banco!
    cursor.execute('''
        INSERT INTO atletas (torneio_id, nome, entidade, whatsapp, comprovante_url, status) 
        VALUES (?, ?, ?, ?, ?, 'PENDENTE')
    ''', (torneio_id, nome.strip().upper(), entidade_limpa, whatsapp.strip(), url_comprovante))
    db.commit()
    
    return RedirectResponse(url="/inscrever?sucesso=true", status_code=303)

@app.get("/api/publico/dados")
def api_dados_publicos(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM config LIMIT 1")
    cfg = dict(cursor.fetchone())
    
    # 1. Cronômetro em memória
    if cfg["crono_ativo"] == 1:
        agora = time.time()
        decorrido = int(agora - cfg["crono_ultimo_clique"])
        if decorrido > 0:
            novo_tempo = max(0, cfg["crono_tempo_restante_seg"] - decorrido)
            cfg["crono_tempo_restante_seg"] = novo_tempo
            cfg["crono_ultimo_clique"] = agora
            
            cursor.execute(
                "UPDATE config SET crono_tempo_restante_seg = ?, crono_ultimo_clique = ?", 
                (novo_tempo, agora)
            )
            db.commit()
            
    fase_status = cfg.get("fase_torneio", "CLASSIFICATORIA").upper()
    tempo_rodada_atual = cfg.get("tempo_rodada") or cfg.get("duracao_rodada") or 0
    forcar_crono_ativo = cfg["crono_ativo"]

    # Cálculo padrão do formato MM:SS
    if tempo_rodada_atual == 0:
        tempo_formatado = "Sem Tempo"
    else:
        mins = cfg["crono_tempo_restante_seg"] // 60
        segs = cfg["crono_tempo_restante_seg"] % 60
        tempo_formatado = f"{mins:02d}:{segs:02d}"

    # --- ADAPTAÇÃO IDÊNTICA AO MAIN.PY COM INTEGRALIZAÇÃO ANTI-CINZA ---
    if cfg["crono_ativo"] == 0 and cfg["crono_tempo_restante_seg"] == 0 and fase_status != "INSCRICAO":
        tempo_formatado = "AGORA TUDO É FALTA!"
        forcar_crono_ativo = 1  # Força o HTML a entrar na regra de execução (Evitando o estilo #555555)
    elif cfg["crono_tempo_restante_seg"] <= 0 and cfg["crono_ativo"] == 1:
        tempo_formatado = "AGORA TUDO É FALTA!"
        forcar_crono_ativo = 1

    # 2. Tratamento Cirúrgico de Fase (Macro) e Andamento (Micro)
    mapeamento_rodadas = {
        "16AVOS": -16,
        "OITAVAS": -1, # Conforme mapeamento original do banco do usuário
        "QUARTAS": -2,
        "SEMIFINAL": -3,
        "FINAL": -4
    }
    
    if fase_status == "CLASSIFICATORIA":
        cursor.execute("SELECT rodada FROM confrontos WHERE rodada > 0 ORDER BY id DESC LIMIT 1")
        row_r = cursor.fetchone()
        rodada_atual = row_r["rodada"] if row_r else 1
        nome_fase = "Classificatória"
        detalhe_fase = f"Rodada {rodada_atual}"
    else:
        rodada_atual = mapeamento_rodadas.get(fase_status, 0)
        nome_fase = "Eliminatória"
        
        if fase_status == "16AVOS": detalhe_fase = "16 avos de Final"
        elif fase_status == "OITAVAS": detalhe_fase = "Oitavas de Final"
        elif fase_status == "QUARTAS": detalhe_fase = "Quartas de Final"
        elif fase_status == "SEMIFINAL": detalhe_fase = "Semifinal"
        elif fase_status == "FINAL": 
            nome_fase = "Finais"
            detalhe_fase = "Grande Final"
        else:
            nome_fase = "Inscrições Abertas"
            detalhe_fase = "--"

    # 3. Busca de Confrontos Corrigida para buscar tanto positivos quanto negativos
    confrontos = []
    if rodada_atual != 0:
        cursor.execute("SELECT * FROM confrontos WHERE rodada = ? ORDER BY mesa ASC", (rodada_atual,))
        linhas_confrontos = cursor.fetchall()
        
        for row in linhas_confrontos:
            dados_jogo = dict(row)
            if rodada_atual == -4:
                if dados_jogo["mesa"] == 1:
                    dados_jogo["fase_mesa_nome"] = "Grande Final"
                elif dados_jogo["mesa"] == 2:
                    dados_jogo["fase_mesa_nome"] = "Disputa de 3º Lugar"
                else:
                    dados_jogo["fase_mesa_nome"] = "Final"
            else:
                dados_jogo["fase_mesa_nome"] = detalhe_fase
                
            confrontos.append(dados_jogo)

    # =========================================================================
    # 4. Totalizadores e Líder de Flores (BLINDADO E SINCRONIZADO COM MAIN.PY)
    # =========================================================================
    torneio_id_ativo = cfg.get("id") or cfg.get("torneio_id") or 1
    
    # Conta os atletas vinculados a este torneio específico cujo status seja 'APROVADO' (Case Insensitive)
    cursor.execute(
        "SELECT COUNT(*) FROM atletas WHERE torneio_id = ? AND UPPER(status) = 'APROVADO'", 
        (torneio_id_ativo,)
    )
    total_atletas = cursor.fetchone()[0]
    
    # Fallback Prático: Se por acaso ainda estiverem pendentes no banco local, 
    # garante que não exiba 0 caso existam registros vinculados ao torneio
    if total_atletas == 0:
        cursor.execute("SELECT COUNT(*) FROM atletas WHERE torneio_id = ?", (torneio_id_ativo,))
        total_atletas = cursor.fetchone()[0]
    
    rei_flores = obter_rei_das_flores_atual(cursor)

    ranking = []
    if fase_status != "INSCRICAO":
        ranking = obter_ranking_publico(cursor)[:5]

    return JSONResponse({
        "fase_torneio": fase_status, 
        "nome_fase": nome_fase, 
        "detalhe_fase": detalhe_fase,
        "tempo": tempo_formatado,
        "crono_ativo": forcar_crono_ativo,  # Retorna a variável modificada para forçar o destaque visual
        "confrontos": confrontos, 
        "ranking": ranking,
        "total_atletas": total_atletas,
        "rei_flores_atual": rei_flores,
        "max_rodadas": cfg.get("max_rodadas_classificatoria") or cfg.get("max_rodadas") or 5
    })
