// =========================================
// CADASTRO DE PATROCINADORES
// =========================================

const patrocinadores = [

    // =====================================================
    // SISTEMA
    // =====================================================
    {
        tipo: "sistema",
        prioridade: 0,

        titulo: "💻 Sistema de Telão",

        nome: "Eduardo Luis Ferreira",

        slogan: "Desenvolvido especialmente para torneios de Truco Cego",

        logo: "",

        botao1: {
            texto: "📱 Adquirir Sistema",
            link: "https://wa.me/5554991410550?text=Olá! Gostaria de adquirir o sistema."
        },

        botao2: {
            texto: "🤝 Quero Patrocinar",
            link: "https://wa.me/5554991410550?text=Olá! Gostaria de informações sobre patrocínio."
        },

        tempo: 6
    },

    // =====================================================
    // PATROCINADOR MASTER
    // =====================================================
    {
        tipo: "master",
        prioridade: 1,

        titulo: "🏆 MASTER",

        nome: "SUPERMERCADO CENTRAL",

        slogan: "Patrocinador Oficial",

        logo: "/static/patrocinadores/mercado-central.jpg",

        botao1: {
            texto: "Conheça",
            link: "#"
        },

        botao2: {
            texto: "WhatsApp",
            link: "https://wa.me/5554991410550"
        },

        tempo: 16
    },

    // =====================================================
    // PATROCINADOR OURO
    // =====================================================
    {
        tipo: "ouro",
        prioridade: 2,

        titulo: "🥇 OURO",

        nome: "POSTO AVENIDA",

        slogan: "Seu combustível de confiança",

        logo: "/static/patrocinadores/posto-avenida.jpg",

        botao1: {
            texto: "Conheça",
            link: "https://maps.google.com"
        },

        botao2: {
            texto: "WhatsApp",
            link: "https://wa.me/5554991410550"
        },

        tempo: 10
    }

];
