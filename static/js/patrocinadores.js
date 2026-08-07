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

        titulo: "DESENVOLVIDO POR",

        nome: "Ferreira Sistemas",

        slogan: "Tecnologia com propósito.",

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

        nome: "Cusco artigos gaúchos",

        slogan: "Patrocinador",

        mensagem: "Há mais de uma década, a Cusco Artigos Gaúchos vem preservando as raízes das tradições gaúchas.",

        logo: "/static/patrocinadores/Logo-cusco.jpg",

        botao1: {
            texto: "Conheça",
            link: "https://www.cuscoartigosgauchos.com.br"
        },

        botao2: {
            texto: "WhatsApp",
            link: "https://api.whatsapp.com/send?1=pt_BR&phone=5554993001127"
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

        mensagem: "⛽ Combustível, conveniência e atendimento de qualidade.",

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
