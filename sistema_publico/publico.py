<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Inscrição Online - Torneio de Truco</title>
    <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;800&family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {
            --bg-principal: #0d2e1b;
            --bg-cards: #092113;
            --ouro: #d4af37;
            --ouro-brilhante: #f3e5ab;
            --texto-claro: #ffffff; 
            --texto-subtil: #bdc3c7; 
            --verde-sucesso: #1e8449;
        }

        body { 
            background: var(--bg-principal); 
            color: var(--texto-claro); 
            font-family: 'Montserrat', sans-serif; 
            margin: 0; 
            padding: 0;
            background-image: linear-gradient(rgba(255, 255, 255, 0.005) 1px, transparent 0);
            background-size: 100% 4px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .container-inscricao {
            background: var(--bg-cards);
            width: 100%;
            max-width: 500px;
            margin: 20px;
            padding: 40px;
            border-radius: 12px;
            border: 2px solid var(--ouro);
            box-shadow: 0 15px 40px rgba(0,0,0,0.8);
            box-sizing: border-box;
        }

        .header-inscricao {
            text-align: center;
            margin-bottom: 30px;
        }

        .header-inscricao h1 {
            font-family: 'Cinzel', serif;
            color: var(--ouro);
            font-size: 1.8rem;
            margin: 0 0 10px 0;
            text-shadow: 0px 3px 6px rgba(0,0,0,0.9);
            letter-spacing: 1px;
            border-bottom: 2px double var(--ouro);
            padding-bottom: 15px;
        }

        .taxa-badge {
            background: rgba(212, 175, 55, 0.1);
            border: 1px solid var(--ouro);
            color: var(--ouro-brilhante);
            padding: 10px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.95rem;
            margin-top: 15px;
            display: inline-block;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 0.8rem;
            color: var(--texto-subtil);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .input-field {
            width: 100%;
            padding: 12px 15px;
            background: rgba(0,0,0,0.5);
            border: 1px solid rgba(212, 175, 55, 0.3);
            color: #fff;
            border-radius: 6px;
            box-sizing: border-box;
            font-size: 1rem;
            font-family: 'Montserrat', sans-serif;
            transition: 0.3s;
        }

        .input-field:focus {
            border-color: var(--ouro);
            outline: none;
            box-shadow: 0 0 10px rgba(212,175,55,0.2);
        }

        /* customização do campo de upload */
        .file-wrapper {
            position: relative;
            background: rgba(0,0,0,0.5);
            border: 2px dashed rgba(212, 175, 55, 0.4);
            border-radius: 6px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: 0.3s;
        }

        .file-wrapper:hover {
            border-color: var(--ouro);
            background: rgba(212, 175, 55, 0.05);
        }

        .file-wrapper input[type="file"] {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            opacity: 0;
            cursor: pointer;
        }

        .file-label-text {
            font-size: 0.9rem;
            color: var(--texto-subtil);
            font-weight: 600;
        }

        .file-label-text i {
            font-size: 1.8rem;
            color: var(--ouro);
            margin-bottom: 10px;
            display: block;
        }

        .btn-enviar {
            background: linear-gradient(135deg, var(--ouro) 0%, #9a7d28 100%); 
            color: #111; 
            font-family: 'Cinzel', serif; 
            font-weight: 800; 
            border: none; 
            padding: 15px 20px; 
            border-radius: 6px; 
            cursor: pointer; 
            width: 100%; 
            display: inline-flex; 
            align-items: center; 
            justify-content: center; 
            gap: 10px; 
            text-transform: uppercase; 
            font-size: 0.95rem;
            box-shadow: 0 6px 12px rgba(0,0,0,0.5); 
            letter-spacing: 1px;
            transition: 0.3s ease;
            margin-top: 10px;
        }

        .btn-enviar:hover { 
            background: linear-gradient(135deg, var(--ouro-brilhante) 0%, var(--ouro) 100%); 
            transform: translateY(-2px); 
            box-shadow: 0 10px 20px rgba(212,175,55,0.4); 
        }

        /* Alertas de Sucesso */
        .alerta-sucesso {
            background: rgba(30, 132, 73, 0.2);
            border: 1px solid var(--verde-sucesso);
            color: #2ecc71;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
            font-weight: 600;
            margin-bottom: 25px;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>

    <div class="container-inscricao">
        <div class="header-inscricao">
            <h1>Ficha de Inscrição</h1>
            <div class="taxa-badge">
                <i class="fas fa-ticket-alt"></i> Valor da Inscrição: R$ {{ config_taxa }}
            </div>
        </div>

        <div id="msg-sucesso" class="alerta-sucesso" style="display: none;">
            <i class="fas fa-circle-check"></i> Inscrição enviada com sucesso!<br>
            Aguarde a aprovação da organização do torneio.
        </div>

        <form action="/inscrever" method="POST" enctype="multipart/form-data">
            
            <div class="form-group">
                <label for="inp_nome">Nome Completo do Atleta</label>
                <input type="text" id="inp_nome" name="nome" class="input-field" placeholder="Ex: João Silva" required>
            </div>

            <div class="form-group">
                <label for="inp_entidade">CTG / Entidade / Piquete</label>
                <input type="text" id="inp_entidade" name="entidade" class="input-field" placeholder="Ex: CTG SENTINELA DOS PAMPAS" list="lista-entidades" required>
                <datalist id="lista-entidades">
                    {% for ent in entidades %}
                        <option value="{{ ent }}"></option>
                    {% endfor %}
                </datalist>
            </div>

            <div class="form-group">
                <label for="inp_whatsapp">WhatsApp para Contato</label>
                <input type="tel" id="inp_whatsapp" name="whatsapp" class="input-field" placeholder="(54) 99999-0000" required>
            </div>

            <div class="form-group">
                <label>Comprovante de Pagamento (PIX)</label>
                <div class="file-wrapper">
                    <input type="file" id="inp_comprovante" name="comprovante" accept="image/*,application/pdf" onchange="mostrarNomeArquivo(this)" required>
                    <span class="file-label-text" id="file-text">
                        <i class="fas fa-cloud-arrow-up"></i>
                        Clique para anexar o Comprovante (Imagem ou PDF)
                    </span>
                </div>
            </div>

            <button type="submit" class="btn-enviar">
                <i class="fas fa-paper-plane"></i> Enviar Inscrição
            </button>
        </form>
    </div>

    <script>
        // Função simples para mostrar o nome do arquivo anexado na caixa de upload
        function mostrarNomeArquivo(input) {
            const label = document.getElementById('file-text');
            if (input.files && input.files.length > 0) {
                label.innerHTML = `<i class="fas fa-file-circle-check" style="color: #2ecc71;"></i> <strong>Arquivo pronto:</strong><br>${input.files[0].name}`;
            }
        }

        // Verifica se a URL contém '?sucesso=true' para exibir a caixa verde de confirmação
        window.onload = function() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('sucesso') === 'true') {
                document.getElementById('msg-sucesso').style.display = 'block';
            }
        }
    </script>
</body>
</html>
