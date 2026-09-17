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

  let rucActual = null;

  function addBubble(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${role}`;
    bubble.textContent = text;
    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function setLoading(form, loading) {
    const button = form.querySelector("button");
    button.disabled = loading;
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

  async function chat(ruc, mensaje) {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ruc, mensaje }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "No se pudo procesar el mensaje.");
    }
    return data;
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

  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const mensaje = chatInput.value.trim();
    if (!mensaje || !rucActual) return;

    addBubble("user", mensaje);
    chatInput.value = "";
    setLoading(chatForm, true);

    try {
      const data = await chat(rucActual, mensaje);
      (data.avisos || []).forEach((aviso) => addBubble("system", `Aviso: ${aviso}`));
      addBubble("assistant", data.respuesta);
    } catch (err) {
      addBubble("system", err.message);
    } finally {
      setLoading(chatForm, false);
      chatInput.focus();
    }
  });
})();
