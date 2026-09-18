(() => {
  const loginView = document.getElementById("login-view");
  const chatView = document.getElementById("chat-view");
  const loginForm = document.getElementById("login-form");
  const rucInput = document.getElementById("ruc-input");
  const loginError = document.getElementById("login-error");
  const empresaBadge = document.getElementById("empresa-badge");
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const resetButton = document.getElementById("reset-button");
  const confirmModal = document.getElementById("confirm-modal");
  const confirmModalCancel = document.getElementById("confirm-modal-cancel");
  const confirmModalAccept = document.getElementById("confirm-modal-accept");

  let rucActual = null;

  const ACCIONES_TEXTO = [
    "Puedo ayudarte con:",
    "",
    "- Base de conocimiento interna: preguntas sobre comprobantes electrónicos y el SIRE (SUNAT).",
    '- Consulta de RUC (OpenRuc): escribe "busca el ruc" + 11 dígitos.',
    '- Búsqueda en internet (Tavily): escribe "busca en internet" + tu consulta.',
    '- Cartera de cuentas por cobrar: escribe algo con la palabra "cartera" para ver el estado de tu cartera. Si además quieres recomendaciones de factoring/financiamiento, pídelas explícitamente (ej. "qué me recomiendas", "me conviene el factoring").',
    "",
    "Comandos: /limpiar (borra el chat en pantalla), /acciones (esta lista), /preguntas (preguntas de ejemplo).",
  ].join("\n");

  const PREGUNTAS_EJEMPLO = [
    "¿Cuáles son los requisitos para el certificado digital del emisor?",
    "busca el ruc 20131312955",
    "¿Cómo está mi cartera de cobranza?",
    "busca en internet las últimas noticias de la SUNAT",
  ];

  // Comandos locales: se resuelven en el navegador, sin llamar a /api/chat (sin
  // costo de LLM, y "/limpiar" no toca el historial guardado en Supabase).
  function manejarComando(mensaje) {
    const comando = mensaje.toLowerCase();
    if (comando === "/limpiar") {
      chatMessages.innerHTML = "";
      return true;
    }
    if (comando === "/acciones") {
      addBubble("user", mensaje);
      addBubble("assistant", ACCIONES_TEXTO);
      return true;
    }
    if (comando === "/preguntas") {
      addBubble("user", mensaje);
      addSugerencias(PREGUNTAS_EJEMPLO);
      return true;
    }
    return false;
  }

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${role}`;
    bubble.textContent = text;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
  }

  function formatMonto(n) {
    return Number(n).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function crearTablaCartera(caption, columnas, filas, filaTotal) {
    const table = document.createElement("table");
    table.className = "tabla-cartera";

    if (caption) {
      const captionEl = document.createElement("caption");
      captionEl.textContent = caption;
      table.appendChild(captionEl);
    }

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    columnas.forEach((col) => {
      const th = document.createElement("th");
      th.textContent = col.label;
      if (col.numerica) th.className = "num";
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    const agregarFila = (fila, esTotal) => {
      const tr = document.createElement("tr");
      if (esTotal) tr.className = "total-row";
      columnas.forEach((col) => {
        const td = document.createElement("td");
        td.textContent = fila[col.key];
        if (col.numerica) td.className = "num";
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    };
    filas.forEach((fila) => agregarFila(fila, false));
    if (filaTotal) agregarFila(filaTotal, true);
    table.appendChild(tbody);

    const wrap = document.createElement("div");
    wrap.className = "tabla-cartera-wrap";
    wrap.appendChild(table);
    return wrap;
  }

  // Tablas deterministas armadas desde los datos crudos (no le pedimos al LLM
  // que las formatee: nunca seria consistente). Solo se llama cuando el
  // backend trajo datos reales de cartera (ver app/conversation.py).
  function addTablaCartera(tabla) {
    if (!tabla) return;
    const hayTramos = tabla.tramos && tabla.tramos.length > 0;
    const hayVencidas = tabla.facturas_vencidas && tabla.facturas_vencidas.length > 0;
    if (!hayTramos && !hayVencidas) return;

    const contenedor = document.createElement("div");
    contenedor.className = "bubble assistant tabla-cartera-bubble";

    if (hayTramos) {
      contenedor.appendChild(
        crearTablaCartera(
          "Distribución por tramo de mora",
          [
            { key: "tramo", label: "Tramo" },
            { key: "cantidad", label: "Facturas", numerica: true },
            { key: "monto", label: "Monto (S/)", numerica: true },
          ],
          tabla.tramos.map((t) => ({
            tramo: t.tramo,
            cantidad: t.cantidad,
            monto: formatMonto(t.monto),
          })),
          {
            tramo: "Total",
            cantidad: tabla.total_facturas,
            monto: formatMonto(tabla.monto_total),
          }
        )
      );
    }

    if (hayVencidas) {
      contenedor.appendChild(
        crearTablaCartera(
          "Facturas más vencidas",
          [
            { key: "numero", label: "Factura" },
            { key: "cliente", label: "Cliente" },
            { key: "monto", label: "Monto (S/)", numerica: true },
            { key: "dias_vencido", label: "Días vencido", numerica: true },
          ],
          tabla.facturas_vencidas.map((f) => ({
            numero: f.numero,
            cliente: f.cliente,
            monto: formatMonto(f.monto),
            dias_vencido: f.dias_vencido,
          })),
          null
        )
      );
    }

    chatMessages.appendChild(contenedor);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function addSugerencias(preguntas) {
    if (!preguntas || preguntas.length === 0) return;

    const contenedor = document.createElement("div");
    contenedor.className = "sugerencias";
    preguntas.forEach((pregunta) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "sugerencia-chip";
      chip.textContent = pregunta;
      chip.addEventListener("click", () => {
        contenedor.remove();
        enviarMensaje(pregunta);
      });
      contenedor.appendChild(chip);
    });
    chatMessages.appendChild(contenedor);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function addFaseBubble(textoInicial) {
    const bubble = document.createElement("div");
    bubble.className = "bubble assistant fase";

    const dots = document.createElement("span");
    dots.className = "fase-dots";
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("span");
      dot.className = "fase-dot";
      dots.appendChild(dot);
    }

    const textEl = document.createElement("span");
    textEl.className = "fase-texto";
    textEl.textContent = textoInicial;

    bubble.append(dots, textEl);
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return { bubble, textEl };
  }

  function setLoading(form, loading) {
    const button = form.querySelector("button");
    button.disabled = loading;
  }

  async function resetHistorial(ruc) {
    const response = await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruc }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "No se pudo eliminar el historial.");
    }
    return data;
  }

  async function login(ruc) {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruc }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "No se pudo iniciar sesion.");
    }
    return data;
  }

  async function chat(ruc, mensaje, onFase) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruc, mensaje }),
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "No se pudo procesar el mensaje.");
    }

    // La respuesta es NDJSON (una linea JSON por evento): primero 0+ eventos
    // "fase" con la fuente que se esta consultando, y al final "resultado".
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let resultado = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lineas = buffer.split("\n");
      buffer = lineas.pop();

      for (const linea of lineas) {
        if (!linea.trim()) continue;
        const evento = JSON.parse(linea);
        if (evento.tipo === "fase") {
          onFase(evento.texto);
        } else if (evento.tipo === "error") {
          throw new Error(evento.detalle || "No se pudo procesar el mensaje.");
        } else if (evento.tipo === "resultado") {
          resultado = evento;
        }
      }
    }

    if (!resultado) {
      throw new Error("No se recibio una respuesta completa del servidor.");
    }
    return resultado;
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginError.hidden = true;
    setLoading(loginForm, true);

    try {
      const data = await login(rucInput.value.trim());
      rucActual = data.ruc;

      empresaBadge.textContent = `${data.razon_social} · RUC ${data.ruc}`;
      empresaBadge.hidden = false;

      loginView.hidden = true;
      chatView.hidden = false;

      chatMessages.innerHTML = "";
      if (data.historial.length === 0) {
        addBubble(
          "system",
          data.es_nuevo
            ? "Empresa registrada. Escribe tu primer mensaje."
            : "Continuando tu conversacion anterior."
        );
      } else {
        data.historial.forEach((m) => addBubble(m.role === "user" ? "user" : "assistant", m.content));
      }

      chatInput.focus();
    } catch (err) {
      loginError.textContent = err.message;
      loginError.hidden = false;
    } finally {
      setLoading(loginForm, false);
    }
  });

  async function enviarMensaje(mensaje) {
    if (!mensaje || !rucActual) return;

    addBubble("user", mensaje);
    chatInput.value = "";
    setLoading(chatForm, true);

    const { bubble: faseBubble, textEl: faseTexto } = addFaseBubble("Procesando...");

    try {
      const data = await chat(rucActual, mensaje, (fase) => {
        faseTexto.textContent = fase;
      });
      faseBubble.remove();
      (data.avisos || []).forEach((aviso) => addBubble("system", `Aviso: ${aviso}`));
      addBubble("assistant", data.respuesta);
      addTablaCartera(data.tabla_cartera);
      addSugerencias(data.sugerencias);
    } catch (err) {
      faseBubble.remove();
      addBubble("system", err.message);
    } finally {
      setLoading(chatForm, false);
      chatInput.focus();
    }
  }

  chatForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const mensaje = chatInput.value.trim();
    if (!mensaje) return;
    if (manejarComando(mensaje)) {
      chatInput.value = "";
      chatInput.focus();
      return;
    }
    enviarMensaje(mensaje);
  });

  function abrirModalConfirmacion() {
    confirmModal.hidden = false;
  }

  function cerrarModalConfirmacion() {
    confirmModal.hidden = true;
  }

  resetButton.addEventListener("click", () => {
    if (!rucActual) return;
    abrirModalConfirmacion();
  });

  confirmModalCancel.addEventListener("click", cerrarModalConfirmacion);

  confirmModalAccept.addEventListener("click", async () => {
    cerrarModalConfirmacion();
    resetButton.disabled = true;
    try {
      await resetHistorial(rucActual);
      chatMessages.innerHTML = "";
      addBubble("system", "Historial eliminado. Empezando de nuevo.");
    } catch (err) {
      addBubble("system", err.message);
    } finally {
      resetButton.disabled = false;
    }
  });
})();
