// =========================================
// MOTOR DE PUBLICIDADE
// =========================================

let publicidadeAtual = null;
let timerPublicidade = null;

// =========================================
// CONFIGURAÇÃO DAS CATEGORIAS
// =========================================

const categorias = {
    master: {
        peso: 4,
        tempo: 10
    },
    ouro: {
        peso: 3,
        tempo: 8
    },
    prata: {
        peso: 2,
        tempo: 7
    },
    bronze: {
        peso: 1,
        tempo: 6
    }
};

// =========================================
// MOTOR DE ROTAÇÃO
// =========================================

const rotacao = {
    master: [],
    ouro: [],
    prata: [],
    bronze: []
};

const ponteiros = {
    master: 0,
    ouro: 0,
    prata: 0,
    bronze: 0
};

let sequencia = [];
let indiceSequencia = 0;

// =========================================
// GERA A SEQUÊNCIA AUTOMATICAMENTE
// =========================================

function montarSequencia() {

    sequencia = [];

    const pesos = {};

    Object.keys(categorias).forEach(tipo => {
        pesos[tipo] = categorias[tipo].peso;
    });

    while (Object.values(pesos).some(p => p > 0)) {

        const disponiveis = Object.keys(pesos)
            .filter(tipo => pesos[tipo] > 0)
            .sort((a, b) => pesos[b] - pesos[a]);

        disponiveis.forEach(tipo => {

            sequencia.push(tipo);

            pesos[tipo]--;

        });

    }

}

// =========================================
// MONTA A ROTAÇÃO
// =========================================

function montarRotacao() {

    Object.keys(rotacao).forEach(tipo => {

        rotacao[tipo] = [];
        ponteiros[tipo] = 0;

    });

    patrocinadores.forEach(item => {

        // Ferreira Sistemas não participa da publicidade
        if (item.tipo === "sistema") {
            return;
        }

        if (rotacao[item.tipo]) {
            rotacao[item.tipo].push(item);
        }

    });

    // Embaralha cada categoria apenas uma vez
    Object.keys(rotacao).forEach(tipo => {
        rotacao[tipo].sort(() => Math.random() - 0.5);
    });
    
}

// =========================================
// PRÓXIMO DA CATEGORIA
// =========================================

function obterProximoDaCategoria(tipo) {

    const lista = rotacao[tipo];

    if (!lista || lista.length === 0) {
        return null;
    }

    const indice = ponteiros[tipo];

    const patrocinador = lista[indice];

    ponteiros[tipo]++;

    if (ponteiros[tipo] >= lista.length) {
        ponteiros[tipo] = 0;
    }

    return patrocinador;

}

// =========================================
// PRÓXIMA PUBLICIDADE
// =========================================

function obterProximaPublicidade() {

    let tentativas = 0;

    while (tentativas < sequencia.length) {

        const categoria = sequencia[indiceSequencia];

        indiceSequencia++;

        if (indiceSequencia >= sequencia.length) {
            indiceSequencia = 0;
        }

        const patrocinador =
            obterProximoDaCategoria(categoria);

        if (patrocinador) {
            return patrocinador;
        }

        tentativas++;

    }

    return null;

}

// =========================================
// RENDERIZAÇÃO
// =========================================

function renderizarPublicidade(item) {

    if (!item) return;

    const titulo = document.getElementById("publicidade-titulo");
    const logo = document.getElementById("publicidade-logo");
    const texto = document.getElementById("publicidade-texto");
    const botoes = document.getElementById("publicidade-botoes");

    if (!titulo || !logo || !texto || !botoes) {
        return;
    }

    titulo.textContent = item.titulo;

    if (item.logo && item.logo.trim() !== "") {

        logo.innerHTML = `
            <img src="${item.logo}" alt="${item.nome}">
        `;

    } else {

        logo.innerHTML = "";

    }

    texto.innerHTML = `
        <strong>${item.nome}</strong>
        <span>${item.slogan}</span>
    `;

    botoes.innerHTML = `
        <a href="${item.botao1.link}"
           target="_blank"
           class="btn-dev btn-dev-comprar">
            ${item.botao1.texto}
        </a>

        <a href="${item.botao2.link}"
           target="_blank"
           class="btn-dev btn-dev-patrocinar">
            ${item.botao2.texto}
        </a>
    `;

}

// =========================================
// TROCA PUBLICIDADE
// =========================================

function trocarPublicidade() {

    const card = document.getElementById("publicidade-info");

    if (!card) return;

    card.classList.remove("publicidade-fade-in");
    card.classList.add("publicidade-fade-out");

    setTimeout(() => {

        publicidadeAtual = obterProximaPublicidade();

        if (!publicidadeAtual) {

            card.classList.remove("publicidade-fade-out");
            card.classList.add("publicidade-fade-in");

            iniciarTimer();
            return;

        }

        renderizarPublicidade(publicidadeAtual);

        card.classList.remove("publicidade-fade-out");
        card.classList.add("publicidade-fade-in");

        iniciarTimer();

    }, 350);

}

// =========================================
// TIMER
// =========================================

function iniciarTimer() {

    clearTimeout(timerPublicidade);

    if (!publicidadeAtual) {
        return;
    }

    const tempo =
        categorias[publicidadeAtual.tipo]?.tempo || 8;

    timerPublicidade = setTimeout(
        trocarPublicidade,
        tempo * 1000
    );

}

// =========================================
// INICIALIZAÇÃO
// =========================================

window.addEventListener("DOMContentLoaded", () => {

    montarRotacao();

    montarSequencia();

    publicidadeAtual = obterProximaPublicidade();

    if (publicidadeAtual) {
        renderizarPublicidade(publicidadeAtual);
    }

    const card = document.getElementById("publicidade-info");

    if (card) {
        card.classList.add("publicidade-fade-in");
    }

    iniciarTimer();

});
