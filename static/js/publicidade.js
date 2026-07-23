// =========================================
// PUBLICIDADE V1
// =========================================

const publicidade = [
    {
        titulo: "💻 Sistema de Telão Digital",
        texto: "Desenvolvido por <strong>Eduardo Luis Ferreira</strong>"
    },
    {
        titulo: "🏆 PATROCINADOR MASTER",
        texto: "<strong>Sua empresa pode anunciar aqui.</strong>"
    }
];

let indice = 0;

function atualizarPublicidade() {

    const bloco = document.getElementById("publicidade-info");

    if (!bloco) return;

    bloco.innerHTML = `
        <h3>${publicidade[indice].titulo}</h3>
        <p>${publicidade[indice].texto}</p>
    `;

    indice++;

    if (indice >= publicidade.length) {
        indice = 0;
    }
}

window.addEventListener("DOMContentLoaded", () => {

    atualizarPublicidade();

    setInterval(atualizarPublicidade, 8000);

});
