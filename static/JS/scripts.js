// ======================================================
// SYNAPSE VIRTUAL IA - Sistema de Asistentes Virtuales
// Archivo: scripts.js
// Versión: 4.0 (Mejorado: sidebar toggle, notificaciones, AJAX, accesibilidad)
// ======================================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('🧠 Synapse Virtual IA v4.0 - Sistema iniciado.');

    // ==========================================
    // 1. CONFIGURACIÓN
    // ==========================================
    const CONFIG = {
        selectores: {
            formularios: 'form',
            camposTexto: 'input[type="text"], input[type="password"], input[type="email"], textarea',
            botonesEnviar: 'button[type="submit"]',
            contenedorRespuesta: '.respuesta',
            contenedorFlash: '.flash-messages',
            campoError: 'campo-error',
            claseCargando: 'cargando',
            sidebar: '.sidebar',
            sidebarToggle: '.sidebar-toggle',
            sidebarOverlay: '.sidebar-overlay',
            chatMessages: '.chat-messages',
            chatInput: '.chat-input input',
            chatForm: '.chat-input',
        },
        mensajes: {
            cargando: '⏳ Procesando...',
            errorConexion: '❌ Error de conexión. Intente nuevamente.',
            camposVacios: '⚠️ Por favor, complete todos los campos requeridos.',
            confirmarEliminar: '¿Está seguro de eliminar este elemento?',
            exito: '✅ Operación realizada con éxito.',
            emailInvalido: '⚠️ Por favor, ingrese un correo electrónico válido.',
        },
        urls: {
            // Si usas AJAX, puedes definir las URLs aquí
        },
    };

    // ==========================================
    // 2. FUNCIONES AUXILIARES
    // ==========================================

    function mostrarMensaje(mensaje, tipo = 'info', contenedor = null) {
        const target = contenedor || document.querySelector(CONFIG.selectores.contenedorRespuesta);
        if (target) {
            const iconos = { error: '❌', exito: '✅', info: '📌', warning: '⚠️' };
            target.innerHTML = `
                <h3>${iconos[tipo] || '📌'} ${tipo.charAt(0).toUpperCase() + tipo.slice(1)}</h3>
                <p>${mensaje}</p>
            `;
            target.style.display = 'block';
        } else {
            // Fallback: mostrar en flash si existe
            const flash = document.querySelector(CONFIG.selectores.contenedorFlash);
            if (flash) {
                const div = document.createElement('div');
                div.className = `flash ${tipo}`;
                div.textContent = mensaje;
                flash.appendChild(div);
                setTimeout(() => div.remove(), 5000);
            } else {
                // Último recurso: alert
                alert(mensaje);
            }
        }
    }

    function toggleBoton(boton, estado, textoAlternativo = null) {
        if (!boton) return;
        if (estado) {
            boton.disabled = true;
            boton.dataset.textoOriginal = boton.dataset.textoOriginal || boton.textContent;
            boton.textContent = textoAlternativo || CONFIG.mensajes.cargando;
            boton.classList.add(CONFIG.selectores.claseCargando);
        } else {
            boton.disabled = false;
            boton.textContent = boton.dataset.textoOriginal || boton.textContent;
            boton.classList.remove(CONFIG.selectores.claseCargando);
        }
    }

    function validarCampos(formulario) {
        const campos = formulario.querySelectorAll(CONFIG.selectores.camposTexto);
        let valido = true;
        campos.forEach((campo) => {
            campo.classList.remove(CONFIG.selectores.campoError);
            if (campo.hasAttribute('required') && campo.value.trim() === '') {
                campo.classList.add(CONFIG.selectores.campoError);
                valido = false;
            }
            // Validación de email
            if (campo.type === 'email' && campo.value.trim() !== '') {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(campo.value.trim())) {
                    campo.classList.add(CONFIG.selectores.campoError);
                    valido = false;
                }
            }
            // Validación de número
            if (campo.type === 'number' && campo.value.trim() !== '') {
                if (isNaN(parseFloat(campo.value))) {
                    campo.classList.add(CONFIG.selectores.campoError);
                    valido = false;
                }
            }
        });
        return valido;
    }

    function scrollUltimoMensaje(contenedor) {
        if (!contenedor) return;
        contenedor.scrollTop = contenedor.scrollHeight;
    }

    // ==========================================
    // 3. SIDEBAR TOGGLE (móvil)
    // ==========================================

    const sidebar = document.querySelector(CONFIG.selectores.sidebar);
    const toggleBtn = document.querySelector(CONFIG.selectores.sidebarToggle);
    const overlay = document.querySelector(CONFIG.selectores.sidebarOverlay);

    // Crear el toggle si no existe
    if (sidebar && !toggleBtn) {
        const btn = document.createElement('button');
        btn.className = 'sidebar-toggle';
        btn.innerHTML = '☰';
        btn.setAttribute('aria-label', 'Abrir menú');
        document.body.prepend(btn);
        // Actualizar referencia
        const newToggle = document.querySelector(CONFIG.selectores.sidebarToggle);
        if (newToggle) {
            newToggle.addEventListener('click', toggleSidebar);
        }
    } else if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', toggleSidebar);
    }

    function toggleSidebar() {
        if (!sidebar) return;
        sidebar.classList.toggle('open');
        if (overlay) overlay.classList.toggle('active');
        // Cambiar aria-label
        const btn = document.querySelector(CONFIG.selectores.sidebarToggle);
        if (btn) {
            const isOpen = sidebar.classList.contains('open');
            btn.innerHTML = isOpen ? '✕' : '☰';
            btn.setAttribute('aria-label', isOpen ? 'Cerrar menú' : 'Abrir menú');
        }
    }

    // Cerrar sidebar al hacer clic fuera en móvil
    document.addEventListener('click', function (e) {
        if (window.innerWidth <= 768) {
            if (sidebar && sidebar.classList.contains('open')) {
                const isClickInside = sidebar.contains(e.target) || (toggleBtn && toggleBtn.contains(e.target));
                if (!isClickInside) {
                    sidebar.classList.remove('open');
                    if (overlay) overlay.classList.remove('active');
                    const btn = document.querySelector(CONFIG.selectores.sidebarToggle);
                    if (btn) {
                        btn.innerHTML = '☰';
                        btn.setAttribute('aria-label', 'Abrir menú');
                    }
                }
            }
        }
    });

    // ==========================================
    // 4. CONFIGURACIÓN DE FORMULARIOS
    // ==========================================

    document.querySelectorAll(CONFIG.selectores.formularios).forEach((form) => {
        const boton = form.querySelector(CONFIG.selectores.botonesEnviar);
        if (boton) {
            boton.dataset.textoOriginal = boton.textContent;
        }

        form.addEventListener('submit', function (e) {
            // Limpiar mensajes previos
            const respuestas = this.querySelectorAll(CONFIG.selectores.contenedorRespuesta);
            respuestas.forEach((el) => (el.style.display = 'none'));

            if (!validarCampos(this)) {
                e.preventDefault();
                mostrarMensaje(CONFIG.mensajes.camposVacios, 'error', this.querySelector('.respuesta'));
                const primerError = this.querySelector(`.${CONFIG.selectores.campoError}`);
                if (primerError) primerError.focus();
                return;
            }

            // Deshabilitar botón y mostrar carga
            if (boton) {
                toggleBoton(boton, true);
            }

            // Si el formulario tiene el atributo data-ajax, usar fetch
            if (this.dataset.ajax === 'true') {
                e.preventDefault();
                enviarFormularioAjax(this, boton);
            }
        });

        // Restaurar botón después de un reset
        form.addEventListener('reset', function () {
            if (boton) toggleBoton(boton, false);
        });
    });

    // ==========================================
    // 5. ENVÍO AJAX (opcional)
    // ==========================================

    async function enviarFormularioAjax(form, boton) {
        const formData = new FormData(form);
        const url = form.action || window.location.href;

        try {
            const response = await fetch(url, {
                method: form.method || 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            const data = await response.json();

            if (data.success) {
                mostrarMensaje(data.message || CONFIG.mensajes.exito, 'exito', form.querySelector('.respuesta'));
                if (data.redirect) {
                    setTimeout(() => (window.location.href = data.redirect), 1500);
                }
            } else {
                mostrarMensaje(data.message || 'Error en el servidor.', 'error', form.querySelector('.respuesta'));
            }
        } catch (error) {
            console.error('Error en AJAX:', error);
            mostrarMensaje(CONFIG.mensajes.errorConexion, 'error', form.querySelector('.respuesta'));
        } finally {
            if (boton) toggleBoton(boton, false);
        }
    }

    // ==========================================
    // 6. CHAT – scroll automático y enviar con Enter
    // ==========================================

    const chatContainer = document.querySelector(CONFIG.selectores.chatMessages);
    if (chatContainer) {
        scrollUltimoMensaje(chatContainer);

        // Observador para nuevos mensajes
        const observer = new MutationObserver(() => {
            scrollUltimoMensaje(chatContainer);
        });
        observer.observe(chatContainer, { childList: true, subtree: true });
    }

    // Enviar chat con Enter (si no está ya manejado por el formulario)
    const chatInput = document.querySelector(CONFIG.selectores.chatInput);
    if (chatInput) {
        chatInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                const form = this.closest('form');
                if (form) {
                    e.preventDefault();
                    form.submit();
                }
            }
        });
    }

    // ==========================================
    // 7. CONFIRMACIÓN PARA ACCIONES DESTRUCTIVAS
    // ==========================================

    document.querySelectorAll('.btn-eliminar, .eliminar-link, a[data-confirm]').forEach((enlace) => {
        enlace.addEventListener('click', function (e) {
            const mensaje = this.dataset.confirm || CONFIG.mensajes.confirmarEliminar;
            if (!confirm(mensaje)) {
                e.preventDefault();
            }
        });
    });

    // ==========================================
    // 8. AUTO-FOCUS en primer campo de formularios visibles
    // ==========================================

    document.querySelectorAll(CONFIG.selectores.formularios).forEach((form) => {
        if (form.offsetParent !== null) {
            // visible
            const primerCampo = form.querySelector(CONFIG.selectores.camposTexto);
            if (primerCampo && !primerCampo.value) {
                primerCampo.focus();
            }
        }
    });

    // Quitar clase de error al escribir
    document.addEventListener('input', function (e) {
        if (e.target.matches(CONFIG.selectores.camposTexto)) {
            e.target.classList.remove(CONFIG.selectores.campoError);
        }
    });

    // ==========================================
    // 9. MANEJO DE ERRORES DE RED (opcional)
    // ==========================================

    window.addEventListener('error', function (e) {
        if (e.target.tagName === 'FORM') {
            console.warn('Error en envío de formulario:', e);
            // Si el formulario no tiene AJAX, no podemos prevenir el envío.
        }
    }, true);

    // ==========================================
    // 10. DETECCIÓN DE MODO OSCURO (preferencia del sistema)
    // ==========================================

    function detectarModoOscuro() {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const currentTheme = document.documentElement.getAttribute('data-theme');
        // Si no se ha forzado un tema manualmente, usar el del sistema
        if (!currentTheme || currentTheme === 'auto') {
            document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
        }
    }

    detectarModoOscuro();

    // Escuchar cambios en la preferencia del sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        if (!currentTheme || currentTheme === 'auto') {
            document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
        }
    });

    // ==========================================
    // 11. FUNCIÓN PARA COPIAR TEXTO AL PORTAPAPELES
    // ==========================================

    document.querySelectorAll('[data-copy]').forEach((elemento) => {
        elemento.addEventListener('click', function () {
            const texto = this.dataset.copy;
            navigator.clipboard
                .writeText(texto)
                .then(() => {
                    mostrarMensaje('✅ Texto copiado al portapapeles.', 'exito');
                })
                .catch(() => {
                    // Fallback
                    const input = document.createElement('input');
                    input.value = texto;
                    document.body.appendChild(input);
                    input.select();
                    document.execCommand('copy');
                    input.remove();
                    mostrarMensaje('✅ Texto copiado al portapapeles.', 'exito');
                });
        });
    });

    // Autocompletar comandos rápidos (para cualquier .ejemplo-tag)
    document.querySelectorAll('.ejemplo-tag').forEach(tag => {
        tag.addEventListener('click', function() {
            const input = document.querySelector('input[name="pregunta"]');
            if (input) {
                input.value = this.textContent.trim();
                input.focus();
                // Opcional: enviar automáticamente después de 300ms
                // setTimeout(() => input.closest('form').submit(), 300);
            }
        });
    });

    console.log('✅ Sistema listo. Todos los componentes configurados.');
});
