// =========================================
// MOTOR DE PUBLICIDADE
// =========================================

let indice = 0;
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

function montarRotacao() {

    // Limpa os grupos
    Object.keys(rotacao).forEach(chave => {
        rotacao[chave] = [];
    });

    // Distribui os patrocinadores por categoria
    patrocinadores.forEach(item => {

        if (rotacao[item.tipo]) {
            rotacao[item.tipo].push(item);
        }

    });

    console.log("Motor de rotação:", rotacao);

}

function renderizarPublicidade(item) {

    const titulo = document.getElementById("publicidade-titulo");
    const logo = document.getElementById("publicidade-logo");
    const texto = document.getElementById("publicidade-texto");
    const botoes = document.getElementById("publicidade-botoes");

    if (!titulo || !logo || !texto || !botoes) {
        return;
    }

    // Título
    titulo.textContent = item.titulo;

    // Logo
    if (item.logo && item.logo.trim() !== "") {

        logo.innerHTML = `
            <img src="${item.logo}" alt="${item.nome}">
        `;

    } else {

        logo.innerHTML = "";

    }

    // Texto
    texto.innerHTML = `
        <strong>${item.nome}</strong>
        ${item.slogan}
    `;

    // Botões
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

function trocarPublicidade() {

    const card = document.getElementById("publicidade-info");

    if (!card) return;

    card.classList.remove("publicidade-fade-in");
    card.classList.add("publicidade-fade-out");

    setTimeout(() => {

        renderizarPublicidade(patrocinadores[indice]);

        card.classList.remove("publicidade-fade-out");
        card.classList.add("publicidade-fade-in");

        indice++;

        if (indice >= patrocinadores.length) {
            indice = 0;
        }

        iniciarTimer();

    }, 350);

}

function iniciarTimer() {

    clearTimeout(timerPublicidade);

    timerPublicidade = setTimeout(
        trocarPublicidade,
        patrocinadores[indice].tempo * 1000
    );

}

window.addEventListener("DOMContentLoaded", () => {

    montarRotacao();

    renderizarPublicidade(patrocinadores[0]);

    indice = 1;

    const card = document.getElementById("publicidade-info");

    if (card) {
        card.classList.add("publicidade-fade-in");
    }

    iniciarTimer();

});
