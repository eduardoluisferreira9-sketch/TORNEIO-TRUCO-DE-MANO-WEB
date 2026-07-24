// =========================================
// MOTOR DE PUBLICIDADE
// =========================================

let publicidadeAtual = null;
let timerPublicidade = null;

// =========================================
// MOTOR DE ROTAÇÃO
// =========================================

const rotacao = {
    sistema: [],
    master: [],
    ouro: [],
    prata: [],
    bronze: []
};

// Ponteiro de cada categoria
const ponteiros = {
    sistema: 0,
    master: 0,
    ouro: 0,
    prata: 0,
    bronze: 0
};

// Sequência de exibição
const sequencia = [
    "sistema",
    "master",
    "ouro",
    "prata",
    "bronze",
    "ouro",
    "prata",
    "bronze",
    "prata",
    "bronze"
];

let indiceSequencia = 0;

// =========================================
// MONTA A ROTAÇÃO
// =========================================

function montarRotacao() {

    Object.keys(rotacao).forEach(chave => {
        rotacao[chave] = [];
    });

    patrocinadores.forEach(item => {

        if (rotacao[item.tipo]) {
            rotacao[item.tipo].push(item);
        }

    });

    console.log("Motor de rotação:", rotacao);

}

// =========================================
// PRÓXIMO DA CATEGORIA
// =========================================

function obterProximoDaCategoria(tipo) {

    const lista = rotacao[tipo];

    if (!lista || lista.length === 0) {
        return null;
    }

    const item = lista[ponteiros[tipo]];

    ponteiros[tipo]++;

    if (ponteiros[tipo] >= lista.length) {
        ponteiros[tipo] = 0;
    }

    return item;

}

// =========================================
// PRÓXIMA PUBLICIDADE
// =========================================

function obterProximaPublicidade() {

    let tentativas = 0;

    while (tentativas < sequencia.length) {

        const tipo = sequencia[indiceSequencia];

        indiceSequencia++;

        if (indiceSequencia >= sequencia.length) {
            indiceSequencia = 0;
        }

        const item = obterProximoDaCategoria(tipo);

        if (item) {
            return item;
        }

        tentativas++;

    }

    return patrocinadores[0];

}

// =========================================
// RENDERIZAÇÃO
// =========================================

function renderizarPublicidade(item) {

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
        ${item.slogan}
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

    const tempo = publicidadeAtual?.tempo || 8;

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

    publicidadeAtual = obterProximaPublicidade();

    renderizarPublicidade(publicidadeAtual);

    const card = document.getElementById("publicidade-info");

    if (card) {
        card.classList.add("publicidade-fade-in");
    }

    iniciarTimer();

});
