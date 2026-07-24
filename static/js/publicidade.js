// =========================================
// PUBLICIDADE V1.3
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
            <strong>SUPERMERCADO CENTRAL</strong>
            Patrocinador Oficial
        `,

        logo: "/static/patrocinadores/mercado-central.jpg",

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

function renderizarPublicidade(item){

    const titulo  = document.getElementById("publicidade-titulo");
    const logo    = document.getElementById("publicidade-logo");
    const texto   = document.getElementById("publicidade-texto");
    const botoes  = document.getElementById("publicidade-botoes");
    const card    = document.getElementById("publicidade-info");

    if(!titulo || !logo || !texto || !botoes || !card){
        return;
    }

    titulo.textContent = item.titulo;

    texto.innerHTML = item.texto;

    if(item.logo){

        logo.innerHTML = `
            <img src="${item.logo}" alt="Logo do patrocinador">
        `;

    }else{

        logo.innerHTML = "";

    }

    botoes.innerHTML = item.botoes;

}

function atualizarPublicidade(){

    const card = document.getElementById("publicidade-info");

    if(!card) return;

    card.classList.remove("publicidade-fade-in");
    card.classList.add("publicidade-fade-out");

    setTimeout(() => {

        renderizarPublicidade(publicidade[indice]);

        card.classList.remove("publicidade-fade-out");
        card.classList.add("publicidade-fade-in");

        indice++;

        if(indice >= publicidade.length){
            indice = 0;
        }

    },350);

}

window.addEventListener("DOMContentLoaded", () => {

    renderizarPublicidade(publicidade[0]);

    indice = 1;

    const card = document.getElementById("publicidade-info");

    if(card){
        card.classList.add("publicidade-fade-in");
    }

    setInterval(atualizarPublicidade,8000);

});
