/*
=====================================================

 MÓDULO DE PUBLICIDADE
 Sistema de Telão - Truco de Mano

 Desenvolvido para ser independente do telão.

=====================================================
*/

class Publicidade{

    constructor(){

        this.patrocinadores=[];

        this.indice=0;

        this.tempoTroca=8000;

        this.container=null;

    }

    iniciar(){

        this.criarBanner();

        this.carregar();

        this.renderizar();

        this.iniciarRotacao();

    }

    criarBanner(){

        this.container=document.createElement("div");

        this.container.id="publicidade-master";

        document.body.appendChild(this.container);

    }

    carregar(){

        this.patrocinadores=[

            {

                nome:"Sistema de Telão",

                subtitulo:"Desenvolvido por Eduardo Luis Ferreira",

                logo:"",

                tipo:"sistema"

            }

        ];

    }

    renderizar(){

        if(this.patrocinadores.length===0){

            this.container.style.display="none";

            return;

        }

        const patrocinador=this.patrocinadores[this.indice];

        this.container.innerHTML=`

            <div class="pub-card">

                <div class="pub-titulo">

                    ${patrocinador.nome}

                </div>

                <div class="pub-logo">

                    ${
                        patrocinador.logo
                        ? `<img src="${patrocinador.logo}">`
                        : "💻"
                    }

                </div>

                <div class="pub-subtitulo">

                    ${patrocinador.subtitulo}

                </div>

            </div>

        `;

    }

    proximo(){

        this.indice++;

        if(this.indice>=this.patrocinadores.length){

            this.indice=0;

        }

        this.renderizar();

    }

    iniciarRotacao(){

        setInterval(()=>{

            this.proximo();

        },this.tempoTroca);

    }

}

window.addEventListener("load",()=>{

    const publicidade=new Publicidade();

    publicidade.iniciar();

});
