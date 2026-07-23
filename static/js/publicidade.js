// =========================================
// PUBLICIDADE V1.2
// =========================================

const publicidade = [
    {
        titulo: "💻 Sistema de Telão Digital",

        texto: "Desenvolvido por <strong>Eduardo Luis Ferreira</strong>",

        logo: "",

        botoes: `
            <a href="https://wa.me/5554991410550?text=Olá! Gostaria de adquirir o sistema."
               target="_blank"
               class="btn-dev btn-dev-comprar">
                📱 Adquirir Sistema
            </a>

            <a href="https://wa.me/5554991410550?text=Olá! Gostaria de informações sobre patrocínio."
               target="_blank"
               class="btn-dev btn-dev-patrocinar">
                🤝 Quero Patrocinar
            </a>
        `
    },

    {
        titulo: "🏆 PATROCINADOR MASTER",

        texto: `
            <strong>SUPERMERCADO CENTRAL</strong><br>
            Patrocinador Oficial
        `,

        logo: "/static/patrocinadores/mercado-central.png",

        botoes: `
            <a href="#"
               class="btn-dev btn-dev-comprar">
                🛒 Conheça
            </a>

            <a href="https://wa.me/5554991410550"
               target="_blank"
               class="btn-dev btn-dev-patrocinar">
                📞 WhatsApp
            </a>
        `
    }
];

let indice = 0;

function atualizarPublicidade() {

    const topo = document.getElementById("publicidade-info");
    const logo = document.getElementById("publicidade-logo");
    const texto = document.getElementById("publicidade-texto");
    const botoes = document.getElementById("publicidade-botoes");

    if (!topo || !logo || !texto || !botoes) return;

    const item = publicidade[indice];

    // Atualiza texto
    texto.innerHTML = `
        <h3>${item.titulo}</h3>
        <p>${item.texto}</p>
    `;

    // Atualiza logo
    if (item.logo && item.logo.trim() !== "") {

        logo.innerHTML = `
            <img src="${item.logo}"
                 alt="Logo"
                 style="max-height:70px; max-width:180px;">
        `;

    } else {

        logo.innerHTML = "";

    }

    // Atualiza botões
    botoes.innerHTML = item.botoes;

    indice++;

    if (indice >= publicidade.length) {
        indice = 0;
    }
}

window.addEventListener("DOMContentLoaded", () => {

    atualizarPublicidade();

    setInterval(atualizarPublicidade, 8000);

});
