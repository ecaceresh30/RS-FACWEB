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

  let rucActual = null;

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${role}`;
    bubble.textContent = text;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return bubble;
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
    enviarMensaje(chatInput.value.trim());
  });

  resetButton.addEventListener("click", async () => {
    if (!rucActual) return;
    const confirmado = window.confirm(
      "Esto elimina todo tu historial de conversaciones y no se puede deshacer. ¿Continuar?"
    );
    if (!confirmado) return;

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
