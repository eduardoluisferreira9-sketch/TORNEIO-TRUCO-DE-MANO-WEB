// =========================================
// PUBLICIDADE V1
// =========================================

const publicidade = [
    {
        titulo: "💻 Sistema de Telão Digital",
        texto: "Desenvolvido por <strong>Eduardo Luis Ferreira</strong>",

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
        texto: "<strong>SUPERMERCADO CENTRAL</strong><br>Patrocinador Oficial",

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

    const bloco = document.getElementById("publicidade-info");
    const botoes = document.getElementById("publicidade-botoes");
    
    if (!bloco || !botoes) return;

    bloco.innerHTML = `
        <h3>${publicidade[indice].titulo}</h3>
        <p>${publicidade[indice].texto}</p>
    `;

botoes.innerHTML = publicidade[indice].botoes;

    indice++;

    if (indice >= publicidade.length) {
        indice = 0;
    }
}

window.addEventListener("DOMContentLoaded", () => {

    atualizarPublicidade();

    setInterval(atualizarPublicidade, 8000);

});
