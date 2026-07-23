// ===============================
// PUBLICIDADE V1.0
// ===============================

const publicidade = [
    {
        titulo: "💻 Sistema de Telão Digital",
        texto: "Desenvolvido por Eduardo Luis Ferreira",
        botao1: {
            texto: "📱 Adquirir Sistema",
            link: "https://wa.me/5554991410550?text=Olá!%20Gostaria%20de%20comprar/licenciar%20o%20sistema%20de%20Telão."
        },
        botao2: {
            texto: "🤝 Quero Patrocinar",
            link: "https://wa.me/5554991410550?text=Olá!%20Gostaria%20de%20informações%20sobre%20cotas%20de%20patrocínio%20no%20Telão."
        }
    },

    {
        titulo: "🏆 PATROCINADOR MASTER",
        texto: "Sua empresa pode aparecer aqui.",
        botao1: {
            texto: "⭐ Mercado Central",
            link: "#"
        },
        botao2: {
            texto: "📞 Seja Patrocinador",
            link: "https://wa.me/5554991410550"
        }
    }
];

let indicePublicidade = 0;

function trocarPublicidade() {

    const titulo = document.querySelector(".dev-info h3");
    const texto = document.querySelector(".dev-info p");

    const botoes = document.querySelectorAll(".dev-botoes a");

    if (!titulo || !texto || botoes.length < 2) return;

    const atual = publicidade[indicePublicidade];

    titulo.innerHTML = atual.titulo;
    texto.innerHTML = atual.texto;

    botoes[0].innerHTML = atual.botao1.texto;
    botoes[0].href = atual.botao1.link;

    botoes[1].innerHTML = atual.botao2.texto;
    botoes[1].href = atual.botao2.link;

    indicePublicidade++;

    if (indicePublicidade >= publicidade.length)
        indicePublicidade = 0;
}

window.addEventListener("load", () => {

    trocarPublicidade();

    setInterval(trocarPublicidade, 8000);

});
